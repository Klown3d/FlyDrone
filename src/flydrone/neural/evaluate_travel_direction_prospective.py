"""Run-once prospective gate for the frozen PFN/hDeltaB travel-direction model."""
from __future__ import annotations

from pathlib import Path
import argparse
import json

import numpy as np
import pandas as pd
import yaml

from flydrone.data.acquire import file_hash, save_json, utc_now
from flydrone.neural.travel_direction_model import ConnectomeTravelDirection, wrap


def summarize(frame: pd.DataFrame) -> dict[str, float]:
    return {
        "median_absolute_error_deg": float(frame.absolute_error_deg.median()),
        "p90_absolute_error_deg": float(frame.absolute_error_deg.quantile(0.9)),
        "maximum_absolute_error_deg": float(frame.absolute_error_deg.max()),
        "within_45deg_fraction": float(frame.absolute_error_deg.lt(45.0).mean()),
        "minimum_resultant": float(frame.resultant.min()),
    }


def run(root: Path, config_path: Path) -> dict:
    path = root / config_path
    c = yaml.safe_load(path.read_text(encoding="utf-8"))
    output = root / c["output"]
    report_path = output / "report.json"
    if c.get("run_once", False) and report_path.exists():
        raise RuntimeError(f"Prospective report already exists: {report_path}")
    model_path = root / c["model_config"]
    model = ConnectomeTravelDirection(root, model_path)
    rng = np.random.default_rng(c["master_seed"])
    rows = []
    case_id = 0
    for scenario in c["scenarios"]:
        for heading_deg in c["headings_deg"]:
            for ego_deg in c["egocentric_motion_deg"]:
                for speed in c["speeds"]:
                    observed_heading = heading_deg + rng.normal(0.0, scenario["heading_noise_sd_deg"])
                    observed_ego = ego_deg + rng.normal(0.0, scenario["motion_noise_sd_deg"])
                    decoded, resultant, _, _ = model.decode(
                        np.deg2rad(observed_heading), np.deg2rad(observed_ego), float(speed)
                    )
                    expected = float(wrap(np.deg2rad(heading_deg + ego_deg)))
                    error = abs(float(wrap(decoded - expected)))
                    rows.append({
                        "case_id": case_id, "scenario": scenario["name"], "heading_deg": heading_deg,
                        "egocentric_motion_deg": ego_deg, "speed": speed,
                        "observed_heading_deg": observed_heading,
                        "observed_egocentric_motion_deg": observed_ego,
                        "expected_allocentric_deg": float(np.rad2deg(expected)),
                        "decoded_allocentric_deg": float(np.rad2deg(decoded)),
                        "absolute_error_deg": float(np.rad2deg(error)), "resultant": resultant,
                    })
                    case_id += 1
    frame = pd.DataFrame(rows)
    metrics = {name: summarize(group) for name, group in frame.groupby("scenario", sort=False)}
    metrics["all"] = summarize(frame)
    ideal, all_metrics, gate = metrics["ideal"], metrics["all"], c["gate"]
    criteria = {
        "ideal_median_error": ideal["median_absolute_error_deg"] <= gate["ideal_maximum_median_error_deg"],
        "ideal_worst_error": ideal["maximum_absolute_error_deg"] <= gate["ideal_maximum_worst_error_deg"],
        "all_median_error": all_metrics["median_absolute_error_deg"] <= gate["all_maximum_median_error_deg"],
        "all_p90_error": all_metrics["p90_absolute_error_deg"] <= gate["all_maximum_p90_error_deg"],
        "all_direction": all_metrics["within_45deg_fraction"] >= gate["all_minimum_within_45deg_fraction"],
        "all_resultant": all_metrics["minimum_resultant"] >= gate["all_minimum_resultant"],
    }
    output.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output / "responses.csv", index=False)
    report = {
        "created_at": utc_now(), "status": "immutable_run_once_prospective_result",
        "dataset": c["dataset"], "materialization_version": c["materialization_version"],
        "claim": "Held-out static transform and sensor-noise gate; no temporal delay, drone dynamics, or biological firing-rate claim.",
        "configuration": config_path.as_posix(), "configuration_sha256": file_hash(path),
        "source_sha256": file_hash(Path(__file__)), "model_configuration_sha256": file_hash(model_path),
        "model_source_sha256": file_hash(root / "src/flydrone/neural/travel_direction_model.py"),
        "column_mapping_sha256": file_hash(root / model.config["column_mapping"]),
        "edges_sha256": file_hash(root / model.config["edges"]),
        "cases": len(frame), "metrics": metrics, "criteria": criteria,
        "passes_prospective_gate": bool(all(criteria.values())),
    }
    save_json(report_path, report)
    manifest_path = root / "data/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest[c["manifest_key"]] = {
        "status": "prospective_gate_completed", "report": report_path.relative_to(root).as_posix(),
        "report_sha256": file_hash(report_path), "passed": report["passes_prospective_gate"],
    }
    save_json(manifest_path, manifest)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/travel_direction_prospective.yaml"))
    print(json.dumps(run(Path.cwd(), parser.parse_args().config), indent=2), flush=True)

