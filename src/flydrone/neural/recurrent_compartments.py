"""Separate recurrent compass contacts and EPG phase relations by neuropil."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import yaml
from flydrone.data.acquire import file_hash,save_json,utc_now
from flydrone.neural.recurrent_compass_map import weighted_phase,circular_difference


def projection_compartments(edges: pd.DataFrame) -> pd.DataFrame:
    grouped=edges.groupby(['pre_type','post_type','neuropil'],as_index=False).syn_count.sum()
    grouped['projection_contacts']=grouped.groupby(['pre_type','post_type']).syn_count.transform('sum')
    grouped['projection_fraction']=grouped.syn_count/grouped.projection_contacts
    return grouped.sort_values(['pre_type','post_type','syn_count'],ascending=[True,True,False])


def run(root: Path,config_path: Path=Path('configs/recurrent_compartment_audit.yaml')) -> None:
    c=yaml.safe_load((root/config_path).read_text());source=root/c['extraction'];output=root/c['output'];output.mkdir(parents=True,exist_ok=True)
    edges=pd.read_csv(source/'edges.csv',dtype={'pre_pt_root_id':str,'post_pt_root_id':str});nodes=pd.read_csv(source/'nodes.csv',dtype={'root_id':str});types=nodes.set_index('root_id').selected_type
    edges['pre_type']=edges.pre_pt_root_id.map(types);edges['post_type']=edges.post_pt_root_id.map(types)
    compartments=projection_compartments(edges);compartments.to_csv(output/'projection_compartments.csv',index=False)
    features=pd.read_csv(root/c['steering_features'],dtype={'root_id':str});phase_config=yaml.safe_load((root/c['epg_phase_config']).read_text());epg=features.loc[features.selected_type.eq('EPG'),['root_id','geometric_column']].copy();epg['phase_rad']=epg.geometric_column.map(phase_config['epg_preferred_heading_deg']).map(np.deg2rad);phases=epg.set_index('root_id').phase_rad
    rows=[];targets=nodes.loc[nodes.selected_type.isin(c['target_types'])]
    for cell in targets.itertuples(index=False):
        for neuropil in c['neuropils']:
            incoming=edges.loc[edges.neuropil.eq(neuropil)&edges.post_pt_root_id.eq(cell.root_id)&edges.pre_pt_root_id.isin(phases.index)]
            outgoing=edges.loc[edges.neuropil.eq(neuropil)&edges.pre_pt_root_id.eq(cell.root_id)&edges.post_pt_root_id.isin(phases.index)]
            input_phase,input_r=weighted_phase(phases.loc[incoming.pre_pt_root_id].to_numpy(),incoming.syn_count.to_numpy());output_phase,output_r=weighted_phase(phases.loc[outgoing.post_pt_root_id].to_numpy(),outgoing.syn_count.to_numpy())
            shift=circular_difference(output_phase,input_phase) if np.isfinite(input_phase) and np.isfinite(output_phase) else np.nan
            rows.append({'root_id':cell.root_id,'type':cell.selected_type,'side':cell.side,'neuropil':neuropil,'epg_input_contacts':int(incoming.syn_count.sum()),'epg_output_contacts':int(outgoing.syn_count.sum()),'input_phase_deg':float(np.rad2deg(input_phase)),'input_resultant_length':input_r,'output_phase_deg':float(np.rad2deg(output_phase)),'output_resultant_length':output_r,'output_minus_input_phase_deg':float(np.rad2deg(shift))})
    frame=pd.DataFrame(rows);frame.to_csv(output/'cell_neuropil_phase_map.csv',index=False)
    usable=frame.loc[(frame.epg_input_contacts>0)&(frame.epg_output_contacts>0)]
    summary=usable.groupby(['type','side','neuropil']).agg(neurons_with_bidirectional_epg=('root_id','size'),input_contacts=('epg_input_contacts','sum'),output_contacts=('epg_output_contacts','sum'),median_shift_deg=('output_minus_input_phase_deg','median'),median_input_resultant=('input_resultant_length','median'),median_output_resultant=('output_resultant_length','median')).reset_index();summary.to_csv(output/'phase_summary.csv',index=False)
    report={'created_at':utc_now(),'dataset':'FAFB','materialization_version':783,'claim':'Anatomical contact audit by reported neuropil; no sub-neuropil compartment, dynamics, gain, or memory inferred','configuration':config_path.as_posix(),'configuration_sha256':file_hash(root/config_path),'source_sha256':file_hash(Path(__file__)),'edges_sha256':file_hash(source/'edges.csv'),'projection_rows':len(compartments),'cell_neuropil_rows':len(frame),'phase_summary':summary.to_dict(orient='records')};save_json(output/'report.json',report)
    manifest_path=root/'data/manifest.json';manifest=json.loads(manifest_path.read_text(encoding='utf-8'));manifest[c['manifest_key']]={'status':c['status'],'report':(output/'report.json').relative_to(root).as_posix(),'report_sha256':file_hash(output/'report.json'),'projection_rows':len(compartments)};save_json(manifest_path,manifest)


if __name__=='__main__':run(Path.cwd())
