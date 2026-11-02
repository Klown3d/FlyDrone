"""Gain/delay exploration with identical noisy observations and saved neural traces."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import yaml
from flydrone.data.acquire import file_hash, save_json, utc_now
from flydrone.neural.epg_delta7 import EPGDelta7Candidate
from flydrone.neural.orientation_closed_loop import wrap, yaw_step


def harmonic_transfer(weights: np.ndarray, angles: np.ndarray, heading: np.ndarray) -> np.ndarray:
    z=weights@np.exp(1j*angles)
    return np.cos(heading[:,None])*z.real+np.sin(heading[:,None])*z.imag


def run(root: Path, config: Path = Path('configs/orientation_sensitivity.yaml')) -> None:
    path=root/config;c=yaml.safe_load(path.read_text())
    base_path=root/c['base_config'];b=yaml.safe_load(base_path.read_text())
    m=EPGDelta7Candidate(root,root/b['candidate_config'])
    out=root/c['output'];out.mkdir(parents=True,exist_ok=True)
    goals=np.repeat(np.deg2rad(b['goals_deg']),len(b['initial_errors_deg']))
    initial=np.tile(np.deg2rad(b['initial_errors_deg']),len(b['goals_deg']))
    steps=round(b['duration_s']/b['dt_s']);hold=round(b['success_hold_s']/b['dt_s'])
    angles=b['epg_heading_sign']*m.epg_angles_rad+np.deg2rad(b['phase_offset_deg'])
    z=m.via_delta7@np.exp(1j*angles)
    goal_drive=np.cos(goals[:,None]-m.base.fc2_angles_rad)@m.base.fc2_weights.T
    p=m.base.parameters;reports=[];episodes=[]
    for delay in c['delays_s']:
        lag=round(delay/b['dt_s'])
        for seed in c['seeds']:
            noise=np.random.default_rng(seed).normal(0,np.deg2rad(c['noise_std_deg']),size=(steps,len(goals)))
            for gain in [None]+c['gains']:
                heading=wrap(goals+initial);rate=np.zeros(len(goals));history=[heading.copy()]
                observations=[];neural=[];commands=[]
                for step in range(steps):
                    observed=wrap(history[max(0,step-lag)]+noise[step]);observations.append(observed)
                    if gain is None:
                        command=-b['proportional_baseline_gain_per_s']*wrap(observed-goals)
                    else:
                        drive=np.cos(observed[:,None])*z.real+np.sin(observed[:,None])*z.imag+p.goal_input_gain_d*goal_drive
                        rates=p.output_scale_hz_a*np.logaddexp(0,p.softplus_slope_b*(drive+p.input_offset_c))
                        neural.append(rates.astype('float32'))
                        command=gain*(rates[:,m.base.right].sum(axis=1)-rates[:,m.base.left].sum(axis=1))
                    command=np.clip(command,-b['maximum_yaw_rate_rad_s'],b['maximum_yaw_rate_rad_s']);commands.append(command)
                    rate=yaw_step(rate,command,b['dt_s'],b['yaw_response_tau_s'])
                    heading=wrap(heading+b['dt_s']*rate);history.append(heading.copy())
                error=np.rad2deg(wrap(np.asarray(history)-goals))
                success=np.all(np.abs(error[-hold-1:])<=b['success_error_deg'],axis=0)
                peak=np.max(np.abs(error[-hold-1:]),axis=0)
                tail_std=np.std(error[-hold-1:],axis=0)
                name='baseline' if gain is None else f'gain{gain}'
                trace=out/f'{name}-delay{delay}-seed{seed}.npz'
                np.savez_compressed(trace,heading_rad=np.array(history),observed_heading_rad=np.array(observations),
                    command_rad_s=np.array(commands),pfl3_rates_hz=np.array(neural),goals_rad=goals,
                    initial_error_rad=initial,epg_angles_rad=angles,pfl3_root_ids=m.base.pfl3.root_id.to_numpy(str))
                reports.append({'controller':name,'gain':gain,'delay_s':delay,'seed':seed,'episodes':len(goals),
                    'success_rate':float(success.mean()),'median_final_abs_error_deg':float(np.median(np.abs(error[-1]))),
                    'p95_tail_peak_error_deg':float(np.percentile(peak,95)),
                    'median_tail_std_deg':float(np.median(tail_std)),
                    'trace':trace.relative_to(root).as_posix(),'trace_sha256':file_hash(trace)})
                for i in range(len(goals)):
                    episodes.append({'controller':name,'gain':gain,'delay_s':delay,'seed':seed,
                        'goal_deg':float(np.rad2deg(goals[i])),'initial_error_deg':float(np.rad2deg(initial[i])),
                        'success':bool(success[i]),'final_abs_error_deg':float(abs(error[-1,i])),
                        'tail_peak_error_deg':float(peak[i]),'tail_std_deg':float(tail_std[i])})
            print(f'Finished delay {delay}s, seed {seed}',flush=True)
    pd.DataFrame(episodes).to_csv(out/'episodes.csv',index=False)
    grouped=pd.DataFrame(episodes).groupby(['controller','delay_s']).agg(success_rate=('success','mean'),episodes=('success','size'),median_final_abs_error_deg=('final_abs_error_deg','median')).reset_index()
    grouped.to_csv(out/'summary.csv',index=False)
    original=pd.read_csv(root/'results/neural/orientation_closed_loop/episodes.csv')
    failure=original.loc[original.condition.eq('corrected') & ~original.success].to_dict('records')
    report={'created_at':utc_now(),'dataset':'FAFB','materialization_version':783,
        'claim':'Engineering sensitivity exploration of provisional heading loop, not drone navigation',
        'episodes':len(episodes),'config_sha256':file_hash(path),'base_config_sha256':file_hash(base_path),
        'source_sha256':file_hash(Path(__file__)),'previous_failed_episodes':failure,
        'neural_model':'Same algebraic signed contact propagation; harmonic form exactly preserves sinusoidal inputs',
        'evaluation_role':c.get('evaluation_role','exploration'),
        'selection_limit':'Held-out seeds test new noise realizations only; same goals and initial conditions' if c.get('evaluation_role')=='held_out_noise' else 'Any gain chosen here is evaluated on exploration seeds; held-out validation still required',
        'results':reports}
    save_json(out/'report.json',report)
    manifest_path=root/'data/manifest.json';manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    key='orientation_held_out_noise' if c.get('evaluation_role')=='held_out_noise' else 'orientation_sensitivity'
    manifest[key]={'status':'completed','report':(out/'report.json').relative_to(root).as_posix(),'report_sha256':file_hash(out/'report.json')}
    save_json(manifest_path,manifest)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=Path('configs/orientation_sensitivity.yaml'))
    run(Path.cwd(),parser.parse_args().config)
