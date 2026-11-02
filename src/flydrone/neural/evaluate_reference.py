"""Run the published PFL3 reference model over a deterministic heading sweep."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

from flydrone.data.acquire import file_hash, save_json, utc_now
from flydrone.neural.pfl3 import PFL3ReferenceModel


def git_revision(root: Path) -> str | None:
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def run(root: Path, config_path: Path, output_dir: Path, step_deg: float = 1.0) -> None:
    model = PFL3ReferenceModel.from_config(root, config_path)
    headings = np.arange(-180.0, 180.0 + step_deg / 2, step_deg)
    rows: list[dict[str, object]] = []
    rate_names = [f"rate_hz_{root_id}" for root_id in model.mapping["root_id"]]
    for heading_deg in headings:
        rates, readout = model.evaluate(np.deg2rad(heading_deg), 0.0)
        row: dict[str, object] = {"heading_deg": heading_deg, "goal_deg": 0.0, **readout}
        row.update(dict(zip(rate_names, rates)))
        rows.append(row)
    output_dir.mkdir(parents=True, exist_ok=True)
    trace_path = output_dir / "heading-sweep.csv"
    frame = pd.DataFrame(rows)
    frame.to_csv(trace_path, index=False)
    signal = frame["right_minus_left_hz"].to_numpy()
    zero_index = int(np.argmin(np.abs(signal)))
    # Exclude duplicated periodic endpoints; samples then pair -179 with +179.
    core = signal[1:-1]
    odd_rmse = float(np.sqrt(np.mean((core + core[::-1]) ** 2)))
    report = {
        "created_at": utc_now(),
        "model": "published_pfl3_reference",
        "model_scope": "24 mapped FAFB PFL3 identities using published angles and firing-rate equation",
        "connectome_weighted": False,
        "simulator_connected": False,
        "units": 24,
        "goal_deg": 0.0,
        "heading_step_deg": step_deg,
        "closest_sampled_zero_heading_deg": float(frame.iloc[zero_index]["heading_deg"]),
        "closest_sampled_zero_abs_signal_hz": float(abs(signal[zero_index])),
        "odd_symmetry_rmse_hz": odd_rmse,
        "peak_abs_readout_hz": float(np.max(np.abs(signal))),
        "config": config_path.relative_to(root).as_posix(),
        "config_sha256": file_hash(config_path),
        "mapping_sha256": file_hash(root / "data/processed/fafb783_epg_delta7_fc2_pfl3/functional-mapping.csv"),
        "trace": trace_path.relative_to(root).as_posix(),
        "trace_sha256": file_hash(trace_path),
        "git_revision": git_revision(root),
    }
    report_path = output_dir / "report.json"
    save_json(report_path, report)
    manifest_path = root / "data/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["phase"] = "3_computational_neural_model"
    manifest["status"] = "published_pfl3_reference_verified_connectome_weighted_model_pending"
    manifest["neural_model"] = {
        "status": "reference_model_verified",
        "connectome_weighted": False,
        "configuration": config_path.relative_to(root).as_posix(),
        "configuration_sha256": file_hash(config_path),
        "report": report_path.relative_to(root).as_posix(),
        "report_sha256": file_hash(report_path),
        "activity_trace": trace_path.relative_to(root).as_posix(),
        "activity_trace_sha256": file_hash(trace_path),
    }
    save_json(manifest_path, manifest)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--config", type=Path, default=Path("configs/neural_model.yaml"))
    parser.add_argument("--output", type=Path, default=Path("results/neural/published_pfl3_reference"))
    parser.add_argument("--step-deg", type=float, default=1.0)
    args = parser.parse_args()
    root = args.root.resolve()
    run(root, (root / args.config).resolve(), (root / args.output).resolve(), args.step_deg)
