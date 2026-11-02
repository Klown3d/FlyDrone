"""Engineering rate-model gate for the FAFB recurrent compass candidate."""
from itertools import product
from pathlib import Path
import json
import numpy as np
import pandas as pd
import yaml
from flydrone.data.acquire import file_hash,save_json,utc_now


def wrap(angle):return np.angle(np.exp(1j*angle))


def normalized_signed_matrix(nodes: pd.DataFrame,edges: pd.DataFrame,compartment_gated: bool=False) -> np.ndarray:
    ids=nodes.root_id.tolist();index={rid:i for i,rid in enumerate(ids)};matrix=np.zeros((len(ids),len(ids)))
    metadata=nodes.set_index('root_id');signs=metadata.selected_type.map(lambda value:-1. if value=='Delta7' else 1.)
    if compartment_gated:
        if 'neuropil' not in edges:raise ValueError('Compartment-gated matrix requires neuropil labels')
        pre=edges.pre_pt_root_id.map(metadata.selected_type);post=edges.post_pt_root_id.map(metadata.selected_type)
        delta=pre.eq('Delta7')|post.eq('Delta7');pen=pre.str.startswith('PEN_')&post.str.startswith('PEN_')
        keep=(delta&edges.neuropil.eq('PB'))|(~delta&~pen&edges.neuropil.eq('EB'))|(pen&edges.neuropil.eq('NO'))
        edges=edges.loc[keep]
    for row in edges.itertuples(index=False):matrix[index[row.post_pt_root_id],index[row.pre_pt_root_id]]+=row.syn_count*signs[row.pre_pt_root_id]
    scale=np.abs(matrix).sum(axis=1,keepdims=True)
    return np.divide(matrix,scale,out=np.zeros_like(matrix),where=scale>0)


def readout(state: np.ndarray,epg_indices: np.ndarray,epg_phases: np.ndarray):
    activity=state[:,epg_indices];vector=np.sum(activity*np.exp(1j*epg_phases),axis=1);total=activity.sum(axis=1)
    return np.angle(vector),np.divide(np.abs(vector),total,out=np.zeros_like(total),where=total>0),activity.max(axis=1)-activity.min(axis=1)


def advance(state,steps,dt,tau,matrix,gain,bias,slope,external):
    for _ in range(steps):
        drive=gain*(state@matrix.T)+bias+external
        target=1/(1+np.exp(-np.clip(slope*drive,-40,40)))
        state+=dt/tau*(target-state)
    return state


def evaluate(headings,c,nodes,matrix,epg_indices,epg_phases,recurrent_gain,bias,velocity_gain,angular_sign):
    headings=np.asarray(headings);episodes=len(headings);n=len(nodes);dt=c['dt_s'];tau=c['time_constant_s']
    cue=np.zeros((episodes,n));cue[:,epg_indices]=c['cue_gain']*np.exp(c['cue_concentration']*(np.cos(headings[:,None]-epg_phases)-1))
    zero=np.zeros_like(cue);state=np.zeros_like(cue)
    state=advance(state,round(c['cue_duration_s']/dt),dt,tau,matrix,recurrent_gain,bias,c['activation_slope'],cue)
    cue_phase,_,_=readout(state,epg_indices,epg_phases)
    dark=advance(state.copy(),round(c['dark_duration_s']/dt),dt,tau,matrix,recurrent_gain,bias,c['activation_slope'],zero)
    dark_phase,dark_r,dark_contrast=readout(dark,epg_indices,epg_phases)
    velocity=np.zeros_like(cue);pen=nodes.selected_type.eq('PEN_a(PEN1)').to_numpy();side=nodes.side.map({'left':-1.,'right':1.}).fillna(0).to_numpy();velocity[:,pen]=velocity_gain*angular_sign*side[pen]*np.deg2rad(c['turn_velocity_deg_s'])
    turned=advance(state.copy(),round(c['turn_duration_s']/dt),dt,tau,matrix,recurrent_gain,bias,c['activation_slope'],velocity)
    turn_phase,turn_r,turn_contrast=readout(turned,epg_indices,epg_phases);expected=wrap(cue_phase+np.deg2rad(c['turn_velocity_deg_s'])*c['turn_duration_s'])
    return {'median_dark_drift_deg':float(np.median(np.abs(np.rad2deg(wrap(dark_phase-cue_phase))))),'minimum_dark_resultant':float(dark_r.min()),'minimum_dark_contrast':float(dark_contrast.min()),'median_turn_error_deg':float(np.median(np.abs(np.rad2deg(wrap(turn_phase-expected))))),'turn_direction_accuracy':float(np.mean(np.sign(wrap(turn_phase-cue_phase))==1)),'minimum_turn_resultant':float(turn_r.min()),'minimum_turn_contrast':float(turn_contrast.min())}


