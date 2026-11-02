"""Acquire selected FAFB 783 synapse coordinates through authenticated CAVE."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from flydrone.data.acquire import file_hash, save_json, utc_now


def selected_root_ids(path: Path) -> list[int]:
    nodes = pd.read_csv(path, usecols=["root_id"], dtype={"root_id": "uint64"})
    return sorted({int(value) for value in nodes["root_id"]})


def select_internal_pb(frame: pd.DataFrame, root_ids: set[int], neuropil: str = "PB") -> pd.DataFrame:
    """Retain directed synapses inside the selected circuit and neuropil."""
    required = {"pre_pt_root_id", "post_pt_root_id", "neuropil"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Synapse response is missing columns: {sorted(missing)}")
    result = frame.loc[
        frame["pre_pt_root_id"].isin(root_ids)
        & frame["post_pt_root_id"].isin(root_ids)
        & frame["neuropil"].eq(neuropil)
    ].copy()
    sort_columns = [column for column in ("pre_pt_root_id", "post_pt_root_id", "id") if column in result]
    return result.sort_values(sort_columns, kind="stable").reset_index(drop=True)


def acquire(root: Path, config_path: Path) -> None:
    config: dict[str, Any] = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    token_name = config["token_environment_variable"]
    token = os.environ.get(token_name)
    if not token:
        raise RuntimeError(
            f"Missing {token_name}. Create a FlyWire CAVE token and expose it only as an environment variable."
        )
    try:
        from caveclient import CAVEclient
    except ImportError as error:
        raise RuntimeError(
            "caveclient is required for this authenticated extraction. Its official support currently ends at "
            "Python 3.12, so run this command in a separate Python 3.12 environment."
        ) from error

    ids = selected_root_ids(root / config["root_ids_file"])
    raw_dir = root / config["raw_output_dir"]
    raw_dir.mkdir(parents=True, exist_ok=True)
    client = CAVEclient(config["datastack"], auth_token=token)
    frames: list[pd.DataFrame] = []
    for start in range(0, len(ids), int(config["chunk_size"])):
        chunk = ids[start : start + int(config["chunk_size"])]
        chunk_path = raw_dir / f"pre-{start:03d}-{start + len(chunk) - 1:03d}.parquet"
        if chunk_path.exists():
            frame = pd.read_parquet(chunk_path)
        else:
            frame = client.materialize.query_view(
                config["view"],
                filter_in_dict={"pre_pt_root_id": chunk, "post_pt_root_id": ids},
                materialization_version=int(config["materialization_version"]),
                split_positions=False,
            )
            missing = set(config["required_columns"]) - set(frame.columns)
            if missing:
                raise ValueError(f"CAVE view schema changed; missing {sorted(missing)}")
            frame.to_parquet(chunk_path, index=False)
        frames.append(frame)
        print(f"  selected presynaptic IDs {start + len(chunk)}/{len(ids)}", flush=True)

    combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    processed = select_internal_pb(combined, set(ids), config["neuropil"])
    output_path = root / config["processed_output"]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    processed.to_parquet(output_path, index=False)
    provenance_path = output_path.with_suffix(".metadata.json")
    provenance = {
        "created_at": utc_now(),
        "dataset": config["dataset"],
        "datastack": config["datastack"],
        "materialization_version": config["materialization_version"],
        "view": config["view"],
        "query": "selected pre IDs AND selected post IDs; processed neuropil=PB",
        "selected_root_ids": len(ids),
        "synapses": len(processed),
        "output": output_path.relative_to(root).as_posix(),
        "output_sha256": file_hash(output_path),
        "raw_chunks": [
            {"path": path.relative_to(root).as_posix(), "sha256": file_hash(path)}
            for path in sorted(raw_dir.glob("pre-*.parquet"))
        ],
        "credentials_stored": False,
    }
    save_json(provenance_path, provenance)
    manifest_path = root / "data/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["synapse_coordinates"] = {
        "status": "downloaded_selected_circuit",
        "configuration": config_path.relative_to(root).as_posix(),
        "configuration_sha256": file_hash(config_path),
        "output": output_path.relative_to(root).as_posix(),
        "output_sha256": file_hash(output_path),
        "metadata": provenance_path.relative_to(root).as_posix(),
        "metadata_sha256": file_hash(provenance_path),
    }
    manifest["status"] = "selected_pb_synapse_coordinates_acquired_mapping_pending"
    save_json(manifest_path, manifest)
    print(json.dumps(provenance, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--config", type=Path, default=Path("configs/synapse_coordinates.yaml"))
    args = parser.parse_args()
    project_root = args.root.resolve()
    acquire(project_root, (project_root / args.config).resolve())

