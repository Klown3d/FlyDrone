"""Frozen intact and projection-null circuits under sensor and wind perturbations."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import yaml
from flydrone.data.acquire import file_hash,save_json,utc_now
from flydrone.neural.epg_delta7 import EPGDelta7Candidate
from flydrone.simulation.benchmark_circuit_ablation import degree_preserving_rewire
from flydrone.simulation.benchmark_quadrotor import simulate


def run(root: Path,config_path: Path=Path('configs/quadrotor_projection_robustness.yaml')) -> None:
    c=yaml.safe_load((root/config_path).read_text());plant=yaml.safe_load((root/c['plant_config']).read_text());orientation=yaml.safe_load((root/c['orientation_config']).read_text());model=EPGDelta7Candidate(root,root/orientation['candidate_config']);source={'epg_to_delta':model.epg_to_delta,'fc2_weights':model.base.fc2_weights};variants={'intact':None}
    for projection in c['conditions']:
        if projection!='intact':variants[projection]={projection:degree_preserving_rewire(source[projection],np.random.default_rng(int(c['null_seed'])))[0]}
    cases=[(np.deg2rad(t),np.deg2rad(h)) for t in c['target_bearings_deg'] for h in c['initial_relative_headings_deg']]
    output=root/c['output'];output.mkdir(parents=True,exist_ok=True)
    checkpoint=output/'checkpoint.json';partial=output/'episodes.partial.csv';config_hash=file_hash(root/config_path)
    if checkpoint.exists():
        metadata=json.loads(checkpoint.read_text(encoding='utf-8'))
        if metadata['configuration_sha256']!=config_hash or not partial.exists():raise ValueError('Checkpoint does not match this configuration')
        rows=pd.read_csv(partial).to_dict(orient='records')
    else:
        if partial.exists():raise ValueError('Unidentified partial results exist')
        rows=[]
    for scenario in c['scenarios']:
        for label,variant in variants.items():
            condition='intact' if label=='intact' else f'{label}_degree_null'
            completed=[r for r in rows if r['scenario']==scenario['name'] and r['circuit_condition']==condition]
            if len(completed)==len(cases):
                print(f'{scenario["name"]} {condition}: resumed {sum(r["success"] for r in completed)}/{len(cases)}',flush=True);continue
            if completed:raise ValueError(f'Incomplete checkpoint block: {scenario["name"]} {condition}')
            block=[]
            for index,(target,heading) in enumerate(cases):
                result,_=simulate(root,c,plant,model,orientation,target,heading,False,False,scenario,int(scenario['seed'])+index,variant,condition);block.append(result)
            rows.extend(block);temporary=output/'episodes.partial.tmp.csv';pd.DataFrame(rows).to_csv(temporary,index=False);temporary.replace(partial)
            save_json(checkpoint,{'configuration_sha256':config_hash,'completed_episodes':len(rows)})
            print(f'{scenario["name"]} {condition}: {sum(r["success"] for r in block)}/{len(cases)}',flush=True)
    frame=pd.DataFrame(rows)
    if len(frame)!=len(c['scenarios'])*len(variants)*len(cases):raise ValueError('Incomplete robustness episode matrix')
    frame.to_csv(output/'episodes.csv',index=False);summary=frame.groupby(['scenario','circuit_condition']).agg(episodes=('success','size'),successes=('success','sum'),success_rate=('success','mean'),median_final_distance_m=('final_distance_m','median'),median_terminal_progress=('normalized_terminal_progress','median'),median_successful_path_efficiency=('path_efficiency','median'),maximum_tilt_deg=('max_tilt_deg','max')).reset_index();summary.to_csv(output/'summary.csv',index=False);records=summary.astype(object).where(pd.notna(summary),None).to_dict(orient='records')
    report={'created_at':utc_now(),'dataset':'FAFB','materialization_version':783,'episodes':len(frame),'null_seed':c['null_seed'],'claim':'Frozen computational circuit variants under simulated sensor noise, delay and physical wind; no biological perturbation','configuration':config_path.as_posix(),'configuration_sha256':file_hash(root/config_path),'summary':records};save_json(output/'report.json',report);manifest_path=root/'data/manifest.json';manifest=json.loads(manifest_path.read_text(encoding='utf-8'));manifest[c['manifest_key']]={'status':'projection_null_robustness_completed','report':(output/'report.json').relative_to(root).as_posix(),'report_sha256':file_hash(output/'report.json'),'episodes':len(frame)};save_json(manifest_path,manifest)


if __name__=='__main__':run(Path.cwd())
