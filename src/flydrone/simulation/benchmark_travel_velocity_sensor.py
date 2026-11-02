"""Development diagnostic of the non-privileged PFN/hDeltaB velocity interface."""
from pathlib import Path
import argparse,json
import numpy as np
import pandas as pd
import yaml
from flydrone.data.acquire import file_hash,save_json,utc_now
from flydrone.neural.epg_delta7 import EPGDelta7Candidate
from flydrone.neural.travel_direction_drift import TravelDirectionDriftController
from flydrone.simulation.benchmark_quadrotor import simulate
from flydrone.simulation.travel_velocity_sensor import PositionVelocityEstimator


def run(root:Path,config_path:Path)->dict:
    spec=yaml.safe_load((root/config_path).read_text(encoding='utf-8'));base=yaml.safe_load((root/spec['base_config']).read_text(encoding='utf-8'));c={**base,**spec}
    plant=yaml.safe_load((root/c['plant_config']).read_text());orientation=yaml.safe_load((root/c['orientation_config']).read_text());model=EPGDelta7Candidate(root,root/orientation['candidate_config']);drift=TravelDirectionDriftController(root,root/c['travel_direction_drift_config'])
    cases=[(np.deg2rad(t),np.deg2rad(h)) for t in c['target_bearings_deg'] for h in c['initial_relative_headings_deg']];rows=[]
    for condition in c['conditions']:
        local={**c,'lateral_velocity_kd_per_s':float(condition['lateral_velocity_kd_per_s'])}
        for scenario in c['scenarios']:
            for index,(target,heading) in enumerate(cases):
                estimator=PositionVelocityEstimator(root/c['travel_velocity_sensor_config']) if condition['velocity_source']=='position_difference' else None
                result,_=simulate(root,local,plant,model,orientation,target,heading,False,False,scenario,int(scenario['seed'])+index,heading_mode='direct',controller_label=condition['name'],drift_controller=drift,drift_enabled=bool(condition['hdelta_enabled']),velocity_estimator=estimator);rows.append(result)
    frame=pd.DataFrame(rows);output=root/c['output'];output.mkdir(parents=True,exist_ok=True);frame.to_csv(output/'episodes.csv',index=False)
    summary=frame.groupby('controller',as_index=False).agg(episodes=('success','size'),successes=('success','sum'),median_maximum_cross_track_m=('maximum_absolute_cross_track_m','median'),median_mean_cross_track_m=('mean_absolute_cross_track_m','median'),median_arrival_time_s=('arrival_time_s','median'),median_path_efficiency=('path_efficiency','median'))
    s=summary.set_index('controller');estimated=s.loc['hdelta_position_velocity'];direct=s.loc['hdelta_direct_velocity'];absent=s.loc['no_drift_compensation']
    report={'created_at':utc_now(),'dataset':'FAFB','materialization_version':783,'claim':'Development-only 6DoF sensor-interface diagnostic; position-difference velocity is an engineering abstraction, not reconstructed optic flow.','configuration':config_path.as_posix(),'configuration_sha256':file_hash(root/config_path),'source_sha256':file_hash(Path(__file__)),'episodes':len(frame),'estimated_cross_track_reduction_vs_absent_fraction':float(1-estimated.median_maximum_cross_track_m/absent.median_maximum_cross_track_m),'estimated_cross_track_cost_vs_direct_m':float(estimated.median_maximum_cross_track_m-direct.median_maximum_cross_track_m),'summary':summary.to_dict(orient='records')}
    save_json(output/'report.json',report);manifest_path=root/'data/manifest.json';manifest=json.loads(manifest_path.read_text(encoding='utf-8'));manifest[c['manifest_key']]={'status':'development_diagnostic_completed','report':(output/'report.json').relative_to(root).as_posix(),'report_sha256':file_hash(output/'report.json')};save_json(manifest_path,manifest);print(json.dumps(report,indent=2),flush=True);return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',type=Path,default=Path('configs/quadrotor_travel_sensor_development.yaml'));run(Path.cwd(),p.parse_args().config)
