"""Run-once prospective equivalence gate for PFL2 high-level advance."""
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
    spec=yaml.safe_load((root/config_path).read_text());output=root/spec['output'];report_path=output/'report.json'
    if spec.get('run_once') and report_path.exists():raise RuntimeError(f'Prospective report already exists: {report_path}')
    base=yaml.safe_load((root/spec['base_config']).read_text());c={**base,**spec};plant=yaml.safe_load((root/c['plant_config']).read_text());orientation=yaml.safe_load((root/c['orientation_config']).read_text());model=EPGDelta7Candidate(root,root/orientation['candidate_config']);pfl2=PFL2SteeringController(root,root/c['pfl2_steering_config']);advance=PFL2AdvanceController(root/c['pfl2_advance_config']);cases=[(np.deg2rad(t),np.deg2rad(h)) for t in c['target_bearings_deg'] for h in c['initial_relative_headings_deg']];rows=[]
    for label,enabled in [('pfl2_advance',True),('angular_advance',False)]:
        for scenario in c['scenarios']:
            for index,(target,heading) in enumerate(cases):
                result,_=simulate(root,c,plant,model,orientation,target,heading,False,False,scenario,int(scenario['seed'])+index,heading_mode='direct',controller_label=label,pfl2_controller=pfl2,pfl2_enabled=True,advance_controller=advance,neural_advance_enabled=enabled);rows.append(result)
    frame=pd.DataFrame(rows);output.mkdir(parents=True,exist_ok=True);frame.to_csv(output/'episodes.csv',index=False);summary=frame.groupby('controller',as_index=False).agg(episodes=('success','size'),successes=('success','sum'),median_arrival_time_s=('arrival_time_s','median'),median_path_efficiency=('path_efficiency','median'),median_maximum_cross_track_m=('maximum_absolute_cross_track_m','median'),maximum_motor_saturation_fraction=('motor_saturation_fraction','max'))
    s=summary.set_index('controller');p=s.loc['pfl2_advance'];a=s.loc['angular_advance'];g=c['gate'];effects={'success_deficit':int(a.successes-p.successes),'arrival_time_cost_s':float(p.median_arrival_time_s-a.median_arrival_time_s),'efficiency_cost':float(a.median_path_efficiency-p.median_path_efficiency),'cross_track_cost_m':float(p.median_maximum_cross_track_m-a.median_maximum_cross_track_m)}
    criteria={'pfl2_successes':bool(p.successes>=g['minimum_pfl2_successes']),'success_deficit':bool(effects['success_deficit']<=g['maximum_success_deficit']),'arrival_time_cost':bool(effects['arrival_time_cost_s']<=g['maximum_arrival_time_cost_s']),'efficiency_cost':bool(effects['efficiency_cost']<=g['maximum_efficiency_cost']),'cross_track_cost':bool(effects['cross_track_cost_m']<=g['maximum_cross_track_cost_m']),'motor_saturation':bool(p.maximum_motor_saturation_fraction<=g['maximum_motor_saturation_fraction'])}
    report={'created_at':utc_now(),'status':'immutable_run_once_prospective_result','dataset':'FAFB','materialization_version':783,'claim':'Prospective equivalence gate for PFL2 advance; squared mapping and distance braking are engineering choices.','configuration':config_path.as_posix(),'configuration_sha256':file_hash(root/config_path),'source_sha256':file_hash(Path(__file__)),'advance_source_sha256':file_hash(root/'src/flydrone/neural/pfl2_advance.py'),'episodes':len(frame),'effects':effects,'criteria':criteria,'passes_prospective_gate':all(criteria.values()),'summary':summary.to_dict(orient='records')};save_json(report_path,report);manifest_path=root/'data/manifest.json';manifest=json.loads(manifest_path.read_text());manifest[c['manifest_key']]={'status':'prospective_gate_completed','report':report_path.relative_to(root).as_posix(),'report_sha256':file_hash(report_path),'passed':report['passes_prospective_gate']};save_json(manifest_path,manifest);print(json.dumps(report,indent=2),flush=True);return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',type=Path,default=Path('configs/quadrotor_pfl2_advance_prospective.yaml'));run(Path.cwd(),p.parse_args().config)
