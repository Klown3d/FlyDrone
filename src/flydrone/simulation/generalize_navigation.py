"""Novel geometry and imperfect position observations for both controllers."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import yaml
from flydrone.simulation.navigation import NavigationState,advance,goal_bearing
from flydrone.neural.steering_interface import command
from flydrone.neural.epg_delta7 import EPGDelta7Candidate
from flydrone.neural.orientation_closed_loop import wrap
from flydrone.data.acquire import save_json,file_hash,utc_now


def run(root: Path, config: Path=Path('configs/navigation_generalization.yaml')) -> None:
    path=root/config;c=yaml.safe_load(path.read_text())
    plant=yaml.safe_load((root/c['plant_config']).read_text());nav=yaml.safe_load((root/c['navigation_config']).read_text())
    b=yaml.safe_load((root/plant['orientation_config']).read_text());m=EPGDelta7Candidate(root,root/b['candidate_config'])
    n=c['cases'];rng=np.random.default_rng(c['case_seed'])
    start=rng.uniform(*c['initial_xy_range_m'],size=(n,2));angle=rng.uniform(-np.pi,np.pi,n)
    radius=np.resize(np.asarray(c['target_distances_m']),n)
    targets=start+radius[:,None]*np.column_stack([np.cos(angle),np.sin(angle)])
    heading0=rng.uniform(-np.pi,np.pi,n);target=(targets[:,0],targets[:,1])
    dt=plant['dt_s'];steps=round(c['duration_s']/dt);hold=round(2/dt)
    output=root/c['output'];output.mkdir(parents=True,exist_ok=True);rows=[];reports=[]
    pd.DataFrame({'case':np.arange(n),'start_x':start[:,0],'start_y':start[:,1],'target_x':targets[:,0],'target_y':targets[:,1],'initial_heading_rad':heading0,'initial_distance_m':radius}).to_csv(output/'cases.csv',index=False)
    for scenario in c['scenarios']:
        lag=round(scenario['delay_s']/dt)
        for seed in scenario['seeds']:
            srng=np.random.default_rng(seed)
            pos_noise=srng.normal(0,scenario['position_noise_std_m'],size=(steps,n,2))
            head_noise=srng.normal(0,np.deg2rad(scenario['heading_noise_std_deg']),size=(steps,n))
            bias_angle=srng.uniform(-np.pi,np.pi,n)
            bias=scenario['position_bias_m']*np.column_stack([np.cos(bias_angle),np.sin(bias_angle)])
            for label in ('neural','proportional'):
                state=NavigationState(altitude=np.full(n,.7),vertical_speed=np.zeros(n),heading=heading0.copy(),yaw_rate=np.zeros(n),x=start[:,0].copy(),y=start[:,1].copy(),vx=np.zeros(n),vy=np.zeros(n),arrived=np.zeros(n,dtype=bool))
                disturbed=np.zeros(n,dtype=bool);displacement=float(scenario.get('post_arrival_displacement_m',0.))
                xyz=[np.column_stack([state.x,state.y,state.altitude])];heads=[state.heading.copy()];vel=[np.column_stack([state.vx,state.vy])]
                observed_xy=[];observed_heading=[];rates=[];deltas=[];commands=[];arrivals=[]
                for step in range(steps):
                    past=max(0,step-lag);sensed_xy=xyz[past][:,:2]+pos_noise[step]+bias
                    sensed=NavigationState(altitude=state.altitude,heading=wrap(heads[past]+head_noise[step]),x=sensed_xy[:,0],y=sensed_xy[:,1],vx=vel[past][:,0],vy=vel[past][:,1])
                    bearing=goal_bearing(sensed,target)
                    yaw,values=command(m,sensed.heading,bearing,b,label=='proportional')
                    advance(state,yaw,target,plant,nav,b['yaw_response_tau_s'],dt,observation=sensed)
                    newly_arrived=np.asarray(state.arrived,dtype=bool)&~disturbed
                    if displacement>0 and np.any(newly_arrived):
                        state.x[newly_arrived]+=displacement*np.cos(bias_angle[newly_arrived])
                        state.y[newly_arrived]+=displacement*np.sin(bias_angle[newly_arrived])
                        disturbed[newly_arrived]=True
                    xyz.append(np.column_stack([state.x,state.y,state.altitude]));heads.append(state.heading.copy());vel.append(np.column_stack([state.vx,state.vy]))
                    observed_xy.append(sensed_xy);observed_heading.append(sensed.heading);rates.append(values[3].astype('float32'));deltas.append(values[1].astype('float32'));commands.append(yaw);arrivals.append(state.arrived.copy())
                positions=np.array(xyz);speeds=np.linalg.norm(np.array(vel),axis=-1)
                distances=np.linalg.norm(positions[:,:,:2]-targets[None,:,:],axis=-1)
                success=state.arrived&np.all(distances[-hold-1:]<=nav['arrival_radius_m'],axis=0)&np.all(speeds[-hold-1:]<=nav['stop_speed_m_s'],axis=0)&np.all(np.abs(positions[-hold-1:,:,2]-plant['target_altitude_m'])<=.1,axis=0)&~np.any(positions[:,:,2]<=0,axis=0)
                lengths=np.linalg.norm(np.diff(positions[:,:,:2],axis=0),axis=-1).sum(axis=0)
                for i in range(n):
                    reason='success' if success[i] else ('stopped_outside_goal' if state.arrived[i] and distances[-1,i]>nav['arrival_radius_m'] else 'no_valid_terminal_hold')
                    rows.append({'scenario':scenario['name'],'seed':seed,'controller':label,'case':i,'initial_distance_m':radius[i],'post_arrival_disturbed':bool(disturbed[i]),'success':bool(success[i]),'failure_reason':reason,'final_distance_m':float(distances[-1,i]),'final_speed_m_s':float(speeds[-1,i]),'path_length_m':float(lengths[i]),'progress_efficiency':float((radius[i]-distances[-1,i])/lengths[i]) if success[i] and lengths[i]>0 else None})
                trace=output/f"{scenario['name']}-{label}-{seed}.npz"
                np.savez_compressed(trace,time_s=np.arange(steps+1)*dt,xyz_m=positions,heading_rad=np.array(heads),observed_xy_m=np.array(observed_xy),observed_heading_rad=np.array(observed_heading),command_rad_s=np.array(commands),pfl3_rates_hz=np.array(rates),delta7_signed_deviation=np.array(deltas),arrival_latch=np.array(arrivals),target_xy_m=targets,position_bias_m=bias,pfl3_root_ids=m.base.pfl3.root_id.to_numpy(str),delta7_root_ids=np.array(m.base.delta_ids))
                reports.append({'scenario':scenario['name'],'controller':label,'seed':seed,'episodes':n,'successes':int(success.sum()),'trace_sha256':file_hash(trace)})
                print(f"{scenario['name']} {label} seed{seed}: {success.mean():.1%}",flush=True)
    frame=pd.DataFrame(rows);frame.to_csv(output/'episodes.csv',index=False)
    frame.groupby(['scenario','controller']).agg(episodes=('success','size'),success_rate=('success','mean'),median_final_distance_m=('final_distance_m','median')).to_csv(output/'summary.csv')
    frame.loc[~frame.success].to_csv(output/'failures.csv',index=False)
    report={'created_at':utc_now(),'dataset':'FAFB','materialization_version':783,'episodes':len(rows),'claim':'Novel geometry and position observation perturbations; simplified plant, not full flight',
        'observations':'Position and heading delayed/noisy; fixed per-episode bias; velocity delayed exact; altitude ideal; target known exactly',
        'controller_fairness':'Same observed position/heading also used by conventional advance/braking/arrival logic; true state used only for dynamics and scoring',
        'delay_actual_s':{s['name']:round(s['delay_s']/dt)*dt for s in c['scenarios']},
        'tuning':'No parameters adjusted to these cases; settings remain candidate_v1',
        'config_sha256':file_hash(path),'navigation_sha256':file_hash(root/c['navigation_config']),'source_sha256':file_hash(Path(__file__)),
        'plant_source_sha256':file_hash(root/'src/flydrone/simulation/navigation.py'),'edges_sha256':file_hash(root/m.config['neuropil_edges']),'results':reports}
    save_json(output/'report.json',report)
    p=root/'data/manifest.json';manifest=json.loads(p.read_text(encoding='utf-8'));manifest[c.get('manifest_key','navigation_generalization')]={'report':(output/'report.json').relative_to(root).as_posix(),'sha256':file_hash(output/'report.json'),'status':'novel_geometry_imperfect_position_evaluated'};save_json(p,manifest)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--config',type=Path,default=Path('configs/navigation_generalization.yaml'))
    run(Path.cwd(),parser.parse_args().config)
