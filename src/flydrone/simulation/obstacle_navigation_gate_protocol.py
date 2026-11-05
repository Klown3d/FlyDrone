"""Freeze, verify, execute, and analyze the v34 obstacle-navigation gate."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from flydrone.data.acquire import file_hash, save_json, utc_now
from flydrone.simulation.benchmark_free_navigation import run
from flydrone.simulation.benchmark_integrated_v2 import load_config
from flydrone.simulation.free_navigation_gate_protocol import environment, locked_paths


EXPECTED_CONDITIONS = {"flywire_v34", "conventional_navigation"}


def _development_configs(root: Path, gate_path: Path, gate_protocol_id: str) -> list[Path]:
    """Return only configurations that could predate the frozen gate.

    A replay created from the completed gate necessarily shares its cases.  It is
    excluded only when it declares that provenance explicitly; otherwise a new
    development file still participates in the leakage check.
    """
    result = []
    for path in sorted((root / "configs").glob("free_navigation_obstacles_development_v*.yaml")):
        if path.resolve() == (root / gate_path).resolve():
            continue
        development = load_config(root, path.relative_to(root))
        if development.get("posthoc_of_gate") == gate_protocol_id:
            continue
        result.append(path.relative_to(root))
    return result


def validate(root: Path, config_path: Path, allow_output: bool = False) -> dict:
    config = load_config(root, config_path)
    errors: list[str] = []
    if config.get("parameter_status") != "prospectively_frozen_obstacle_navigation_gate_v1":
        errors.append("unexpected parameter_status")
    if config.get("run_once") is not True:
        errors.append("run_once must be true")
    if {item["name"] for item in config["conditions"]} != EXPECTED_CONDITIONS:
        errors.append("unexpected controller conditions")
    cases = (len(config["behavior_modes"]) * len(config["scenarios"]) *
             len(config["initial_relative_headings_deg"]))
    if cases != 12:
        errors.append(f"expected 12 cases per controller, found {cases}")
    gate_headings = set(config["initial_relative_headings_deg"])
    gate_seeds = {int(item["seed"]) for item in config["scenarios"]}
    gate_names = {str(item["name"]) for item in config["scenarios"]}
    for path in _development_configs(root, config_path, str(config["protocol_id"])):
        development = load_config(root, path)
        if gate_headings & set(development.get("initial_relative_headings_deg", [])):
            errors.append(f"heading overlap with {path.as_posix()}")
        if gate_seeds & {int(item["seed"]) for item in development.get("scenarios", [])}:
            errors.append(f"seed overlap with {path.as_posix()}")
        if gate_names & {str(item["name"]) for item in development.get("scenarios", [])}:
            errors.append(f"scenario-name overlap with {path.as_posix()}")
    for scenario in config["scenarios"]:
        obstacles = scenario.get("obstacles", [])
        if len(obstacles) < 5:
            errors.append(f"{scenario['name']} has fewer than five obstacles")
        for obstacle in obstacles:
            center = obstacle.get("center_xy_m", [])
            radius = float(obstacle.get("radius_m", 0.0))
            if len(center) != 2 or radius <= 0:
                errors.append(f"invalid obstacle in {scenario['name']}")
    output = root / config["output"]
    if not allow_output and output.exists() and any(output.iterdir()):
        errors.append("run-once output already exists")
    if errors:
        raise ValueError("Invalid obstacle-navigation gate: " + "; ".join(errors))
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
    current = {path.as_posix(): file_hash(root / path)
               for path in locked_paths(root, config_path)}
    changed = sorted(path for path in set(current) | set(lock.get("files_sha256", {}))
                     if current.get(path) != lock.get("files_sha256", {}).get(path))
    if changed:
        raise RuntimeError("Obstacle-navigation gate lock mismatch: " + ", ".join(changed))
    if environment() != lock.get("environment"):
        raise RuntimeError("Python environment differs from frozen environment")
    if summary["total_episodes"] != lock.get("total_episodes"):
        raise RuntimeError("Episode count differs from lock")
    return lock


def analyze(root: Path, config_path: Path) -> dict:
    config = load_config(root, config_path)
    frame = pd.read_csv(root / config["output"] / "episodes.csv")
    flywire = frame[frame.controller == "flywire_v34"]
    conventional = frame[frame.controller == "conventional_navigation"]
    gate = config["operational_gate"]
    effects = {
        "flywire_successful_episodes": int(flywire.development_success.sum()),
        "total_flywire_targets": int(flywire.targets_completed.sum()),
        "minimum_flywire_patrol_targets": int(flywire.loc[flywire.behavior_mode == "patrol", "targets_completed"].min()),
        "minimum_flywire_explore_targets": int(flywire.loc[flywire.behavior_mode == "explore", "targets_completed"].min()),
        "total_target_deficit_vs_conventional": int(conventional.targets_completed.sum() - flywire.targets_completed.sum()),
        "minimum_flywire_clearance_m": float(flywire.minimum_obstacle_clearance_m.min()),
        "flywire_collisions": int(flywire.collision.sum()),
        "maximum_workspace_escape_fraction": float(flywire.workspace_escape_fraction.max()),
        "maximum_barrier_active_fraction": float(flywire.engineering_range_barrier_active_fraction.max()),
        "maximum_stalled_fraction": float(flywire.stalled_fraction.max()),
        "minimum_neural_yaw_active_fraction": float(flywire.neural_yaw_command_active_fraction.min()),
        "maximum_motor_saturation_fraction": float(flywire.motor_saturation_fraction.max()),
    }
    criteria = {
        "primary_successful_episodes": effects["flywire_successful_episodes"] >= gate["minimum_successful_flywire_episodes"],
        "total_progress": effects["total_flywire_targets"] >= gate["minimum_total_flywire_targets"],
        "patrol_progress": effects["minimum_flywire_patrol_targets"] >= gate["minimum_patrol_targets_each_episode"],
        "explore_progress": effects["minimum_flywire_explore_targets"] >= gate["minimum_explore_targets_each_episode"],
        "conventional_comparability": effects["total_target_deficit_vs_conventional"] <= gate["maximum_total_target_deficit_vs_conventional"],
        "clearance": effects["minimum_flywire_clearance_m"] >= gate["minimum_obstacle_clearance_m"],
        "no_collisions": effects["flywire_collisions"] <= gate["maximum_collisions"],
        "workspace_safety": effects["maximum_workspace_escape_fraction"] <= gate["maximum_workspace_escape_fraction"],
        "bounded_barrier": effects["maximum_barrier_active_fraction"] <= gate["maximum_barrier_active_fraction"],
        "bounded_stall": effects["maximum_stalled_fraction"] <= gate["maximum_stalled_fraction"],
        "neural_yaw_active": effects["minimum_neural_yaw_active_fraction"] >= gate["minimum_neural_yaw_active_fraction"],
        "no_motor_saturation": effects["maximum_motor_saturation_fraction"] <= gate["maximum_motor_saturation_fraction"],
    }
    report = {"created_at": utc_now(),
              "status": "prospective_obstacle_navigation_gate_completed",
              "claim_limit": config["claim"], "effects": effects,
              "criteria": criteria, "passes_gate": all(criteria.values())}
    save_json(root / config["output"] / "operational_gate_report.json", report)
    return report


def execute(root: Path, config_path: Path) -> dict:
    verify(root, config_path)
    run(root, config_path)
    return analyze(root, config_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("validate", "freeze", "verify", "run", "analyze"))
    parser.add_argument("--config", type=Path,
                        default=Path("configs/free_navigation_obstacles_gate_v1.yaml"))
    args = parser.parse_args(); root = Path.cwd()
    if args.action == "validate": result = validate(root, args.config)
    elif args.action == "freeze": result = freeze(root, args.config)
    elif args.action == "verify": result = verify(root, args.config)
    elif args.action == "analyze": result = analyze(root, args.config)
    else: result = execute(root, args.config)
    print(json.dumps(result, indent=2))
