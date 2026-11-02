"""Single-run prospective paired PFL2 steering evaluation in 6-DoF."""
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


def _sign(value: float | None) -> int:
    if value is None or np.isclose(value, 0.0):
        return 0
    return 1 if value > 0 else -1


def run(root: Path, config_path: Path) -> None:
    spec = yaml.safe_load((root / config_path).read_text(encoding="utf-8"))
    output = root / spec["output"]
    report_path = output / "report.json"
    if spec.get("run_once", False) and report_path.exists():
        raise RuntimeError(f"Prospective report already exists: {report_path}")

    base = yaml.safe_load((root / spec["base_config"]).read_text(encoding="utf-8"))
    c = {**base, **spec}
    plant = yaml.safe_load((root / c["plant_config"]).read_text(encoding="utf-8"))
    orientation = yaml.safe_load((root / c["orientation_config"]).read_text(encoding="utf-8"))
    model = EPGDelta7Candidate(root, root / orientation["candidate_config"])
    pfl2 = PFL2SteeringController(root, root / c["pfl2_steering_config"])
    cases = [
        (scenario, target, heading, case_index)
        for scenario in c["scenarios"]
        for case_index, (target, heading) in enumerate(
            (t, h) for t in c["target_bearings_deg"] for h in c["initial_relative_headings_deg"]
        )
    ]
    rows: list[dict] = []
    for label, enabled in (("pfl3_plus_pfl2", True), ("pfl3_only", False)):
        for scenario, target_deg, heading_deg, case_index in cases:
            seed = int(scenario["seed"]) + case_index
            result, _ = simulate(
                root, c, plant, model, orientation,
                np.deg2rad(target_deg), np.deg2rad(heading_deg), False, False,
                scenario, seed, heading_mode="direct", controller_label=label,
                pfl2_controller=pfl2, pfl2_enabled=enabled,
            )
            result.update({"case_id": f"{scenario['name']}:{case_index}", "seed": seed})
            rows.append(result)
        completed = [row for row in rows if row["controller"] == label]
        print(f"{label}: {sum(row['success'] for row in completed)}/{len(completed)}", flush=True)

    frame = pd.DataFrame(rows)
    output.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output / "episodes.csv", index=False)
    pivot = frame.pivot(index="case_id", columns="controller")
    valid_time = pivot["arrival_time_s"].dropna()
    paired_improvement = valid_time["pfl3_only"] - valid_time["pfl3_plus_pfl2"]
    efficiency_difference = (
        pivot["path_efficiency"]["pfl3_plus_pfl2"]
        - pivot["path_efficiency"]["pfl3_only"]
    ).dropna()
    initial_direction_changes = sum(
        _sign(pair["pfl3_plus_pfl2"]) != _sign(pair["pfl3_only"])
        for _, pair in pivot["initial_yaw_command_rad_s"].iterrows()
    )
    scenario_improvements = {}
    for scenario_name in frame["scenario"].unique():
        ids = frame.loc[frame["scenario"].eq(scenario_name), "case_id"].unique()
        values = paired_improvement.reindex(ids).dropna()
        scenario_improvements[scenario_name] = None if values.empty else float(values.median())

    summary = frame.groupby(["controller", "scenario"], as_index=False).agg(
        episodes=("success", "size"), successes=("success", "sum"),
        median_arrival_time_s=("arrival_time_s", "median"),
        median_path_efficiency=("path_efficiency", "median"),
        maximum_tilt_deg=("max_tilt_deg", "max"),
        maximum_motor_saturation_fraction=("motor_saturation_fraction", "max"),
    )
    plus = frame.loc[frame["controller"].eq("pfl3_plus_pfl2")]
    ablated = frame.loc[frame["controller"].eq("pfl3_only")]
    gate = c["gate"]
    criteria = {
        "pfl2_success_rate": float(plus["success"].mean()) >= float(gate["minimum_pfl2_success_rate"]),
        "success_not_worse_than_ablation": int(plus["success"].sum()) + int(gate["maximum_success_deficit_vs_ablation"]) >= int(ablated["success"].sum()),
        "paired_arrival_improvement": float(paired_improvement.median()) >= float(gate["minimum_overall_median_paired_arrival_improvement_s"]),
        "scenario_consistency": sum(value is not None and value > 0 for value in scenario_improvements.values()) >= int(gate["minimum_scenarios_with_positive_median_improvement"]),
        "path_efficiency_noninferiority": float(efficiency_difference.median()) >= float(gate["minimum_median_efficiency_difference"]),
        "direction_preserved": initial_direction_changes <= int(gate["maximum_direction_changes"]),
    }
    report = {
        "created_at": utc_now(), "dataset": "FAFB", "materialization_version": 783,
        "claim": "Single-run prospective paired 6-DoF PFL2 magnitude-modulation evaluation under new sensor and wind perturbations; conventional inner-loop stabilization remains active.",
        "configuration": config_path.as_posix(), "configuration_sha256": file_hash(root / config_path),
        "source_sha256": file_hash(Path(__file__)), "pfl2_steering_sha256": file_hash(root / c["pfl2_steering_config"]),
        "episodes": len(frame), "paired_cases": len(cases),
        "overall_median_paired_arrival_improvement_s": float(paired_improvement.median()),
        "median_paired_path_efficiency_difference": float(efficiency_difference.median()),
        "initial_direction_changes": int(initial_direction_changes),
        "scenario_median_arrival_improvement_s": scenario_improvements,
        "summary": summary.to_dict(orient="records"), "criteria": criteria,
        "passes_prospective_gate": bool(all(criteria.values())),
    }
    save_json(report_path, report)
    manifest_path = root / "data/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest[c["manifest_key"]] = {
        "status": "completed_single_run_prospective",
        "report": report_path.relative_to(root).as_posix(),
        "report_sha256": file_hash(report_path), "episodes": len(frame),
        "passed": report["passes_prospective_gate"],
    }
    save_json(manifest_path, manifest)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/quadrotor_pfl2_prospective.yaml"))
    run(Path.cwd(), parser.parse_args().config)
