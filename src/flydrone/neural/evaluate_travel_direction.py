"""Development gate for the contact-weighted PFN/hDeltaB travel-direction model."""
from __future__ import annotations

from pathlib import Path
import argparse
import json

import numpy as np
import pandas as pd
import yaml

from flydrone.data.acquire import file_hash, save_json, utc_now
from flydrone.neural.travel_direction_model import ConnectomeTravelDirection, wrap


def run(root: Path, config_path: Path) -> None:
    c = yaml.safe_load((root / config_path).read_text(encoding="utf-8"))
    model = ConnectomeTravelDirection(root, root / config_path)
    rows = []
    for heading_deg in c["development_headings_deg"]:
        for ego_deg in c["development_egocentric_motion_deg"]:
            heading = np.deg2rad(heading_deg)
            ego = np.deg2rad(ego_deg)
            decoded, resultant, _, _ = model.decode(heading, ego)
            expected = float(wrap(heading + ego))
            error = abs(float(wrap(decoded - expected)))
            rows.append({
                "heading_deg": heading_deg, "egocentric_motion_deg": ego_deg,
                "expected_allocentric_deg": float(np.rad2deg(expected)),
                "decoded_allocentric_deg": float(np.rad2deg(decoded)),
                "absolute_error_deg": float(np.rad2deg(error)), "resultant": resultant,
            })
    frame = pd.DataFrame(rows)
    output = root / c["output"]
    output.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output / "responses.csv", index=False)
    gate = c["gate"]
    metrics = {
        "median_absolute_error_deg": float(frame["absolute_error_deg"].median()),
        "maximum_absolute_error_deg": float(frame["absolute_error_deg"].max()),
        "within_45deg_fraction": float(frame["absolute_error_deg"].lt(45.0).mean()),
        "minimum_resultant": float(frame["resultant"].min()),
    }
    criteria = {
        "median_error": metrics["median_absolute_error_deg"] <= gate["maximum_median_error_deg"],
        "worst_error": metrics["maximum_absolute_error_deg"] <= gate["maximum_worst_error_deg"],
        "direction": metrics["within_45deg_fraction"] >= gate["minimum_within_45deg_fraction"],
        "resultant": metrics["minimum_resultant"] >= gate["minimum_resultant"],
    }
    report = {
        "created_at": utc_now(), "dataset": c["dataset"], "materialization_version": c["materialization_version"],
        "claim": "Development-only baseline-subtracted PFN/hDeltaB phasor model. Contact weights are FAFB 783; velocity encoding and global phase anchor are computational abstractions.",
        "configuration": config_path.as_posix(), "configuration_sha256": file_hash(root / config_path),
        "source_sha256": file_hash(Path(__file__)), "model_source_sha256": file_hash(root / "src/flydrone/neural/travel_direction_model.py"),
        "cases": len(frame), "metrics": metrics, "criteria": criteria,
        "passes_development_gate": bool(all(criteria.values())),
    }
    save_json(output / "report.json", report)
    manifest_path = root / "data/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest[c["manifest_key"]] = {"status": "development_gate_completed", "report": (output / "report.json").relative_to(root).as_posix(), "report_sha256": file_hash(output / "report.json"), "passed": report["passes_development_gate"]}
    save_json(manifest_path, manifest)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/travel_direction_model.yaml"))
    run(Path.cwd(), parser.parse_args().config)
