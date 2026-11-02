"""Ablate the isolated phase-resolved compass after parameter freezing."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import yaml
from flydrone.data.acquire import file_hash,save_json,utc_now
from flydrone.neural.phase_resolved_compass import normalize_columns
from flydrone.neural.phase_compass_dynamics import evaluate


def run(root: Path,config_path: Path=Path('configs/phase_compass_dynamics_v2.yaml')) -> None:
    c=yaml.safe_load((root/config_path).read_text());base=root/c['output'];selected=json.loads((base/'report.json').read_text())['selected_parameters'];data=np.load(root/c['transfers']);phases=np.deg2rad(data['phases_deg']);norm=lambda name:normalize_columns(data[name]);delta=norm('delta7');peg=norm('peg');pen=(norm('pen_b_left')+norm('pen_b_right')+norm('pen_a_left')+norm('pen_a_right'))/4;excitation=(peg+4*pen)/5;identity=np.eye(len(phases));velocity=(np.roll(identity,1,axis=0)-np.roll(identity,-1,axis=0))/2;headings=np.deg2rad(c['held_out_headings_deg'])
    conditions=[('intact',excitation,delta,velocity),('without_delta7_inhibition',excitation,np.zeros_like(delta),velocity),('without_recurrent_excitation',np.zeros_like(excitation),delta,velocity),('without_peg_feedback',pen,delta,velocity),('without_pen_update',excitation,delta,np.zeros_like(velocity))];rng=np.random.default_rng(20260923)
    for index in range(10):conditions.append((f'independent_phase_shuffle_{index}',excitation[rng.permutation(len(phases))],delta[rng.permutation(len(phases))],velocity))
    rows=[]
    for name,exc,inh,vel in conditions:
        result=evaluate(headings,c,phases,exc,inh,vel,selected['excitation_gain'],selected['inhibition_gain'],selected['bias'],selected['velocity_gain'],selected['angular_sign']);rows.append({'condition':name,**result})
    frame=pd.DataFrame(rows);frame['persistence_pass']=(frame.median_dark_drift_deg<=c['maximum_dark_drift_deg'])&(frame.minimum_dark_resultant>=c['minimum_dark_resultant'])&(frame.minimum_dark_contrast>=c['minimum_dark_contrast']);frame['turn_pass']=frame.persistence_pass&(frame.median_turn_error_deg<=c['maximum_turn_error_deg'])&(frame.turn_direction_accuracy==1);frame.to_csv(base/'ablations.csv',index=False)
    report={'created_at':utc_now(),'claim':'Computational ablations of frozen isolated phase model; not biological perturbations','configuration':config_path.as_posix(),'configuration_sha256':file_hash(root/config_path),'source_sha256':file_hash(Path(__file__)),'selected_parameters':selected,'conditions':frame.to_dict(orient='records')};save_json(base/'ablation_report.json',report);manifest_path=root/'data/manifest.json';manifest=json.loads(manifest_path.read_text());manifest['phase_compass_ablation']={'status':'frozen_isolated_computational_ablation','report':(base/'ablation_report.json').relative_to(root).as_posix(),'report_sha256':file_hash(base/'ablation_report.json')};save_json(manifest_path,manifest);print(frame.to_string(index=False),flush=True)


if __name__=='__main__':run(Path.cwd())
