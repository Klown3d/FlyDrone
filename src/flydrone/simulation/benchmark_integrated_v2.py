"""Development and prospective runner for the integrated FlyDrone v2 stack."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from flydrone.data.acquire import file_hash, save_json, utc_now
from flydrone.neural.epg_delta7 import EPGDelta7Candidate
from flydrone.neural.pfl2_advance import PFL2AdvanceController
from flydrone.neural.pfl2_steering import PFL2SteeringController
from flydrone.neural.steering_connectome_nulls import build_steering_null
from flydrone.neural.travel_direction_drift import TravelDirectionDriftController
from flydrone.simulation.benchmark_quadrotor import simulate
from flydrone.simulation.travel_velocity_sensor import (
    InertialPositionVelocityEstimator,
    PositionVelocityEstimator,
)


def velocity_estimator(root: Path, config: dict, source: str):
    if source == "inertial_fusion":
        return InertialPositionVelocityEstimator(root / config["travel_velocity_inertial_config"])
    if source == "position_difference":
        return PositionVelocityEstimator(root / config["travel_velocity_sensor_config"])
    if source == "none":
        return None
    raise ValueError(f"Unknown velocity source: {source}")


def circuit_variant(condition: dict) -> dict | None:
    ablation = condition.get("steering_ablation", "none")
    if ablation == "none":
        return None
    if ablation == "delta7":
        return {"delta7_enabled": False}
    if ablation == "fc2":
        return {"fc2_enabled": False}
    raise ValueError(f"Unknown steering ablation: {ablation}")


def load_config(root: Path, config_path: Path, seen: set[Path] | None = None) -> dict:
    """Load a benchmark configuration with deterministic recursive inheritance."""
    relative = Path(config_path)
    visited = set() if seen is None else set(seen)
    if relative in visited:
        raise ValueError(f"Circular base_config inheritance at {relative}")
    visited.add(relative)
    spec = yaml.safe_load((root / relative).read_text(encoding="utf-8"))
    if "base_config" not in spec:
        return spec
    base = load_config(root, Path(spec["base_config"]), visited)
    return {**base, **spec}


def run(root: Path, config_path: Path) -> dict:
    config = load_config(root, config_path)
    if config.get("block_null_seeds"):
        intact = dict(config["null_intact_condition"])
        template = dict(config["null_condition_template"])
        config["conditions"] = [intact] + [
            {
                **template,
                "name": f"null_rewire_block_{int(seed)}",
                "block_weight_rewire_seed": int(seed),
            }
            for seed in config["block_null_seeds"]
        ]
    elif config.get("steering_null_seeds"):
        intact = dict(config["steering_null_intact_condition"])
        template = dict(config["steering_null_condition_template"])
        config["conditions"] = [intact] + [
            {
                **template,
                "name": f"steering_null_side_block_{int(seed)}",
                "steering_null_seed": int(seed),
            }
            for seed in config["steering_null_seeds"]
        ]
    output = root / config["output"]
    report_path = output / "report.json"
    if config.get("run_once") and report_path.exists():
        raise RuntimeError(f"Run-once report already exists: {report_path}")
    plant = yaml.safe_load((root / config["plant_config"]).read_text(encoding="utf-8"))
    orientation = yaml.safe_load((root / config["orientation_config"]).read_text(encoding="utf-8"))
    model = EPGDelta7Candidate(root, root / orientation["candidate_config"])
    pfl2 = PFL2SteeringController(root, root / config["pfl2_steering_config"])
    advance = PFL2AdvanceController(root / config["pfl2_advance_config"])
    cases = [
        (np.deg2rad(target), np.deg2rad(heading))
        for target in config["target_bearings_deg"]
        for heading in config["initial_relative_headings_deg"]
    ]
    trace_dir = output / "traces"
    trace_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    saved_first_success: set[str] = set()
    for condition in config["conditions"]:
        steering_variant = circuit_variant(condition)
        steering_metadata: dict[str, object] = {
            "mode": "intact",
            "seed": None,
            "epg_to_delta_accepted_swaps": 0,
            "delta_to_pfl3_accepted_swaps": 0,
            "global_phase_alignment_deg": 0.0,
            "mean_pfl3_phase_residual_deg": 0.0,
            "maximum_pfl3_phase_residual_deg": 0.0,
        }
        if condition.get("steering_null_seed") is not None:
            steering_null = build_steering_null(
                model,
                int(condition["steering_null_seed"]),
                float(orientation["epg_heading_sign"]),
                float(orientation["phase_offset_deg"]),
                projection_mode=condition.get("steering_null_projection", "both"),
            )
            steering_variant = {**(steering_variant or {}), **steering_null.variant}
            steering_metadata = steering_null.metadata
        drift = TravelDirectionDriftController(
            root,
            root / config["travel_direction_drift_config"],
            block_weight_rewire_seed=condition.get("block_weight_rewire_seed"),
        )
        arrival = dict(config.get("arrival_supervisor", {}))
        arrival.update(condition.get("arrival_supervisor_overrides", {}))
        arrival["enabled"] = bool(condition.get("arrival_supervisor_enabled", arrival.get("enabled", False)))
        local = {
            **config,
            "arrival_supervisor": arrival,
            "lateral_velocity_kd_per_s": float(condition["lateral_velocity_kd_per_s"]),
        }
        for scenario in config["scenarios"]:
            for index, (target, heading) in enumerate(cases):
                enabled = bool(condition["hdelta_enabled"])
                estimator = velocity_estimator(root, config, condition["velocity_source"]) if enabled else None
                result, trace = simulate(
                    root,
                    local,
                    plant,
                    model,
                    orientation,
                    target,
                    heading,
                    condition["yaw_controller"] == "proportional",
                    True,
                    scenario,
                    int(scenario["seed"]) + index,
                    circuit_variant=steering_variant,
                    circuit_condition=condition.get("circuit_condition", "intact"),
                    yaw_controller=condition["yaw_controller"],
                    heading_mode=condition["heading_mode"],
                    compass_config=root / condition.get(
                        "compass_config", config["phase_compass_config"]
                    ),
                    controller_label=condition["name"],
                    pfl2_controller=pfl2,
                    pfl2_enabled=bool(condition["pfl2_enabled"]),
                    drift_controller=drift,
                    drift_enabled=enabled,
                    velocity_estimator=estimator,
                    advance_controller=advance,
                    neural_advance_enabled=bool(condition["advance_enabled"]),
                    drift_oracle_mode=condition.get("drift_oracle_mode", "none"),
                    drift_readout_mode=condition.get("drift_readout_mode", "connectome"),
                )
                result.update(
                    {
                        "steering_ablation": condition.get("steering_ablation", "none"),
                        "connectome_null_mode": drift.null_metadata["mode"],
                        "connectome_null_seed": drift.null_metadata["seed"],
                        "steering_null_mode": steering_metadata["mode"],
                        "steering_null_seed": steering_metadata["seed"],
                        "steering_null_epg_to_delta_swaps": steering_metadata[
                            "epg_to_delta_accepted_swaps"
                        ],
                        "steering_null_delta_to_pfl3_swaps": steering_metadata[
                            "delta_to_pfl3_accepted_swaps"
                        ],
                        "steering_null_phase_alignment_deg": steering_metadata[
                            "global_phase_alignment_deg"
                        ],
                        "steering_null_mean_phase_residual_deg": steering_metadata[
                            "mean_pfl3_phase_residual_deg"
                        ],
                        "steering_null_max_phase_residual_deg": steering_metadata[
                            "maximum_pfl3_phase_residual_deg"
                        ],
                    }
                )
                rows.append(result)
                save_trace = bool(config.get("save_all_traces", False)) or not result["success"]
                if result["success"] and condition["name"] not in saved_first_success:
                    save_trace = True
                    saved_first_success.add(condition["name"])
                if save_trace and trace is not None:
                    np.savez_compressed(
                        trace_dir / f"{condition['name']}__{scenario['name']}__{index:02d}.npz",
                        columns=np.asarray(trace["columns"]),
                        values=trace["values"],
                    )
        subset = [row for row in rows if row["controller"] == condition["name"]]
        print(
            f"{condition['name']}: {sum(row['success'] for row in subset)}/{len(subset)}",
            flush=True,
        )

    frame = pd.DataFrame(rows)
    output.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output / "episodes.csv", index=False)
    aggregations = dict(
        episodes=("success", "size"),
        successes=("success", "sum"),
        success_rate=("success", "mean"),
        median_arrival_time_s=("arrival_time_s", "median"),
        median_path_efficiency=("path_efficiency", "median"),
        median_maximum_cross_track_m=("maximum_absolute_cross_track_m", "median"),
        median_dropout_heading_error_deg=("median_dropout_heading_error_deg", "median"),
        median_mean_compass_neural_weight_during_dropout=(
            "mean_compass_neural_weight_during_dropout", "median"
        ),
        maximum_compass_neural_weight_during_dropout=(
            "maximum_compass_neural_weight_during_dropout", "max"
        ),
        median_arrival_latched_fraction=("arrival_latched_fraction", "median"),
        median_drift_suppressed_fraction=("drift_suppressed_at_arrival_fraction", "median"),
        maximum_motor_saturation_fraction=("motor_saturation_fraction", "max"),
    )
    summary = frame.groupby("controller", as_index=False).agg(**aggregations)
    by_scenario = frame.groupby(["controller", "scenario"], as_index=False).agg(**aggregations)
    summary.to_csv(output / "summary.csv", index=False)
    by_scenario.to_csv(output / "summary_by_scenario.csv", index=False)
    effects: dict[str, float | int] = {}
    criteria: dict[str, bool] = {}
    if config.get("gate"):
        indexed = summary.set_index("controller")
        names = {
            "full": "full_flywire_v2",
            "direct": "direct_velocity_matched",
            "conventional": "conventional_navigation",
            "no_hdelta": "no_hdelta",
            "no_delta7": "delta7_ablated",
            "no_pfl2": "no_pfl2",
            **config.get("gate_controller_names", {}),
        }
        full = indexed.loc[names["full"]]
        direct = indexed.loc[names["direct"]]
        conventional = indexed.loc[names["conventional"]]
        no_hdelta = indexed.loc[names["no_hdelta"]]
        no_delta7 = indexed.loc[names["no_delta7"]]
        no_pfl2 = indexed.loc[names["no_pfl2"]]
        full_scenario_min = int(
            by_scenario.loc[by_scenario.controller == names["full"], "successes"].min()
        )
        effects = {
            "minimum_full_scenario_successes": full_scenario_min,
            "success_advantage_over_no_hdelta": int(full.successes - no_hdelta.successes),
            "success_advantage_over_delta7_ablation": int(full.successes - no_delta7.successes),
            "success_deficit_vs_direct": int(direct.successes - full.successes),
            "success_deficit_vs_conventional": int(conventional.successes - full.successes),
            "success_deficit_vs_no_pfl2": int(no_pfl2.successes - full.successes),
            "arrival_time_cost_vs_conventional_s": float(
                full.median_arrival_time_s - conventional.median_arrival_time_s
            ),
            "cross_track_cost_vs_conventional_m": float(
                full.median_maximum_cross_track_m - conventional.median_maximum_cross_track_m
            ),
        }
        gate = config["gate"]
        criteria = {
            "full_functional": bool(full.successes >= gate["minimum_full_successes"]),
            "each_scenario_functional": bool(
                full_scenario_min >= gate["minimum_successes_each_scenario"]
            ),
            "hdelta_dependency": bool(
                effects["success_advantage_over_no_hdelta"]
                >= gate["minimum_success_advantage_over_no_hdelta"]
            ),
            "delta7_pfl3_dependency": bool(
                effects["success_advantage_over_delta7_ablation"]
                >= gate["minimum_success_advantage_over_delta7_ablation"]
            ),
            "direct_comparability": bool(
                effects["success_deficit_vs_direct"]
                <= gate["maximum_success_deficit_vs_direct"]
            ),
            "conventional_comparability": bool(
                effects["success_deficit_vs_conventional"]
                <= gate["maximum_success_deficit_vs_conventional"]
            ),
            "pfl2_non_degradation": bool(
                effects["success_deficit_vs_no_pfl2"]
                <= gate["maximum_success_deficit_vs_no_pfl2"]
            ),
            "bounded_arrival_cost": bool(
                effects["arrival_time_cost_vs_conventional_s"]
                <= gate["maximum_arrival_time_cost_vs_conventional_s"]
            ),
            "bounded_cross_track_cost": bool(
                effects["cross_track_cost_vs_conventional_m"]
                <= gate["maximum_cross_track_cost_vs_conventional_m"]
            ),
            "motor_saturation": bool(
                full.maximum_motor_saturation_fraction
                <= gate["maximum_motor_saturation_fraction"]
            ),
        }
    report = {
        "created_at": utc_now(),
        "status": config.get("parameter_status", "integrated_v2_result"),
        "dataset": "FAFB",
        "materialization_version": 783,
        "claim": config.get(
            "claim",
            "Integrated simulated controller evaluation. Arrival supervision and sensor fusion "
            "are explicit engineering layers; neural connectivity remains FlyWire-grounded.",
        ),
        "configuration": config_path.as_posix(),
        "configuration_sha256": file_hash(root / config_path),
        "source_sha256": file_hash(Path(__file__)),
        "simulation_source_sha256": file_hash(root / "src/flydrone/simulation/benchmark_quadrotor.py"),
        "arrival_source_sha256": file_hash(root / "src/flydrone/simulation/quadrotor_arrival.py"),
        "episodes": len(frame),
        "effects": effects,
        "criteria": criteria,
        "passes_gate": bool(criteria) and all(criteria.values()),
        "summary": summary.astype(object).where(pd.notna(summary), None).to_dict(orient="records"),
        "summary_by_scenario": by_scenario.astype(object).where(pd.notna(by_scenario), None).to_dict(orient="records"),
    }
    save_json(report_path, report)
    manifest_path = root / "data/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest[config["manifest_key"]] = {
        "status": "integrated_v2_completed",
        "report": report_path.relative_to(root).as_posix(),
        "report_sha256": file_hash(report_path),
        "episodes": len(frame),
    }
    save_json(manifest_path, manifest)
    print(json.dumps(report, indent=2), flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/quadrotor_integrated_v2_development.yaml"),
    )
    run(Path.cwd(), parser.parse_args().config)
