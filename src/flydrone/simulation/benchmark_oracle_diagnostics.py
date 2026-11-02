"""Paired oracle experiments and complete 50 Hz PFN/hDeltaB traces."""
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


def wrap(value):return np.angle(np.exp(1j*value))


def sustained_first(mask:np.ndarray,count:int)->int|None:
    if len(mask)<count:return None
    hits=np.flatnonzero(np.convolve(mask.astype(int),np.ones(count,dtype=int),mode='valid')==count)
    return None if not len(hits) else int(hits[0])


def trace_metrics(trace:dict,scenario:dict,c:dict)->dict:
    frame=pd.DataFrame(trace['values'],columns=trace['columns']);true_speed=np.asarray(np.hypot(frame.vx_m_s,frame.vy_m_s));estimated_speed=np.asarray(np.hypot(frame.estimated_vx_m_s,frame.estimated_vy_m_s));moving=true_speed>.05
    decoded_error=np.asarray(np.abs(wrap(frame.decoded_travel_direction_rad-frame.true_travel_direction_rad)));velocity_direction=np.arctan2(frame.estimated_vy_m_s,frame.estimated_vx_m_s);true_direction=np.arctan2(frame.vy_m_s,frame.vx_m_s)
    velocity_direction_error=np.asarray(np.abs(wrap(velocity_direction-true_direction)));ego_error=np.asarray(np.abs(wrap(frame.estimated_egocentric_motion_rad-frame.true_egocentric_motion_rad)));relative_speed_error=np.abs(estimated_speed-true_speed)/np.maximum(true_speed,.05)
    input_speed=np.asarray(frame.drift_input_speed_m_s);input_direction=np.arctan2(frame.drift_input_vy_m_s,frame.drift_input_vx_m_s)
    input_velocity_direction_error=np.asarray(np.abs(wrap(input_direction-true_direction)));input_speed_error=np.abs(input_speed-true_speed)/np.maximum(true_speed,.05)
    input_ego_error=np.asarray(np.abs(wrap(frame.drift_input_egocentric_motion_rad-frame.true_egocentric_motion_rad)));input_heading_error=np.asarray(np.abs(wrap(frame.drift_input_heading_rad-frame.yaw_rad)))
    dt=float(c['neural_update_period_s']);count=max(1,round(float(c['sustained_duration_s'])/dt));valid=np.asarray(moving&np.isfinite(decoded_error));divergence=sustained_first((decoded_error>np.deg2rad(c['divergence_threshold_deg']))&valid,count)
    first_divergence_s=None if divergence is None else float(frame.time_s.iloc[divergence]);loss_start=float(scenario['velocity_dropout_start_s']);loss_end=float(scenario['velocity_dropout_end_s'])
    if first_divergence_s is None:classification='no_sustained_divergence'
    elif first_divergence_s<loss_start:classification='normal_before_loss'
    elif first_divergence_s<loss_end:classification='during_loss'
    elif first_divergence_s<loss_end+2.:classification='during_recovery'
    else:classification='later_normal_flight'
    post=np.flatnonzero(frame.time_s.to_numpy()>=loss_end);recovery_s=None
    if len(post):
        recovered=sustained_first((decoded_error[post]<np.deg2rad(c['recovery_threshold_deg']))&valid[post],count)
        if recovered is not None:recovery_s=float(frame.time_s.iloc[post[recovered]]-loss_end)
    select=lambda values:None if not np.any(valid) else float(np.rad2deg(np.nanmedian(np.asarray(values)[valid])))
    return {'median_decoded_direction_error_deg':select(decoded_error),'median_sensor_velocity_direction_error_deg':select(velocity_direction_error),'median_sensor_egocentric_error_deg':select(ego_error),'median_sensor_relative_speed_error':None if not np.any(valid) else float(np.nanmedian(relative_speed_error[valid])),'median_drift_input_velocity_direction_error_deg':select(input_velocity_direction_error),'median_drift_input_egocentric_error_deg':select(input_ego_error),'median_drift_input_heading_error_deg':select(input_heading_error),'median_drift_input_relative_speed_error':None if not np.any(valid) else float(np.nanmedian(input_speed_error[valid])),'first_divergence_s':first_divergence_s,'divergence_class':classification,'recovery_time_s':recovery_s}


