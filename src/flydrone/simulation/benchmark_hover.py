"""Use the desktop plant itself for multi-episode hover and neural steering tests."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import yaml
from flydrone.simulation.hover import HoverState, update
from flydrone.neural.epg_delta7 import EPGDelta7Candidate
from flydrone.neural.orientation_closed_loop import wrap
from flydrone.data.acquire import save_json, file_hash, utc_now


def run(root: Path) -> None:
    config_path=root/'configs/hover_benchmark.yaml';c=yaml.safe_load(config_path.read_text())
    plant_path=root/c['desktop_config'];plant=yaml.safe_load(plant_path.read_text())
    b=yaml.safe_load((root/plant['orientation_config']).read_text())
    m=EPGDelta7Candidate(root,root/b['candidate_config']);p=m.base.parameters
    pairs=[(g,e,z) for g in b['goals_deg'] for e in b['initial_errors_deg'] for z in c['initial_altitudes_m']]
    goals=np.deg2rad([g for g,e,z in pairs]);initial=np.deg2rad([e for g,e,z in pairs]);z0=np.array([z for g,e,z in pairs])
    dt=plant['dt_s'];steps=round(b['duration_s']/dt);hold=round(b['success_hold_s']/dt)
    angles=b['epg_heading_sign']*m.epg_angles_rad+np.deg2rad(b['phase_offset_deg'])
    goal_drive=m.base.fc2_weights@np.cos(goals[:,None]-m.base.fc2_angles_rad).T
    out=root/c['output'];out.mkdir(parents=True,exist_ok=True);rows=[];reports=[]
    for scenario in c['scenarios']:
        delay=round(scenario['delay_s']/dt)
        for seed in scenario['seeds']:
            noise=np.random.default_rng(seed).normal(0,np.deg2rad(scenario['noise_std_deg']),size=(steps,len(goals)))
            for controller in ('neural','proportional'):
                state=HoverState(altitude=z0.copy(),vertical_speed=np.zeros(len(goals)),heading=wrap(goals+initial),yaw_rate=np.zeros(len(goals)))
                history=[state.heading.copy()];altitude=[state.altitude.copy()];neural=[];observations=[];commands=[];thrusts=[];delta_history=[]
                for step in range(steps):
                    observed=wrap(history[max(0,step-delay)]+noise[step]);observations.append(observed)
                    delta=np.cos(observed[:,None]-angles)@m.epg_to_delta.T
                    drive=-delta@m.delta_to_pfl3.T+p.goal_input_gain_d*goal_drive.T
                    rates=p.output_scale_hz_a*np.logaddexp(0,p.softplus_slope_b*(drive+p.input_offset_c))
                    signal=rates[:,m.base.right].sum(axis=1)-rates[:,m.base.left].sum(axis=1)
                    command=b['readout_gain_rad_per_s_per_hz']*signal if controller=='neural' else -b['proportional_baseline_gain_per_s']*wrap(observed-goals)
                    command=np.clip(command,-b['maximum_yaw_rate_rad_s'],b['maximum_yaw_rate_rad_s'])
                    thrust=update(state,command,plant,b['yaw_response_tau_s'],dt)
                    history.append(state.heading.copy());altitude.append(state.altitude.copy())
                    neural.append(rates.astype('float32'));delta_history.append(delta.astype('float32'));commands.append(command);thrusts.append(thrust)
                errors=np.rad2deg(wrap(np.array(history)-goals));alt=np.array(altitude)
                heading_ok=np.all(np.abs(errors[-hold-1:])<=b['success_error_deg'],axis=0)
                altitude_ok=np.all(np.abs(alt[-hold-1:]-plant['target_altitude_m'])<=c['altitude_tolerance_m'],axis=0)
                ground=np.any(alt<=0,axis=0);success=heading_ok&altitude_ok&~ground
                trace=out/f"{scenario['name']}-{controller}-{seed}.npz"
                np.savez_compressed(trace,time_s=np.arange(steps+1)*dt,heading_rad=np.array(history),altitude_m=alt,
                    observed_heading_rad=np.array(observations),command_rad_s=np.array(commands),thrust_n=np.array(thrusts),
                    pfl3_rates_hz=np.array(neural),delta7_signed_deviation=np.array(delta_history),goals_rad=goals,
                    initial_errors_rad=initial,initial_altitudes_m=z0,pfl3_root_ids=m.base.pfl3.root_id.to_numpy(str),delta7_root_ids=np.array(m.base.delta_ids))
                reports.append({'scenario':scenario['name'],'seed':seed,'controller':controller,'episodes':len(goals),
                    'successes':int(success.sum()),'success_rate':float(success.mean()),'altitude_success_rate':float(altitude_ok.mean()),
                    'ground_contacts':int(ground.sum()),'median_final_heading_error_deg':float(np.median(np.abs(errors[-1]))),
                    'trace':trace.relative_to(root).as_posix(),'trace_sha256':file_hash(trace)})
                for i,(g,e,z) in enumerate(pairs):
                    rows.append({'scenario':scenario['name'],'seed':seed,'controller':controller,'goal_deg':g,'initial_error_deg':e,
                        'initial_altitude_m':z,'success':bool(success[i]),'altitude_success':bool(altitude_ok[i]),
                        'ground_contact':bool(ground[i]),'final_heading_error_deg':float(errors[-1,i]),'final_altitude_m':float(alt[-1,i])})
                print(f"{scenario['name']} {controller} seed{seed}: {success.mean():.2%}",flush=True)
    frame=pd.DataFrame(rows);frame.to_csv(out/'episodes.csv',index=False)
    frame.groupby(['scenario','controller']).agg(episodes=('success','size'),success_rate=('success','mean'),altitude_success_rate=('altitude_success','mean')).to_csv(out/'summary.csv')
    report={'created_at':utc_now(),'dataset':'FAFB','materialization_version':783,'episodes':len(rows),
        'claim':'Desktop constrained hover/yaw plant; no horizontal navigation or full quadrotor dynamics',
        'success':'Heading <=10deg and altitude error <=0.1m throughout last2s; no sampled ground contact',
        'noise_control':'Identical arrays per seed/scenario between controllers; altitude sensing remains ideal',
        'delay_actual_s':{s['name']:round(s['delay_s']/dt)*dt for s in c['scenarios']},
        'config_sha256':file_hash(config_path),'plant_sha256':file_hash(plant_path),
        'orientation_sha256':file_hash(root/plant['orientation_config']),'source_sha256':file_hash(Path(__file__)),
        'edges_sha256':file_hash(root/m.config['neuropil_edges']),
        'plant_source_sha256':file_hash(root/'src/flydrone/simulation/hover.py'),'results':reports}
    save_json(out/'report.json',report)
    path=root/'data/manifest.json';manifest=json.loads(path.read_text(encoding='utf-8'))
    manifest['hover_benchmark']={'status':'completed_provisional_hover_yaw','report':(out/'report.json').relative_to(root).as_posix(),'sha256':file_hash(out/'report.json')};save_json(path,manifest)


if __name__=='__main__':run(Path.cwd())
