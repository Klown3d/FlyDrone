"""Locked hierarchical analysis for the PFN-to-hDeltaB confirmatory gate."""
from __future__ import annotations

from pathlib import Path
import argparse
import json
import math

import numpy as np
import pandas as pd
import yaml

from flydrone.data.acquire import file_hash, save_json, utc_now


KEY = ["scenario", "target_bearing_deg", "initial_relative_heading_deg"]


def wilson(successes: int, episodes: int, z: float = 1.959963984540054) -> list[float]:
    proportion = successes / episodes
    denominator = 1 + z * z / episodes
    center = (proportion + z * z / (2 * episodes)) / denominator
    half = z * math.sqrt(proportion * (1 - proportion) / episodes + z * z / (4 * episodes**2)) / denominator
    return [float(center - half), float(center + half)]


def paired_bootstrap(values: np.ndarray, seed: int, samples: int = 20_000) -> list[float]:
    values = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    boot = np.median(values[rng.integers(0, len(values), size=(samples, len(values)))], axis=1)
    return [float(value) for value in np.quantile(boot, [0.025, 0.975])]


def _criterion(required: bool, passed: bool, evidence: dict) -> dict:
    return {"status": "passed" if passed else "failed"} | evidence if required else {
        "status": "not_tested_due_prior_failure", **evidence}


def analyze(root: Path, config_path: Path) -> dict:
    from flydrone.simulation.confirmatory_protocol import verify_lock

    lock = verify_lock(root, config_path, allow_existing_output=True)
    config = yaml.safe_load((root / config_path).read_text(encoding="utf-8"))
    output = root / config["output"]
    episodes_path = output / "episodes.csv"
    if not episodes_path.exists():
        raise FileNotFoundError("The confirmatory episodes file does not exist")
    frame = pd.read_csv(episodes_path)
    expected = set(condition["name"] for condition in config["conditions"])
    if set(frame.controller) != expected:
        raise ValueError("Episode conditions differ from the frozen protocol")
    counts = frame.groupby("controller").size()
    if not np.all(counts.to_numpy() == 100):
        raise ValueError(f"Every condition must contain 100 episodes: {counts.to_dict()}")
    reference_keys = set(map(tuple, frame.loc[frame.controller.eq("flywire_hdelta_intact"), KEY].to_numpy()))
    for name in expected:
        keys = set(map(tuple, frame.loc[frame.controller.eq(name), KEY].to_numpy()))
        if keys != reference_keys:
            raise ValueError(f"Unpaired cases in {name}")

    summaries = []
    for name, subset in frame.groupby("controller"):
        successes = int(subset.success.sum())
        summaries.append({
            "controller": name,
            "episodes": int(len(subset)),
            "successes": successes,
            "success_rate": successes / len(subset),
            "success_rate_wilson_95pct": wilson(successes, len(subset)),
            "collisions": int(subset.collision.sum()),
            "maximum_motor_saturation_fraction": float(subset.motor_saturation_fraction.max()),
            "median_arrival_time_s": None if not subset.arrival_time_s.notna().any() else float(subset.arrival_time_s.median()),
            "median_path_efficiency": None if not subset.path_efficiency.notna().any() else float(subset.path_efficiency.median()),
            "median_maximum_cross_track_m": float(subset.maximum_absolute_cross_track_m.median()),
            "median_decoded_direction_error_deg": None if not subset.median_decoded_direction_error_deg.notna().any() else float(subset.median_decoded_direction_error_deg.median()),
        })
    summary = {item["controller"]: item for item in summaries}
    intact = summary["flywire_hdelta_intact"]
    direct = summary["direct_velocity_matched"]
    null_names = sorted(name for name in expected if name.startswith("null_rewire_block_"))
    null_rates = np.asarray([summary[name]["success_rate"] for name in null_names])
    gate = config["gate"]

    primary_pass = intact["successes"] >= int(gate["minimum_intact_successes"])
    null_median = float(np.median(null_rates))
    null_p95 = float(np.quantile(null_rates, 0.95))
    median_advantage_pp = 100 * (intact["success_rate"] - null_median)
    attribution_pass = (median_advantage_pp >= float(gate["minimum_success_advantage_over_null_median_percentage_points"])
                        and (not gate["require_intact_at_or_above_null_95th_percentile"]
                             or intact["success_rate"] >= null_p95))
    direct_deficit_pp = 100 * (direct["success_rate"] - intact["success_rate"])
    comparability_pass = direct_deficit_pp <= float(gate["maximum_success_deficit_vs_direct_percentage_points"])
    safety_pass = (intact["collisions"] <= int(gate["maximum_collisions"])
                   and intact["maximum_motor_saturation_fraction"] <= float(gate["maximum_motor_saturation_fraction"]))
    criteria = {
        "primary_functional": _criterion(True, primary_pass, {
            "observed_successes": intact["successes"], "required_successes": int(gate["minimum_intact_successes"])}),
        "connectome_attribution": _criterion(primary_pass, attribution_pass, {
            "success_advantage_over_null_median_percentage_points": median_advantage_pp,
            "required_advantage_percentage_points": float(gate["minimum_success_advantage_over_null_median_percentage_points"]),
            "null_success_rate_median": null_median, "null_success_rate_95th_percentile": null_p95}),
        "matched_direct_comparability": _criterion(primary_pass and attribution_pass, comparability_pass, {
            "success_deficit_vs_direct_percentage_points": direct_deficit_pp,
            "maximum_allowed_deficit_percentage_points": float(gate["maximum_success_deficit_vs_direct_percentage_points"])}),
        "safety": _criterion(primary_pass and attribution_pass and comparability_pass, safety_pass, {
            "collisions": intact["collisions"],
            "maximum_motor_saturation_fraction": intact["maximum_motor_saturation_fraction"]}),
    }

    intact_frame = frame.loc[frame.controller.eq("flywire_hdelta_intact")].set_index(KEY)
    secondary = []
    for offset, name in enumerate(null_names):
        null = frame.loc[frame.controller.eq(name)].set_index(KEY).loc[intact_frame.index]
        difference = (null.median_decoded_direction_error_deg
                      - intact_frame.median_decoded_direction_error_deg).to_numpy(float)
        secondary.append({
            "null_condition": name,
            "median_direction_error_increase_deg": float(np.median(difference)),
            "paired_bootstrap_95pct_deg": paired_bootstrap(difference, 62001 + offset),
        })

    ordered = [criteria[key]["status"] for key in
               ("primary_functional", "connectome_attribution", "matched_direct_comparability", "safety")]
    report = {
        "created_at": utc_now(),
        "status": "confirmatory_gate_completed",
        "protocol_id": config["protocol_id"],
        "lock_created_at": lock["created_at"],
        "configuration_sha256": file_hash(root / config_path),
        "episodes_sha256": file_hash(episodes_path),
        "episodes": int(len(frame)),
        "criteria": criteria,
        "overall_gate_passed": all(status == "passed" for status in ordered),
        "summary": summaries,
        "secondary_direction_error": secondary,
        "interpretation_rule": "Criteria are hierarchical. A failed earlier criterion makes later criteria non-confirmatory even when their descriptive values are favorable.",
    }
    save_json(output / "confirmatory_analysis.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/quadrotor_connectome_confirmatory.yaml"))
    print(json.dumps(analyze(Path.cwd(), parser.parse_args().config), indent=2))
