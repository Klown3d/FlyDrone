"""Anatomical audit of the FAFB PFNd/PFNv to hDeltaB travel-direction route."""
from __future__ import annotations

from pathlib import Path
import argparse
import json

import pandas as pd
import yaml

from flydrone.data.acquire import file_hash, save_json, utc_now


ROUTES = (
    ("Delta7", "PFNd"), ("Delta7", "PFNv"),
    ("EPG", "PFNd"), ("EPG", "PFNv"),
    ("LNO1", "PFNd"), ("LNO1", "PFNv"),
    ("LNO2", "PFNd"), ("LNO2", "PFNv"),
    ("IbSpsP", "PFNd"), ("IbSpsP", "PFNv"),
    ("PFNd", "hDeltaB"), ("PFNv", "hDeltaB"),
)


def audit(root: Path, config_path: Path) -> dict:
    c = yaml.safe_load((root / config_path).read_text(encoding="utf-8"))
    directory = root / c["output_dir"]
    nodes = pd.read_csv(directory / "nodes.csv", dtype={"root_id": str})
    edges = pd.read_csv(directory / "edges.csv", dtype={"pre_pt_root_id": str, "post_pt_root_id": str})
    types = dict(zip(nodes["root_id"], nodes["selected_type"]))
    edges["pre_type"] = edges["pre_pt_root_id"].map(types)
    edges["post_type"] = edges["post_pt_root_id"].map(types)
    pair_edges = edges.groupby(["pre_pt_root_id", "post_pt_root_id", "pre_type", "post_type"], as_index=False, dropna=False)["syn_count"].sum()
    routes = []
    for pre_type, post_type in ROUTES:
        selected = pair_edges.loc[pair_edges["pre_type"].eq(pre_type) & pair_edges["post_type"].eq(post_type)]
        post_total = int(nodes["selected_type"].eq(post_type).sum())
        routes.append({
            "pre_type": pre_type, "post_type": post_type,
            "directed_pairs": len(selected), "synapses": int(selected["syn_count"].sum()),
            "presynaptic_neurons": int(selected["pre_pt_root_id"].nunique()),
            "postsynaptic_neurons": int(selected["post_pt_root_id"].nunique()),
            "postsynaptic_coverage": float(selected["post_pt_root_id"].nunique() / post_total),
        })
    counts = nodes["selected_type"].value_counts().sort_index().astype(int).to_dict()
    nt = {cell_type: group["top_nt"].value_counts(dropna=False).astype(int).to_dict() for cell_type, group in nodes.groupby("selected_type")}
    return {"counts": counts, "routes": routes, "predicted_neurotransmitters": nt}


def run(root: Path, config_path: Path) -> None:
    c = yaml.safe_load((root / config_path).read_text(encoding="utf-8"))
    result = audit(root, config_path)
    output = root / c["output_dir"] / "travel-direction-audit.json"
    report = {
        "created_at": utc_now(), "dataset": c["dataset"],
        "materialization_version": c["materialization_version"],
        "claim": "Anatomical contact audit only; no velocity tuning, phase assignment, synaptic sign, gain, or neural dynamics inferred from topology.",
        "configuration": config_path.as_posix(), "configuration_sha256": file_hash(root / config_path),
        "source_sha256": file_hash(Path(__file__)), **result,
    }
    save_json(output, report)
    manifest_path = root / "data/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["travel_direction_anatomical_audit"] = {
        "status": "anatomical_contacts_only",
        "report": output.relative_to(root).as_posix(), "report_sha256": file_hash(output),
        "neurons": sum(result["counts"].values()),
    }
    save_json(manifest_path, manifest)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/data_travel_direction.yaml"))
    run(Path.cwd(), parser.parse_args().config)
