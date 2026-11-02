"""Test whether contact-weighted circular means are sufficient for Phase 6 mapping."""
from __future__ import annotations

from pathlib import Path
import argparse
import json

import numpy as np
import pandas as pd
import yaml

from flydrone.data.acquire import file_hash, save_json, utc_now
from flydrone.neural.connectome_pfl3 import ConnectomeWeightedPFL3, weighted_circular_mean_deg


def diagnose(root: Path, config_path: Path) -> dict:
    c = yaml.safe_load((root / config_path).read_text(encoding="utf-8"))
    directory = root / c["output_dir"]
    nodes = pd.read_csv(directory / "nodes.csv", dtype={"root_id": str})
    edges = pd.read_csv(directory / "edges.csv", dtype={"pre_pt_root_id": str, "post_pt_root_id": str})
    types = dict(zip(nodes["root_id"], nodes["selected_type"]))
    edges["pre_type"] = edges["pre_pt_root_id"].map(types)
    base = ConnectomeWeightedPFL3(root, root / "configs/connectome_model.yaml")
    delta_phase = dict(zip(base.delta_ids, np.rad2deg(base.delta_angles_rad)))
    pfn_phase: dict[str, float] = {}
    pfn_resultants: dict[str, list[float]] = {"PFNd": [], "PFNv": []}
    for cell_type in pfn_resultants:
        for root_id in nodes.loc[nodes["selected_type"].eq(cell_type), "root_id"]:
            selected = edges.loc[edges["post_pt_root_id"].eq(root_id) & edges["pre_type"].eq("Delta7")]
            phase, resultant = weighted_circular_mean_deg(
                np.asarray([delta_phase[item] for item in selected["pre_pt_root_id"]]),
                selected["syn_count"].to_numpy(),
            )
            pfn_phase[root_id] = phase
            pfn_resultants[cell_type].append(resultant)
    hdelta_resultants: dict[str, list[float]] = {"PFNd": [], "PFNv": []}
    for stream in hdelta_resultants:
        for root_id in nodes.loc[nodes["selected_type"].eq("hDeltaB"), "root_id"]:
            selected = edges.loc[edges["post_pt_root_id"].eq(root_id) & edges["pre_type"].eq(stream)]
            _, resultant = weighted_circular_mean_deg(
                np.asarray([pfn_phase[item] for item in selected["pre_pt_root_id"]]),
                selected["syn_count"].to_numpy(),
            )
            hdelta_resultants[stream].append(resultant)
    return {
        "pfn_phase_resultants": {
            cell_type: {"minimum": float(np.min(values)), "median": float(np.median(values)), "maximum": float(np.max(values))}
            for cell_type, values in pfn_resultants.items()
        },
        "naive_hdelta_input_phase_resultants": {
            stream: {"minimum": float(np.min(values)), "median": float(np.median(values)), "maximum": float(np.max(values))}
            for stream, values in hdelta_resultants.items()
        },
        "naive_single_phase_mapping_accepted": False,
        "reason": "PFNd-to-hDeltaB convergence is deliberately multi-phase; a single contact-weighted circular mean cancels structure and must not be used as hDeltaB phase.",
    }


def run(root: Path, config_path: Path) -> None:
    c = yaml.safe_load((root / config_path).read_text(encoding="utf-8"))
    result = diagnose(root, config_path)
    output = root / c["output_dir"] / "travel-direction-phase-diagnostic.json"
    report = {
        "created_at": utc_now(), "dataset": c["dataset"], "materialization_version": c["materialization_version"],
        "claim": "Diagnostic of an intentionally rejected phase shortcut; PFN phases inherit provisional Delta7 mapping and do not constitute validated physiology.",
        "configuration_sha256": file_hash(root / config_path), "source_sha256": file_hash(Path(__file__)), **result,
    }
    save_json(output, report)
    manifest_path = root / "data/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["travel_direction_phase_diagnostic"] = {"status": "naive_single_phase_mapping_rejected", "report": output.relative_to(root).as_posix(), "report_sha256": file_hash(output)}
    save_json(manifest_path, manifest)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/data_travel_direction.yaml"))
    run(Path.cwd(), parser.parse_args().config)
