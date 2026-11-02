"""Closed-loop 6DoF tests of explicit FlyWire-circuit ablations and nulls."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import yaml

from flydrone.data.acquire import file_hash,save_json,utc_now
from flydrone.neural.epg_delta7 import EPGDelta7Candidate
from flydrone.neural.connectome_nulls import degree_preserving_rewire
from flydrone.simulation.benchmark_quadrotor import simulate


def uniform_support(weights: np.ndarray) -> np.ndarray:
    """Erase contact multiplicity while preserving every nonzero edge."""
    support=(np.asarray(weights)>0).astype(float);totals=support.sum(axis=1,keepdims=True)
    return np.divide(support,totals,out=np.zeros_like(support),where=totals>0)


def degree_preserving_variants(model: EPGDelta7Candidate,seeds: list[int]) -> list[tuple[str,dict,int]]:
    output=[]
    for seed in seeds:
        rng=np.random.default_rng(seed);variant={};stats={}
        for name,weights in [('epg_to_delta',model.epg_to_delta),('delta_to_pfl3',model.delta_to_pfl3),('fc2_weights',model.base.fc2_weights)]:
            variant[name],stats[name]=degree_preserving_rewire(weights,rng)
        variant['_accepted_swaps']=stats;output.append((f'degree_preserving_rewired_seed_{seed}',variant,seed))
    return output


def variants(model: EPGDelta7Candidate,seeds: list[int]) -> list[tuple[str,dict|None,int|None]]:
    fixed=[
        ('intact',None,None),
        ('Delta7_ablated',{'delta7_enabled':False},None),
        ('FC2_ablated',{'fc2_enabled':False},None),
        ('contact_multiplicity_uniformized',{
            'epg_to_delta':uniform_support(model.epg_to_delta),
            'delta_to_pfl3':uniform_support(model.delta_to_pfl3),
            'fc2_weights':uniform_support(model.base.fc2_weights)},None),
    ]
    randomized=[]
    for seed in seeds:
        rng=np.random.default_rng(seed)
        randomized.append((f'all_streams_row_shuffled_seed_{seed}',{
            'epg_to_delta':model.base.shuffled_rows(model.epg_to_delta,rng),
            'delta_to_pfl3':model.base.shuffled_rows(model.delta_to_pfl3,rng),
            'fc2_weights':model.base.shuffled_rows(model.base.fc2_weights,rng)},seed))
    return fixed+randomized


def finalize(root: Path,config_path: Path,frame: pd.DataFrame) -> None:
    """Write metrics; path efficiency is undefined for unsuccessful episodes."""
    c=yaml.safe_load((root/config_path).read_text());output=root/c['output'];output.mkdir(parents=True,exist_ok=True)
    frame=frame.copy();frame['success']=frame['success'].astype(bool)
    frame['normalized_terminal_progress']=1-frame['final_distance_m']/float(c['target_distance_m'])
    frame.loc[~frame['success'],'path_efficiency']=np.nan
    frame.to_csv(output/'episodes.csv',index=False)
    summary=frame.groupby(['circuit_condition','controller'],dropna=False).agg(episodes=('success','size'),successes=('success','sum'),success_rate=('success','mean'),median_final_distance_m=('final_distance_m','median'),median_terminal_progress=('normalized_terminal_progress','median'),median_successful_path_efficiency=('path_efficiency','median'),maximum_tilt_deg=('max_tilt_deg','max')).reset_index();summary.to_csv(output/'summary.csv',index=False)
    shuffled=summary[summary.circuit_condition.str.startswith('all_streams_row_shuffled')]
    summary_records=summary.astype(object).where(pd.notna(summary),None).to_dict(orient='records')
    report={'created_at':utc_now(),'dataset':'FAFB','materialization_version':783,'episodes':len(frame),'cases_per_condition':int(frame.groupby('circuit_condition').size().min()),'claim':'6DoF closed-loop computational ablations; no ablation is claimed as a biological perturbation experiment','configuration':config_path.as_posix(),'configuration_sha256':file_hash(root/config_path),'interface_source_sha256':file_hash(root/'src/flydrone/neural/steering_interface.py'),'simulation_source_sha256':file_hash(root/'src/flydrone/simulation/benchmark_quadrotor.py'),'summary':summary_records,'shuffle_success_rate_range':[float(shuffled.success_rate.min()),float(shuffled.success_rate.max())],'metric_note':'Path efficiency is reported only for successful episodes; normalized terminal progress is 1-final distance/initial target distance.'}
    save_json(output/'report.json',report);manifest_path=root/'data/manifest.json';manifest=json.loads(manifest_path.read_text(encoding='utf-8'));manifest[c['manifest_key']]={'status':'closed_loop_6dof_circuit_ablations_completed','report':(output/'report.json').relative_to(root).as_posix(),'report_sha256':file_hash(output/'report.json'),'episodes':len(frame)};save_json(manifest_path,manifest)


def run(root: Path,config_path: Path=Path('configs/quadrotor_circuit_ablation.yaml')) -> None:
    c=yaml.safe_load((root/config_path).read_text());plant=yaml.safe_load((root/c['plant_config']).read_text());orientation=yaml.safe_load((root/c['orientation_config']).read_text());model=EPGDelta7Candidate(root,root/orientation['candidate_config'])
    output=root/c['output'];output.mkdir(parents=True,exist_ok=True);cases=[(np.deg2rad(t),np.deg2rad(h)) for t in c['target_bearings_deg'] for h in c['initial_relative_headings_deg']];rows=[]
    all_variants=variants(model,[int(seed) for seed in c['shuffle_seeds']])+[('proportional',None,None)]
    for label,variant,shuffle_seed in all_variants:
        baseline=label=='proportional'
        for index,(target,heading) in enumerate(cases):
            result,_=simulate(root,c,plant,model,orientation,target,heading,baseline,False,None,0,variant,label)
            result['shuffle_seed']=shuffle_seed;rows.append(result)
        subset=[r for r in rows if r['circuit_condition']==label]
        print(f"{label}: {sum(r['success'] for r in subset)}/{len(cases)}",flush=True)
    finalize(root,config_path,pd.DataFrame(rows))


if __name__=='__main__':run(Path.cwd())
