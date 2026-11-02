"""Run-once prospective gate for the non-privileged PFN/hDeltaB velocity interface."""
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
    c=yaml.safe_load((root/config_path).read_text(encoding='utf-8'));output=root/c['output'];report_path=output/'report.json'
    if c.get('run_once') and report_path.exists():raise RuntimeError(f'Prospective report already exists: {report_path}')
    base=yaml.safe_load((root/c['base_config']).read_text());c={**base,**c};plant=yaml.safe_load((root/c['plant_config']).read_text());orientation=yaml.safe_load((root/c['orientation_config']).read_text());model=EPGDelta7Candidate(root,root/orientation['candidate_config']);drift=TravelDirectionDriftController(root,root/c['travel_direction_drift_config'])
    cases=[(np.deg2rad(t),np.deg2rad(h)) for t in c['target_bearings_deg'] for h in c['initial_relative_headings_deg']];rows=[]
    for condition in c['conditions']:
        local={**c,'lateral_velocity_kd_per_s':float(condition['lateral_velocity_kd_per_s'])}
        for scenario in c['scenarios']:
            for index,(target,heading) in enumerate(cases):
                estimator=PositionVelocityEstimator(root/c['travel_velocity_sensor_config']) if condition['velocity_source']=='position_difference' else None
                result,_=simulate(root,local,plant,model,orientation,target,heading,False,False,scenario,int(scenario['seed'])+index,heading_mode='direct',controller_label=condition['name'],drift_controller=drift,drift_enabled=bool(condition['hdelta_enabled']),velocity_estimator=estimator);rows.append(result)
    frame=pd.DataFrame(rows);output.mkdir(parents=True,exist_ok=True);frame.to_csv(output/'episodes.csv',index=False)
    summary=frame.groupby('controller',as_index=False).agg(episodes=('success','size'),successes=('success','sum'),median_maximum_cross_track_m=('maximum_absolute_cross_track_m','median'),median_mean_cross_track_m=('mean_absolute_cross_track_m','median'),median_arrival_time_s=('arrival_time_s','median'),median_path_efficiency=('path_efficiency','median'),maximum_motor_saturation_fraction=('motor_saturation_fraction','max'))
    s=summary.set_index('controller');e=s.loc['hdelta_position_velocity'];d=s.loc['hdelta_direct_velocity'];a=s.loc['no_drift_compensation'];g=c['gate'];dropout=int(frame.loc[(frame.controller=='hdelta_position_velocity')&(frame.scenario=='heldout_long_velocity_dropout'),'success'].sum())
    effects={'success_advantage_over_absent':int(e.successes-a.successes),'success_deficit_vs_direct':int(d.successes-e.successes),'cross_track_reduction_vs_absent_fraction':float(1-e.median_maximum_cross_track_m/a.median_maximum_cross_track_m),'cross_track_cost_vs_direct_m':float(e.median_maximum_cross_track_m-d.median_maximum_cross_track_m),'dropout_scenario_successes':dropout}
    criteria={'estimated_successes':bool(e.successes>=g['minimum_estimated_successes']),'success_advantage':bool(effects['success_advantage_over_absent']>=g['minimum_success_advantage_over_absent']),'reduction_vs_absent':bool(effects['cross_track_reduction_vs_absent_fraction']>=g['minimum_cross_track_reduction_vs_absent_fraction']),'bounded_cost_vs_direct':bool(effects['cross_track_cost_vs_direct_m']<=g['maximum_cross_track_cost_vs_direct_m']),'bounded_success_deficit':bool(effects['success_deficit_vs_direct']<=g['maximum_success_deficit_vs_direct']),'dropout_successes':bool(dropout>=g['minimum_dropout_scenario_successes']),'motor_saturation':bool(e.maximum_motor_saturation_fraction<=g['maximum_motor_saturation_fraction'])}
    report={'created_at':utc_now(),'status':'immutable_run_once_prospective_result','dataset':'FAFB','materialization_version':783,'claim':'Prospective 6DoF gate for position-difference velocity; engineering sensor abstraction, not reconstructed optic flow.','configuration':config_path.as_posix(),'configuration_sha256':file_hash(root/config_path),'source_sha256':file_hash(Path(__file__)),'sensor_source_sha256':file_hash(root/'src/flydrone/simulation/travel_velocity_sensor.py'),'episodes':len(frame),'effects':effects,'criteria':criteria,'passes_prospective_gate':all(criteria.values()),'summary':summary.to_dict(orient='records')}
    save_json(report_path,report);manifest_path=root/'data/manifest.json';manifest=json.loads(manifest_path.read_text(encoding='utf-8'));manifest[c['manifest_key']]={'status':'prospective_gate_completed','report':report_path.relative_to(root).as_posix(),'report_sha256':file_hash(report_path),'passed':report['passes_prospective_gate']};save_json(manifest_path,manifest);print(json.dumps(report,indent=2),flush=True);return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',type=Path,default=Path('configs/quadrotor_travel_sensor_prospective.yaml'));run(Path.cwd(),p.parse_args().config)
