"""Heading diagnostic for degree-preserving rewired circuit nulls."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import yaml
from flydrone.data.acquire import file_hash,save_json,utc_now
from flydrone.neural.epg_delta7 import EPGDelta7Candidate
from flydrone.neural.orientation_closed_loop import wrap,yaw_step
from flydrone.neural.steering_interface import command
from flydrone.simulation.benchmark_circuit_ablation import degree_preserving_variants


def run(root: Path,config_path: Path=Path('configs/degree_null_orientation.yaml')) -> None:
    c=yaml.safe_load((root/config_path).read_text());orientation=yaml.safe_load((root/c['orientation_config']).read_text());model=EPGDelta7Candidate(root,root/c['candidate_config']);goals=np.repeat(np.deg2rad(c['goals_deg']),len(c['initial_errors_deg']));initial=np.tile(np.deg2rad(c['initial_errors_deg']),len(c['goals_deg']));steps=round(c['duration_s']/c['dt_s']);hold=round(c['success_hold_s']/c['dt_s']);rows=[];metadata=[]
    for label,variant,seed in degree_preserving_variants(model,[int(v) for v in c['seeds']]):
        heading=wrap(goals+initial);rate=np.zeros_like(heading);history=[]
        for _ in range(steps):
            yaw=command(model,heading,goals,orientation,False,variant)[0];rate=yaw_step(rate,yaw,c['dt_s'],c['yaw_response_tau_s']);heading=wrap(heading+c['dt_s']*rate);history.append(wrap(heading-goals))
        errors=np.abs(np.rad2deg(np.asarray(history)));success=np.all(errors[-hold:]<=c['success_error_deg'],axis=0)
        for i in range(len(goals)):rows.append({'condition':label,'seed':seed,'goal_deg':float(np.rad2deg(goals[i])),'initial_error_deg':float(np.rad2deg(initial[i])),'success':bool(success[i]),'final_abs_error_deg':float(errors[-1,i])})
        metadata.append({'condition':label,'accepted_swaps':variant['_accepted_swaps']});print(f'{label}: {success.sum()}/{len(success)}',flush=True)
    output=root/c['output'];output.mkdir(parents=True,exist_ok=True);frame=pd.DataFrame(rows);frame.to_csv(output/'episodes.csv',index=False);summary=frame.groupby('condition').agg(episodes=('success','size'),successes=('success','sum'),success_rate=('success','mean'),median_final_abs_error_deg=('final_abs_error_deg','median')).reset_index();summary.to_csv(output/'summary.csv',index=False)
    report={'created_at':utc_now(),'dataset':'FAFB','materialization_version':783,'claim':'Degree-preserving computational null; no biological perturbation or measured dynamics','configuration':config_path.as_posix(),'configuration_sha256':file_hash(root/config_path),'rewiring':'Binary row and column degrees plus each row weight multiset and sum preserved; column weight sums not preserved','rewire_metadata':metadata,'summary':summary.to_dict(orient='records')};save_json(output/'report.json',report);manifest_path=root/'data/manifest.json';manifest=json.loads(manifest_path.read_text(encoding='utf-8'));manifest[c['manifest_key']]={'status':'degree_preserving_null_heading_diagnostic_completed','report':(output/'report.json').relative_to(root).as_posix(),'report_sha256':file_hash(output/'report.json'),'episodes':len(frame)};save_json(manifest_path,manifest)


if __name__=='__main__':run(Path.cwd())