def run(root:Path,config_path:Path=Path('configs/quadrotor_oracle_diagnostics.yaml'))->dict:
    spec=yaml.safe_load((root/config_path).read_text());base=yaml.safe_load((root/spec['base_config']).read_text());c={**base,**spec};plant=yaml.safe_load((root/c['plant_config']).read_text());orientation=yaml.safe_load((root/c['orientation_config']).read_text());model=EPGDelta7Candidate(root,root/orientation['candidate_config']);pfl2=PFL2SteeringController(root,root/c['pfl2_steering_config']);advance=PFL2AdvanceController(root/c['pfl2_advance_config']);drift=TravelDirectionDriftController(root,root/c['travel_direction_drift_config']);output=root/c['output'];trace_dir=output/'traces';trace_dir.mkdir(parents=True,exist_ok=True)
    cases=[(np.deg2rad(t),np.deg2rad(h)) for t in c['target_bearings_deg'] for h in c['initial_relative_headings_deg']];rows=[]
    for condition in c['conditions']:
        local={**c,'lateral_velocity_kd_per_s':0.0}
        for scenario in c['scenarios']:
            for index,(target,heading) in enumerate(cases):
                estimator=PositionVelocityEstimator(root/c['travel_velocity_sensor_config']);result,trace=simulate(root,local,plant,model,orientation,target,heading,False,True,scenario,int(scenario['seed'])+index,heading_mode='neural_compass',compass_config=root/c['phase_compass_config'],controller_label=condition['name'],pfl2_controller=pfl2,pfl2_enabled=False,drift_controller=drift,drift_enabled=True,velocity_estimator=estimator,advance_controller=advance,neural_advance_enabled=False,drift_oracle_mode=condition['oracle_mode'])
                metrics=trace_metrics(trace,scenario,c);row={**result,**metrics};rows.append(row);np.savez_compressed(trace_dir/f"{condition['name']}__{scenario['name']}__{index:02d}.npz",columns=np.asarray(trace['columns']),values=trace['values'])
    frame=pd.DataFrame(rows);output.mkdir(parents=True,exist_ok=True);frame.to_csv(output/'episodes.csv',index=False)
    summary=frame.groupby('controller',as_index=False).agg(episodes=('success','size'),successes=('success','sum'),median_decoded_direction_error_deg=('median_decoded_direction_error_deg','median'),median_sensor_velocity_direction_error_deg=('median_sensor_velocity_direction_error_deg','median'),median_sensor_egocentric_error_deg=('median_sensor_egocentric_error_deg','median'),median_sensor_relative_speed_error=('median_sensor_relative_speed_error','median'),median_drift_input_velocity_direction_error_deg=('median_drift_input_velocity_direction_error_deg','median'),median_drift_input_egocentric_error_deg=('median_drift_input_egocentric_error_deg','median'),median_drift_input_heading_error_deg=('median_drift_input_heading_error_deg','median'),median_drift_input_relative_speed_error=('median_drift_input_relative_speed_error','median'),median_recovery_time_s=('recovery_time_s','median'),median_arrival_time_s=('arrival_time_s','median'),median_maximum_cross_track_m=('maximum_absolute_cross_track_m','median'))
    failures=frame.loc[~frame.success].groupby(['controller','divergence_class']).size().reset_index(name='failures')
    report={'created_at':utc_now(),'status':'development_oracle_diagnostic','dataset':'FAFB','materialization_version':783,'claim':'Oracle inputs are privileged simulator truth used only for causal diagnosis; not a controller result. PFL2 disabled.','configuration':config_path.as_posix(),'configuration_sha256':file_hash(root/config_path),'source_sha256':file_hash(Path(__file__)),'episodes':len(frame),'trace_rate_hz':1/float(c['neural_update_period_s']),'summary':summary.to_dict(orient='records'),'failure_classification':failures.to_dict(orient='records')}
    save_json(output/'report.json',report);manifest_path=root/'data/manifest.json';manifest=json.loads(manifest_path.read_text());manifest[c['manifest_key']]={'status':'development_oracle_diagnostic_completed','report':(output/'report.json').relative_to(root).as_posix(),'report_sha256':file_hash(output/'report.json'),'episodes':len(frame)};save_json(manifest_path,manifest);print(json.dumps(report,indent=2),flush=True);return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--config',type=Path,default=Path('configs/quadrotor_oracle_diagnostics.yaml'));run(Path.cwd(),parser.parse_args().config)
