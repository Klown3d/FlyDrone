"""Stream pinned static synapses; retain PB contacts internal to selected circuit."""
from pathlib import Path
import json
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.ipc as ipc
import pyarrow.parquet as pq
from flydrone.data.acquire import file_hash, save_json, utc_now


def run(root: Path, include_boundary: bool = False) -> None:
    directory = root / 'data/processed/fafb783_epg_delta7_fc2_pfl3'
    source = root / 'data/raw/flywire_synapses_783.feather'
    stem = 'pb-synapses-with-boundary' if include_boundary else 'pb-synapses'
    destination = directory / f'{stem}.parquet'
    ids = pa.array(pd.read_csv(directory / 'nodes.csv')['root_id'].to_numpy(), type=pa.int64())
    tables = []
    with pa.memory_map(str(source)) as mapped:
        reader = ipc.open_file(mapped)
        schema = reader.schema
        for index in range(reader.num_record_batches):
            batch = reader.get_batch(index)
            pre = pc.is_in(batch.column('pre_pt_root_id'), value_set=ids)
            post = pc.is_in(batch.column('post_pt_root_id'), value_set=ids)
            endpoints = pc.or_(pre, post) if include_boundary else pc.and_(pre, post)
            mask = pc.and_(pc.equal(batch.column('neuropil'), 'PB'), endpoints)
            selected = batch.filter(mask)
            if selected.num_rows:
                tables.append(pa.Table.from_batches([selected]))
            if index % 200 == 0:
                print(f'Processed {index}/{reader.num_record_batches} batches', flush=True)
    table = pa.concat_tables(tables) if tables else pa.Table.from_batches([], schema=schema)
    pq.write_table(table, destination, compression='zstd')
    frame = table.to_pandas()
    selected_ids = ids.to_pylist()
    internal = frame.loc[frame.pre_pt_root_id.isin(selected_ids) & frame.post_pt_root_id.isin(selected_ids)]
    actual = internal.groupby(['pre_pt_root_id', 'post_pt_root_id']).size().rename('actual').reset_index()
    expected = pd.read_csv(directory / 'edges.csv')
    expected = expected.loc[expected.neuropil.eq('PB'), ['pre_pt_root_id', 'post_pt_root_id', 'syn_count']]
    comparison = expected.merge(actual, how='outer').fillna(0)
    mismatch = comparison.loc[comparison.syn_count.ne(comparison.actual)]
    mismatch.to_csv(directory / f'{stem}-count-discrepancies.csv', index=False)
    metadata = json.loads((source.with_suffix(source.suffix + '.metadata.json')).read_text())
    save_json(directory / f'{stem}.provenance.json', {
        'created_at': utc_now(), 'dataset': 'FAFB', 'materialization_version': 783,
        'source': source.relative_to(root).as_posix(), 'source_metadata': metadata,
        'filter': f'neuropil == PB AND {"either" if include_boundary else "both"} endpoints in selected nodes; no extra confidence threshold',
        'internal_rows': len(internal),
        'rows': len(frame), 'unique_synapse_ids': int(frame.id.nunique()),
        'schema_columns': schema.names, 'synaptic_area_available': False,
        'pair_count_mismatches': len(mismatch), 'output_sha256': file_hash(destination),
    })
    print(f'Extracted {len(frame)} contacts; mismatched pairs: {len(mismatch)}', flush=True)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--include-boundary', action='store_true')
    run(Path.cwd(), parser.parse_args().include_boundary)
