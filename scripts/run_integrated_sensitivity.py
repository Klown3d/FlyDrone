"""Small one-at-a-time engineering sensitivity diagnostic on reused cases."""
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
from flydrone.neural.travel_direction_drift import TravelDirectionDriftController
from flydrone.simulation.benchmark_integrated_v2 import load_config, velocity_estimator
from flydrone.simulation.benchmark_quadrotor import simulate

ROOT = Path(__file__).resolve().parents[1]


def run(config_path: Path = Path("configs/integrated_v4_sensitivity.yaml")) -> None:
    path = ROOT / config_path
    config = load_config(ROOT, path)
    output = ROOT / config["output"]
    if (output / "report.json").exists():
        raise FileExistsError("Preserve the existing diagnostic; use a new version to rerun.")
    output.mkdir(parents=True, exist_ok=True)
    orientation = yaml.safe_load((ROOT / config["orientation_config"]).read_text())
    plant = yaml.safe_load((ROOT / config["plant_config"]).read_text())
    model = EPGDelta7Candidate(ROOT, ROOT / orientation["candidate_config"])
    pfl2 = PFL2SteeringController(ROOT, ROOT / config["pfl2_steering_config"])
    advance = PFL2AdvanceController(ROOT / config["pfl2_advance_config"])
    rows = []
    for variant in config["variants"]:
        local_orientation = dict(orientation)
        drift = TravelDirectionDriftController(ROOT, ROOT / config["travel_direction_drift_config"])
        factor = float(variant["multiplier"])
        if variant["parameter"] == "steering_gain":
            local_orientation["readout_gain_rad_per_s_per_hz"] *= factor
        elif variant["parameter"] == "drift_gain":
            drift.gain *= factor
        elif variant["parameter"] not in {"none", "compass_time_constant"}:
            raise ValueError(variant["parameter"])
        local = {**config, "lateral_velocity_kd_per_s": 0.25}
        for scenario in config["scenarios"]:
            for index, target in enumerate(config["target_bearings_deg"]):
                result, _ = simulate(
                    ROOT, local, plant, model, local_orientation,
                    np.deg2rad(target), np.deg2rad(config["initial_relative_headings_deg"][0]),
                    False, False, scenario, int(scenario["seed"]) + index,
                    yaw_controller="neural", heading_mode="neural_compass",
                    compass_config=ROOT / variant.get("compass_config", config["phase_compass_config"]),
                    controller_label=variant["name"], pfl2_controller=pfl2,
                    drift_controller=drift,
                    velocity_estimator=velocity_estimator(ROOT, config, "inertial_fusion"),
                    advance_controller=advance,
                )
                rows.append({**result, "parameter": variant["parameter"], "multiplier": factor})
        pd.DataFrame(rows).to_csv(output / "episodes.csv", index=False)
        selected = [r for r in rows if r["controller"] == variant["name"]]
        print(f"{variant['name']}: {sum(r['success'] for r in selected)}/{len(selected)}", flush=True)
    frame = pd.DataFrame(rows)
    summary = frame.groupby("controller", as_index=False).agg(
        episodes=("success", "size"), successes=("success", "sum"),
        median_cross_track_m=("maximum_absolute_cross_track_m", "median"),
        median_arrival_s=("arrival_time_s", "median"),
    )
    summary.to_csv(output / "summary.csv", index=False)
    save_json(output / "report.json", {
        "created_at": utc_now(), "evaluation_role": config["evaluation_role"],
        "dataset": "FAFB", "materialization_version": 783,
        "configuration_sha256": file_hash(path), "source_sha256": file_hash(Path(__file__)),
        "episodes_sha256": file_hash(output / "episodes.csv"),
        "summary": json.loads(summary.to_json(orient="records")),
        "limit": "Small one-at-a-time diagnostic on reused development cases; OOD and interactions remain untested.",
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/integrated_v4_sensitivity.yaml"))
    run(parser.parse_args().config)
