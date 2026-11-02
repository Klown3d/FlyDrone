"""Spatial target benchmark on the same simplified desktop navigation plant."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import yaml
from flydrone.simulation.navigation import NavigationState, advance, goal_bearing
from flydrone.neural.steering_interface import command
from flydrone.neural.epg_delta7 import EPGDelta7Candidate
from flydrone.neural.orientation_closed_loop import wrap
from flydrone.data.acquire import save_json,file_hash,utc_now


def run(root: Path) -> None:
    plant=yaml.safe_load((root/'configs/desktop.yaml').read_text());nav=yaml.safe_load((root/'configs/navigation.yaml').read_text())
    b=yaml.safe_load((root/plant['orientation_config']).read_text());m=EPGDelta7Candidate(root,root/b['candidate_config'])
    goals=np.repeat(np.deg2rad(b['goals_deg']),len(b['initial_errors_deg']));initial=np.tile(np.deg2rad(b['initial_errors_deg']),len(b['goals_deg']))
    target=(4*np.cos(goals),4*np.sin(goals));n=len(goals);dt=plant['dt_s'];steps=round(nav['duration_s']/dt);hold=round(2/dt)
    original=m.epg_to_delta.copy();shuffled=m.base.shuffled_rows(original,np.random.default_rng(792))
    output=root/'results/simulation/navigation';output.mkdir(parents=True,exist_ok=True);rows=[];reports=[]
    for scenario,noise_std,delay_s,seed in [('ideal',0.,0.,792),('noise_delay',3.,.3,792),('noise_delay',3.,.3,793)]:
        noise=np.random.default_rng(seed).normal(0,np.deg2rad(noise_std),size=(steps,n));lag=round(delay_s/dt)
        for label in ('neural','proportional','shuffled','previous_convention'):
            m.epg_to_delta=shuffled if label=='shuffled' else original
            config=dict(b)
            if label=='previous_convention':config['epg_heading_sign']=1
            state=NavigationState(altitude=np.full(n,.7),vertical_speed=np.zeros(n),heading=wrap(goals+initial),yaw_rate=np.zeros(n),x=np.zeros(n),y=np.zeros(n),vx=np.zeros(n),vy=np.zeros(n),arrived=np.zeros(n,dtype=bool))
            history=[state.heading.copy()];xy=[np.column_stack([state.x,state.y])];alt=[state.altitude.copy()];rates=[];deltas=[];observed_history=[];distance=[];speed=[];arrival_time=np.full(n,np.nan)
            for step in range(steps):
                bearing=goal_bearing(state,target)
                observed=wrap(history[max(0,step-lag)]+noise[step]);yaw,values=command(m,observed,bearing,config,label=='proportional')
                advance(state,yaw,target,plant,nav,b['yaw_response_tau_s'],dt)
                arrival_time=np.where(np.isnan(arrival_time)&state.arrived,(step+1)*dt,arrival_time)
                history.append(state.heading.copy());xy.append(np.column_stack([state.x,state.y]));alt.append(state.altitude.copy())
                rates.append(values[3].astype('float32'));deltas.append(values[1].astype('float32'));observed_history.append(observed)
                distance.append(np.hypot(target[0]-state.x,target[1]-state.y));speed.append(np.hypot(state.vx,state.vy))
            distances=np.array(distance);speeds=np.array(speed);altitude=np.array(alt)
            success=state.arrived&np.all(distances[-hold-1:]<=nav['arrival_radius_m'],axis=0)&np.all(speeds[-hold-1:]<=nav['stop_speed_m_s'],axis=0)&np.all(np.abs(altitude[-hold-1:]-plant['target_altitude_m'])<=.1,axis=0)&~np.any(altitude<=0,axis=0)
            positions=np.array(xy);length=np.linalg.norm(np.diff(positions,axis=0),axis=-1).sum(axis=0)
            trace=output/f'{scenario}-{label}-{seed}.npz'
            np.savez_compressed(trace,time_s=np.arange(steps+1)*dt,xy_m=positions,altitude_m=altitude,heading_rad=np.array(history),observed_heading_rad=np.array(observed_history),pfl3_rates_hz=np.array(rates),delta7_signed_deviation=np.array(deltas),target_xy_m=np.column_stack(target),arrival_time_s=arrival_time,pfl3_root_ids=m.base.pfl3.root_id.to_numpy(str))
            for i in range(n):rows.append({'scenario':scenario,'seed':seed,'controller':label,'goal_deg':float(np.rad2deg(goals[i])),'initial_error_deg':float(np.rad2deg(initial[i])),'success':bool(success[i]),'arrival_time_s':float(arrival_time[i]),'final_distance_m':float(distances[-1,i]),'final_speed_m_s':float(speeds[-1,i]),'path_length_m':float(length[i]),'path_efficiency':float(4/length[i]) if success[i] and length[i]>0 else None})
            reports.append({'scenario':scenario,'seed':seed,'controller':label,'successes':int(success.sum()),'episodes':n,'trace_sha256':file_hash(trace)})
            print(f'{scenario} {label} {seed}: {success.mean():.1%}',flush=True)
    frame=pd.DataFrame(rows);frame.to_csv(output/'episodes.csv',index=False)
    frame.groupby(['scenario','controller']).agg(episodes=('success','size'),success_rate=('success','mean'),median_final_distance_m=('final_distance_m','median')).to_csv(output/'summary.csv')
    save_json(output/'report.json',{'created_at':utc_now(),'dataset':'FAFB','materialization_version':783,'episodes':len(rows),'claim':'Simplified navigation, ideal target bearing and position; roll/pitch/aerodynamics absent',
        'forward_control':'Conventional distance/alignment/altitude gating, braking and arrival latch; heading circuit does not decide forward speed',
        'sensing':'Only heading is noisy/delayed; target bearing and position remain ideal, conventional speed gate uses true heading',
        'shuffling':'One exploratory independent row permutation; preserves incoming values but not outgoing degree',
        'path_efficiency':'4m/path length for successful trials; stopping radius may permit values above1; interpret with tolerance',
        'navigation_config':nav,'navigation_config_sha256':file_hash(root/'configs/navigation.yaml'),'plant_sha256':file_hash(root/'src/flydrone/simulation/navigation.py'),'orientation_sha256':file_hash(root/plant['orientation_config']),'results':reports})
    path=root/'data/manifest.json';manifest=json.loads(path.read_text(encoding='utf-8'));manifest['navigation_benchmark']={'report':(output/'report.json').relative_to(root).as_posix(),'sha256':file_hash(output/'report.json'),'status':'simplified_navigation_provisional'};save_json(path,manifest)


if __name__=='__main__':run(Path.cwd())
