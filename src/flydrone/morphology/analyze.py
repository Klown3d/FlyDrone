"""Measure FlyWire skeleton arbors in pinned neuropil meshes and infer columns.

Column labels produced here are geometric hypotheses, not FlyWire annotations.
They use only the left-to-right coordinate order and are kept separate from
source-provided cell types.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import struct
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import trimesh
from scipy.cluster.hierarchy import fcluster, linkage

from flydrone.data.acquire import file_hash, save_json, utc_now


def skeleton_points(path: Path) -> np.ndarray:
    raw = path.read_bytes()
    vertices, _edges = struct.unpack_from("<II", raw, 0)
    return np.frombuffer(raw, dtype="<f4", count=vertices * 3, offset=8).reshape(-1, 3)


def inside_mesh(mesh: trimesh.Trimesh, points: np.ndarray, batch_size: int = 4_000) -> np.ndarray:
    """Containment with an AABB prefilter and bounded-memory ray batches."""
    result = np.zeros(len(points), dtype=bool)
    candidates = np.flatnonzero(np.all((points >= mesh.bounds[0]) & (points <= mesh.bounds[1]), axis=1))
    for start in range(0, len(candidates), batch_size):
        idx = candidates[start : start + batch_size]
        result[idx] = mesh.contains(points[idx])
    return result


def optimal_1d_clusters(values: np.ndarray, cluster_count: int) -> np.ndarray:
    """Globally minimize within-cluster SSE for contiguous one-dimensional groups."""
    if len(values) < cluster_count or not np.isfinite(values).all():
        raise ValueError("Insufficient finite values for requested clustering")
    order = np.argsort(values, kind="stable")
    ordered = values[order].astype(float)
    n = len(ordered)
    sums = np.r_[0.0, np.cumsum(ordered)]
    squares = np.r_[0.0, np.cumsum(ordered * ordered)]
    cost = np.full((cluster_count + 1, n + 1), np.inf)
    previous = np.full((cluster_count + 1, n + 1), -1, dtype=int)
    cost[0, 0] = 0.0
    for groups in range(1, cluster_count + 1):
        for end in range(groups, n + 1):
            for start in range(groups - 1, end):
                count = end - start
                sse = squares[end] - squares[start] - (sums[end] - sums[start]) ** 2 / count
                candidate = cost[groups - 1, start] + sse
                if candidate < cost[groups, end]:
                    cost[groups, end] = candidate
                    previous[groups, end] = start
    ordered_labels = np.empty(n, dtype=int)
    end = n
    for groups in range(cluster_count, 0, -1):
        start = previous[groups, end]
        ordered_labels[start:end] = groups
        end = start
    labels = np.empty(n, dtype=int)
    labels[order] = ordered_labels
    return labels


def epg_pb_columns(points_xyz: np.ndarray) -> np.ndarray:
    """Infer the 16 EPG-occupied PB glomeruli from 3-D arbor centroids.

    EPG imaging omits the two outermost ROIs of the 18-glomerulus PB mask.
    FAFB's PB curves in depth at both ends, so x alone cannot separate the
    outer EPG arbors. Ward clusters supply the groups; nearest-neighbour
    traversal along the curved PB supplies their anatomical order.

    The result is an explicitly geometric hypothesis, with labels PB02..PB17.
    """
    points = np.asarray(points_xyz, dtype=float)
    if points.shape[0] < 16 or points.shape[1:] != (3,) or not np.isfinite(points).all():
        raise ValueError("EPG PB mapping needs at least 16 finite xyz centroids")
    raw = fcluster(linkage(points, method="ward"), 16, criterion="maxclust")
    unique = sorted(set(raw))
    if len(unique) != 16:
        raise ValueError(f"Expected 16 EPG PB clusters, found {len(unique)}")
    centers = {label: points[raw == label].mean(axis=0) for label in unique}
    mid_x = float(np.median([center[0] for center in centers.values()]))
    left = [label for label, center in centers.items() if center[0] < mid_x]
    right = [label for label, center in centers.items() if center[0] >= mid_x]
    start = max(left, key=lambda label: centers[label][1])
    expected_end = max(right, key=lambda label: centers[label][1])
    order = [start]
    remaining = set(unique) - {start}
    while remaining:
        current = centers[order[-1]]
        next_label = min(
            remaining,
            key=lambda label: (float(np.linalg.norm(current - centers[label])), int(label)),
        )
        order.append(next_label)
        remaining.remove(next_label)
    if order[-1] != expected_end:
        raise ValueError("Inferred EPG clusters do not form the expected PB arc")
    column_by_cluster = {label: position + 2 for position, label in enumerate(order)}
    return np.asarray([column_by_cluster[label] for label in raw], dtype=int)


def analyze(root: Path) -> None:
    manifest_path = root / "data/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    output_dir = root / manifest["extraction"]["output_dir"]
    nodes = pd.read_csv(output_dir / "nodes.csv", dtype={"root_id": "uint64"})
    atlas_path = root / manifest["morphology"]["atlas_path"]
    with zipfile.ZipFile(atlas_path) as archive:
        meshes = {
            name: trimesh.load(io.BytesIO(archive.read(f"{name}.ply")), file_type="ply", process=False)
            for name in ("PB", "FB")
        }

    rows: list[dict[str, object]] = []
    skeleton_dir = root / "data/raw/flywire_skeletons_783"
    for index, node in nodes.iterrows():
        root_id = int(node["root_id"])
        points = skeleton_points(skeleton_dir / f"{root_id}.bin")
        row: dict[str, object] = {
            "root_id": str(root_id),
            "selected_type": node["selected_type"],
            "source_side": node["side"],
            "lal_projection_side": node["dominant_LAL_contact_side"],
            "skeleton_vertices": len(points),
        }
        for name, mesh in meshes.items():
            selected = points[inside_mesh(mesh, points)]
            row[f"{name}_vertices"] = len(selected)
            for axis, axis_name in enumerate("xyz"):
                row[f"{name}_median_{axis_name}_nm"] = float(np.median(selected[:, axis])) if len(selected) else np.nan
        rows.append(row)
        if (index + 1) % 20 == 0 or index + 1 == len(nodes):
            print(f"  neurons {index + 1}/{len(nodes)}", flush=True)

    features = pd.DataFrame(rows)
    features["geometric_column"] = ""
    epg_mask = features["selected_type"].eq("EPG")
    epg_labels = epg_pb_columns(
        features.loc[epg_mask, ["PB_median_x_nm", "PB_median_y_nm", "PB_median_z_nm"]].to_numpy()
    )
    features.loc[epg_mask, "geometric_column"] = [f"PB{value:02d}" for value in epg_labels]
    epg_grouped = features.loc[epg_mask].assign(_label=epg_labels).groupby("_label")
    scheme_report: list[dict[str, object]] = [{
        "cell_type": "EPG",
        "region": "PB",
        "cluster_count": 16,
        "anatomical_columns": "PB02..PB17; PB01 and PB18 are not occupied by EPG in the published 18-ROI mask",
        "counts_left_to_right": [int(v) for v in epg_grouped.size().tolist()],
        "median_xyz_nm_left_to_right": [
            [float(value) for value in row]
            for row in epg_grouped[["PB_median_x_nm", "PB_median_y_nm", "PB_median_z_nm"]].median().to_numpy()
        ],
        "method": "Ward clustering of 3-D PB skeleton centroids followed by nearest-neighbour traversal of the curved PB",
    }]
    schemes = (("FC2A", "FB", 9, "FB"), ("FC2B", "FB", 9, "FB"), ("FC2C", "FB", 9, "FB"))
    for cell_type, region, count, prefix in schemes:
        mask = features["selected_type"].eq(cell_type)
        labels = optimal_1d_clusters(features.loc[mask, f"{region}_median_x_nm"].to_numpy(), count)
        features.loc[mask, "geometric_column"] = [f"{prefix}{value:02d}" for value in labels]
        grouped = features.loc[mask].assign(_label=labels).groupby("_label")
        scheme_report.append({
            "cell_type": cell_type,
            "region": region,
            "cluster_count": count,
            "counts_left_to_right": [int(v) for v in grouped.size().tolist()],
            "median_x_nm_left_to_right": [float(v) for v in grouped[f"{region}_median_x_nm"].median().tolist()],
        })

    # The published PFL3 model contains 12 cells projecting to each LAL and one
    # member of each projection-side population in every functional FB column.
    # Enforcing that documented pairing avoids inventing boundaries from small
    # geometric differences between the two interleaved populations.
    pfl3_mask = features["selected_type"].eq("PFL3")
    pfl3_counts: list[int] = []
    pfl3_centers: list[float] = []
    for projection_side in ("left", "right"):
        side_mask = pfl3_mask & features["lal_projection_side"].eq(projection_side)
        if int(side_mask.sum()) != 12:
            raise ValueError(f"Expected 12 PFL3 cells projecting {projection_side}, found {side_mask.sum()}")
        ordered_index = features.loc[side_mask, "FB_median_x_nm"].sort_values(kind="stable").index
        features.loc[ordered_index, "geometric_column"] = [f"FB{value:02d}" for value in range(1, 13)]
    for column in range(1, 13):
        column_mask = pfl3_mask & features["geometric_column"].eq(f"FB{column:02d}")
        pfl3_counts.append(int(column_mask.sum()))
        pfl3_centers.append(float(features.loc[column_mask, "FB_median_x_nm"].median()))
    scheme_report.append({
        "cell_type": "PFL3",
        "region": "FB",
        "cluster_count": 12,
        "counts_left_to_right": pfl3_counts,
        "median_x_nm_left_to_right": pfl3_centers,
        "constraint": "ranked separately within the 12 left-LAL and 12 right-LAL projecting populations",
    })

    feature_path = output_dir / "morphology-features.csv"
    features.to_csv(feature_path, index=False, quoting=csv.QUOTE_MINIMAL)
    report = {
        "created_at": utc_now(),
        "dataset": manifest["dataset"],
        "atlas_sha256": file_hash(atlas_path),
        "method": "skeleton vertices contained by pinned neuropil mesh; EPG uses 3-D PB centroids and 16 occupied glomeruli; FB populations use median-x ordering",
        "interpretation": "inferred geometric ordering, not a source annotation and not a synapse-density measurement",
        "coordinate_labels": "PB01/FB01 are lowest atlas x (atlas left): LAL_L has lower x than LAL_R in this atlas",
        "schemes": scheme_report,
        "features": feature_path.relative_to(root).as_posix(),
        "features_sha256": file_hash(feature_path),
    }
    report_path = output_dir / "morphology-report.json"
    save_json(report_path, report)
    manifest["morphology_analysis"] = {
        "status": "geometric_columns_inferred",
        "features": feature_path.relative_to(root).as_posix(),
        "features_sha256": file_hash(feature_path),
        "report": report_path.relative_to(root).as_posix(),
        "report_sha256": file_hash(report_path),
    }
    save_json(manifest_path, manifest)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    analyze(args.root.resolve())
