"""Run-once prospective gate for the corrected integrated FlyDrone controller."""
from pathlib import Path
import argparse,json
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


def run(root:Path,config_path:Path)->dict:
    spec=yaml.safe_load((root/config_path).read_text(encoding='utf-8'));output=root/spec['output'];report_path=output/'report.json'
    if spec.get('run_once') and report_path.exists():raise RuntimeError(f'Prospective report already exists: {report_path}')
    base=yaml.safe_load((root/spec['base_config']).read_text());c={**base,**spec};plant=yaml.safe_load((root/c['plant_config']).read_text());orientation=yaml.safe_load((root/c['orientation_config']).read_text())
    model=EPGDelta7Candidate(root,root/orientation['candidate_config']);pfl2=PFL2SteeringController(root,root/c['pfl2_steering_config']);advance=PFL2AdvanceController(root/c['pfl2_advance_config']);drift=TravelDirectionDriftController(root,root/c['travel_direction_drift_config'])
    cases=[(np.deg2rad(t),np.deg2rad(h)) for t in c['target_bearings_deg'] for h in c['initial_relative_headings_deg']];rows=[]
    for condition in c['conditions']:
        local={**c,'lateral_velocity_kd_per_s':float(condition['lateral_velocity_kd_per_s'])}
        for scenario in c['scenarios']:
            for index,(target,heading) in enumerate(cases):
                estimator=PositionVelocityEstimator(root/c['travel_velocity_sensor_config']) if condition['velocity_source']=='position_difference' else None
                result,_=simulate(root,local,plant,model,orientation,target,heading,condition['yaw_controller']=='proportional',False,scenario,int(scenario['seed'])+index,
                    heading_mode=condition['heading_mode'],compass_config=root/c['phase_compass_config'],controller_label=condition['name'],pfl2_controller=pfl2,pfl2_enabled=bool(condition['pfl2_enabled']),
                    drift_controller=drift,drift_enabled=bool(condition['hdelta_enabled']),velocity_estimator=estimator,advance_controller=advance,neural_advance_enabled=bool(condition['advance_enabled']))
                rows.append(result)
    frame=pd.DataFrame(rows);output.mkdir(parents=True,exist_ok=True);frame.to_csv(output/'episodes.csv',index=False)
    summary=frame.groupby('controller',as_index=False).agg(episodes=('success','size'),successes=('success','sum'),median_arrival_time_s=('arrival_time_s','median'),median_path_efficiency=('path_efficiency','median'),median_maximum_cross_track_m=('maximum_absolute_cross_track_m','median'),median_dropout_heading_error_deg=('median_dropout_heading_error_deg','median'),maximum_motor_saturation_fraction=('motor_saturation_fraction','max'))
    by_scenario=frame.groupby(['controller','scenario'],as_index=False).agg(episodes=('success','size'),successes=('success','sum'),median_arrival_time_s=('arrival_time_s','median'),median_maximum_cross_track_m=('maximum_absolute_cross_track_m','median'))
    s=summary.set_index('controller');full=s.loc['full_flywire'];conventional=s.loc['conventional_navigation'];no_hdelta=s.loc['no_hdelta'];no_pfl2=s.loc['no_pfl2'];g=c['gate']
    full_scenario_min=int(by_scenario.loc[by_scenario.controller=='full_flywire','successes'].min())
    effects={'minimum_full_scenario_successes':full_scenario_min,'success_deficit_vs_conventional':int(conventional.successes-full.successes),'arrival_time_cost_vs_conventional_s':float(full.median_arrival_time_s-conventional.median_arrival_time_s),'cross_track_cost_vs_conventional_m':float(full.median_maximum_cross_track_m-conventional.median_maximum_cross_track_m),'success_advantage_over_no_hdelta':int(full.successes-no_hdelta.successes),'success_deficit_vs_no_pfl2':int(no_pfl2.successes-full.successes)}
    criteria={'full_successes':bool(full.successes>=g['minimum_full_successes']),'each_scenario_successes':bool(full_scenario_min>=g['minimum_successes_each_scenario']),'bounded_deficit_vs_conventional':bool(effects['success_deficit_vs_conventional']<=g['maximum_success_deficit_vs_conventional']),'bounded_arrival_cost':bool(effects['arrival_time_cost_vs_conventional_s']<=g['maximum_arrival_time_cost_vs_conventional_s']),'bounded_cross_track_cost':bool(effects['cross_track_cost_vs_conventional_m']<=g['maximum_cross_track_cost_vs_conventional_m']),'hdelta_success_advantage':bool(effects['success_advantage_over_no_hdelta']>=g['minimum_success_advantage_over_no_hdelta']),'bounded_deficit_vs_no_pfl2':bool(effects['success_deficit_vs_no_pfl2']<=g['maximum_success_deficit_vs_no_pfl2']),'motor_saturation':bool(full.maximum_motor_saturation_fraction<=g['maximum_motor_saturation_fraction'])}
    report={'created_at':utc_now(),'status':'immutable_run_once_prospective_result','dataset':'FAFB','materialization_version':783,'claim':'Prospective integrated gate after a frozen corrective development cycle; sensor window and output mappings are engineering choices.','configuration':config_path.as_posix(),'configuration_sha256':file_hash(root/config_path),'source_sha256':file_hash(Path(__file__)),'velocity_sensor_sha256':file_hash(root/'src/flydrone/simulation/travel_velocity_sensor.py'),'velocity_sensor_config_sha256':file_hash(root/c['travel_velocity_sensor_config']),'episodes':len(frame),'effects':effects,'criteria':criteria,'passes_prospective_gate':all(criteria.values()),'summary':summary.to_dict(orient='records'),'summary_by_scenario':by_scenario.to_dict(orient='records')}
    save_json(report_path,report);manifest_path=root/'data/manifest.json';manifest=json.loads(manifest_path.read_text());manifest[c['manifest_key']]={'status':'prospective_gate_completed','report':report_path.relative_to(root).as_posix(),'report_sha256':file_hash(report_path),'passed':report['passes_prospective_gate']};save_json(manifest_path,manifest);print(json.dumps(report,indent=2),flush=True);return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--config',type=Path,default=Path('configs/quadrotor_integrated_prospective.yaml'));run(Path.cwd(),parser.parse_args().config)
