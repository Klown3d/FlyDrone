"""Infer provisional PFN/hDeltaB FB columns from pinned FAFB synapse coordinates."""
from __future__ import annotations

from pathlib import Path
import argparse
import json

import numpy as np
import pandas as pd
import yaml

from flydrone.data.acquire import file_hash, save_json, utc_now
from flydrone.morphology.analyze import optimal_1d_clusters
from flydrone.neural.connectome_pfl3 import ConnectomeWeightedPFL3, weighted_circular_mean_deg


def infer(root: Path, config_path: Path) -> tuple[pd.DataFrame, dict]:
    c = yaml.safe_load((root / config_path).read_text(encoding="utf-8"))
    directory = root / c["output_dir"]
    nodes = pd.read_csv(directory / "nodes.csv", dtype={"root_id": str})
    synapses = pd.read_csv(directory / "synapses.csv.gz", dtype={"pre_pt_root_id": str, "post_pt_root_id": str})
    types = dict(zip(nodes["root_id"], nodes["selected_type"]))
    synapses["pre_type"] = synapses["pre_pt_root_id"].map(types)
    synapses["post_type"] = synapses["post_pt_root_id"].map(types)
    base = ConnectomeWeightedPFL3(root, root / "configs/connectome_model.yaml")
    delta_phase = dict(zip(base.delta_ids, np.rad2deg(base.delta_angles_rad)))
    rows: list[dict] = []

    for cell_type in ("PFNd", "PFNv"):
        type_rows = []
        for root_id in nodes.loc[nodes["selected_type"].eq(cell_type), "root_id"]:
            outputs = synapses.loc[
                synapses["pre_pt_root_id"].eq(root_id)
                & synapses["post_type"].eq("hDeltaB")
                & synapses["neuropil"].eq("FB")
            ]
            inputs = synapses.loc[
                synapses["post_pt_root_id"].eq(root_id)
                & synapses["pre_type"].eq("Delta7")
                & synapses["neuropil"].eq("PB")
            ]
            phase, resultant = weighted_circular_mean_deg(
                np.asarray([delta_phase[item] for item in inputs["pre_pt_root_id"]]),
                np.ones(len(inputs)),
            )
            type_rows.append({
                "root_id": root_id, "selected_type": cell_type,
                "side": nodes.loc[nodes["root_id"].eq(root_id), "side"].iloc[0],
                "fb_output_median_x_nm": float(outputs["pre_pt_position_x"].median()),
                "fb_output_contacts_to_hdeltaB": len(outputs),
                "delta7_input_contacts_pb": len(inputs),
                "inherited_heading_phase_deg": phase,
                "inherited_heading_resultant": resultant,
            })
        labels = optimal_1d_clusters(np.asarray([row["fb_output_median_x_nm"] for row in type_rows]), 8)
        for row, label in zip(type_rows, labels):
            row["fb_output_column"] = f"PFN_FB{label:02d}"
            rows.append(row)

    hdelta_rows = []
    for root_id in nodes.loc[nodes["selected_type"].eq("hDeltaB"), "root_id"]:
        outputs = synapses.loc[
            synapses["pre_pt_root_id"].eq(root_id) & synapses["neuropil"].eq("FB")
        ]
        # Lyu et al. report that PFNv targets the hDeltaB dendritic region,
        # whereas PFNd targets both regions; PFNv therefore anchors dendrite x.
        dendrite_inputs = synapses.loc[
            synapses["post_pt_root_id"].eq(root_id)
            & synapses["pre_type"].eq("PFNv")
            & synapses["neuropil"].eq("FB")
        ]
        hdelta_rows.append({
            "root_id": root_id, "selected_type": "hDeltaB",
            "side": nodes.loc[nodes["root_id"].eq(root_id), "side"].iloc[0],
            "fb_axon_median_x_nm": float(outputs["pre_pt_position_x"].median()),
            "fb_dendrite_median_x_nm": float(dendrite_inputs["post_pt_position_x"].median()),
            "fb_internal_output_contacts": len(outputs),
            "pfnv_dendrite_contacts": len(dendrite_inputs),
        })
    axon_labels = optimal_1d_clusters(np.asarray([row["fb_axon_median_x_nm"] for row in hdelta_rows]), 12)
    dendrite_labels = optimal_1d_clusters(np.asarray([row["fb_dendrite_median_x_nm"] for row in hdelta_rows]), 12)
    offsets = []
    for row, axon, dendrite in zip(hdelta_rows, axon_labels, dendrite_labels):
        offset = int((dendrite - axon) % 12)
        row.update({"fb_axon_column": f"HDB_FB{axon:02d}", "fb_dendrite_column": f"HDB_FB{dendrite:02d}", "dendrite_minus_axon_columns_mod12": offset})
        offsets.append(offset)
        rows.append(row)

    frame = pd.DataFrame(rows)
    circular_deviation = np.minimum(np.abs(np.asarray(offsets) - 6), 12 - np.abs(np.asarray(offsets) - 6))
    report = {
        "mapping_status": "provisional_geometry_plus_published_compartment_rule",
        "pfn_columns": 8, "hdeltaB_columns": 12,
        "hdeltaB_neurons_in_fafb": len(hdelta_rows),
        "published_hdeltaB_count": 19,
        "hdeltaB_half_width_offset": {
            "offset_counts_mod12": {str(value): int(offsets.count(value)) for value in sorted(set(offsets))},
            "median_offset_columns": float(np.median(offsets)),
            "fraction_within_one_column_of_half_width": float(np.mean(circular_deviation <= 1)),
            "fraction_within_two_columns_of_half_width": float(np.mean(circular_deviation <= 2)),
        },
        "claim_limit": "Columns are geometric hypotheses from median synapse x, not FlyWire annotations. Delta7 phases are inherited from the provisional steering map. No velocity gain or hDeltaB activity is inferred.",
    }
    return frame, report


def run(root: Path, config_path: Path) -> None:
    c = yaml.safe_load((root / config_path).read_text(encoding="utf-8"))
    frame, summary = infer(root, config_path)
    directory = root / c["output_dir"]
    mapping_path = directory / "travel-direction-columns.csv"
    frame.to_csv(mapping_path, index=False)
    report = {
        "created_at": utc_now(), "dataset": c["dataset"], "materialization_version": c["materialization_version"],
        "configuration_sha256": file_hash(root / config_path), "source_sha256": file_hash(Path(__file__)),
        "coordinate_source_sha256": file_hash(directory / "synapses.csv.gz"),
        "mapping": mapping_path.relative_to(root).as_posix(), "mapping_sha256": file_hash(mapping_path), **summary,
    }
    report_path = directory / "travel-direction-columns.report.json"
    save_json(report_path, report)
    manifest_path = root / "data/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["travel_direction_columns"] = {"status": summary["mapping_status"], "report": report_path.relative_to(root).as_posix(), "report_sha256": file_hash(report_path), "mapping": mapping_path.relative_to(root).as_posix(), "mapping_sha256": file_hash(mapping_path)}
    save_json(manifest_path, manifest)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/data_travel_direction.yaml"))
    run(Path.cwd(), parser.parse_args().config)
