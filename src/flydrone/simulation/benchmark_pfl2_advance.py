"""Development comparison of PFL2 and angular forward-speed modulation."""
from pathlib import Path
import argparse,json
import numpy as np
import pandas as pd
import yaml
from flydrone.data.acquire import file_hash,save_json,utc_now
from flydrone.neural.epg_delta7 import EPGDelta7Candidate
from flydrone.neural.pfl2_steering import PFL2SteeringController
from flydrone.neural.pfl2_advance import PFL2AdvanceController
from flydrone.simulation.benchmark_quadrotor import simulate


def run(root:Path,config_path:Path)->dict:
    spec=yaml.safe_load((root/config_path).read_text());base=yaml.safe_load((root/spec['base_config']).read_text());c={**base,**spec};plant=yaml.safe_load((root/c['plant_config']).read_text());orientation=yaml.safe_load((root/c['orientation_config']).read_text());model=EPGDelta7Candidate(root,root/orientation['candidate_config']);pfl2=PFL2SteeringController(root,root/c['pfl2_steering_config']);advance=PFL2AdvanceController(root/c['pfl2_advance_config']);cases=[(np.deg2rad(t),np.deg2rad(h)) for t in c['target_bearings_deg'] for h in c['initial_relative_headings_deg']];rows=[]
    for label,enabled in [('pfl2_advance',True),('angular_advance',False)]:
        for index,(target,heading) in enumerate(cases):
            result,_=simulate(root,c,plant,model,orientation,target,heading,False,False,c['scenario'],int(c['scenario']['seed'])+index,heading_mode='direct',controller_label=label,pfl2_controller=pfl2,pfl2_enabled=True,advance_controller=advance,neural_advance_enabled=enabled);rows.append(result)
    frame=pd.DataFrame(rows);output=root/c['output'];output.mkdir(parents=True,exist_ok=True);frame.to_csv(output/'episodes.csv',index=False);summary=frame.groupby('controller',as_index=False).agg(episodes=('success','size'),successes=('success','sum'),median_arrival_time_s=('arrival_time_s','median'),median_path_efficiency=('path_efficiency','median'),median_maximum_cross_track_m=('maximum_absolute_cross_track_m','median'),median_advance_fraction=('mean_advance_fraction','median'))
    report={'created_at':utc_now(),'dataset':'FAFB','materialization_version':783,'claim':'Development-only PFL2 high-level advance modulation; squared output mapping and distance braking are engineering choices.','configuration':config_path.as_posix(),'configuration_sha256':file_hash(root/config_path),'source_sha256':file_hash(Path(__file__)),'episodes':len(frame),'summary':summary.to_dict(orient='records')};save_json(output/'report.json',report);manifest_path=root/'data/manifest.json';manifest=json.loads(manifest_path.read_text());manifest[c['manifest_key']]={'status':'development_diagnostic_completed','report':(output/'report.json').relative_to(root).as_posix(),'report_sha256':file_hash(output/'report.json')};save_json(manifest_path,manifest);print(json.dumps(report,indent=2),flush=True);return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',type=Path,default=Path('configs/quadrotor_pfl2_advance_development.yaml'));run(Path.cwd(),p.parse_args().config)
