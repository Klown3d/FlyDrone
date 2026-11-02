"""First 6-DoF waypoint benchmark with neural yaw and conventional inner loop."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import yaml
from flydrone.data.acquire import file_hash,save_json,utc_now
from flydrone.neural.epg_delta7 import EPGDelta7Candidate
from flydrone.neural.phase_compass_estimator import PhaseCompassEstimator,HybridCompassEstimator
from flydrone.neural.orientation_closed_loop import wrap
from flydrone.neural.steering_interface import command
from flydrone.neural.travel_direction_drift import direct_velocity_correction
from flydrone.simulation.navigation import NavigationState,held_goal_bearing
from flydrone.simulation.obstacles import CircleObstacle,ObstaclePlanner,point_clearance
from flydrone.simulation.quadrotor_arrival import QuadrotorArrivalSupervisor
from flydrone.simulation.quadrotor import (QuadrotorState,acceleration_attitude_controller,
    euler_to_quaternion,quaternion_to_rotation,step,yaw_from_quaternion)
from flydrone.simulation.yaw_pid import from_config as yaw_pid_from_config


def simulate(root: Path,c: dict,plant: dict,model: EPGDelta7Candidate,orientation: dict,
             target_bearing: float,relative_heading: float,baseline: bool,trace: bool=False,
             scenario: dict|None=None,seed: int=0,circuit_variant: dict|None=None,
             circuit_condition: str='intact',yaw_controller: str|None=None,
             pid_config: dict|None=None,heading_mode: str='direct',
             compass_config: Path=Path('configs/phase_compass_dynamics_v2.yaml'),
             controller_label: str|None=None,pfl2_controller=None,
             pfl2_enabled: bool=True,drift_controller=None,
             drift_enabled: bool=True,velocity_estimator=None,
             advance_controller=None,neural_advance_enabled: bool=True,
             confidence_governor=None,drift_oracle_mode:str='none',
             apply_drift_correction:bool=True,drift_confidence_governor=None,
             drift_readout_mode:str='connectome') -> tuple[dict,dict|None]:
    scenario={} if scenario is None else scenario;rng=np.random.default_rng(seed);imu_rng=np.random.default_rng(seed+104729)
    yaw_controller=('proportional' if baseline else 'neural') if yaw_controller is None else yaw_controller
    if yaw_controller not in {'neural','proportional','pid'}:raise ValueError(f'Unknown yaw controller: {yaw_controller}')
    if heading_mode not in {'direct','sample_hold','gyro_integrated','neural_compass','hybrid_compass'}:raise ValueError(f'Unknown heading mode: {heading_mode}')
    oracle_modes={'none','true_heading','true_velocity','true_heading_velocity','true_egocentric','true_direction_readout'}
    if drift_oracle_mode not in oracle_modes:raise ValueError(f'Unknown drift oracle mode: {drift_oracle_mode}')
    if drift_readout_mode not in {'connectome','direct_velocity'}:raise ValueError(f'Unknown drift readout mode: {drift_readout_mode}')
    pid=None
    if yaw_controller=='pid':
        if pid_config is None:raise ValueError('pid_config is required for the PID yaw controller')
        pid=yaw_pid_from_config(pid_config)
    dt=float(plant['dt_s']);steps=round(c['duration_s']/dt);control_stride=round(c['neural_update_period_s']/dt)
    target=np.array([c['target_distance_m']*np.cos(target_bearing),c['target_distance_m']*np.sin(target_bearing),c['target_altitude_m']])
    arrival_config=c.get('arrival_supervisor',{});arrival_supervisor=QuadrotorArrivalSupervisor(arrival_config,target[:2]) if arrival_config.get('enabled',False) else None
    arrival_status={'arrived':False,'filtered_distance_m':float('nan'),'estimated_speed_m_s':float('nan'),'arrival_candidate_s':0.,'departure_candidate_s':0.};arrival_latched_steps=0;drift_suppressed_steps=0;arrival_hold_correction=np.zeros(2);arrival_hold_history=[]
    obstacles=[];planner=None;minimum_clearance=float('inf')
    if 'obstacle_radius_m' in scenario:
        center=target[:2]*float(scenario.get('obstacle_distance_fraction',.5));obstacles=[CircleObstacle(center,float(scenario['obstacle_radius_m']))]
        if scenario.get('planner_enabled',False):
            planner=ObstaclePlanner(obstacles,float(scenario['vehicle_radius_m']),float(scenario['safety_margin_m']),float(scenario['waypoint_margin_m']),float(scenario.get('waypoint_acceptance_m',.25)))
    initial_heading=float(wrap(target_bearing+relative_heading));state=QuadrotorState(quaternion_wxyz=euler_to_quaternion(0,0,initial_heading))
    compass=PhaseCompassEstimator(root,compass_config,initial_heading) if heading_mode=='neural_compass' else (HybridCompassEstimator(root,compass_config,initial_heading) if heading_mode=='hybrid_compass' else None)
    estimated_heading=initial_heading;gyro_heading=initial_heading;last_resultant=1.;last_contrast=1.
    compass_neural_heading=initial_heading;compass_neural_weight=float('nan');compass_disagreement=0.
    dropout_compass_neural_weights=[]
    last_goal=target_bearing;goal_held=False;yaw_command=0.;desired_speed=0.;distance_history=[];speed_history=[];altitude_history=[]
    position_history=[state.position_m.copy()];velocity_history=[state.velocity_m_s.copy()];yaw_history=[initial_heading];rate_history=[0.];delay_steps=round(float(scenario.get('sensor_delay_s',0))/dt)
    max_tilt=0.;saturated=0;path=0.;previous=state.position_m.copy();records=[];dropout_heading_errors=[]
    current_pfl2_index=float('nan');current_pfl2_scale=1.;pfl2_indices=[];initial_yaw_command=None;current_advance_fraction=1.;advance_fractions=[];current_confidence_fraction=1.;confidence_fractions=[]
    drift_correction=np.zeros(2);decoded_travel=float('nan');travel_resultant=float('nan');lateral_drift=0.;cross_track_history=[]
    observed_position=np.zeros(3);observed_velocity=np.zeros(2);velocity_dropout=False;measurement_age_s=0.;drift_heading=initial_heading;estimated_egocentric=0.;true_egocentric=0.;true_travel_direction=initial_heading
    raw_yaw=initial_heading;yaw_rate=0.;drift_velocity=np.zeros(2);drift_input_egocentric=0.;drift_input_speed=0.;raw_drift_correction=np.zeros(2);inertial_acceleration=np.zeros(3);previous_control_true_velocity=np.zeros(3)
    drift_confidence={'confidence':1.,'raw_confidence':1.,'velocity_confidence':1.,'heading_confidence':1.,'coherence_confidence':1.,'backup_correction_m_s2':np.zeros(2)}
    drift_confidence_history=[]
    pfn_activity=np.zeros(len(drift_controller.model.pfn)) if drift_controller is not None else np.zeros(0);hdelta_activity=np.zeros(len(drift_controller.model.hdelta)) if drift_controller is not None else np.zeros(0)
    if velocity_estimator is not None:velocity_estimator.reset(state.position_m[:2])
    if confidence_governor is not None:confidence_governor.reset()
    if drift_confidence_governor is not None:drift_confidence_governor.reset()
    for i in range(steps):
        yaw=yaw_from_quaternion(state.quaternion_wxyz);distance=float(np.linalg.norm(target[:2]-state.position_m[:2]))
        if i%control_stride==0:
            past=max(0,len(position_history)-1-delay_steps);observed_position=position_history[past].copy()
            observed_position[:2]+=rng.normal(0,float(scenario.get('position_noise_std_m',0)),2)
            if arrival_supervisor is not None:arrival_status=arrival_supervisor.update(observed_position[:2],float(c['neural_update_period_s']))
            raw_yaw=float(wrap(yaw_history[past]+np.deg2rad(rng.normal(0,float(scenario.get('heading_noise_std_deg',0))))))
            yaw_rate=float(rate_history[past]+np.deg2rad(rng.normal(0,float(scenario.get('angular_rate_noise_std_deg_s',0)))))
            now=i*dt;dropout=float(scenario.get('heading_dropout_start_s',float('inf')))<=now<float(scenario.get('heading_dropout_end_s',-float('inf')))
            gyro_heading=float(wrap(gyro_heading+yaw_rate*float(c['neural_update_period_s']))) if dropout else raw_yaw
            if heading_mode=='direct':estimated_heading=raw_yaw;last_resultant=1.
            elif heading_mode=='sample_hold':
                if not dropout:estimated_heading=raw_yaw
            elif heading_mode=='gyro_integrated':
                estimated_heading=float(wrap(estimated_heading+yaw_rate*float(c['neural_update_period_s']))) if dropout else raw_yaw
            elif heading_mode in {'neural_compass','hybrid_compass'}:
                estimated_heading,last_resultant,last_contrast=compass.update(None if dropout else raw_yaw,yaw_rate,float(c['neural_update_period_s']))
                if heading_mode=='hybrid_compass':
                    compass_neural_heading=float(compass.last_neural_heading)
                    compass_neural_weight=float(compass.last_neural_weight)
                    compass_disagreement=float(compass.last_disagreement_rad)
                else:
                    compass_neural_heading=float(estimated_heading)
                    compass_neural_weight=1.0
                    compass_disagreement=float(wrap(estimated_heading-gyro_heading))
            else:
                compass_neural_heading=float('nan');compass_neural_weight=0.;compass_disagreement=float(wrap(estimated_heading-gyro_heading))
            observed_yaw=estimated_heading
            if dropout:
                dropout_heading_errors.append(abs(float(wrap(observed_yaw-yaw))))
                if np.isfinite(compass_neural_weight):dropout_compass_neural_weights.append(compass_neural_weight)
            sensed=NavigationState(x=float(observed_position[0]),y=float(observed_position[1]),heading=observed_yaw)
            local_target=target[:2] if planner is None else planner.local_goal(observed_position[:2],target[:2],observed_yaw)
            if np.allclose(local_target,target[:2]):
                last_goal,goal_held=held_goal_bearing(last_goal,goal_held,sensed,tuple(target[:2]),c['goal_hold_radius_m'],c['goal_release_radius_m'])
            else:
                last_goal=float(np.arctan2(local_target[1]-observed_position[1],local_target[0]-observed_position[0]));goal_held=False
            velocity_dropout=False
            if drift_controller is not None and drift_enabled:
                velocity_dropout=float(scenario.get('velocity_dropout_start_s',float('inf')))<=now<float(scenario.get('velocity_dropout_end_s',-float('inf')))
                measurement_age_s=measurement_age_s+float(c['neural_update_period_s']) if velocity_dropout else 0.
                true_velocity=np.asarray(state.velocity_m_s[:2],float);inertial_acceleration=(np.asarray(state.velocity_m_s,float)-previous_control_true_velocity)/float(c['neural_update_period_s']);previous_control_true_velocity=np.asarray(state.velocity_m_s,float).copy()
                if velocity_estimator is None:
                    observed_velocity=velocity_history[past][:2].copy();observed_velocity+=rng.normal(0,float(scenario.get('velocity_noise_std_m_s',0)),2)
                elif getattr(velocity_estimator,'uses_acceleration',False):
                    noise=float(scenario.get('accelerometer_noise_std_m_s2',velocity_estimator.config.get('accelerometer_noise_std_m_s2',0.)));bias=np.array([scenario.get('accelerometer_bias_x_m_s2',velocity_estimator.config.get('accelerometer_bias_x_m_s2',0.)),scenario.get('accelerometer_bias_y_m_s2',velocity_estimator.config.get('accelerometer_bias_y_m_s2',0.)),scenario.get('accelerometer_bias_z_m_s2',velocity_estimator.config.get('accelerometer_bias_z_m_s2',0.))],dtype=float);frame=velocity_estimator.config.get('accelerometer_frame','world')
                    if frame=='body_specific_force_3d':
                        true_rotation=quaternion_to_rotation(state.quaternion_wxyz);pitch=float(np.arcsin(np.clip(-true_rotation[2,0],-1.,1.)));roll=float(np.arctan2(true_rotation[2,1],true_rotation[2,2]));estimated_rotation=quaternion_to_rotation(euler_to_quaternion(roll,pitch,observed_yaw));gravity=np.array([0.,0.,-float(plant['gravity_m_s2'])]);specific_body=true_rotation.T@(inertial_acceleration-gravity);measured_acceleration=(estimated_rotation@(specific_body+bias+imu_rng.normal(0,noise,3))+gravity)[:2]
                    elif frame=='body':
                        true_rotation=np.array([[np.cos(yaw),-np.sin(yaw)],[np.sin(yaw),np.cos(yaw)]]);estimated_rotation=np.array([[np.cos(observed_yaw),-np.sin(observed_yaw)],[np.sin(observed_yaw),np.cos(observed_yaw)]]);measured_acceleration=estimated_rotation@(true_rotation.T@inertial_acceleration[:2]+bias[:2]+imu_rng.normal(0,noise,2))
                    else:measured_acceleration=inertial_acceleration[:2]+bias[:2]+imu_rng.normal(0,noise,2)
                    observed_velocity=velocity_estimator.update(None if velocity_dropout else observed_position[:2],float(c['neural_update_period_s']),measured_acceleration)
                else:
                    observed_velocity=velocity_estimator.update(None if velocity_dropout else observed_position[:2],float(c['neural_update_period_s']))
                true_speed=float(np.linalg.norm(true_velocity));estimated_speed=float(np.linalg.norm(observed_velocity))
                true_travel_direction=float(np.arctan2(true_velocity[1],true_velocity[0])) if true_speed>1e-9 else yaw
                estimated_direction=float(np.arctan2(observed_velocity[1],observed_velocity[0])) if estimated_speed>1e-9 else observed_yaw
                true_egocentric=float(wrap(true_travel_direction-yaw));estimated_egocentric=float(wrap(estimated_direction-observed_yaw))
                drift_heading=yaw if drift_oracle_mode in {'true_heading','true_heading_velocity'} else observed_yaw
                drift_velocity=true_velocity if drift_oracle_mode in {'true_velocity','true_heading_velocity'} else observed_velocity
                ego_override=true_egocentric if drift_oracle_mode=='true_egocentric' else None;speed_override=true_speed if drift_oracle_mode=='true_egocentric' else None
                drift=drift_controller.command(drift_heading,drift_velocity,last_goal,ego_override,speed_override)
                if drift_readout_mode=='direct_velocity':drift.update(direct_velocity_correction(drift_heading,drift_velocity,last_goal,drift_controller.gain,drift_controller.minimum_speed))
                if drift_oracle_mode=='true_direction_readout':
                    oracle_lateral=true_speed*np.sin(float(wrap(true_travel_direction-last_goal)));desired_lateral=np.array([-np.sin(last_goal),np.cos(last_goal)])
                    drift['decoded_direction_rad']=true_travel_direction;drift['lateral_drift_m_s']=oracle_lateral;drift['correction_world_m_s2']=-drift_controller.gain*oracle_lateral*desired_lateral
                raw_drift_correction=np.asarray(drift['correction_world_m_s2'],float);drift_correction=raw_drift_correction.copy();pfn_activity=np.asarray(drift['pfn_activity']);hdelta_activity=np.asarray(drift['hdelta_activity'])
                decoded_travel=float(drift['decoded_direction_rad']);travel_resultant=float(drift['resultant']);lateral_drift=float(drift['lateral_drift_m_s'])
                drift_input_egocentric=float(drift['egocentric_motion_rad']);drift_input_speed=true_speed if speed_override is not None else float(np.linalg.norm(drift_velocity))
                if drift_confidence_governor is not None:
                    direct_direction=float(wrap(drift_heading+drift_input_egocentric))
                    drift_correction,drift_confidence=drift_confidence_governor.update(raw_drift_correction,measurement_age_s,not velocity_dropout,drift_heading,gyro_heading,decoded_travel,direct_direction,float(c['neural_update_period_s']))
                    drift_confidence_history.append(float(drift_confidence['confidence']))
            else:
                drift_correction=np.zeros(2);raw_drift_correction=np.zeros(2);decoded_travel=float('nan');travel_resultant=float('nan');lateral_drift=0.;drift_velocity=np.zeros(2);drift_input_egocentric=0.;drift_input_speed=0.
            if yaw_controller=='pid':yaw_command=pid.update(observed_yaw,last_goal,float(c['neural_update_period_s']))
            elif pfl2_controller is not None and yaw_controller=='neural':
                yaw_command,_,_,current_pfl2_index,current_pfl2_scale,_=pfl2_controller.command(
                    model,observed_yaw,last_goal,orientation,enabled=pfl2_enabled,circuit_variant=circuit_variant)
                pfl2_indices.append(current_pfl2_index)
            else:yaw_command=float(command(model,np.array(observed_yaw),np.array(last_goal),orientation,yaw_controller=='proportional',circuit_variant)[0])
            if initial_yaw_command is None:initial_yaw_command=float(yaw_command)
            observed_distance=float(np.linalg.norm(target[:2]-observed_position[:2]));heading_error=float(wrap(observed_yaw-last_goal))
            if advance_controller is not None and neural_advance_enabled and yaw_controller=='neural' and np.isfinite(current_pfl2_index):
                desired_speed,current_advance_fraction=advance_controller.desired_speed(observed_distance,current_pfl2_index,c['maximum_forward_speed_m_s'],c['distance_gain_per_s'])
            else:
                current_advance_fraction=float(max(0.,np.cos(heading_error)));desired_speed=min(c['maximum_forward_speed_m_s'],c['distance_gain_per_s']*observed_distance)*current_advance_fraction
            if confidence_governor is not None:
                current_confidence_fraction=confidence_governor.update(last_resultant,not velocity_dropout,float(c['neural_update_period_s']));desired_speed*=current_confidence_fraction
            confidence_fractions.append(current_confidence_fraction)
            advance_fractions.append(current_advance_fraction)
            if (arrival_supervisor is not None and arrival_status['arrived']) or (arrival_supervisor is None and observed_distance<=c['arrival_radius_m']):desired_speed=0.
        forward=np.array([np.cos(yaw),np.sin(yaw)]);lateral=np.array([-np.sin(yaw),np.cos(yaw)])
        forward_speed=float(state.velocity_m_s[:2]@forward);lateral_speed=float(state.velocity_m_s[:2]@lateral)
        arrival_latched=bool(arrival_supervisor is not None and arrival_status['arrived']);arrival_latched_steps+=int(arrival_latched)
        suppress_arrival_drift=bool(arrival_latched and arrival_config.get('suppress_drift_when_arrived',True));drift_suppressed_steps+=int(suppress_arrival_drift and drift_controller is not None and drift_enabled)
        applied_drift_correction=drift_correction if apply_drift_correction and not suppress_arrival_drift else np.zeros(2)
        arrival_hold_correction=arrival_supervisor.holding_correction() if arrival_supervisor is not None else np.zeros(2)
        arrival_hold_history.append(float(np.linalg.norm(arrival_hold_correction)))
        acceleration_xy=forward*c['forward_speed_kp_per_s']*(desired_speed-forward_speed)-lateral*c['lateral_velocity_kd_per_s']*lateral_speed+applied_drift_correction+arrival_hold_correction
        acceleration_z=plant['altitude_kp_per_s2']*(target[2]-state.position_m[2])-plant['altitude_kd_per_s']*state.velocity_m_s[2]
        motors,diagnostics=acceleration_attitude_controller(state,np.r_[acceleration_xy,acceleration_z],yaw_command,plant)
        saturated+=int(np.any((motors<=1e-9)|(motors>=plant['maximum_motor_thrust_n']-1e-9)))
        wind=np.zeros(3);wind_magnitude=float(scenario.get('crosswind_force_n',0));now=i*dt
        if float(scenario.get('wind_start_s',0))<=now<float(scenario.get('wind_end_s',0)):
            wind[:2]=wind_magnitude*np.array([-np.sin(target_bearing),np.cos(target_bearing)])
        step(state,motors,plant,dt,external_force_world_n=wind);path+=float(np.linalg.norm(state.position_m[:2]-previous[:2]));previous=state.position_m.copy()
        if obstacles:minimum_clearance=min(minimum_clearance,min(point_clearance(state.position_m[:2],o,float(scenario['vehicle_radius_m'])) for o in obstacles))
        position_history.append(state.position_m.copy());velocity_history.append(state.velocity_m_s.copy());yaw_history.append(yaw_from_quaternion(state.quaternion_wxyz));rate_history.append(float(state.body_rate_rad_s[2]))
        rotation=quaternion_to_rotation(state.quaternion_wxyz);max_tilt=max(max_tilt,float(np.arccos(np.clip(rotation[2,2],-1,1))))
        distance_history.append(float(np.linalg.norm(target[:2]-state.position_m[:2])));speed_history.append(float(np.linalg.norm(state.velocity_m_s)));altitude_history.append(float(state.position_m[2]))
        cross_track_history.append(float(state.position_m[0]*-np.sin(target_bearing)+state.position_m[1]*np.cos(target_bearing)))
        if trace and i%control_stride==0:
            records.append([i*dt,*state.position_m,*state.velocity_m_s,*observed_position[:2],*observed_velocity,*inertial_acceleration,yaw,raw_yaw,yaw_rate,observed_yaw,gyro_heading,float(wrap(observed_yaw-gyro_heading)),compass_neural_heading,compass_neural_weight,compass_disagreement,last_goal,yaw_command,desired_speed,float(arrival_latched),arrival_status['filtered_distance_m'],arrival_status['estimated_speed_m_s'],float(suppress_arrival_drift),*arrival_hold_correction,last_resultant,last_contrast,float(dropout),float(not velocity_dropout),measurement_age_s,current_pfl2_index,current_pfl2_scale,*drift_velocity,drift_heading,drift_input_speed,drift_input_egocentric,decoded_travel,true_travel_direction,estimated_egocentric,true_egocentric,travel_resultant,lateral_drift,*raw_drift_correction,*drift_correction,drift_confidence['confidence'],drift_confidence['raw_confidence'],drift_confidence['velocity_confidence'],drift_confidence['heading_confidence'],drift_confidence['coherence_confidence'],*drift_confidence['backup_correction_m_s2'],*pfn_activity,*hdelta_activity,*state.motor_thrust_n])
    hold=round(c['terminal_hold_s']/dt);dist=np.asarray(distance_history);speed=np.asarray(speed_history);alt=np.asarray(altitude_history)
    stable=(dist<=c['arrival_radius_m'])&(speed<=c['stop_speed_m_s'])&(np.abs(alt-target[2])<=.1)
    stable_windows=np.convolve(stable.astype(int),np.ones(hold,dtype=int),mode='valid');stable_matches=np.flatnonzero(stable_windows==hold)
    arrival_time_s=None if not len(stable_matches) else float(stable_matches[0]*dt)
    collision=bool(minimum_clearance<0);success=bool(np.all(stable[-hold:]) and np.all(alt>0) and not collision)
    result={'scenario':scenario.get('name','ideal'),'controller':controller_label or yaw_controller,'yaw_controller':yaw_controller,'heading_mode':heading_mode,'circuit_condition':yaw_controller if yaw_controller!='neural' else circuit_condition,'target_bearing_deg':float(np.rad2deg(target_bearing)),
            'initial_relative_heading_deg':float(np.rad2deg(relative_heading)),'success':success,'final_distance_m':float(dist[-1]),
            'final_speed_m_s':float(speed[-1]),'final_altitude_m':float(alt[-1]),'path_length_m':path,
            'path_efficiency':float(c['target_distance_m']/path) if success else None,
            'normalized_terminal_progress':float(1-dist[-1]/c['target_distance_m']),'max_tilt_deg':float(np.rad2deg(max_tilt)),
            'motor_saturation_fraction':saturated/steps,'final_heading_error_deg':float(np.rad2deg(wrap(yaw_from_quaternion(state.quaternion_wxyz)-last_goal))),
            'arrival_time_s':arrival_time_s,'pfl2_enabled':bool(pfl2_controller is not None and pfl2_enabled),
            'arrival_supervisor_enabled':bool(arrival_supervisor is not None),'arrival_latched_fraction':arrival_latched_steps/steps,'drift_suppressed_at_arrival_fraction':drift_suppressed_steps/steps,
            'arrival_position_hold_enabled':bool(arrival_supervisor is not None and float(arrival_config.get('maximum_hold_acceleration_m_s2',0.))>0.),'mean_arrival_hold_acceleration_m_s2':float(np.mean(arrival_hold_history)) if arrival_hold_history else 0.,'maximum_arrival_hold_acceleration_m_s2':float(np.max(arrival_hold_history)) if arrival_hold_history else 0.,
            'initial_yaw_command_rad_s':initial_yaw_command,
            'mean_pfl2_antigoal_index':None if not pfl2_indices else float(np.mean(pfl2_indices)),
            'pfl2_advance_enabled':bool(advance_controller is not None and neural_advance_enabled and yaw_controller=='neural'),
            'mean_advance_fraction':float(np.mean(advance_fractions)) if advance_fractions else None,
            'confidence_governor_enabled':bool(confidence_governor is not None),'mean_confidence_speed_fraction':float(np.mean(confidence_fractions)) if confidence_fractions else None,
            'drift_model_enabled':bool(drift_controller is not None and drift_enabled),'drift_compensation_enabled':bool(drift_controller is not None and drift_enabled and apply_drift_correction),'drift_output_applied_to_plant':bool(apply_drift_correction),'drift_confidence_governor_enabled':bool(drift_confidence_governor is not None),'mean_drift_confidence':None if not drift_confidence_history else float(np.mean(drift_confidence_history)),'drift_oracle_mode':drift_oracle_mode,'drift_readout_mode':drift_readout_mode,
            'travel_velocity_source':str(velocity_estimator.config.get('source','engineering_velocity_estimator')) if velocity_estimator is not None else 'delayed_simulator_velocity',
            'maximum_absolute_cross_track_m':float(np.max(np.abs(cross_track_history))),
            'mean_absolute_cross_track_m':float(np.mean(np.abs(cross_track_history))),
            'final_decoded_travel_direction_deg':None if not np.isfinite(decoded_travel) else float(np.rad2deg(decoded_travel)),
            'final_travel_resultant':None if not np.isfinite(travel_resultant) else travel_resultant,
            'collision':collision,'minimum_obstacle_clearance_m':None if not obstacles else minimum_clearance,'planner_activations':0 if planner is None else planner.activations,
            'heading_dropout_duration_s':max(0.,float(scenario.get('heading_dropout_end_s',0))-float(scenario.get('heading_dropout_start_s',0))),
            'median_dropout_heading_error_deg':None if not dropout_heading_errors else float(np.rad2deg(np.median(dropout_heading_errors))),
            'maximum_dropout_heading_error_deg':None if not dropout_heading_errors else float(np.rad2deg(np.max(dropout_heading_errors))),
            'mean_compass_neural_weight_during_dropout':None if not dropout_compass_neural_weights else float(np.mean(dropout_compass_neural_weights)),
            'maximum_compass_neural_weight_during_dropout':None if not dropout_compass_neural_weights else float(np.max(dropout_compass_neural_weights)),
            'final_compass_resultant':last_resultant if heading_mode in {'neural_compass','hybrid_compass'} else None,'final_compass_contrast':last_contrast if heading_mode in {'neural_compass','hybrid_compass'} else None}
    trace_columns=['time_s','x_m','y_m','z_m','vx_m_s','vy_m_s','vz_m_s','observed_x_m','observed_y_m','estimated_vx_m_s','estimated_vy_m_s','inertial_ax_m_s2','inertial_ay_m_s2','inertial_az_m_s2','yaw_rad','raw_heading_cue_rad','observed_yaw_rate_rad_s','observed_yaw_rad','gyro_heading_rad','heading_disagreement_rad','compass_neural_heading_rad','compass_neural_weight','compass_neural_gyro_disagreement_rad','goal_rad','yaw_command_rad_s','desired_speed_m_s','arrival_latched','arrival_filtered_distance_m','arrival_estimated_speed_m_s','drift_suppressed_at_arrival','arrival_hold_correction_x_m_s2','arrival_hold_correction_y_m_s2','compass_resultant','compass_contrast','heading_dropout','position_available','position_measurement_age_s','pfl2_antigoal_index','pfl2_scale','drift_input_vx_m_s','drift_input_vy_m_s','drift_input_heading_rad','drift_input_speed_m_s','drift_input_egocentric_motion_rad','decoded_travel_direction_rad','true_travel_direction_rad','estimated_egocentric_motion_rad','true_egocentric_motion_rad','travel_resultant','lateral_drift_m_s','raw_drift_correction_x_m_s2','raw_drift_correction_y_m_s2','drift_correction_x_m_s2','drift_correction_y_m_s2','drift_confidence','drift_raw_confidence','drift_velocity_confidence','drift_heading_confidence','drift_coherence_confidence','backup_correction_x_m_s2','backup_correction_y_m_s2']+[f'pfn_activity_{i}' for i in range(len(pfn_activity))]+[f'hdelta_activity_{i}' for i in range(len(hdelta_activity))]+['motor_0_n','motor_1_n','motor_2_n','motor_3_n']
    trace_data=None if not trace else {'columns':trace_columns,'values':np.asarray(records)}
    return result,trace_data


def run(root: Path,config_path: Path=Path('configs/quadrotor_benchmark.yaml')) -> None:
    c=yaml.safe_load((root/config_path).read_text());plant=yaml.safe_load((root/c['plant_config']).read_text());orientation=yaml.safe_load((root/c['orientation_config']).read_text());model=EPGDelta7Candidate(root,root/orientation['candidate_config'])
    output=root/c['output'];output.mkdir(parents=True,exist_ok=True);rows=[];traces={}
    cases=[(np.deg2rad(t),np.deg2rad(h)) for t in c['target_bearings_deg'] for h in c['initial_relative_headings_deg']]
    for baseline in (False,True):
        for index,(target,heading) in enumerate(cases):
            result,trace=simulate(root,c,plant,model,orientation,target,heading,baseline,index==0)
            rows.append(result)
            if trace is not None:traces[result['controller']]=trace
        passed=sum(r['success'] for r in rows if r['controller']==('proportional' if baseline else 'neural'))
        print(f"{rows[-1]['controller']}: {passed}/{len(cases)}",flush=True)
    frame=pd.DataFrame(rows);frame.to_csv(output/'episodes.csv',index=False)
    summary=frame.groupby('controller').agg(episodes=('success','size'),successes=('success','sum'),success_rate=('success','mean'),median_final_distance_m=('final_distance_m','median'),median_path_efficiency=('path_efficiency','median'),maximum_tilt_deg=('max_tilt_deg','max'),maximum_motor_saturation_fraction=('motor_saturation_fraction','max')).reset_index();summary.to_csv(output/'summary.csv',index=False)
    for label,data in traces.items():np.savez_compressed(output/f'{label}-representative-trace.npz',**data)
    report={'created_at':utc_now(),'dataset':'FAFB','materialization_version':783,'episodes':len(frame),'claim':'First deterministic 6-DoF rigid-body waypoint integration; engineering airframe and conventional inner loop; neural circuit commands yaw only','configuration':config_path.as_posix(),'configuration_sha256':file_hash(root/config_path),'plant_configuration_sha256':file_hash(root/c['plant_config']),'source_sha256':file_hash(Path(__file__)),'plant_source_sha256':file_hash(root/'src/flydrone/simulation/quadrotor.py'),'summary':summary.to_dict(orient='records')}
    save_json(output/'report.json',report);manifest_path=root/'data/manifest.json';manifest=json.loads(manifest_path.read_text(encoding='utf-8'));manifest[c['manifest_key']]={'status':'first_6dof_waypoint_benchmark_completed','report':(output/'report.json').relative_to(root).as_posix(),'report_sha256':file_hash(output/'report.json'),'episodes':len(frame)};save_json(manifest_path,manifest)


if __name__=='__main__':run(Path.cwd())
