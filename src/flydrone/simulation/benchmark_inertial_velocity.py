"""Development comparison of position-only and inertial velocity inputs."""
from pathlib import Path
import argparse,json
import numpy as np
import pandas as pd
import yaml
from flydrone.data.acquire import file_hash,save_json,utc_now
from flydrone.neural.epg_delta7 import EPGDelta7Candidate
from flydrone.neural.travel_direction_drift import TravelDirectionDriftController
from flydrone.simulation.benchmark_oracle_diagnostics import trace_metrics
from flydrone.simulation.benchmark_quadrotor import simulate
from flydrone.simulation.travel_velocity_sensor import PositionVelocityEstimator,InertialPositionVelocityEstimator


def run(root:Path,config_path:Path=Path('configs/quadrotor_inertial_velocity_development.yaml'))->dict:
    spec=yaml.safe_load((root/config_path).read_text(encoding='utf-8'));base=yaml.safe_load((root/spec['base_config']).read_text(encoding='utf-8'));c={**base,**spec};plant=yaml.safe_load((root/c['plant_config']).read_text());orientation=yaml.safe_load((root/c['orientation_config']).read_text())
    model=EPGDelta7Candidate(root,root/orientation['candidate_config']);output=root/c['output'];trace_dir=output/'traces';trace_dir.mkdir(parents=True,exist_ok=True);rows=[];null_metadata=[]
    cases=[(np.deg2rad(t),np.deg2rad(h)) for t in c['target_bearings_deg'] for h in c['initial_relative_headings_deg']]
    for condition in c['conditions']:
        drift=TravelDirectionDriftController(root,root/c['travel_direction_drift_config'],phase_shuffle_seed=condition.get('phase_shuffle_seed'),weight_rewire_seed=condition.get('weight_rewire_seed'),block_weight_rewire_seed=condition.get('block_weight_rewire_seed'))
        null_metadata.append({'condition':condition['name'],**drift.null_metadata})
        local={**c,'lateral_velocity_kd_per_s':float(condition['lateral_velocity_kd_per_s'])}
        for scenario in c['scenarios']:
            for index,(target,heading) in enumerate(cases):
                enabled=bool(condition['hdelta_enabled']);source=condition['velocity_source'];estimator=InertialPositionVelocityEstimator(root/c['travel_velocity_inertial_config']) if source=='inertial_fusion' else (PositionVelocityEstimator(root/c['travel_velocity_sensor_config']) if source=='position_difference' else None)
                result,trace=simulate(root,local,plant,model,orientation,target,heading,condition['yaw_controller']=='proportional',enabled,scenario,int(scenario['seed'])+index,circuit_condition=condition.get('circuit_condition','intact'),heading_mode=condition['heading_mode'],compass_config=root/c['phase_compass_config'],controller_label=condition['name'],pfl2_enabled=False,drift_controller=drift,drift_enabled=enabled,velocity_estimator=estimator,neural_advance_enabled=False,drift_readout_mode=condition.get('drift_readout_mode','connectome'))
                row={**result,'connectome_null_mode':drift.null_metadata['mode'],'connectome_null_seed':drift.null_metadata['seed']}
                if enabled:row.update(trace_metrics(trace,scenario,c));np.savez_compressed(trace_dir/f"{condition['name']}__{scenario['name']}__{index:02d}.npz",columns=np.asarray(trace['columns']),values=trace['values'])
                rows.append(row)
    frame=pd.DataFrame(rows);output.mkdir(parents=True,exist_ok=True);frame.to_csv(output/'episodes.csv',index=False)
    summary=frame.groupby('controller',as_index=False).agg(episodes=('success','size'),successes=('success','sum'),median_arrival_time_s=('arrival_time_s','median'),median_path_efficiency=('path_efficiency','median'),median_maximum_cross_track_m=('maximum_absolute_cross_track_m','median'),median_decoded_direction_error_deg=('median_decoded_direction_error_deg','median'),median_sensor_velocity_direction_error_deg=('median_sensor_velocity_direction_error_deg','median'),median_sensor_relative_speed_error=('median_sensor_relative_speed_error','median'),median_recovery_time_s=('recovery_time_s','median'),maximum_motor_saturation_fraction=('motor_saturation_fraction','max'))
    by_scenario=frame.groupby(['controller','scenario'],as_index=False).agg(episodes=('success','size'),successes=('success','sum'),median_arrival_time_s=('arrival_time_s','median'),median_maximum_cross_track_m=('maximum_absolute_cross_track_m','median'))
    report={'created_at':utc_now(),'status':'development_inertial_velocity_candidate','dataset':'FAFB','materialization_version':783,'claim':'Engineering inertial velocity fusion diagnostic; simulated acceleration is a noisy sensor derived from plant motion, not a biological input or privileged controller oracle. PFL2 and graded confidence are disabled. Any direct_velocity condition replaces the PFN/hDeltaB readout with the same lateral rule applied directly to the same estimated velocity. Degree-preserving nulls preserve binary PFN-to-hDeltaB row and column degrees and every postsynaptic row weight multiset, then receive the same global phase calibration as the intact model.','configuration':config_path.as_posix(),'configuration_sha256':file_hash(root/config_path),'source_sha256':file_hash(Path(__file__)),'estimator_source_sha256':file_hash(root/'src/flydrone/simulation/travel_velocity_sensor.py'),'episodes':len(frame),'connectome_nulls':null_metadata,'summary':summary.astype(object).where(pd.notna(summary),None).to_dict(orient='records'),'summary_by_scenario':by_scenario.astype(object).where(pd.notna(by_scenario),None).to_dict(orient='records')}
    save_json(output/'report.json',report);manifest_path=root/'data/manifest.json';manifest=json.loads(manifest_path.read_text());manifest[c['manifest_key']]={'status':'development_inertial_velocity_candidate_completed','report':(output/'report.json').relative_to(root).as_posix(),'report_sha256':file_hash(output/'report.json'),'episodes':len(frame)};save_json(manifest_path,manifest);print(json.dumps(report,indent=2),flush=True);return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--config',type=Path,default=Path('configs/quadrotor_inertial_velocity_development.yaml'));run(Path.cwd(),parser.parse_args().config)
