"""Freeze, verify, execute, and analyze free-navigation gate v1."""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
from pathlib import Path

import pandas as pd

from flydrone.data.acquire import file_hash, save_json, utc_now
from flydrone.simulation.benchmark_free_navigation import run
from flydrone.simulation.benchmark_integrated_v2 import load_config


DEVELOPMENT_CONFIGS = (
    Path("configs/free_navigation_development.yaml"),
    Path("configs/free_navigation_development_v2.yaml"),
    Path("configs/free_navigation_development_v3.yaml"),
)


def environment() -> dict:
    names = ("numpy", "pandas", "scipy", "PyYAML", "pyarrow", "panda3d")
    return {"python": platform.python_version(),
            "packages": {name: importlib.metadata.version(name) for name in names}}


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
    if config.get("parameter_status") != "prospectively_frozen_free_navigation_gate":
        errors.append("unexpected parameter_status")
    if config.get("run_once") is not True:
        errors.append("run_once must be true")
    if {item["name"] for item in config["conditions"]} != {"flywire_hybrid", "conventional_navigation"}:
        errors.append("unexpected controller conditions")
    cases = len(config["behavior_modes"]) * len(config["scenarios"]) * len(config["initial_relative_headings_deg"])
    if cases != 12:
        errors.append(f"expected 12 cases per controller, found {cases}")
    gate_headings = set(config["initial_relative_headings_deg"])
    gate_seeds = {item["seed"] for item in config["scenarios"]}
    for path in DEVELOPMENT_CONFIGS:
        development = load_config(root, path)
        if gate_headings & set(development.get("initial_relative_headings_deg", [])):
            errors.append(f"heading overlap with {path.as_posix()}")
        if gate_seeds & {item["seed"] for item in development.get("scenarios", [])}:
            errors.append(f"seed overlap with {path.as_posix()}")
    output = root / config["output"]
    if not allow_output and output.exists() and any(output.iterdir()):
        errors.append("run-once output already exists")
    if errors:
        raise ValueError("Invalid free-navigation gate: " + "; ".join(errors))
    return {"protocol_id": config["protocol_id"], "cases_per_controller": cases,
            "controllers": 2, "total_episodes": cases * 2}


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
        raise RuntimeError("Free-navigation gate lock mismatch: " + ", ".join(changed))
    if environment() != lock.get("environment"):
        raise RuntimeError("Python environment differs from frozen environment")
    if summary["total_episodes"] != lock.get("total_episodes"):
        raise RuntimeError("Episode count differs from lock")
    return lock


def analyze(root: Path, config_path: Path) -> dict:
    config = load_config(root, config_path)
    frame = pd.read_csv(root / config["output"] / "episodes.csv")
    hybrid = frame[frame.controller == "flywire_hybrid"]
    conventional = frame[frame.controller == "conventional_navigation"]
    gate = config["operational_gate"]
    effects = {
        "total_hybrid_targets": int(hybrid.targets_completed.sum()),
        "minimum_hybrid_targets_each_episode": int(hybrid.targets_completed.min()),
        "median_hybrid_patrol_targets": float(hybrid.loc[hybrid.behavior_mode == "patrol", "targets_completed"].median()),
        "median_hybrid_explore_targets": float(hybrid.loc[hybrid.behavior_mode == "explore", "targets_completed"].median()),
        "total_target_deficit_vs_conventional": int(conventional.targets_completed.sum() - hybrid.targets_completed.sum()),
        "maximum_workspace_escape_fraction": float(hybrid.workspace_escape_fraction.max()),
        "maximum_geofence_active_fraction": float(hybrid.engineering_geofence_active_fraction.max()),
        "maximum_goal_capture_active_fraction": float(hybrid.engineering_goal_capture_active_fraction.max()),
        "minimum_neural_yaw_active_fraction": float(hybrid.neural_yaw_command_active_fraction.min()),
        "minimum_hdelta_active_fraction": float(hybrid.hdelta_activity_active_fraction.min()),
        "maximum_engineering_heading_dominant_fraction": float(hybrid.engineering_heading_dominant_fraction.max()),
        "hybrid_collisions": int(hybrid.collision.sum()),
        "maximum_motor_saturation_fraction": float(hybrid.motor_saturation_fraction.max()),
    }
    criteria = {
        "primary_total_targets": effects["total_hybrid_targets"] >= gate["minimum_total_hybrid_targets"],
        "minimum_each_episode": effects["minimum_hybrid_targets_each_episode"] >= gate["minimum_targets_each_episode"],
        "patrol_progress": effects["median_hybrid_patrol_targets"] >= gate["minimum_median_patrol_targets"],
        "explore_progress": effects["median_hybrid_explore_targets"] >= gate["minimum_median_explore_targets"],
        "conventional_comparability": effects["total_target_deficit_vs_conventional"] <= gate["maximum_total_target_deficit_vs_conventional"],
        "workspace_safety": effects["maximum_workspace_escape_fraction"] <= gate["maximum_workspace_escape_fraction"],
        "bounded_geofence": effects["maximum_geofence_active_fraction"] <= gate["maximum_geofence_active_fraction"],
        "bounded_goal_capture": effects["maximum_goal_capture_active_fraction"] <= gate["maximum_goal_capture_active_fraction"],
        "neural_yaw_active": effects["minimum_neural_yaw_active_fraction"] >= gate["minimum_neural_yaw_active_fraction"],
        "hdelta_active": effects["minimum_hdelta_active_fraction"] >= gate["minimum_hdelta_active_fraction"],
        "bounded_inertial_heading_dominance": effects["maximum_engineering_heading_dominant_fraction"] <= gate["maximum_engineering_heading_dominant_fraction"],
        "no_collisions": effects["hybrid_collisions"] <= gate["maximum_collisions"],
        "no_motor_saturation": effects["maximum_motor_saturation_fraction"] <= gate["maximum_motor_saturation_fraction"],
    }
    report = {"created_at": utc_now(), "status": "prospective_free_navigation_gate_completed",
              "claim_limit": config["claim"], "effects": effects, "criteria": criteria,
              "passes_gate": all(criteria.values())}
    save_json(root / config["output"] / "operational_gate_report.json", report)
    return report


def execute(root: Path, config_path: Path) -> dict:
    verify(root, config_path)
    run(root, config_path)
    return analyze(root, config_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("validate", "freeze", "verify", "run", "analyze"))
    parser.add_argument("--config", type=Path, default=Path("configs/free_navigation_gate_v1.yaml"))
    args = parser.parse_args(); root = Path.cwd()
    if args.action == "validate": result = validate(root, args.config)
    elif args.action == "freeze": result = freeze(root, args.config)
    elif args.action == "verify": result = verify(root, args.config)
    elif args.action == "analyze": result = analyze(root, args.config)
    else: result = execute(root, args.config)
    print(json.dumps(result, indent=2))

