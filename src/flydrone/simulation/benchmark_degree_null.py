"""Run degree-preserving rewired circuit nulls in the frozen 6DoF plant."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import yaml
from flydrone.data.acquire import file_hash,save_json,utc_now
from flydrone.neural.epg_delta7 import EPGDelta7Candidate
from flydrone.simulation.benchmark_circuit_ablation import degree_preserving_variants
from flydrone.simulation.benchmark_quadrotor import simulate


def run(root: Path,config_path: Path=Path('configs/quadrotor_degree_null.yaml')) -> None:
    c=yaml.safe_load((root/config_path).read_text());plant=yaml.safe_load((root/c['plant_config']).read_text());orientation=yaml.safe_load((root/c['orientation_config']).read_text());model=EPGDelta7Candidate(root,root/orientation['candidate_config']);cases=[(np.deg2rad(t),np.deg2rad(h)) for t in c['target_bearings_deg'] for h in c['initial_relative_headings_deg']];rows=[];metadata=[]
    for label,variant,seed in degree_preserving_variants(model,[int(v) for v in c['seeds']]):
        for target,heading in cases:
            result,_=simulate(root,c,plant,model,orientation,target,heading,False,False,None,0,variant,label);result['null_seed']=seed;rows.append(result)
        subset=[r for r in rows if r['circuit_condition']==label];metadata.append({'condition':label,'accepted_swaps':variant['_accepted_swaps']});print(f'{label}: {sum(r["success"] for r in subset)}/{len(cases)}',flush=True)
    output=root/c['output'];output.mkdir(parents=True,exist_ok=True);frame=pd.DataFrame(rows);frame.to_csv(output/'episodes.csv',index=False);summary=frame.groupby('circuit_condition').agg(episodes=('success','size'),successes=('success','sum'),success_rate=('success','mean'),median_final_distance_m=('final_distance_m','median'),median_terminal_progress=('normalized_terminal_progress','median')).reset_index();summary.to_csv(output/'summary.csv',index=False)
    report={'created_at':utc_now(),'dataset':'FAFB','materialization_version':783,'episodes':len(frame),'claim':'6DoF degree-preserving computational nulls; no biological perturbation experiment','configuration':config_path.as_posix(),'configuration_sha256':file_hash(root/config_path),'rewiring':'Binary row and column degrees plus each row weight multiset and sum preserved; column weight sums not preserved','rewire_metadata':metadata,'summary':summary.to_dict(orient='records')};save_json(output/'report.json',report);manifest_path=root/'data/manifest.json';manifest=json.loads(manifest_path.read_text(encoding='utf-8'));manifest[c['manifest_key']]={'status':'degree_preserving_null_6dof_completed','report':(output/'report.json').relative_to(root).as_posix(),'report_sha256':file_hash(output/'report.json'),'episodes':len(frame)};save_json(manifest_path,manifest)


if __name__=='__main__':run(Path.cwd())
