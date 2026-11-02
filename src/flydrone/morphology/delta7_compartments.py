"""Compare provisional Delta7 dominant outputs to archived hemibrain patterns."""
from pathlib import Path
import json
import re
import numpy as np
import pandas as pd
import yaml
from flydrone.data.acquire import save_json, file_hash, utc_now


def pb_name(index: int) -> str:
    if not 1 <= index <= 18:
        raise ValueError('PB index must be 1..18')
    return f'L{10-index}' if index <= 9 else f'R{index-9}'


def pattern_name(columns: list[str]) -> str:
    names = [pb_name(int(c[2:])) for c in columns]
    return ''.join(sorted(names, key=lambda n:(n[0],int(n[1:]))))


def run(root: Path) -> None:
    config_path = root/'configs/delta7_compartments.yaml'
    config = yaml.safe_load(config_path.read_text())
    profiles = pd.read_csv(root/config['profiles'],dtype={'root_id':str})
    outputs = profiles.loc[profiles.cell_type.eq('Delta7') & profiles.direction.eq('output')]
    published = {frozenset(re.findall(r'[LR]\d+', p)):p for p in config['published_patterns']}
    records=[]
    for rid, group in outputs.groupby('root_id',sort=True):
        top=group.nlargest(2,'contacts')
        columns=top.nearest_epg_anchor.tolist()
        fraction=float(top.contacts.sum()/group.contacts.sum())
        pattern=pattern_name(columns)
        terminal=bool(top.outer_glomerulus_ambiguous.any())
        match=published.get(frozenset(re.findall(r'[LR]\d+',pattern)))
        status='outer_glomerulus_ambiguous' if terminal else ('compatible_candidate' if match and fraction>=config['dominant_pair_minimum_contact_fraction'] else 'requires_compartment_review')
        records.append({'root_id':rid,'dominant_pair':','.join(columns),'candidate_pattern':pattern,
            'published_pattern_match':match,'dominant_pair_fraction':fraction,
            'column_index_gap':abs(int(columns[0][2:])-int(columns[1][2:])),
            'status':status,'verified_subtype':False})
    output=root/'results/morphology/delta7-compartments'
    output.mkdir(parents=True,exist_ok=True)
    summary=pd.DataFrame(records)
    summary.to_csv(output/'candidate-patterns.csv',index=False)
    contacts=pd.read_parquet(root/config['contacts'])
    anchors=pd.read_csv(root/'results/morphology/pb-contact-validation/epg-contact-vs-skeleton-columns.csv')
    xyz=[f'contact_median_{a}_nm' for a in 'xyz']
    centers=anchors.groupby('contact_column')[xyz].mean().sort_index()
    origin=centers.to_numpy().mean(axis=0)
    payload=[]
    rng=np.random.default_rng(config['seed'])
    for record in records:
        points=contacts.loc[contacts.pre_pt_root_id.astype(str).eq(record['root_id']),[f'pre_pt_position_{a}' for a in 'xyz']].to_numpy(float)
        count=len(points)
        if count>config['display_points_per_neuron']:
            points=points[rng.choice(count,config['display_points_per_neuron'],replace=False)]
        payload.append({'id':record['root_id'],'pattern':record['candidate_pattern'],'status':record['status'],
            'fraction':round(record['dominant_pair_fraction'],4),'total':count,
            'points':np.round((points-origin)/1000,2).tolist()})
    data={'neurons':payload,'anchors':[{'label':c,'point':np.round((v.to_numpy()-origin)/1000,2).tolist()} for c,v in centers.iterrows()]}
    template=Path(__file__).with_name('delta7-contacts.html').read_text(encoding='utf-8')
    viewer=output/'delta7-contacts-3d.html'
    viewer.write_text(template.replace('__DATA__',json.dumps(data,separators=(',',':'))),encoding='utf-8')
    report={'created_at':utc_now(),'dataset':'FAFB','materialization_version':783,
        'neurons':len(records),'status_counts':summary.status.value_counts().to_dict(),
        'claim':'Geometric candidate patterns only; no subtype validated and no PB01/PB18 labels inferred',
        'gap_definition':'Absolute difference of ordered PB indices, not count of intervening glomeruli',
        'config_sha256':file_hash(config_path),'profiles_sha256':file_hash(root/config['profiles']),
        'contacts_sha256':file_hash(root/config['contacts']),'viewer_sha256':file_hash(viewer),
        'view':'Real presynaptic coordinates; deterministic subsample for display only; statistics use all contacts',
        'gate':'Angular sign correction can be tested dynamically as provisional model; full anatomical validation remains open'}
    save_json(output/'report.json',report)
    print(report,flush=True)


if __name__=='__main__':
    run(Path.cwd())
