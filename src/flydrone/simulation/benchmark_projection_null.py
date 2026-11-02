"""Projection-specific degree-preserving circuit nulls in frozen 6DoF."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import yaml
from flydrone.data.acquire import file_hash,save_json,utc_now
from flydrone.neural.epg_delta7 import EPGDelta7Candidate
from flydrone.simulation.benchmark_circuit_ablation import degree_preserving_rewire
from flydrone.simulation.benchmark_quadrotor import simulate


def run(root: Path,config_path: Path=Path('configs/quadrotor_projection_null.yaml')) -> None:
    c=yaml.safe_load((root/config_path).read_text());plant=yaml.safe_load((root/c['plant_config']).read_text());orientation=yaml.safe_load((root/c['orientation_config']).read_text());model=EPGDelta7Candidate(root,root/orientation['candidate_config']);source={'epg_to_delta':model.epg_to_delta,'delta_to_pfl3':model.delta_to_pfl3,'fc2_weights':model.base.fc2_weights};cases=[(np.deg2rad(t),np.deg2rad(h)) for t in c['target_bearings_deg'] for h in c['initial_relative_headings_deg']];rows=[];metadata=[]
    for projection in c['projections']:
        rewired,accepted=degree_preserving_rewire(source[projection],np.random.default_rng(int(c['seed'])));variant={projection:rewired};label=f'{projection}_degree_null'
        for target,heading in cases:
            result,_=simulate(root,c,plant,model,orientation,target,heading,False,False,None,0,variant,label);rows.append(result)
        subset=[r for r in rows if r['circuit_condition']==label];metadata.append({'projection':projection,'accepted_swaps':accepted});print(f'{label}: {sum(r["success"] for r in subset)}/{len(cases)}',flush=True)
    output=root/c['output'];output.mkdir(parents=True,exist_ok=True);frame=pd.DataFrame(rows);frame.to_csv(output/'episodes.csv',index=False);summary=frame.groupby('circuit_condition').agg(episodes=('success','size'),successes=('success','sum'),success_rate=('success','mean'),median_final_distance_m=('final_distance_m','median'),median_terminal_progress=('normalized_terminal_progress','median'),median_successful_path_efficiency=('path_efficiency','median')).reset_index();summary.to_csv(output/'summary.csv',index=False)
    records=summary.astype(object).where(pd.notna(summary),None).to_dict(orient='records');report={'created_at':utc_now(),'dataset':'FAFB','materialization_version':783,'episodes':len(frame),'held_out_seed':c['seed'],'claim':'Projection-specific 6DoF computational nulls with one previously unused common seed; no biological perturbation','configuration':config_path.as_posix(),'configuration_sha256':file_hash(root/config_path),'rewiring':'Only named projection rewired; binary row/column degrees and each row weight multiset/sum preserved','metadata':metadata,'summary':records};save_json(output/'report.json',report);manifest_path=root/'data/manifest.json';manifest=json.loads(manifest_path.read_text(encoding='utf-8'));manifest[c['manifest_key']]={'status':'projection_specific_degree_null_6dof_completed','report':(output/'report.json').relative_to(root).as_posix(),'report_sha256':file_hash(output/'report.json'),'episodes':len(frame),'held_out_seed':c['seed']};save_json(manifest_path,manifest)


if __name__=='__main__':run(Path.cwd())
