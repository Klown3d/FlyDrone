"""Generate a standalone interactive 3D viewer for mapped PFL3 activity."""
from __future__ import annotations

import argparse
import json
import struct
import webbrowser
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from flydrone.neural.connectome_pfl3 import ConnectomeWeightedPFL3


def read_skeleton(path: Path) -> tuple[np.ndarray, np.ndarray]:
    raw = path.read_bytes()
    vertices, edges = struct.unpack_from("<II", raw, 0)
    points = np.frombuffer(raw, dtype="<f4", count=vertices * 3, offset=8).reshape(-1, 3)
    edge_offset = 8 + vertices * 12
    links = np.frombuffer(raw, dtype="<u4", count=edges * 2, offset=edge_offset).reshape(-1, 2)
    return points, links


def build_payload(root: Path) -> tuple[list[dict[str, object]], dict[str, object]]:
    config = yaml.safe_load((root / "configs/neural_model.yaml").read_text(encoding="utf-8"))
    mapping = pd.read_csv(root / config["mapping"], dtype={"root_id": str})
    skeleton_dir = root / "data/raw/flywire_skeletons_783"
    loaded: list[tuple[pd.Series, np.ndarray, np.ndarray]] = []
    all_points = []
    for _, row in mapping.iterrows():
        points, edges = read_skeleton(skeleton_dir / f"{row['root_id']}.bin")
        loaded.append((row, points, edges))
        all_points.append(points)
    center = np.concatenate(all_points).mean(axis=0)
    geometry: list[dict[str, object]] = []
    for row, points, edges in loaded:
        # Micrometres around a common origin; 0.01 µm display precision is ample.
        points_um = np.round((points - center) / 1000.0, 2)
        geometry.append({
            "rootId": row["root_id"],
            "column": row["functional_column"],
            "side": row["lal_projection_side"],
            "points": points_um.reshape(-1).tolist(),
            "edges": edges.reshape(-1).tolist(),
        })
    p = config["parameters"]
    model = {
        "headingPreferredDeg": mapping["preferred_heading_deg"].astype(float).tolist(),
        "goalPreferredDeg": mapping["preferred_goal_deg"].astype(float).tolist(),
        "sides": mapping["lal_projection_side"].tolist(),
        "d": float(p["goal_input_gain_d"]),
        "a": float(p["output_scale_hz_a"]),
        "b": float(p["softplus_slope_b"]),
        "c": float(p["input_offset_c"]),
        "source": config["source"],
    }
    weighted = ConnectomeWeightedPFL3(root, root / "configs/connectome_model.yaml")
    model["connectome"] = {
        "deltaAnglesDeg": np.rad2deg(weighted.delta_angles_rad).round(6).tolist(),
        "fc2AnglesDeg": np.rad2deg(weighted.fc2_angles_rad).round(6).tolist(),
        "deltaWeights": weighted.delta_weights.round(8).tolist(),
        "fc2Weights": weighted.fc2_weights.round(8).tolist(),
        "fc2Subtypes": list(weighted.fc2_subtypes),
    }
    return geometry, model


def generate(root: Path, output: Path) -> Path:
    geometry, model = build_payload(root)
    template = (Path(__file__).with_name("pfl3-viewer.html")).read_text(encoding="utf-8")
    document = template.replace("__GEOMETRY_JSON__", json.dumps(geometry, separators=(",", ":")))
    document = document.replace("__MODEL_JSON__", json.dumps(model, separators=(",", ":")))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(document, encoding="utf-8")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, default=Path("results/visualization/pfl3-activity-3d.html"))
    parser.add_argument("--open", action="store_true", help="Open the generated viewer in the default browser")
    args = parser.parse_args()
    root = args.root.resolve()
    result = generate(root, (root / args.output).resolve())
    print(result)
    if args.open:
        webbrowser.open(result.as_uri())
