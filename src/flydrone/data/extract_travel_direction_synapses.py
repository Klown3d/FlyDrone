"""Stream the pinned FAFB table and extract Phase 6 internal synapse coordinates."""
from __future__ import annotations

from pathlib import Path
import argparse
import json

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.ipc as ipc
import yaml

from flydrone.data.acquire import file_hash, save_json, utc_now


def run(root: Path, config_path: Path) -> None:
    c = yaml.safe_load((root / config_path).read_text(encoding="utf-8"))
    nodes = pd.read_csv(root / c["nodes"], usecols=["root_id"], dtype={"root_id": "uint64"})
    selected = pa.array(nodes["root_id"].to_numpy(), type=pa.int64())
    source = root / c["source"]
    parts = []
    with pa.memory_map(str(source), "r") as stream:
        reader = ipc.open_file(stream)
        for index in range(reader.num_record_batches):
            batch = reader.get_batch(index)
            mask = pc.and_(
                pc.is_in(batch["pre_pt_root_id"], value_set=selected),
                pc.is_in(batch["post_pt_root_id"], value_set=selected),
            )
            filtered = batch.filter(mask)
            if filtered.num_rows:
                parts.append(pa.Table.from_batches([filtered]))
            if (index + 1) % 250 == 0:
                print(f"batches {index + 1}/{reader.num_record_batches}", flush=True)
        table = pa.concat_tables(parts) if parts else pa.Table.from_batches([], schema=reader.schema)
    frame = table.to_pandas()
    frame["neuropil"] = frame["neuropil"].replace({None: "UNASGD", "None": "UNASGD", "": "UNASGD"}).fillna("UNASGD")
    frame = frame.sort_values(["pre_pt_root_id", "post_pt_root_id", "id"], kind="stable").reset_index(drop=True)
    expected = pd.read_csv(root / c["expected_edges"], dtype={"pre_pt_root_id": "uint64", "post_pt_root_id": "uint64"})
    expected = expected.groupby(["pre_pt_root_id", "post_pt_root_id", "neuropil"])["syn_count"].sum().sort_index()
    observed = frame.groupby(["pre_pt_root_id", "post_pt_root_id", "neuropil"]).size().rename("syn_count").sort_index()
    if not expected.equals(observed):
        comparison = pd.concat([expected.rename("expected"), observed.rename("observed")], axis=1).fillna(0)
        bad = comparison.loc[comparison["expected"].ne(comparison["observed"])]
        raise ValueError(f"Coordinate/count mismatch in {len(bad)} pair-neuropil rows")
    output = root / c["output"]
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output, index=False, compression="gzip")
    manifest_path = root / "data/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifact = next(item for item in manifest["artifacts"] if item["local_path"] == c["source"])
    report = {
        "created_at": utc_now(), "dataset": c["dataset"], "materialization_version": c["materialization_version"],
        "claim": "Local coordinate subset with exact pair-neuropil count verification; no compartment or functional phase assignment yet.",
        "configuration": config_path.as_posix(), "configuration_sha256": file_hash(root / config_path),
        "source_path": c["source"], "source_sha256": artifact["local_sha256"],
        "selected_neurons": len(nodes), "synapses": len(frame), "pair_neuropil_rows": len(observed),
        "neuropil_counts": frame["neuropil"].value_counts().astype(int).to_dict(),
        "output": c["output"], "output_sha256": file_hash(output), "source_code_sha256": file_hash(Path(__file__)),
    }
    report_path = output.with_suffix(".report.json")
    save_json(report_path, report)
    manifest[c["manifest_key"]] = {"status": c["status"], "report": report_path.relative_to(root).as_posix(), "report_sha256": file_hash(report_path), "output": c["output"], "output_sha256": file_hash(output), "synapses": len(frame)}
    save_json(manifest_path, manifest)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/travel_direction_synapse_coordinates.yaml"))
    run(Path.cwd(), parser.parse_args().config)
