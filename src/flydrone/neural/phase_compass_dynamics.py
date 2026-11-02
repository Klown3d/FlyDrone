"""Isolated 16-phase dynamics from compartment-specific contact transfers."""
from itertools import product
from pathlib import Path
import json
import numpy as np
import pandas as pd
import yaml
from flydrone.data.acquire import file_hash,save_json,utc_now
from flydrone.neural.phase_resolved_compass import normalize_columns


def wrap(angle):return np.angle(np.exp(1j*angle))


def advance(state,steps,c,excitation,inhibition,velocity_operator,exc_gain,inh_gain,bias,velocity,external):
    for _ in range(steps):
        drive=exc_gain*(state@excitation.T)-inh_gain*(state@inhibition.T)+velocity*(state@velocity_operator.T)+bias+external
        target=1/(1+np.exp(-np.clip(c['activation_slope']*drive,-40,40)))
        state+=c['dt_s']/c['time_constant_s']*(target-state)
    return state


def readout(state,phases):
    vector=np.sum(state*np.exp(1j*phases),axis=1);total=state.sum(axis=1)
    return np.angle(vector),np.divide(np.abs(vector),total,out=np.zeros_like(total),where=total>0),state.max(axis=1)-state.min(axis=1)


def evaluate(headings,c,phases,excitation,inhibition,velocity_operator,exc_gain,inh_gain,bias,velocity_gain,angular_sign):
    headings=np.asarray(headings);cue=c['cue_gain']*np.exp(c['cue_concentration']*(np.cos(headings[:,None]-phases)-1));zero=np.zeros_like(cue);state=np.zeros_like(cue)
    state=advance(state,round(c['cue_duration_s']/c['dt_s']),c,excitation,inhibition,velocity_operator,exc_gain,inh_gain,bias,0.,cue);cue_phase,_,_=readout(state,phases)
    dark=advance(state.copy(),round(c['dark_duration_s']/c['dt_s']),c,excitation,inhibition,velocity_operator,exc_gain,inh_gain,bias,0.,zero);dark_phase,dark_r,dark_contrast=readout(dark,phases)
    velocity=velocity_gain*angular_sign*np.deg2rad(c['turn_velocity_deg_s']);turned=advance(state.copy(),round(c['turn_duration_s']/c['dt_s']),c,excitation,inhibition,velocity_operator,exc_gain,inh_gain,bias,velocity,zero);turn_phase,turn_r,turn_contrast=readout(turned,phases);expected=wrap(cue_phase+np.deg2rad(c['turn_velocity_deg_s'])*c['turn_duration_s'])
    return {'median_dark_drift_deg':float(np.median(np.abs(np.rad2deg(wrap(dark_phase-cue_phase))))),'minimum_dark_resultant':float(dark_r.min()),'minimum_dark_contrast':float(dark_contrast.min()),'median_turn_error_deg':float(np.median(np.abs(np.rad2deg(wrap(turn_phase-expected))))),'turn_direction_accuracy':float(np.mean(np.sign(wrap(turn_phase-cue_phase))==1)),'minimum_turn_resultant':float(turn_r.min()),'minimum_turn_contrast':float(turn_contrast.min())}


def run(root: Path,config_path: Path=Path('configs/phase_compass_dynamics.yaml')) -> None:
    c=yaml.safe_load((root/config_path).read_text());data=np.load(root/c['transfers']);phases=np.deg2rad(data['phases_deg']);norm=lambda name:normalize_columns(data[name]);inhibition=norm('delta7');excitation=(norm('peg')+norm('pen_b_left')+norm('pen_b_right')+norm('pen_a_left')+norm('pen_a_right'))/5
    if c.get('velocity_operator')=='published_one_wedge':
        identity=np.eye(len(phases));velocity_operator=(np.roll(identity,1,axis=0)-np.roll(identity,-1,axis=0))/2
    else:velocity_operator=norm('pen_a_right')-norm('pen_a_left')
    output=root/c['output'];output.mkdir(parents=True,exist_ok=True);rows=[]
    for exc,inh,bias,velocity,sign in product(c['excitation_gains'],c['inhibition_gains'],c['biases'],c['velocity_gains'],c['angular_signs']):rows.append({'excitation_gain':exc,'inhibition_gain':inh,'bias':bias,'velocity_gain':velocity,'angular_sign':sign,**evaluate(np.deg2rad(c['development_headings_deg']),c,phases,excitation,inhibition,velocity_operator,exc,inh,bias,velocity,sign)})
    frame=pd.DataFrame(rows);frame['persistence_pass']=(frame.median_dark_drift_deg<=c['maximum_dark_drift_deg'])&(frame.minimum_dark_resultant>=c['minimum_dark_resultant'])&(frame.minimum_dark_contrast>=c['minimum_dark_contrast']);frame['turn_pass']=frame.persistence_pass&(frame.median_turn_error_deg<=c['maximum_turn_error_deg'])&(frame.turn_direction_accuracy==1);frame=frame.sort_values(['turn_pass','persistence_pass','median_turn_error_deg','median_dark_drift_deg'],ascending=[False,False,True,True]);frame.to_csv(output/'development_grid.csv',index=False);winner=frame.iloc[0];params={key:float(winner[key]) for key in ('excitation_gain','inhibition_gain','bias','velocity_gain','angular_sign')};held=evaluate(np.deg2rad(c['held_out_headings_deg']),c,phases,excitation,inhibition,velocity_operator,params['excitation_gain'],params['inhibition_gain'],params['bias'],params['velocity_gain'],params['angular_sign']);pd.DataFrame([{**params,**held}]).to_csv(output/'held_out.csv',index=False)
    report={'created_at':utc_now(),'dataset':'FAFB','materialization_version':783,'claim':'Isolated 16-phase engineering dynamics built from compartment-specific two-synapse contact transfers; gains and dynamics are not measured physiology','configuration':config_path.as_posix(),'configuration_sha256':file_hash(root/config_path),'source_sha256':file_hash(Path(__file__)),'transfers_sha256':file_hash(root/c['transfers']),'velocity_operator':c.get('velocity_operator','flywire_pen_a_difference'),'candidate_count':len(frame),'development_persistence_passes':int(frame.persistence_pass.sum()),'development_turn_passes':int(frame.turn_pass.sum()),'selected_parameters':params,'held_out':held};save_json(output/'report.json',report);manifest_path=root/'data/manifest.json';manifest=json.loads(manifest_path.read_text());manifest['phase_compass_dynamics']={'status':c['status'],'report':(output/'report.json').relative_to(root).as_posix(),'report_sha256':file_hash(output/'report.json'),'held_out':held};save_json(manifest_path,manifest);print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--config',type=Path,default=Path('configs/phase_compass_dynamics.yaml'))
    run(Path.cwd(),parser.parse_args().config)
