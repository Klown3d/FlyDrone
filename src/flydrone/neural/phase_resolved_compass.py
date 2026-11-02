"""Build phase-resolved EPG→interneuron→EPG transfers by neuropil."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import yaml
from flydrone.data.acquire import file_hash,save_json,utc_now


def normalize_rows(matrix):
    totals=matrix.sum(axis=1,keepdims=True)
    return np.divide(matrix,totals,out=np.zeros_like(matrix,dtype=float),where=totals>0)


def normalize_columns(matrix):
    totals=matrix.sum(axis=0,keepdims=True)
    return np.divide(matrix,totals,out=np.zeros_like(matrix,dtype=float),where=totals>0)


def effective_transfer(inputs: np.ndarray,outputs: np.ndarray) -> np.ndarray:
    """Linear two-synapse audit: outputs[phase,cell] @ inputs[cell,phase]."""
    return normalize_columns(outputs)@normalize_rows(inputs)


def projection_matrix(edges,nodes,phase_by_id,cell_type,neuropil,side=None,output_neuropil=None):
    """Build EPG→cell→EPG transfer, optionally across two neuropils."""
    output_neuropil=neuropil if output_neuropil is None else output_neuropil
    cells=nodes.loc[nodes.selected_type.eq(cell_type)&(True if side is None else nodes.side.eq(side)),'root_id'].tolist();cell_index={rid:i for i,rid in enumerate(cells)};phases=sorted(phase_by_id.dropna().unique());phase_index={value:i for i,value in enumerate(phases)};n=len(phases)
    inputs=np.zeros((len(cells),n));outputs=np.zeros((n,len(cells)))
    for row in edges.loc[edges.neuropil.isin([neuropil,output_neuropil])].itertuples(index=False):
        if row.neuropil==neuropil and row.pre_pt_root_id in phase_by_id.index and row.post_pt_root_id in cell_index:inputs[cell_index[row.post_pt_root_id],phase_index[phase_by_id[row.pre_pt_root_id]]]+=row.syn_count
        if row.neuropil==output_neuropil and row.pre_pt_root_id in cell_index and row.post_pt_root_id in phase_by_id.index:outputs[phase_index[phase_by_id[row.post_pt_root_id]],cell_index[row.pre_pt_root_id]]+=row.syn_count
    valid=(inputs.sum(axis=1)>0)&(outputs.sum(axis=0)>0)
    return effective_transfer(inputs[valid],outputs[:,valid]),int(valid.sum()),int(inputs[valid].sum()),int(outputs[:,valid].sum())


def transfer_summary(matrix,phases_deg):
    source=np.deg2rad(phases_deg);shifts=[];resultants=[]
    for index in range(len(source)):
        weights=matrix[:,index]
        if weights.sum()==0:continue
        vector=np.sum(weights*np.exp(1j*(source-source[index])))/weights.sum();shifts.append(np.rad2deg(np.angle(vector)));resultants.append(abs(vector))
    return {'median_shift_deg':float(np.median(shifts)) if shifts else None,'minimum_resultant':float(np.min(resultants)) if resultants else None,'median_resultant':float(np.median(resultants)) if resultants else None,'sources_defined':len(shifts)}


def run(root: Path,config_path: Path=Path('configs/phase_resolved_compass.yaml')) -> None:
    c=yaml.safe_load((root/config_path).read_text());source=root/c['extraction'];output=root/c['output'];output.mkdir(parents=True,exist_ok=True);nodes=pd.read_csv(source/'nodes.csv',dtype={'root_id':str});edges=pd.read_csv(source/'edges.csv',dtype={'pre_pt_root_id':str,'post_pt_root_id':str})
    features=pd.read_csv(root/c['steering_features'],dtype={'root_id':str});phase_config=yaml.safe_load((root/c['epg_phase_config']).read_text());phase_by_id=features.loc[features.selected_type.eq('EPG')].set_index('root_id').geometric_column.map(phase_config['epg_preferred_heading_deg']);phases=np.array(sorted(phase_by_id.unique()),float)
    specifications=[('delta7','Delta7','PB',None),('peg','PEG','EB',None),('pen_a_left','PEN_a(PEN1)','EB','left'),('pen_a_right','PEN_a(PEN1)','EB','right'),('pen_b_left','PEN_b(PEN2)','EB','left'),('pen_b_right','PEN_b(PEN2)','EB','right')];matrices={};records=[]
    overrides=c.get('projection_compartments',{})
    for label,cell_type,default_neuropil,side in specifications:
        compartments=overrides.get(label,{});input_neuropil=compartments.get('input',default_neuropil);output_neuropil=compartments.get('output',default_neuropil)
        matrix,cells,inputs,outputs=projection_matrix(edges,nodes,phase_by_id,cell_type,input_neuropil,side,output_neuropil);matrices[label]=matrix;records.append({'projection':label,'cell_type':cell_type,'side':side,'input_neuropil':input_neuropil,'output_neuropil':output_neuropil,'bidirectionally_connected_cells':cells,'input_contacts':inputs,'output_contacts':outputs,**transfer_summary(matrix,phases)})
    np.savez_compressed(output/'transfers.npz',phases_deg=phases,**matrices);summary=pd.DataFrame(records);summary.to_csv(output/'summary.csv',index=False)
    report={'created_at':utc_now(),'dataset':'FAFB','materialization_version':783,'claim':'Phase-resolved linear two-synapse contact transfer audit; not measured synaptic gain or neural dynamics','configuration':config_path.as_posix(),'configuration_sha256':file_hash(root/config_path),'source_sha256':file_hash(Path(__file__)),'edges_sha256':file_hash(source/'edges.csv'),'summary':records};save_json(output/'report.json',report)
    manifest_path=root/'data/manifest.json';manifest=json.loads(manifest_path.read_text(encoding='utf-8'));manifest[c['manifest_key']]={'status':c['status'],'report':(output/'report.json').relative_to(root).as_posix(),'report_sha256':file_hash(output/'report.json'),'transfers_sha256':file_hash(output/'transfers.npz')};save_json(manifest_path,manifest);print(summary.to_string(index=False),flush=True)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=Path('configs/phase_resolved_compass.yaml'))
    run(Path.cwd(),parser.parse_args().config)
