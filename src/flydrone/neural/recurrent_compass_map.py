"""Infer PEN/PEG input-output phase shifts only from EPG contact counts."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import yaml
from flydrone.data.acquire import file_hash,save_json,utc_now


def weighted_phase(phases: np.ndarray,weights: np.ndarray) -> tuple[float,float]:
    """Return circular mean and resultant length; no functional gain is inferred."""
    if len(phases)==0 or weights.sum()<=0:return float('nan'),float('nan')
    vector=np.sum(weights*np.exp(1j*phases))/weights.sum()
    return float(np.angle(vector)),float(abs(vector))


def circular_difference(output_phase: float,input_phase: float) -> float:
    return float(np.angle(np.exp(1j*(output_phase-input_phase))))


def run(root: Path,config_path: Path=Path('configs/recurrent_compass_map.yaml')) -> None:
    c=yaml.safe_load((root/config_path).read_text());source=root/c['recurrent_extraction'];output=root/c['output'];output.mkdir(parents=True,exist_ok=True)
    edges=pd.read_csv(source/'edges_by_pair.csv',dtype={'pre_pt_root_id':str,'post_pt_root_id':str});nodes=pd.read_csv(source/'nodes.csv',dtype={'root_id':str})
    features=pd.read_csv(root/c['steering_features'],dtype={'root_id':str});phase_config=yaml.safe_load((root/c['epg_phase_config']).read_text())
    epg=features.loc[features.selected_type.eq('EPG'),['root_id','geometric_column']].copy();epg['phase_rad']=epg.geometric_column.map(phase_config['epg_preferred_heading_deg']).map(np.deg2rad)
    if epg.phase_rad.isna().any():raise ValueError('Every EPG requires a provisional anatomical phase')
    phases=epg.set_index('root_id').phase_rad;metadata=nodes.set_index('root_id');rows=[]
    targets=nodes.loc[nodes.selected_type.isin(c['target_types'])]
    for cell in targets.itertuples(index=False):
        incoming=edges.loc[edges.post_pt_root_id.eq(cell.root_id)&edges.pre_pt_root_id.isin(phases.index)]
        outgoing=edges.loc[edges.pre_pt_root_id.eq(cell.root_id)&edges.post_pt_root_id.isin(phases.index)]
        input_phase,input_r=weighted_phase(phases.loc[incoming.pre_pt_root_id].to_numpy(),incoming.syn_count.to_numpy())
        output_phase,output_r=weighted_phase(phases.loc[outgoing.post_pt_root_id].to_numpy(),outgoing.syn_count.to_numpy())
        rows.append({'root_id':cell.root_id,'type':cell.selected_type,'side':cell.side,
                     'epg_input_contacts':int(incoming.syn_count.sum()),'epg_output_contacts':int(outgoing.syn_count.sum()),
                     'input_phase_deg':float(np.rad2deg(input_phase)),'input_resultant_length':input_r,
                     'output_phase_deg':float(np.rad2deg(output_phase)),'output_resultant_length':output_r,
                     'output_minus_input_phase_deg':float(np.rad2deg(circular_difference(output_phase,input_phase)))})
    frame=pd.DataFrame(rows);frame.to_csv(output/'cell_phase_map.csv',index=False)
    summary=frame.groupby(['type','side']).agg(neurons=('root_id','size'),median_shift_deg=('output_minus_input_phase_deg','median'),mean_shift_deg=('output_minus_input_phase_deg','mean'),minimum_shift_deg=('output_minus_input_phase_deg','min'),maximum_shift_deg=('output_minus_input_phase_deg','max'),median_input_resultant=('input_resultant_length','median'),median_output_resultant=('output_resultant_length','median'),input_contacts=('epg_input_contacts','sum'),output_contacts=('epg_output_contacts','sum')).reset_index();summary.to_csv(output/'summary.csv',index=False)
    report={'created_at':utc_now(),'dataset':'FAFB','materialization_version':783,'claim':'Anatomical circular phase audit from EPG contact counts; phases inherit provisional EPG column mapping; no time constant, gain, firing rate, angular-velocity input, or memory performance inferred','configuration':config_path.as_posix(),'configuration_sha256':file_hash(root/config_path),'source_sha256':file_hash(Path(__file__)),'edges_sha256':file_hash(source/'edges_by_pair.csv'),'nodes_sha256':file_hash(source/'nodes.csv'),'features_sha256':file_hash(root/c['steering_features']),'summary':summary.to_dict(orient='records')};save_json(output/'report.json',report)
    manifest_path=root/'data/manifest.json';manifest=json.loads(manifest_path.read_text(encoding='utf-8'));manifest[c['manifest_key']]={'status':c['status'],'report':(output/'report.json').relative_to(root).as_posix(),'report_sha256':file_hash(output/'report.json'),'neurons':len(frame)};save_json(manifest_path,manifest)


if __name__=='__main__':run(Path.cwd())
