"""Provisional closed-loop heading benchmark; no drone dynamics or flight claim."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import yaml
from flydrone.neural.epg_delta7 import EPGDelta7Candidate
from flydrone.data.acquire import file_hash, save_json, utc_now


def wrap(angle: np.ndarray) -> np.ndarray:
    return np.angle(np.exp(1j * angle))


def yaw_step(rate: np.ndarray, command: np.ndarray, dt: float, tau: float) -> np.ndarray:
    """Exact first-order actuator update for constant command over one step."""
    return command + (rate-command)*np.exp(-dt/tau)


def run(root: Path, config: Path = Path('configs/orientation_closed_loop.yaml')) -> None:
    config_path=root/config
    c=yaml.safe_load(config_path.read_text())
    if c['dt_s']<=0 or c['yaw_response_tau_s']<=0:
        raise ValueError('Positive timestep and actuator time constant required')
    m=EPGDelta7Candidate(root,root/c['candidate_config'])
    output=root/c['output'];output.mkdir(parents=True,exist_ok=True)
    goals=np.repeat(np.deg2rad(c['goals_deg']),len(c['initial_errors_deg']))
    initial=np.tile(np.deg2rad(c['initial_errors_deg']),len(c['goals_deg']))
    steps=round(c['duration_s']/c['dt_s'])
    hold=round(c['success_hold_s']/c['dt_s'])
    if hold<1 or hold>steps:
        raise ValueError('Hold must fit inside experiment')
    p=m.base.parameters
    goal_drive=np.cos(goals[:,None]-m.base.fc2_angles_rad)@m.base.fc2_weights.T
    rng=np.random.default_rng(c['seed'])
    conditions=[('corrected',m.epg_to_delta,False,False),('previous_convention',m.epg_to_delta,True,False),
                ('no_goal',m.epg_to_delta,False,True),('proportional_baseline',None,False,False)]
    for i in range(c['shuffle_replicates']):
        conditions.append((f'shuffled_epg_inputs_{i}',m.base.shuffled_rows(m.epg_to_delta,rng),False,False))
    reports=[];episode_rows=[]
    for scenario_index,scenario in enumerate(c['scenarios']):
        noise=np.random.default_rng(c['seed']+scenario_index).normal(0,np.deg2rad(scenario['heading_noise_std_deg']),size=(steps,len(goals)))
        delay_steps=round(scenario['observation_delay_s']/c['dt_s'])
        for name,weights,previous,no_goal in conditions:
            heading=wrap(goals+initial);rate=np.zeros(len(goals))
            history=[heading.copy()];errors=[wrap(heading-goals)]
            rate_history=[];commands=[];neural=[];delta_history=[]
            for step in range(steps):
                observed=wrap(history[max(0,step-delay_steps)]+noise[step])
                if weights is None:
                    command=-c['proportional_baseline_gain_per_s']*wrap(observed-goals)
                else:
                    angles=m.epg_angles_rad if previous else c['epg_heading_sign']*m.epg_angles_rad+np.deg2rad(c['phase_offset_deg'])
                    delta=np.cos(observed[:,None]-angles)@weights.T
                    drive=-delta@m.delta_to_pfl3.T+(0 if no_goal else p.goal_input_gain_d*goal_drive)
                    rates=p.output_scale_hz_a*np.logaddexp(0,p.softplus_slope_b*(drive+p.input_offset_c))
                    signal=rates[:,m.base.right].sum(axis=1)-rates[:,m.base.left].sum(axis=1)
                    command=c['readout_gain_rad_per_s_per_hz']*signal
                    neural.append(rates);delta_history.append(delta)
                command=np.clip(command,-c['maximum_yaw_rate_rad_s'],c['maximum_yaw_rate_rad_s'])
                rate=yaw_step(rate,command,c['dt_s'],c['yaw_response_tau_s'])
                heading=wrap(heading+c['dt_s']*rate)
                if not np.isfinite(heading).all():
                    raise FloatingPointError('Nonfinite closed-loop state')
                history.append(heading.copy());errors.append(wrap(heading-goals));rate_history.append(rate.copy());commands.append(command)
            err=np.rad2deg(np.array(errors));successful=np.all(np.abs(err[-hold-1:])<=c['success_error_deg'],axis=0)
            settle=[]
            for i in range(len(goals)):
                valid=np.abs(err[:,i])<=c['success_error_deg']
                windows=np.convolve(valid.astype(int),np.ones(hold+1,dtype=int),mode='valid')
                matches=np.flatnonzero(windows==hold+1)
                settle.append(float(matches[0]*c['dt_s']) if len(matches) else None)
                episode_rows.append({'scenario':scenario['name'],'condition':name,'goal_deg':float(np.rad2deg(goals[i])),
                    'initial_error_deg':float(np.rad2deg(initial[i])),'success':bool(successful[i]),
                    'final_abs_error_deg':float(abs(err[-1,i])),'first_hold_start_s':settle[-1]})
            path=output/f"{scenario['name']}-{name}-trace.npz"
            np.savez_compressed(path,time_s=np.arange(steps+1)*c['dt_s'],goals_rad=goals,initial_errors_rad=initial,
                heading_rad=np.asarray(history),error_deg=err,yaw_rate_rad_s=np.asarray(rate_history),command_rad_s=np.asarray(commands),
                pfl3_rates_hz=np.asarray(neural),delta7_signed_deviation=np.asarray(delta_history),
                pfl3_root_ids=m.base.pfl3.root_id.to_numpy(str),delta7_root_ids=np.array(m.base.delta_ids))
            reports.append({'scenario':scenario['name'],'condition':name,'episodes':len(goals),'success_rate':float(successful.mean()),
                'median_final_abs_error_deg':float(np.median(np.abs(err[-1]))),'p95_final_abs_error_deg':float(np.percentile(np.abs(err[-1]),95)),
                'median_first_hold_start_s':float(np.median([s for s in settle if s is not None])) if any(s is not None for s in settle) else None,
                'trace':path.relative_to(root).as_posix(),'trace_sha256':file_hash(path)})
            print(f"{scenario['name']} / {name}: {successful.mean():.1%} success",flush=True)
    pd.DataFrame(episode_rows).to_csv(output/'episodes.csv',index=False)
    report={'created_at':utc_now(),'dataset':'FAFB','materialization_version':783,'claim':'Provisional heading-only engineering loop; not drone navigation or measured fly dynamics',
        'success_definition':f"Every sampled error during final {c['success_hold_s']} seconds <= {c['success_error_deg']} degrees",
        'noise_control':'Identical observation-noise arrays across conditions within each scenario',
        'shuffle_control':'Independent row permutations preserve incoming row values/contact totals and in-degree, not outgoing degree',
        'neural_dynamics':'Algebraic signed feedforward EPG->Delta7->PFL3; Delta7 recurrence omitted',
        'config_sha256':file_hash(config_path),'source_code_sha256':file_hash(Path(__file__)),
        'edges_sha256':file_hash(root/m.config['neuropil_edges']),'results':reports}
    save_json(output/'report.json',report)
    manifest_path=root/'data/manifest.json';manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest['orientation_closed_loop']={'status':'provisional_benchmark_completed_no_drone','report':(output/'report.json').relative_to(root).as_posix(),'report_sha256':file_hash(output/'report.json')}
    save_json(manifest_path,manifest)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=Path('configs/orientation_closed_loop.yaml'))
    run(Path.cwd(),parser.parse_args().config)