def run(root: Path,config_path: Path=Path('configs/recurrent_dynamics.yaml')) -> None:
    c=yaml.safe_load((root/config_path).read_text());source=root/c['extraction'];output=root/c['output'];output.mkdir(parents=True,exist_ok=True)
    nodes=pd.read_csv(source/'nodes.csv',dtype={'root_id':str});edge_file='edges.csv' if c.get('compartment_gated',False) else 'edges_by_pair.csv';edges=pd.read_csv(source/edge_file,dtype={'pre_pt_root_id':str,'post_pt_root_id':str});matrix=normalized_signed_matrix(nodes,edges,bool(c.get('compartment_gated',False)))
    features=pd.read_csv(root/c['steering_features'],dtype={'root_id':str});phase_config=yaml.safe_load((root/c['epg_phase_config']).read_text());phase_by_id=features.loc[features.selected_type.eq('EPG')].set_index('root_id').geometric_column.map(phase_config['epg_preferred_heading_deg']).map(np.deg2rad);epg_mask=nodes.selected_type.eq('EPG').to_numpy();epg_indices=np.flatnonzero(epg_mask);epg_phases=nodes.loc[epg_mask,'root_id'].map(phase_by_id).to_numpy(float)
    rows=[]
    for gain,bias,velocity,sign in product(c['recurrent_gains'],c['biases'],c['velocity_gains'],c['angular_signs']):
        result=evaluate(np.deg2rad(c['development_headings_deg']),c,nodes,matrix,epg_indices,epg_phases,gain,bias,velocity,sign);rows.append({'recurrent_gain':gain,'bias':bias,'velocity_gain':velocity,'angular_sign':sign,**result})
    frame=pd.DataFrame(rows);frame['persistence_pass']=(frame.median_dark_drift_deg<=c['maximum_dark_drift_deg'])&(frame.minimum_dark_resultant>=c['minimum_dark_resultant'])&(frame.minimum_dark_contrast>=c['minimum_dark_contrast']);frame['turn_pass']=frame.persistence_pass&(frame.median_turn_error_deg<=c['maximum_turn_error_deg'])&(frame.turn_direction_accuracy==1);frame=frame.sort_values(['turn_pass','persistence_pass','median_turn_error_deg','median_dark_drift_deg'],ascending=[False,False,True,True]);frame.to_csv(output/'development_grid.csv',index=False)
    winner=frame.iloc[0];params={key:float(winner[key]) for key in ('recurrent_gain','bias','velocity_gain','angular_sign')};held=evaluate(np.deg2rad(c['held_out_headings_deg']),c,nodes,matrix,epg_indices,epg_phases,**params);pd.DataFrame([{**params,**held}]).to_csv(output/'held_out.csv',index=False)
    report={'created_at':utc_now(),'dataset':'FAFB','materialization_version':783,'claim':'Isolated engineering rate-model gate; contact matrix and type-level transmitter signs are anatomical, while all gains, time constant, bias, saturation, cue and velocity interface are engineering parameters','configuration':config_path.as_posix(),'configuration_sha256':file_hash(root/config_path),'source_sha256':file_hash(Path(__file__)),'edges_sha256':file_hash(source/edge_file),'compartment_gated':bool(c.get('compartment_gated',False)),'candidate_count':len(frame),'development_persistence_passes':int(frame.persistence_pass.sum()),'development_turn_passes':int(frame.turn_pass.sum()),'selected_parameters':params,'held_out':held};save_json(output/'report.json',report)
    manifest_path=root/'data/manifest.json';manifest=json.loads(manifest_path.read_text(encoding='utf-8'));manifest['recurrent_dynamics']={'status':c['status'],'report':(output/'report.json').relative_to(root).as_posix(),'report_sha256':file_hash(output/'report.json'),'held_out':held};save_json(manifest_path,manifest);print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--config',type=Path,default=Path('configs/recurrent_dynamics.yaml'))
    run(Path.cwd(),parser.parse_args().config)
