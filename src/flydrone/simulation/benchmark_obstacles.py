"""6-DoF blocked-path control and conventional safety-planner comparison."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import yaml
from flydrone.data.acquire import file_hash,save_json,utc_now
from flydrone.neural.epg_delta7 import EPGDelta7Candidate
from flydrone.simulation.benchmark_quadrotor import simulate


def run(root: Path,config_path: Path=Path('configs/quadrotor_obstacles.yaml')) -> None:
    c=yaml.safe_load((root/config_path).read_text());plant=yaml.safe_load((root/c['plant_config']).read_text());orientation=yaml.safe_load((root/c['orientation_config']).read_text());model=EPGDelta7Candidate(root,root/orientation['candidate_config'])
    output=root/c['output'];output.mkdir(parents=True,exist_ok=True);rows=[]
    cases=[(np.deg2rad(t),np.deg2rad(h)) for t in c['target_bearings_deg'] for h in c['initial_relative_headings_deg']]
    for scenario in c['scenarios']:
        for baseline in (False,True):
            label='proportional' if baseline else 'neural'
            for index,(target,heading) in enumerate(cases):
                result,_=simulate(root,c,plant,model,orientation,target,heading,baseline,False,scenario,scenario['seed']+index);rows.append(result)
            subset=[r for r in rows if r['scenario']==scenario['name'] and r['controller']==label]
            print(f"{scenario['name']} {label}: {sum(r['success'] for r in subset)}/{len(cases)} success, {sum(r['collision'] for r in subset)}/{len(cases)} collisions",flush=True)
    frame=pd.DataFrame(rows);frame.to_csv(output/'episodes.csv',index=False)
    summary=frame.groupby(['scenario','controller']).agg(episodes=('success','size'),successes=('success','sum'),collisions=('collision','sum'),median_minimum_clearance_m=('minimum_obstacle_clearance_m','median'),median_path_efficiency=('path_efficiency','median'),maximum_tilt_deg=('max_tilt_deg','max')).reset_index();summary.to_csv(output/'summary.csv',index=False)
    report={'created_at':utc_now(),'dataset':'FAFB','materialization_version':783,'episodes':len(frame),'claim':'Circular floor-to-ceiling obstacle geometry; conventional waypoint safety layer supplies a local goal; neural circuit remains yaw comparator only','configuration':config_path.as_posix(),'configuration_sha256':file_hash(root/config_path),'planner_source_sha256':file_hash(root/'src/flydrone/simulation/obstacles.py'),'simulation_source_sha256':file_hash(root/'src/flydrone/simulation/benchmark_quadrotor.py'),'summary':summary.to_dict(orient='records')}
    save_json(output/'report.json',report);manifest_path=root/'data/manifest.json';manifest=json.loads(manifest_path.read_text(encoding='utf-8'));manifest[c['manifest_key']]={'status':'conventional_obstacle_safety_layer_evaluated','report':(output/'report.json').relative_to(root).as_posix(),'report_sha256':file_hash(output/'report.json'),'episodes':len(frame)};save_json(manifest_path,manifest)


if __name__=='__main__':run(Path.cwd())
