"""Development benchmark for continuous patrol and exploration goals.

The behavior manager is an engineering layer.  It supplies temporary goals to
the same FlyWire-grounded high-level controller used by the 6-DoF benchmarks;
it is not presented as a biological planner, visual system, or memory model.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from flydrone.data.acquire import file_hash, save_json, utc_now
from flydrone.neural.epg_delta7 import EPGDelta7Candidate
from flydrone.neural.pfl2_advance import PFL2AdvanceController
from flydrone.neural.pfl2_steering import PFL2SteeringController
from flydrone.neural.travel_direction_drift import TravelDirectionDriftController
from flydrone.simulation.behavior_manager import NavigationBehaviorManager
from flydrone.simulation.benchmark_integrated_v2 import load_config, velocity_estimator
from flydrone.simulation.benchmark_quadrotor import simulate
from flydrone.simulation.drift_confidence import DriftConfidenceGovernor
from flydrone.simulation.range_avoidance import RangeAvoidancePlanner
from flydrone.simulation.range_sensor import SimulatedRangeSensor


def _series(trace: dict, name: str) -> np.ndarray:
    columns = [str(item) for item in trace["columns"]]
    return np.asarray(trace["values"][:, columns.index(name)], dtype=float)


def trace_metrics(trace: dict, behavior_config: dict, neural: bool) -> dict:
    """Compute mission metrics from one control-rate trace."""
    x, y = _series(trace, "x_m"), _series(trace, "y_m")
    vx, vy = _series(trace, "vx_m_s"), _series(trace, "vy_m_s")
    tx, ty = _series(trace, "target_x_m"), _series(trace, "target_y_m")
    speed = np.hypot(vx, vy)
    target_distance = np.hypot(tx - x, ty - y)
    bounds = np.asarray(behavior_config["exploration_bounds_xy_m"], dtype=float)
    spacing = float(behavior_config["exploration_grid_spacing_m"])
    xs = np.arange(bounds[0, 0], bounds[0, 1] + spacing * .5, spacing)
    ys = np.arange(bounds[1, 0], bounds[1, 1] + spacing * .5, spacing)
    ix = np.rint((x - bounds[0, 0]) / spacing).astype(int)
    iy = np.rint((y - bounds[1, 0]) / spacing).astype(int)
    inside = ((x >= bounds[0, 0]) & (x <= bounds[0, 1]) &
              (y >= bounds[1, 0]) & (y <= bounds[1, 1]) &
              (ix >= 0) & (ix < len(xs)) & (iy >= 0) & (iy < len(ys)))
    visited = {(int(a), int(b)) for a, b in zip(ix[inside], iy[inside])}
    workspace_margin = 1.5
    escaped = ((x < bounds[0, 0] - workspace_margin) | (x > bounds[0, 1] + workspace_margin) |
               (y < bounds[1, 0] - workspace_margin) | (y > bounds[1, 1] + workspace_margin))
    stalled = (speed < .05) & (target_distance > .65)
    metrics = {
        "spatial_coverage_fraction": len(visited) / float(len(xs) * len(ys)),
        "workspace_escape_fraction": float(np.mean(escaped)),
        "stalled_fraction": float(np.mean(stalled)),
        "median_target_distance_m": float(np.median(target_distance)),
        "maximum_radius_m": float(np.max(np.hypot(x, y))),
        "neural_yaw_command_active_fraction": None,
        "hdelta_activity_active_fraction": None,
        "engineering_heading_dominant_fraction": None,
        "engineering_goal_capture_active_fraction": float(np.mean(
            np.hypot(_series(trace, "arrival_hold_correction_x_m_s2"),
                     _series(trace, "arrival_hold_correction_y_m_s2")) > 1e-6)),
        "engineering_geofence_active_fraction": float(np.mean(
            np.hypot(_series(trace, "geofence_correction_x_m_s2"),
                     _series(trace, "geofence_correction_y_m_s2")) > 1e-6)),
        "engineering_range_avoidance_active_fraction": (float(np.mean(_series(trace, "range_avoidance_active") > .5))
                                                        if "range_avoidance_active" in trace["columns"] else 0.0),
        "engineering_range_barrier_active_fraction": (float(np.mean(_series(trace, "range_barrier_active") > .5))
                                                       if "range_barrier_active" in trace["columns"] else 0.0),
    }
    if neural:
        metrics["neural_yaw_command_active_fraction"] = float(np.mean(np.abs(_series(trace, "yaw_command_rad_s")) > 1e-4))
        hdelta_names = [str(item) for item in trace["columns"] if str(item).startswith("hdelta_activity_")]
        if hdelta_names:
            matrix = np.column_stack([_series(trace, name) for name in hdelta_names])
            metrics["hdelta_activity_active_fraction"] = float(np.mean(np.linalg.norm(matrix, axis=1) > 1e-8))
        weights = _series(trace, "compass_neural_weight")
        finite = np.isfinite(weights)
        if finite.any():
            metrics["engineering_heading_dominant_fraction"] = float(np.mean(weights[finite] < .5))
    return metrics


def development_success(row: dict, heuristic: dict) -> bool:
    if bool(row.get("collision", False)):
        return False
    if row["workspace_escape_fraction"] > float(heuristic["maximum_workspace_escape_fraction"]):
        return False
    if (heuristic.get("minimum_obstacle_clearance_m") is not None and
            row.get("minimum_obstacle_clearance_m") is not None and
            row["minimum_obstacle_clearance_m"] < float(heuristic["minimum_obstacle_clearance_m"])):
        return False
    if row["behavior_mode"] == "patrol":
        return row["targets_completed"] >= int(heuristic["patrol_minimum_targets"])
    return (row["targets_completed"] >= int(heuristic["explore_minimum_targets"]) and
            row["spatial_coverage_fraction"] >= float(heuristic["explore_minimum_spatial_coverage_fraction"]))


def run(root: Path, config_path: Path) -> dict:
    config = load_config(root, config_path)
    allowed_status = {"exploratory_development_not_confirmatory",
                      "prospectively_frozen_free_navigation_gate",
                      "prospectively_frozen_obstacle_navigation_gate_v1"}
    if config.get("parameter_status") not in allowed_status:
        raise ValueError("Free-navigation run has an unknown scientific status")
    output = root / config["output"]
    output.mkdir(parents=True, exist_ok=True)
    trace_dir = output / "traces"
    trace_dir.mkdir(exist_ok=True)
    plant = yaml.safe_load((root / config["plant_config"]).read_text(encoding="utf-8"))
    orientation = yaml.safe_load((root / config["orientation_config"]).read_text(encoding="utf-8"))
    behavior_config = yaml.safe_load((root / config["behavior_manager_config"]).read_text(encoding="utf-8"))
    model = EPGDelta7Candidate(root, root / orientation["candidate_config"])
    pfl2 = PFL2SteeringController(root, root / config["pfl2_steering_config"])
    advance = PFL2AdvanceController(root / config["pfl2_advance_config"])
    rows: list[dict] = []
    for condition in config["conditions"]:
        for mode in config["behavior_modes"]:
            for scenario in config["scenarios"]:
                for heading_index, relative_deg in enumerate(config["initial_relative_headings_deg"]):
                    manager = NavigationBehaviorManager(root / config["behavior_manager_config"])
                    manager.reset((0.0, 0.0))
                    first = manager.set_mode(mode, (0.0, 0.0), 0.0)
                    first_xy = np.asarray(first.target_xy_m, dtype=float)
                    bearing = float(np.arctan2(first_xy[1], first_xy[0]))
                    relative = float(np.deg2rad(relative_deg))
                    manager.set_mode(mode, (0.0, 0.0), bearing + relative)
                    enabled = bool(condition["hdelta_enabled"])
                    estimator = velocity_estimator(root, config, condition["velocity_source"]) if enabled else None
                    drift = TravelDirectionDriftController(root, root / config["travel_direction_drift_config"])
                    drift_confidence = (DriftConfidenceGovernor(root / config["drift_confidence_config"])
                                        if enabled and condition.get("drift_confidence", False) else None)
                    range_sensor = (SimulatedRangeSensor(root / config["range_sensor_config"])
                                    if config.get("range_avoidance_config") else None)
                    range_planner = (RangeAvoidancePlanner(
                                     root / config["range_avoidance_config"],
                                     None if not config.get("range_safety_barrier_config") else
                                     root / config["range_safety_barrier_config"])
                                     if config.get("range_avoidance_config") else None)
                    local = {
                        **config,
                        "lateral_velocity_kd_per_s": float(condition["lateral_velocity_kd_per_s"]),
                        "suppress_drift_when_range_avoidance_active": bool(
                            condition.get("suppress_drift_when_range_avoidance_active", False)
                        ),
                    }
                    seed = int(scenario["seed"]) + heading_index
                    result, trace = simulate(
                        root, local, plant, model, orientation, bearing, relative,
                        condition["yaw_controller"] == "proportional", True, scenario, seed,
                        circuit_condition=condition["circuit_condition"],
                        yaw_controller=condition["yaw_controller"],
                        heading_mode=condition["heading_mode"],
                        compass_config=root / condition.get("compass_config", config["phase_compass_config"]),
                        controller_label=condition["name"], pfl2_controller=pfl2,
                        pfl2_enabled=bool(condition["pfl2_enabled"]), drift_controller=drift,
                        drift_enabled=enabled, velocity_estimator=estimator,
                        advance_controller=advance, neural_advance_enabled=bool(condition["advance_enabled"]),
                        drift_confidence_governor=drift_confidence,
                        target_provider=manager.update, initial_target_xy_m=tuple(first_xy),
                        blocked_target_handler=manager.abandon_current_target,
                        range_sensor=range_sensor, range_avoidance_planner=range_planner,
                    )
                    assert trace is not None
                    metrics = trace_metrics(trace, behavior_config, condition["yaw_controller"] == "neural")
                    row = {
                        **result, **metrics, "behavior_mode": mode,
                        "targets_completed": manager.completed_targets_total,
                        "targets_abandoned": manager.abandoned_targets_total,
                        "cycles_completed": manager.completed_cycles,
                        "mission_duration_s": float(config["duration_s"]),
                        "time_per_completed_target_s": (None if manager.completed_targets_total == 0 else
                                                         float(config["duration_s"]) / manager.completed_targets_total),
                    }
                    row["development_success"] = development_success(row, config["development_success_heuristic"])
                    rows.append(row)
                    stem = f"{condition['name']}__{mode}__{scenario['name']}__{heading_index:02d}"
                    np.savez_compressed(trace_dir / f"{stem}.npz", columns=np.asarray(trace["columns"]), values=trace["values"])
                    print(f"{stem}: targets={manager.completed_targets_total}, coverage={metrics['spatial_coverage_fraction']:.2f}, dev_success={row['development_success']}", flush=True)
    frame = pd.DataFrame(rows)
    frame.to_csv(output / "episodes.csv", index=False)
    summary = frame.groupby(["controller", "behavior_mode"], as_index=False).agg(
        episodes=("development_success", "size"), development_successes=("development_success", "sum"),
        median_targets_completed=("targets_completed", "median"),
        median_spatial_coverage_fraction=("spatial_coverage_fraction", "median"),
        maximum_workspace_escape_fraction=("workspace_escape_fraction", "max"),
        median_stalled_fraction=("stalled_fraction", "median"),
        median_engineering_goal_capture_active_fraction=("engineering_goal_capture_active_fraction", "median"),
        median_engineering_geofence_active_fraction=("engineering_geofence_active_fraction", "median"),
        median_engineering_range_avoidance_active_fraction=("engineering_range_avoidance_active_fraction", "median"),
        median_engineering_range_barrier_active_fraction=("engineering_range_barrier_active_fraction", "median"),
        minimum_obstacle_clearance_m=("minimum_obstacle_clearance_m", "min"),
        collisions=("collision", "sum"),
        maximum_motor_saturation_fraction=("motor_saturation_fraction", "max"),
    )
    summary.to_csv(output / "summary.csv", index=False)
    input_configurations = {}
    for key in ("plant_config", "orientation_config", "behavior_manager_config",
                "range_sensor_config", "range_avoidance_config", "pfl2_steering_config",
                "range_safety_barrier_config", "pfl2_advance_config",
                "travel_direction_drift_config", "drift_confidence_config"):
        if config.get(key):
            path = root / config[key]
            input_configurations[key] = {
                "path": Path(config[key]).as_posix(),
                "sha256": file_hash(path),
            }
    effective_configuration_sha256 = hashlib.sha256(
        json.dumps(config, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    report = {
        "created_at": utc_now(), "status": ("prospective_raw_benchmark_completed" if
            str(config["parameter_status"]).startswith("prospectively_frozen_") else
            "exploratory_development_completed"),
        "dataset": "FAFB", "materialization_version": 783,
        "claim_limit": config.get("claim", "Engineering behavior manager evaluation; no biological planning, vision, or memory claim."),
        "configuration": config_path.as_posix(), "configuration_sha256": file_hash(root / config_path),
        "effective_configuration_sha256": effective_configuration_sha256,
        "input_configurations": input_configurations,
        "simulation_source_sha256": file_hash(root / "src/flydrone/simulation/benchmark_quadrotor.py"),
        "behavior_source_sha256": file_hash(root / "src/flydrone/simulation/behavior_manager.py"),
        "range_avoidance_source_sha256": file_hash(root / "src/flydrone/simulation/range_avoidance.py"),
        "range_sensor_source_sha256": file_hash(root / "src/flydrone/simulation/range_sensor.py"),
        "range_safety_barrier_source_sha256": file_hash(root / "src/flydrone/simulation/range_safety_barrier.py"),
        "episodes": len(frame), "summary": summary.to_dict(orient="records"),
    }
    save_json(output / "report.json", report)
    manifest_path = root / "data/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest[config["manifest_key"]] = {"status": report["status"], "report": (output / "report.json").relative_to(root).as_posix(), "report_sha256": file_hash(output / "report.json"), "episodes": len(frame)}
    save_json(manifest_path, manifest)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/free_navigation_development.yaml"))
    print(json.dumps(run(Path.cwd(), parser.parse_args().config), indent=2))

