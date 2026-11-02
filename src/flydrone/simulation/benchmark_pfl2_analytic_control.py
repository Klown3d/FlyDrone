"""Matched-gain analytic angular-error control for the prospective PFL2 cases."""
from __future__ import annotations

from pathlib import Path
import argparse
import json

import numpy as np
import pandas as pd
import yaml

from flydrone.data.acquire import file_hash, save_json, utc_now
from flydrone.neural.epg_delta7 import EPGDelta7Candidate
from flydrone.neural.pfl2_steering import PFL2SteeringController
from flydrone.simulation.benchmark_quadrotor import simulate


def run(root: Path, config_path: Path) -> None:
    c = yaml.safe_load((root / config_path).read_text(encoding="utf-8"))
    frozen_path = root / c["prospective_config"]
    frozen = yaml.safe_load(frozen_path.read_text(encoding="utf-8"))
    base = yaml.safe_load((root / frozen["base_config"]).read_text(encoding="utf-8"))
    spec = {**base, **frozen}
    plant = yaml.safe_load((root / spec["plant_config"]).read_text(encoding="utf-8"))
    orientation = yaml.safe_load((root / spec["orientation_config"]).read_text(encoding="utf-8"))
    model = EPGDelta7Candidate(root, root / orientation["candidate_config"])
    analytic = PFL2SteeringController(root, root / c["pfl2_steering_config"])
    rows = []
    for scenario in spec["scenarios"]:
        for case_index, (target, heading) in enumerate(
            (t, h) for t in spec["target_bearings_deg"] for h in spec["initial_relative_headings_deg"]
        ):
            seed = int(scenario["seed"]) + case_index
            result, _ = simulate(
                root, spec, plant, model, orientation, np.deg2rad(target), np.deg2rad(heading),
                False, False, scenario, seed, heading_mode="direct",
                controller_label="analytic_error_gain", pfl2_controller=analytic, pfl2_enabled=True,
            )
            result.update({"case_id": f"{scenario['name']}:{case_index}", "seed": seed})
            rows.append(result)
    analytic_frame = pd.DataFrame(rows)
    reference = pd.read_csv(root / c["prospective_episodes"])
    combined = pd.concat([reference, analytic_frame], ignore_index=True)
    output = root / c["output"]
    output.mkdir(parents=True, exist_ok=True)
    analytic_frame.to_csv(output / "analytic_episodes.csv", index=False)
    combined.to_csv(output / "combined_episodes.csv", index=False)
    pivot = combined.pivot(index="case_id", columns="controller")
    time = pivot["arrival_time_s"]
    efficiency = pivot["path_efficiency"]
    summary = combined.groupby("controller", as_index=False).agg(
        episodes=("success", "size"), successes=("success", "sum"),
        median_arrival_time_s=("arrival_time_s", "median"),
        median_path_efficiency=("path_efficiency", "median"),
        maximum_motor_saturation_fraction=("motor_saturation_fraction", "max"),
    )
    report = {
        "created_at": utc_now(), "dataset": "FAFB", "materialization_version": 783,
        "claim": "Post-prospective matched-gain engineering control. Analytic angular error replaces the connectome PFL2 index; cases and gain are unchanged.",
        "configuration": config_path.as_posix(), "configuration_sha256": file_hash(root / config_path),
        "source_sha256": file_hash(Path(__file__)), "frozen_prospective_configuration_sha256": file_hash(frozen_path),
        "episodes_run": len(analytic_frame), "summary": summary.to_dict(orient="records"),
        "paired_median_arrival_improvement_vs_pfl3_only_s": float((time["pfl3_only"] - time["analytic_error_gain"]).median()),
        "paired_median_arrival_difference_analytic_minus_connectome_s": float((time["analytic_error_gain"] - time["pfl3_plus_pfl2"]).median()),
        "paired_median_efficiency_difference_analytic_minus_connectome": float((efficiency["analytic_error_gain"] - efficiency["pfl3_plus_pfl2"]).median()),
    }
    save_json(output / "report.json", report)
    manifest_path = root / "data/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest[c["manifest_key"]] = {"status": "post_prospective_matched_gain_control_completed", "report": (output / "report.json").relative_to(root).as_posix(), "report_sha256": file_hash(output / "report.json"), "episodes": len(analytic_frame)}
    save_json(manifest_path, manifest)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/quadrotor_pfl2_analytic_control.yaml"))
    run(Path.cwd(), parser.parse_args().config)
