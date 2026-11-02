"""Run-once prospective 6DoF gate for PFN/hDeltaB drift compensation."""
from __future__ import annotations

from pathlib import Path
import argparse, json
import numpy as np
import pandas as pd
import yaml

from flydrone.data.acquire import file_hash, save_json, utc_now
from flydrone.neural.epg_delta7 import EPGDelta7Candidate
from flydrone.neural.travel_direction_drift import TravelDirectionDriftController
from flydrone.simulation.benchmark_quadrotor import simulate


def run(root: Path, config_path: Path) -> dict:
    spec = yaml.safe_load((root / config_path).read_text(encoding="utf-8")); output = root / spec["output"]
    report_path = output / "report.json"
    if spec.get("run_once") and report_path.exists(): raise RuntimeError(f"Prospective report already exists: {report_path}")
    base = yaml.safe_load((root / spec["base_config"]).read_text(encoding="utf-8")); c = {**base, **spec}
    plant = yaml.safe_load((root / c["plant_config"]).read_text(encoding="utf-8"))
    orientation = yaml.safe_load((root / c["orientation_config"]).read_text(encoding="utf-8"))
    model = EPGDelta7Candidate(root, root / orientation["candidate_config"])
    intact = TravelDirectionDriftController(root, root / c["travel_direction_drift_config"])
    shuffled = TravelDirectionDriftController(root, root / c["travel_direction_drift_config"], phase_shuffle_seed=91703)
    cases = [(np.deg2rad(t), np.deg2rad(h)) for t in c["target_bearings_deg"] for h in c["initial_relative_headings_deg"]]
    rows = []
    for condition in c["conditions"]:
        local = {**c, "lateral_velocity_kd_per_s": float(condition["lateral_velocity_kd_per_s"])}
        controller = shuffled if "phase_shuffle_seed" in condition else intact
        for scenario in c["scenarios"]:
            for index, (target, heading) in enumerate(cases):
                result, _ = simulate(root, local, plant, model, orientation, target, heading, False, False,
                    scenario, int(scenario["seed"]) + index, heading_mode="direct", controller_label=condition["name"],
                    drift_controller=controller, drift_enabled=bool(condition["hdelta_enabled"]))
                rows.append(result)
    frame = pd.DataFrame(rows); output.mkdir(parents=True, exist_ok=True); frame.to_csv(output / "episodes.csv", index=False)
    summary = frame.groupby("controller", as_index=False).agg(episodes=("success","size"),successes=("success","sum"),
        median_maximum_cross_track_m=("maximum_absolute_cross_track_m","median"),median_mean_cross_track_m=("mean_absolute_cross_track_m","median"),
        median_arrival_time_s=("arrival_time_s","median"),median_path_efficiency=("path_efficiency","median"),
        maximum_motor_saturation_fraction=("motor_saturation_fraction","max"))
    s=summary.set_index("controller"); h=s.loc["hdelta_compensation"]; a=s.loc["no_drift_compensation"]; v=s.loc["conventional_velocity_compensation"]; n=s.loc["shuffled_pfn_phases"]; g=c["gate"]
    effects={"success_advantage_over_absent":int(h.successes-a.successes),
        "cross_track_reduction_vs_absent_fraction":float(1-h.median_maximum_cross_track_m/a.median_maximum_cross_track_m),
        "cross_track_disadvantage_vs_conventional_m":float(h.median_maximum_cross_track_m-v.median_maximum_cross_track_m),
        "cross_track_reduction_vs_shuffled_fraction":float(1-h.median_maximum_cross_track_m/n.median_maximum_cross_track_m)}
    criteria={"hdelta_successes":bool(h.successes>=g["minimum_hdelta_successes"]),"success_advantage":bool(effects["success_advantage_over_absent"]>=g["minimum_success_advantage_over_absent"]),
        "reduction_vs_absent":bool(effects["cross_track_reduction_vs_absent_fraction"]>=g["minimum_cross_track_reduction_vs_absent_fraction"]),
        "bounded_vs_conventional":bool(effects["cross_track_disadvantage_vs_conventional_m"]<=g["maximum_cross_track_disadvantage_vs_conventional_m"]),
        "reduction_vs_shuffled":bool(effects["cross_track_reduction_vs_shuffled_fraction"]>=g["minimum_cross_track_reduction_vs_shuffled_fraction"]),
        "motor_saturation":bool(h.maximum_motor_saturation_fraction<=g["maximum_motor_saturation_fraction"])}
    report={"created_at":utc_now(),"status":"immutable_run_once_prospective_result","dataset":"FAFB","materialization_version":783,
        "claim":"Prospective paired 6DoF drift gate; neural direction with engineering speed magnitude and inner loop.","configuration":config_path.as_posix(),
        "configuration_sha256":file_hash(root/config_path),"source_sha256":file_hash(Path(__file__)),"drift_source_sha256":file_hash(root/"src/flydrone/neural/travel_direction_drift.py"),
        "model_source_sha256":file_hash(root/"src/flydrone/neural/travel_direction_model.py"),"episodes":len(frame),"effects":effects,"criteria":criteria,
        "passes_prospective_gate":bool(all(criteria.values())),"summary":summary.to_dict(orient="records")}
    save_json(report_path,report); manifest_path=root/"data/manifest.json"; manifest=json.loads(manifest_path.read_text(encoding="utf-8")); manifest[c["manifest_key"]]={"status":"prospective_gate_completed","report":report_path.relative_to(root).as_posix(),"report_sha256":file_hash(report_path),"passed":report["passes_prospective_gate"]}; save_json(manifest_path,manifest)
    print(json.dumps(report,indent=2),flush=True); return report


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("--config",type=Path,default=Path("configs/quadrotor_travel_direction_prospective.yaml")); run(Path.cwd(),p.parse_args().config)
