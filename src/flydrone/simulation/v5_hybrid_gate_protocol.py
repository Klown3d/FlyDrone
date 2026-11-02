"""Freeze, verify, execute and analyze the prospective v5 hybrid gate."""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
from pathlib import Path

import pandas as pd

from flydrone.data.acquire import file_hash, save_json, utc_now
from flydrone.simulation.benchmark_integrated_v2 import load_config, run


EXPECTED_CONDITIONS = {
    "full_hybrid_v5", "neural_v4_reference", "gyro_heading_control",
    "conventional_navigation",
}
REFERENCE_CONFIGS = (
    Path("configs/quadrotor_integrated_v4_prospective.yaml"),
    Path("configs/quadrotor_integrated_v4_ood_pilot.yaml"),
    Path("configs/quadrotor_integrated_v5_heading_diagnostic.yaml"),
    Path("configs/quadrotor_integrated_v5_compass_development.yaml"),
)


def environment() -> dict:
    packages = ("numpy", "pandas", "scipy", "PyYAML", "pyarrow", "panda3d")
    return {"python": platform.python_version(),
            "packages": {name: importlib.metadata.version(name) for name in packages}}


def locked_paths(root: Path, config_path: Path) -> list[Path]:
    config = load_config(root, config_path)
    paths = [config_path, Path(config["preregistration_doc"]), Path("pyproject.toml")]
    paths.extend(path.relative_to(root) for path in (root / "src/flydrone").rglob("*.py"))
    paths.extend(path.relative_to(root) for path in (root / "configs").glob("*.yaml"))
    for folder in (root / "data/processed/fafb783_travel_direction",
                   root / "data/processed/fafb783_epg_delta7_fc2_pfl3"):
        paths.extend(path.relative_to(root) for path in folder.rglob("*") if path.is_file())
    paths.append(Path("results/neural/phase_resolved_compass_cross_compartment/transfers.npz"))
    return list(dict.fromkeys(paths))


def validate(root: Path, config_path: Path, allow_output: bool = False) -> dict:
    config = load_config(root, config_path)
    errors: list[str] = []
    if config.get("parameter_status") != "prospectively_frozen_operational_v5_hybrid_gate":
        errors.append("unexpected parameter_status")
    if config.get("run_once") is not True:
        errors.append("run_once must be true")
    if {item["name"] for item in config["conditions"]} != EXPECTED_CONDITIONS:
        errors.append("condition set differs from preregistration")
    cases = (len(config["scenarios"]) * len(config["target_bearings_deg"])
             * len(config["initial_relative_headings_deg"]))
    if cases != 24:
        errors.append(f"expected 24 cases per condition, found {cases}")
    bearings, headings = set(config["target_bearings_deg"]), set(config["initial_relative_headings_deg"])
    seeds = {item["seed"] for item in config["scenarios"]}
    for path in REFERENCE_CONFIGS:
        reference = load_config(root, path)
        if bearings & set(reference.get("target_bearings_deg", [])):
            errors.append(f"bearing overlap with {path.as_posix()}")
        if headings & set(reference.get("initial_relative_headings_deg", [])):
            errors.append(f"heading overlap with {path.as_posix()}")
        if seeds & {item["seed"] for item in reference.get("scenarios", [])}:
            errors.append(f"seed overlap with {path.as_posix()}")
    output = root / config["output"]
    if not allow_output and output.exists() and any(output.iterdir()):
        errors.append("run-once output already exists")
    if errors:
        raise ValueError("Invalid v5 hybrid gate: " + "; ".join(errors))
    return {"protocol_id": config["protocol_id"], "cases_per_condition": cases,
            "conditions": len(EXPECTED_CONDITIONS), "total_episodes": cases * len(EXPECTED_CONDITIONS)}


def freeze(root: Path, config_path: Path) -> dict:
    summary = validate(root, config_path)
    config = load_config(root, config_path)
    lock_path = root / config["lock_file"]
    if lock_path.exists():
        raise FileExistsError(lock_path)
    lock = {"created_at": utc_now(), "status": "frozen_before_execution", **summary,
            "environment": environment(),
            "files_sha256": {path.as_posix(): file_hash(root / path)
                             for path in locked_paths(root, config_path)}}
    save_json(lock_path, lock)
    return lock


