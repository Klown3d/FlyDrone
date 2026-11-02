"""Evaluate the isolated FAFB PFL2 goal-misalignment candidate."""
from dataclasses import asdict
from pathlib import Path
import argparse
import json

import numpy as np
import pandas as pd

from flydrone.data.acquire import file_hash, save_json, utc_now
from flydrone.neural.connectome_pfl2 import ConnectomeWeightedPFL2


def run(root: Path, config_path: Path = Path("configs/pfl2_model.yaml")) -> None:
    model = ConnectomeWeightedPFL2(root, root / config_path)
    goals = np.arange(-180.0, 180.0, 45.0)
    errors = np.arange(-180.0, 181.0, 15.0)
    rows = []
    for goal_deg in goals:
        for error_deg in errors:
            goal = np.deg2rad(goal_deg)
            heading = goal + np.deg2rad(error_deg)
            rows.append({
                "goal_deg": goal_deg,
                "heading_error_deg": error_deg,
                "population_activity": model.population_activity(heading, goal),
                "anti_goal_index": model.anti_goal_index(heading, goal),
            })
    frame = pd.DataFrame(rows)
    monotonicities = []
    for goal_deg in goals:
        group = frame.loc[frame["goal_deg"].eq(goal_deg)]
        for direction in (-1, 1):
            branch = group.loc[np.sign(group["heading_error_deg"]).isin([0, direction])].copy()
            branch["absolute_error_deg"] = branch["heading_error_deg"].abs()
            monotonicities.append(branch["absolute_error_deg"].corr(branch["anti_goal_index"], method="spearman"))
    aligned = frame.loc[frame["heading_error_deg"].eq(0), "population_activity"]
    antialigned = frame.loc[frame["heading_error_deg"].abs().eq(180), "population_activity"]
    output = root / "results/neural/pfl2_goal_misalignment"
    output.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output / "response.csv", index=False)
    model.phase_audit.to_csv(output / "phase_audit.csv", index=False)
    report = {
        "created_at": utc_now(),
        "dataset": "FAFB",
        "materialization_version": 783,
        "claim": "PFL2 contact-weighted goal-misalignment audit; activation and calibration are engineering abstractions, not measured firing rates.",
        "configuration": config_path.as_posix(),
        "configuration_sha256": file_hash(root / config_path),
        "source_sha256": file_hash(Path(__file__)),
        "model_source_sha256": file_hash(root / "src/flydrone/neural/connectome_pfl2.py"),
        "pfl2_neurons": len(model.pfl2_ids),
        "delta_stream": asdict(model.delta_audit),
        "fc2_stream": asdict(model.fc2_audit),
        "median_absolute_delta_fc2_phase_separation_deg": float(model.phase_audit["delta_minus_fc2_deg"].abs().median()),
        "minimum_delta_phase_resultant": float(model.phase_audit["delta_resultant"].min()),
        "minimum_fc2_phase_resultant": float(model.phase_audit["fc2_resultant"].min()),
        "aligned_population_activity_median": float(aligned.median()),
        "antialigned_population_activity_median": float(antialigned.median()),
        "minimum_branch_monotonicity": float(np.min(monotonicities)),
        "passes_isolated_gate": bool(antialigned.median() > aligned.median() and np.min(monotonicities) >= 0.9),
    }
    save_json(output / "report.json", report)
    manifest_path = root / "data/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["pfl2_goal_misalignment_model"] = {
        "status": "isolated_contact_model_evaluated",
        "report": (output / "report.json").relative_to(root).as_posix(),
        "report_sha256": file_hash(output / "report.json"),
    }
    save_json(manifest_path, manifest)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/pfl2_model.yaml"))
    run(Path.cwd(), parser.parse_args().config)
