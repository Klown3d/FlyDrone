"""Tune a conventional PID on development cases and freeze it for held-out tests."""
from itertools import product
from pathlib import Path
import json
import numpy as np
import pandas as pd
import yaml
from flydrone.data.acquire import file_hash,save_json,utc_now
from flydrone.neural.epg_delta7 import EPGDelta7Candidate
from flydrone.simulation.benchmark_quadrotor import simulate


def cases(config: dict):
    return [(np.deg2rad(t),np.deg2rad(h)) for t in config['target_bearings_deg'] for h in config['initial_relative_headings_deg']]


def pid_candidates(config: dict):
    fixed=config['fixed'];grid=config['candidate_grid']
    for kp,ki,kd in product(grid['kp_per_s'],grid['ki_per_s2'],grid['kd']):
        yield {**fixed,'kp_per_s':kp,'ki_per_s2':ki,'kd':kd}


def evaluate_block(root,c,plant,model,orientation,controller,pid,scenario,seed):
    rows=[]
    for index,(target,heading) in enumerate(cases(c)):
        row,_=simulate(root,c,plant,model,orientation,target,heading,controller=='proportional',False,
                       scenario,seed+index,yaw_controller=controller,pid_config=pid)
        rows.append(row)
    return rows


def run(root: Path,config_path: Path=Path('configs/pid_baseline.yaml')) -> None:
    spec=yaml.safe_load((root/config_path).read_text());plant=yaml.safe_load((root/spec['plant_config']).read_text());orientation=yaml.safe_load((root/spec['orientation_config']).read_text());model=EPGDelta7Candidate(root,root/orientation['candidate_config'])
    output=root/spec['output'];output.mkdir(parents=True,exist_ok=True)
    development=spec['development'];tuning=[]
    for index,pid in enumerate(pid_candidates(spec)):
        block=evaluate_block(root,development,plant,model,orientation,'pid',pid,development['scenario'],int(development['scenario']['seed']))
        for row in block:row.update({'candidate':index,**{f'pid_{key}':value for key,value in pid.items()}})
        tuning.extend(block);print(f'candidate {index}: {sum(r["success"] for r in block)}/{len(block)}',flush=True)
    tuning_frame=pd.DataFrame(tuning);tuning_frame.to_csv(output/'development_episodes.csv',index=False)
    ranking=tuning_frame.groupby(['candidate','pid_kp_per_s','pid_ki_per_s2','pid_kd','pid_maximum_yaw_rate_rad_s','pid_integral_limit_rad_s','pid_derivative_filter_tau_s']).agg(successes=('success','sum'),success_rate=('success','mean'),median_terminal_progress=('normalized_terminal_progress','median'),median_path_efficiency=('path_efficiency','median'),median_final_distance_m=('final_distance_m','median')).reset_index()
    ranking=ranking.sort_values(['successes','median_path_efficiency','median_terminal_progress','median_final_distance_m'],ascending=[False,False,False,True],na_position='last');ranking.to_csv(output/'development_ranking.csv',index=False)
    winner=ranking.iloc[0];selected={'kp_per_s':float(winner.pid_kp_per_s),'ki_per_s2':float(winner.pid_ki_per_s2),'kd':float(winner.pid_kd),'maximum_yaw_rate_rad_s':float(winner.pid_maximum_yaw_rate_rad_s),'integral_limit_rad_s':float(winner.pid_integral_limit_rad_s),'derivative_filter_tau_s':float(winner.pid_derivative_filter_tau_s)}
    (output/'selected_pid.yaml').write_text(yaml.safe_dump(selected,sort_keys=False),encoding='utf-8')
    evaluation=yaml.safe_load((root/spec['evaluation_config']).read_text());robustness=yaml.safe_load((root/spec['robustness_config']).read_text());held_out=[]
    scenario={'name':'ideal'}
    for controller in ('pid','proportional'):
        held_out.extend(evaluate_block(root,evaluation,plant,model,orientation,controller,selected if controller=='pid' else None,scenario,int(evaluation['seed'])))
        print(f'ideal {controller}: {sum(r["success"] for r in held_out if r["scenario"]=="ideal" and r["controller"]==controller)}/{len(cases(evaluation))}',flush=True)
    for scenario in robustness['scenarios']:
        for controller in ('pid','proportional'):
            block=evaluate_block(root,robustness,plant,model,orientation,controller,selected if controller=='pid' else None,scenario,int(scenario['seed']))
            held_out.extend(block);print(f'{scenario["name"]} {controller}: {sum(r["success"] for r in block)}/{len(block)}',flush=True)
    frame=pd.DataFrame(held_out);frame.to_csv(output/'held_out_episodes.csv',index=False)
    summary=frame.groupby(['scenario','controller']).agg(episodes=('success','size'),successes=('success','sum'),success_rate=('success','mean'),median_final_distance_m=('final_distance_m','median'),median_terminal_progress=('normalized_terminal_progress','median'),median_successful_path_efficiency=('path_efficiency','median'),maximum_tilt_deg=('max_tilt_deg','max')).reset_index();summary.to_csv(output/'held_out_summary.csv',index=False)
    report={'created_at':utc_now(),'claim':'Conventional PID selected only on separate development geometries and frozen before held-out ideal and perturbed 6-DoF evaluation','configuration':config_path.as_posix(),'configuration_sha256':file_hash(root/config_path),'development_cases':len(cases(development)),'candidate_count':len(ranking),'selected_pid':selected,'held_out_episodes':len(frame),'summary':summary.astype(object).where(pd.notna(summary),None).to_dict(orient='records')};save_json(output/'report.json',report)
    manifest_path=root/'data/manifest.json';manifest=json.loads(manifest_path.read_text(encoding='utf-8'));manifest[spec['manifest_key']]={'status':'pid_development_selection_and_held_out_evaluation_completed','report':(output/'report.json').relative_to(root).as_posix(),'report_sha256':file_hash(output/'report.json'),'development_episodes':len(tuning_frame),'held_out_episodes':len(frame)};save_json(manifest_path,manifest)


if __name__=='__main__':run(Path.cwd())