def verify(root: Path, config_path: Path, allow_output: bool = False) -> dict:
    summary = validate(root, config_path, allow_output=allow_output)
    config = load_config(root, config_path)
    lock = json.loads((root / config["lock_file"]).read_text(encoding="utf-8"))
    current = {path.as_posix(): file_hash(root / path) for path in locked_paths(root, config_path)}
    changed = sorted(path for path in set(current) | set(lock.get("files_sha256", {}))
                     if current.get(path) != lock.get("files_sha256", {}).get(path))
    if changed:
        raise RuntimeError("V5 hybrid gate lock mismatch: " + ", ".join(changed))
    if environment() != lock.get("environment"):
        raise RuntimeError("Python environment differs from frozen environment")
    if summary["total_episodes"] != lock.get("total_episodes"):
        raise RuntimeError("Episode count differs from lock")
    return lock


def analyze(root: Path, config_path: Path) -> dict:
    config = load_config(root, config_path)
    frame = pd.read_csv(root / config["output"] / "episodes.csv")
    grouped = frame.groupby("controller")
    success = grouped.success.sum().astype(int)
    hybrid = frame[frame.controller == "full_hybrid_v5"]
    gyro = frame[frame.controller == "gyro_heading_control"]
    by_scenario = hybrid.groupby("scenario").success.sum().astype(int)
    gate = config["hybrid_gate"]
    effects = {
        "hybrid_successes": int(success["full_hybrid_v5"]),
        "minimum_hybrid_successes_each_scenario": int(by_scenario.min()),
        "success_deficit_vs_gyro": int(success["gyro_heading_control"] - success["full_hybrid_v5"]),
        "success_advantage_over_neural_v4": int(success["full_hybrid_v5"] - success["neural_v4_reference"]),
        "median_dropout_heading_error_deg": float(hybrid.median_dropout_heading_error_deg.median()),
        "cross_track_cost_vs_gyro_m": float(hybrid.maximum_absolute_cross_track_m.median() - gyro.maximum_absolute_cross_track_m.median()),
        "median_neural_weight_during_dropout": float(hybrid.mean_compass_neural_weight_during_dropout.median()),
        "maximum_neural_weight_during_dropout": float(hybrid.maximum_compass_neural_weight_during_dropout.max()),
        "hybrid_collisions": int(hybrid.collision.sum()),
        "maximum_motor_saturation_fraction": float(hybrid.motor_saturation_fraction.max()),
    }
    criteria = {
        "hybrid_functional": effects["hybrid_successes"] >= gate["minimum_hybrid_successes"],
        "each_scenario_functional": effects["minimum_hybrid_successes_each_scenario"] >= gate["minimum_hybrid_successes_each_scenario"],
        "gyro_comparability": effects["success_deficit_vs_gyro"] <= gate["maximum_success_deficit_vs_gyro"],
        "improves_over_neural_v4": effects["success_advantage_over_neural_v4"] >= gate["minimum_success_advantage_over_neural_v4"],
        "bounded_heading_error": effects["median_dropout_heading_error_deg"] <= gate["maximum_median_dropout_heading_error_deg"],
        "bounded_cross_track_cost": effects["cross_track_cost_vs_gyro_m"] <= gate["maximum_cross_track_cost_vs_gyro_m"],
        "neural_branch_active": effects["median_neural_weight_during_dropout"] >= gate["minimum_median_neural_weight_during_dropout"],
        "neural_weight_bounded": effects["maximum_neural_weight_during_dropout"] <= gate["maximum_neural_weight_during_dropout"],
        "no_collisions": effects["hybrid_collisions"] <= gate["maximum_hybrid_collisions"],
        "no_motor_saturation": effects["maximum_motor_saturation_fraction"] <= gate["maximum_motor_saturation_fraction"],
    }
    report = {"created_at": utc_now(), "status": "prospective_operational_gate_completed",
              "claim_limit": "Operational hybrid robustness only; neural branch activity is not causal performance attribution.",
              "effects": effects, "criteria": criteria, "passes_gate": all(criteria.values())}
    save_json(root / config["output"] / "hybrid_gate_report.json", report)
    return report


def execute(root: Path, config_path: Path) -> dict:
    verify(root, config_path)
    run(root, config_path)
    return analyze(root, config_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("validate", "freeze", "verify", "run", "analyze"))
    parser.add_argument("--config", type=Path, default=Path("configs/quadrotor_integrated_v5_hybrid_gate.yaml"))
    args = parser.parse_args(); root = Path.cwd()
    if args.action == "validate": result = validate(root, args.config)
    elif args.action == "freeze": result = freeze(root, args.config)
    elif args.action == "verify": result = verify(root, args.config)
    elif args.action == "analyze": result = analyze(root, args.config)
    else: result = execute(root, args.config)
    print(json.dumps(result, indent=2))
