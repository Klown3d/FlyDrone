"""Independent PB contact-centroid checks; retain unverified outer glomeruli."""
from pathlib import Path
import numpy as np
import pandas as pd
import yaml
from flydrone.morphology.analyze import epg_pb_columns
from flydrone.data.acquire import save_json, file_hash, utc_now


def run(root: Path) -> None:
    directory = root/'data/processed/fafb783_epg_delta7_fc2_pfl3'
    source = directory/'pb-synapses-with-boundary.parquet'
    contacts = pd.read_parquet(source)
    features = pd.read_csv(directory/'morphology-features.csv', dtype={'root_id':str})
    output = root/'results/morphology/pb-contact-validation'
    output.mkdir(parents=True, exist_ok=True)
    xyz = [f'pre_pt_position_{a}' for a in 'xyz']
    epg = features.loc[features.selected_type.eq('EPG')].copy().sort_values('root_id')
    selected = contacts.loc[contacts.pre_pt_root_id.astype(str).isin(epg.root_id)]
    centers = selected.groupby('pre_pt_root_id')[xyz].median()
    centers.index = centers.index.astype(str)
    points = centers.loc[epg.root_id].to_numpy(float)
    epg['contact_column'] = [f'PB{v:02d}' for v in epg_pb_columns(points)]
    epg['same_as_skeleton_column'] = epg.contact_column.eq(epg.geometric_column)
    for i, axis in enumerate('xyz'):
        epg[f'contact_median_{axis}_nm'] = points[:, i]
    epg['PB_output_contacts'] = selected.groupby('pre_pt_root_id').size().rename(index=str).reindex(epg.root_id).to_numpy()
    epg.to_csv(output/'epg-contact-vs-skeleton-columns.csv',index=False)
    anchors = epg.groupby('contact_column')[[f'contact_median_{a}_nm' for a in 'xyz']].mean().sort_index()
    profile_rows = []
    for cell_type in ('Delta7','PFL3'):
        ids = features.loc[features.selected_type.eq(cell_type), 'root_id']
        for direction, endpoint, prefix in [('output','pre_pt_root_id','pre'),('input','post_pt_root_id','post')]:
            rows = contacts.loc[contacts[endpoint].astype(str).isin(ids)].copy()
            positions = rows[[f'{prefix}_pt_position_{a}' for a in 'xyz']].to_numpy(float)
            distances = np.linalg.norm(positions[:,None,:]-anchors.to_numpy()[None,:,:],axis=2)
            nearest = np.argmin(distances, axis=1)
            rows['nearest_epg_anchor'] = anchors.index.to_numpy()[nearest]
            rows['distance_to_anchor_nm'] = distances[np.arange(len(rows)),nearest]
            # Terminal-anchor assignments may include PB01/PB18. Do not fabricate labels.
            rows['outer_glomerulus_ambiguous'] = rows.nearest_epg_anchor.isin(['PB02','PB17'])
            summary = rows.groupby([endpoint,'nearest_epg_anchor']).agg(
                contacts=('id','size'), median_distance_nm=('distance_to_anchor_nm','median'),
                outer_glomerulus_ambiguous=('outer_glomerulus_ambiguous','first')).reset_index().rename(columns={endpoint:'root_id'})
            summary['cell_type'] = cell_type
            summary['direction'] = direction
            profile_rows.append(summary)
    profiles = pd.concat(profile_rows,ignore_index=True)
    profiles.to_csv(output/'full-contact-anchor-profiles.csv',index=False)
    # Cosine fit to actual EPG->Delta7 counts, not target PFL3 phases.
    config = yaml.safe_load((root/'configs/epg_delta7_audit.yaml').read_text())
    delta_ids = features.loc[features.selected_type.eq('Delta7'),'root_id'].sort_values().tolist()
    ed = contacts.loc[contacts.pre_pt_root_id.astype(str).isin(epg.root_id) & contacts.post_pt_root_id.astype(str).isin(delta_ids)].copy()
    ed['column'] = ed.pre_pt_root_id.astype(str).map(dict(zip(epg.root_id,epg.contact_column)))
    table = pd.crosstab(ed.post_pt_root_id.astype(str),ed['column']).reindex(index=delta_ids,columns=anchors.index,fill_value=0)
    theta = np.deg2rad([config['epg_preferred_heading_deg'][c] for c in table.columns])
    design = np.column_stack([np.ones(len(theta)),np.cos(theta),np.sin(theta)])
    fits=[]
    for rid, values in table.iterrows():
        y=values.to_numpy(float)
        predicted=design@np.linalg.lstsq(design,y,rcond=None)[0]
        denom=np.sum((y-y.mean())**2)
        fits.append({'root_id':rid,'cosine_count_profile_r_squared':float(1-np.sum((y-predicted)**2)/denom) if denom else None})
    pd.DataFrame(fits).to_csv(output/'delta7-epg-cosine-fits.csv',index=False)
    report={'created_at':utc_now(),'dataset':'FAFB','materialization_version':783,
        'source_sha256':file_hash(source),'boundary_contacts':len(contacts),
        'epg_neurons':len(epg),'epg_columns_matching_skeleton':int(epg.same_as_skeleton_column.sum()),
        'epg_input_method':'Median of all PB presynaptic contacts for each EPG; Ward16 and PB-arc ordering; no steering fit',
        'delta7_cosine_r_squared_median':float(pd.DataFrame(fits).cosine_count_profile_r_squared.median()),
        'outer_glomeruli':'PB01/PB18 unresolved; no extrapolated anatomical labels',
        'subtype_validation':'Incomplete: nearest-anchor profiles do not establish output compartments/subtypes',
        'gate':'Anatomical mapping remains provisional; angular sign is supported independently by paper Methods',
    }
    save_json(output/'report.json',report)
    print(report,flush=True)


if __name__ == '__main__':
    run(Path.cwd())
