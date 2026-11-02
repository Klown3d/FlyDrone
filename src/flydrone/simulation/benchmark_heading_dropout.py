"""Compare the frozen FlyWire-grounded compass under heading-sensor dropout."""
from pathlib import Path
import json

import numpy as np
import pandas as pd
import yaml

from flydrone.data.acquire import file_hash, save_json, utc_now
from flydrone.neural.epg_delta7 import EPGDelta7Candidate
from flydrone.simulation.benchmark_quadrotor import simulate


def run(root: Path, config_path: Path = Path("configs/quadrotor_heading_dropout.yaml")) -> None:
    experiment = yaml.safe_load((root / config_path).read_text(encoding="utf-8"))
    base = yaml.safe_load((root / experiment["base_config"]).read_text(encoding="utf-8"))
    c = {**base, **experiment}
    plant = yaml.safe_load((root / c["plant_config"]).read_text(encoding="utf-8"))
    orientation = yaml.safe_load((root / c["orientation_config"]).read_text(encoding="utf-8"))
    pid_config = yaml.safe_load((root / c["pid_config"]).read_text(encoding="utf-8"))
    model = EPGDelta7Candidate(root, root / orientation["candidate_config"])
    output = root / c["output"]
    if c.get("run_once") and (output / "report.json").exists():
        raise RuntimeError("Sealed prospective output already exists; refusing to rerun")
    output.mkdir(parents=True, exist_ok=True)
    rows, traces = [], {}
    cases = [
        (np.deg2rad(target), np.deg2rad(relative))
        for target in c["target_bearings_deg"]
        for relative in c["initial_relative_headings_deg"]
    ]
    for scenario in c["scenarios"]:
        for controller in c["controllers"]:
            label = controller["label"]
            for index, (target, relative) in enumerate(cases):
                result, trace = simulate(
                    root, c, plant, model, orientation, target, relative,
                    controller["yaw_controller"] == "proportional", index == 0,
                    scenario, int(scenario["seed"]) + index, None, "intact",
                    controller["yaw_controller"], pid_config,
                    controller["heading_mode"], Path(c["compass_config"]), label,
                )
                rows.append(result)
                if trace is not None:
                    traces[f"{scenario['name']}-{label}"] = trace
            successes = sum(
                row["success"] for row in rows
                if row["scenario"] == scenario["name"] and row["controller"] == label
            )
            print(f"{scenario['name']} / {label}: {successes}/{len(cases)}", flush=True)
    frame = pd.DataFrame(rows)
    frame.to_csv(output / "episodes.csv", index=False)
    summary = frame.groupby(["scenario", "controller", "heading_mode"], as_index=False).agg(
        episodes=("success", "size"), successes=("success", "sum"),
        success_rate=("success", "mean"),
        median_dropout_heading_error_deg=("median_dropout_heading_error_deg", "median"),
        maximum_dropout_heading_error_deg=("maximum_dropout_heading_error_deg", "max"),
        median_final_distance_m=("final_distance_m", "median"),
        median_path_efficiency=("path_efficiency", "median"),
        median_final_speed_m_s=("final_speed_m_s", "median"),
    )
    summary.to_csv(output / "summary.csv", index=False)
    for label, data in traces.items():
        np.savez_compressed(output / f"{label}-trace.npz", **data)
    criteria = c.get("decision_criteria", {})
    decisions = {}
    if criteria:
        indexed = summary.set_index("controller")
        primary = indexed.loc[c["primary_controller"]]
        decisions = {
            "minimum_success_rate": bool(primary.success_rate >= criteria["minimum_success_rate"]),
            "maximum_median_dropout_heading_error_deg": bool(primary.median_dropout_heading_error_deg <= criteria["maximum_median_dropout_heading_error_deg"]),
            "maximum_dropout_heading_error_deg": bool(primary.maximum_dropout_heading_error_deg <= criteria["maximum_dropout_heading_error_deg"]),
        }
        if "minimum_improvement_over_sample_hold_deg" in criteria:
            hold = indexed.loc[c["sample_hold_controller"]]
            improvement = float(hold.median_dropout_heading_error_deg - primary.median_dropout_heading_error_deg)
            decisions["minimum_improvement_over_sample_hold_deg"] = bool(improvement >= criteria["minimum_improvement_over_sample_hold_deg"])
            decisions["observed_improvement_over_sample_hold_deg"] = improvement
        decisions["all_primary_criteria_pass"] = all(value for key, value in decisions.items() if not key.startswith("observed_"))
    report = {
        "created_at": utc_now(), "dataset": "FAFB", "materialization_version": 783,
        "claim": "Held-out 6-DoF simulated waypoint comparison during temporary heading-cue loss; all integrating observers receive the same delayed noisy body yaw-rate sensor.",
        "configuration": config_path.as_posix(),
        "configuration_sha256": file_hash(root / config_path),
        "source_sha256": file_hash(Path(__file__)), "episodes": len(frame),
        "evaluation_role": c.get("evaluation_role", "development_or_held_out"),
        "case_count_per_condition": len(cases) * len(c["scenarios"]),
        "decision_criteria": criteria, "decisions": decisions,
        "summary": summary.to_dict(orient="records"),
    }
    save_json(output / "report.json", report)
    manifest_path = root / "data/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest[c["manifest_key"]] = {
        "status": "heading_dropout_6dof_benchmark_completed",
        "report": (output / "report.json").relative_to(root).as_posix(),
        "report_sha256": file_hash(output / "report.json"), "episodes": len(frame),
    }
    save_json(manifest_path, manifest)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/quadrotor_heading_dropout.yaml"))
    run(Path.cwd(), parser.parse_args().config)
