"""Replay PFN/hDeltaB in shadow mode on paired conventional trajectories."""
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
from flydrone.simulation.travel_velocity_sensor import PositionVelocityEstimator


def run(root:Path,config_path:Path=Path('configs/quadrotor_open_loop_replay.yaml'))->dict:
    spec=yaml.safe_load((root/config_path).read_text(encoding='utf-8'));base=yaml.safe_load((root/spec['base_config']).read_text(encoding='utf-8'));c={**base,**spec}
    plant=yaml.safe_load((root/c['plant_config']).read_text(encoding='utf-8'));orientation=yaml.safe_load((root/c['orientation_config']).read_text(encoding='utf-8'))
    model=EPGDelta7Candidate(root,root/orientation['candidate_config']);drift=TravelDirectionDriftController(root,root/c['travel_direction_drift_config'])
    output=root/c['output'];trace_dir=output/'traces';trace_dir.mkdir(parents=True,exist_ok=True);rows=[];trajectories={}
    cases=[(np.deg2rad(t),np.deg2rad(h)) for t in c['target_bearings_deg'] for h in c['initial_relative_headings_deg']]
    for condition in c['conditions']:
        local={**c,'lateral_velocity_kd_per_s':2.0}
        for scenario in c['scenarios']:
            for index,(target,heading) in enumerate(cases):
                estimator=PositionVelocityEstimator(root/c['travel_velocity_sensor_config'])
                result,trace=simulate(root,local,plant,model,orientation,target,heading,True,True,scenario,int(scenario['seed'])+index,
                    heading_mode='gyro_integrated',controller_label=condition['name'],drift_controller=drift,drift_enabled=True,
                    velocity_estimator=estimator,neural_advance_enabled=False,drift_oracle_mode=condition['oracle_mode'],apply_drift_correction=False)
                metrics=trace_metrics(trace,scenario,c);rows.append({**result,**metrics})
                columns=list(trace['columns']);values=trace['values'];np.savez_compressed(trace_dir/f"{condition['name']}__{scenario['name']}__{index:02d}.npz",columns=np.asarray(columns),values=values)
                xy=values[:,[columns.index('x_m'),columns.index('y_m')]];trajectories.setdefault((scenario['name'],index),[]).append(xy)
    frame=pd.DataFrame(rows);output.mkdir(parents=True,exist_ok=True);frame.to_csv(output/'episodes.csv',index=False)
    summary=frame.groupby('controller',as_index=False).agg(episodes=('success','size'),successes=('success','sum'),median_decoded_direction_error_deg=('median_decoded_direction_error_deg','median'),median_sensor_velocity_direction_error_deg=('median_sensor_velocity_direction_error_deg','median'),median_drift_input_velocity_direction_error_deg=('median_drift_input_velocity_direction_error_deg','median'),median_drift_input_egocentric_error_deg=('median_drift_input_egocentric_error_deg','median'),median_recovery_time_s=('recovery_time_s','median'),median_arrival_time_s=('arrival_time_s','median'),median_maximum_cross_track_m=('maximum_absolute_cross_track_m','median'))
    maximum_trajectory_spread=max(float(np.max(np.linalg.norm(stack-stack[0],axis=2))) for stack in (np.stack(group) for group in trajectories.values()))
    failures=frame.loc[frame.first_divergence_s.notna()].groupby(['controller','divergence_class']).size().reset_index(name='episodes_with_divergence')
    report={'created_at':utc_now(),'status':'development_open_loop_replay_completed','dataset':'FAFB','materialization_version':783,'claim':'PFN/hDeltaB was evaluated in shadow mode on conventional trajectories; its output did not affect the plant. Oracle signals are privileged simulator truth for diagnosis only.','configuration':config_path.as_posix(),'configuration_sha256':file_hash(root/config_path),'source_sha256':file_hash(Path(__file__)),'episodes':len(frame),'trace_rate_hz':1/float(c['neural_update_period_s']),'maximum_paired_trajectory_spread_m':maximum_trajectory_spread,'summary':summary.to_dict(orient='records'),'divergence_classification':failures.to_dict(orient='records')}
    save_json(output/'report.json',report);manifest_path=root/'data/manifest.json';manifest=json.loads(manifest_path.read_text(encoding='utf-8'));manifest[c['manifest_key']]={'status':'development_open_loop_replay_completed','report':(output/'report.json').relative_to(root).as_posix(),'report_sha256':file_hash(output/'report.json'),'episodes':len(frame)};save_json(manifest_path,manifest);print(json.dumps(report,indent=2),flush=True);return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--config',type=Path,default=Path('configs/quadrotor_open_loop_replay.yaml'));run(Path.cwd(),parser.parse_args().config)
