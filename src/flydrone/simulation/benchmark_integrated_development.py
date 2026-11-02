"""Development-only combined perturbation benchmark for the integrated controller."""
from pathlib import Path
import argparse
import json
import numpy as np
import pandas as pd
import yaml
from flydrone.data.acquire import file_hash,save_json,utc_now
from flydrone.neural.epg_delta7 import EPGDelta7Candidate
from flydrone.neural.pfl2_advance import PFL2AdvanceController
from flydrone.neural.pfl2_steering import PFL2SteeringController
from flydrone.neural.travel_direction_drift import TravelDirectionDriftController
from flydrone.simulation.benchmark_quadrotor import simulate
from flydrone.simulation.travel_velocity_sensor import PositionVelocityEstimator
from flydrone.simulation.sensor_confidence import SensorConfidenceGovernor


def run(root:Path,config_path:Path=Path('configs/quadrotor_integrated_development.yaml'))->dict:
    spec=yaml.safe_load((root/config_path).read_text(encoding='utf-8'))
    base=yaml.safe_load((root/spec['base_config']).read_text(encoding='utf-8'));c={**base,**spec}
    plant=yaml.safe_load((root/c['plant_config']).read_text());orientation=yaml.safe_load((root/c['orientation_config']).read_text())
    model=EPGDelta7Candidate(root,root/orientation['candidate_config']);pfl2=PFL2SteeringController(root,root/c['pfl2_steering_config'])
    advance=PFL2AdvanceController(root/c['pfl2_advance_config']);drift=TravelDirectionDriftController(root,root/c['travel_direction_drift_config'])
    cases=[(np.deg2rad(t),np.deg2rad(h)) for t in c['target_bearings_deg'] for h in c['initial_relative_headings_deg']];rows=[]
    for condition in c['conditions']:
        local={**c,'lateral_velocity_kd_per_s':float(condition['lateral_velocity_kd_per_s'])}
        for scenario in c['scenarios']:
            for index,(target,heading) in enumerate(cases):
                position_velocity=condition.get('velocity_source','position_difference')=='position_difference'
                estimator=PositionVelocityEstimator(root/c['travel_velocity_sensor_config']) if condition['hdelta_enabled'] and position_velocity else None
                governor=SensorConfidenceGovernor(root/c['sensor_confidence_config']) if condition.get('confidence_governor',False) else None
                compass_path=root/(c['hybrid_compass_config'] if condition['heading_mode']=='hybrid_compass' else c['phase_compass_config'])
                result,_=simulate(root,local,plant,model,orientation,target,heading,condition['yaw_controller']=='proportional',False,scenario,int(scenario['seed'])+index,
                    heading_mode=condition['heading_mode'],compass_config=compass_path,controller_label=condition['name'],
                    pfl2_controller=pfl2,pfl2_enabled=bool(condition['pfl2_enabled']),drift_controller=drift,drift_enabled=bool(condition['hdelta_enabled']),
                    velocity_estimator=estimator,advance_controller=advance,neural_advance_enabled=bool(condition['advance_enabled']),confidence_governor=governor)
                rows.append(result)
    frame=pd.DataFrame(rows);output=root/c['output'];output.mkdir(parents=True,exist_ok=True);frame.to_csv(output/'episodes.csv',index=False)
    summary=frame.groupby(['controller','scenario'],as_index=False).agg(episodes=('success','size'),successes=('success','sum'),median_arrival_time_s=('arrival_time_s','median'),median_path_efficiency=('path_efficiency','median'),median_maximum_cross_track_m=('maximum_absolute_cross_track_m','median'),median_dropout_heading_error_deg=('median_dropout_heading_error_deg','median'),maximum_motor_saturation_fraction=('motor_saturation_fraction','max'))
    overall=frame.groupby('controller',as_index=False).agg(episodes=('success','size'),successes=('success','sum'),median_arrival_time_s=('arrival_time_s','median'),median_path_efficiency=('path_efficiency','median'),median_maximum_cross_track_m=('maximum_absolute_cross_track_m','median'),maximum_motor_saturation_fraction=('motor_saturation_fraction','max'))
    report={'created_at':utc_now(),'status':'development_result','dataset':'FAFB','materialization_version':783,'claim':'Combined development audit only; cases may inform prospective design and are not confirmatory.','configuration':config_path.as_posix(),'configuration_sha256':file_hash(root/config_path),'source_sha256':file_hash(Path(__file__)),'episodes':len(frame),'summary_by_scenario':summary.to_dict(orient='records'),'overall':overall.to_dict(orient='records')}
    save_json(output/'report.json',report);manifest_path=root/'data/manifest.json';manifest=json.loads(manifest_path.read_text());manifest[c['manifest_key']]={'status':'development_completed','report':(output/'report.json').relative_to(root).as_posix(),'report_sha256':file_hash(output/'report.json'),'episodes':len(frame)};save_json(manifest_path,manifest);print(json.dumps(report,indent=2),flush=True);return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--config',type=Path,default=Path('configs/quadrotor_integrated_development.yaml'))
    run(Path.cwd(),parser.parse_args().config)
