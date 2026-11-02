"""Acquire and validate public precomputed FlyWire 783 skeleton morphology."""
from __future__ import annotations

import argparse
import csv
import json
import struct
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import yaml

from flydrone.data.acquire import file_hash, save_json, utc_now


def parse_header(path: Path) -> dict[str, int]:
    """Validate the documented Neuroglancer skeleton binary layout."""
    size = path.stat().st_size
    with path.open("rb") as stream:
        raw = stream.read(4)
        if len(raw) != 4:
            raise ValueError(f"Truncated skeleton: {path.name}")
        (vertices,) = struct.unpack("<I", raw)
        if vertices < 2:
            raise ValueError(f"Invalid vertex count: {path.name}")
        raw = stream.read(4)
        if len(raw) != 4:
            raise ValueError(f"Missing edge count: {path.name}")
        (edges,) = struct.unpack("<I", raw)
        if edges < 1:
            raise ValueError(f"Invalid edge count: {path.name}")
    # 3 float32 coordinates and one float32 radius per vertex; two uint32s per edge.
    expected = 8 + vertices * 12 + edges * 8 + vertices * 4
    if expected != size:
        raise ValueError(f"Unexpected skeleton layout: {path.name}, {size} != {expected}")
    return {"vertices": vertices, "edges": edges, "bytes": size}


def fetch(url: str, path: Path) -> tuple[str, str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "FlyDrone-research/0.1"})
    with urllib.request.urlopen(req, timeout=90) as response, temp.open("wb") as stream:
        if "text/html" in response.headers.get("Content-Type", ""):
            raise ValueError(f"HTML returned for {url}")
        while chunk := response.read(1024 * 1024):
            stream.write(chunk)
        resolved = response.url
    temp.replace(path)
    return resolved, utc_now()


def acquire(root: Path, config_path: Path) -> None:
    config: dict[str, Any] = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    manifest_path = root / "data/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if config["dataset"] != manifest["dataset"]["specimen_dataset"] or config["materialization_version"] != manifest["dataset"]["materialization_version"]:
        raise ValueError("Morphology and connectivity versions differ")
    nodes_path = root / config.get("nodes", str(Path(manifest["extraction"]["output_dir"]) / "nodes.csv"))
    with nodes_path.open(encoding="utf-8", newline="") as stream:
        ids = sorted({str(int(row["root_id"])) for row in csv.DictReader(stream)}, key=int)
    expected_count = config.get("expected_neuron_count", manifest["neuron_count"])
    if len(ids) != expected_count:
        raise ValueError("Node count mismatch")
    skeleton_dir = root / config["skeleton_dir"]
    def one(root_id: str) -> dict[str, Any]:
        path = skeleton_dir / f"{root_id}.bin"
        retrieved_at = None
        resolved = f"{config['skeleton_base_url']}/{root_id}"
        if not path.exists():
            resolved, retrieved_at = fetch(resolved, path)
        layout = parse_header(path)
        return {"root_id": root_id, "path": path.relative_to(root).as_posix(),
                "source_url": resolved, "retrieved_at": retrieved_at,
                "sha256": file_hash(path), **layout}
    print(f"Fetching {len(ids)} FlyWire 783 skeletons", flush=True)
    entries = []
    with ThreadPoolExecutor(max_workers=config["workers"]) as pool:
        futures = {pool.submit(one, rid): rid for rid in ids}
        for i, future in enumerate(as_completed(futures), 1):
            entries.append(future.result())
            if i % 20 == 0 or i == len(ids):
                print(f"  skeletons {i}/{len(ids)}", flush=True)
    entries.sort(key=lambda item: int(item["root_id"]))
    atlas = root / config["atlas_path"]
    atlas_retrieved_at = None
    resolved_atlas = config["atlas_url"]
    if not atlas.exists():
        resolved_atlas, atlas_retrieved_at = fetch(config["atlas_url"], atlas)
    if atlas.stat().st_size != config["atlas_size_bytes"] or file_hash(atlas, "git-blob-sha1") != config["atlas_git_blob_sha1"]:
        raise ValueError("Pinned atlas volume changed")
    index = {"dataset": manifest["dataset"], "created_at": utc_now(),
             "format": {"type": "neuroglancer_skeletons", "coordinates": "float32 nanometers", "radius": "float32 nanometers", "edges": "uint32 vertex-index pairs"},
             "skeleton_source": config["skeleton_base_url"], "skeleton_source_code_reference": "https://github.com/navis-org/fafbseg-py/blob/master/fafbseg/flywire/skeletonize.py",
             "skeleton_license": None, "skeleton_license_note": "No license assertion made for morphology data; cite FlyWire and clarify redistribution terms before publishing raw files.",
             "atlas": {"path": atlas.relative_to(root).as_posix(), "source_url": resolved_atlas,
                       "retrieved_at": atlas_retrieved_at, "bytes": atlas.stat().st_size,
                       "sha256": file_hash(atlas), "git_blob_sha1": config["atlas_git_blob_sha1"],
                       "fafbseg_commit": config["fafbseg_commit"], "source_citation": "https://doi.org/10.5281/zenodo.10567",
                       "license": None, "license_note": "Transformed atlas file license not independently established."},
             "skeleton_count": len(entries), "total_vertices": sum(x["vertices"] for x in entries),
             "total_edges": sum(x["edges"] for x in entries), "total_bytes": sum(x["bytes"] for x in entries),
             "skeletons": entries}
    index_path = root / config["index_path"]
    save_json(index_path, index)
    record = {"status": "downloaded_verified", "configuration": config_path.relative_to(root).as_posix(),
              "configuration_sha256": file_hash(config_path), "index": index_path.relative_to(root).as_posix(),
              "index_sha256": file_hash(index_path), "skeleton_count": len(entries),
              "atlas_path": atlas.relative_to(root).as_posix()}
    if config.get("manifest_key"):
        manifest.setdefault("additional_morphologies", {})[config["manifest_key"]] = record
    else:
        manifest["morphology"] = record
        manifest["phase"] = "2b_morphology_audit"
        manifest["status"] = "morphology_acquired_functional_mapping_pending"
    save_json(manifest_path, manifest)
    print(json.dumps({k: index[k] for k in ("skeleton_count", "total_vertices", "total_edges", "total_bytes")}, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--config", type=Path, default=Path("configs/morphology.yaml"))
    args = parser.parse_args()
    acquire(args.root.resolve(), args.config.resolve())
