"""Paired 6-DoF development ablation of PFL2 magnitude modulation."""
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


def run(root: Path, config_path: Path = Path("configs/quadrotor_pfl2_steering.yaml")) -> None:
    spec = yaml.safe_load((root / config_path).read_text(encoding="utf-8"))
    base = yaml.safe_load((root / spec["base_config"]).read_text(encoding="utf-8"))
    c = {**base, **spec}
    plant = yaml.safe_load((root / c["plant_config"]).read_text(encoding="utf-8"))
    orientation = yaml.safe_load((root / c["orientation_config"]).read_text(encoding="utf-8"))
    model = EPGDelta7Candidate(root, root / orientation["candidate_config"])
    pfl2 = PFL2SteeringController(root, root / c["pfl2_steering_config"])
    cases = [(np.deg2rad(t), np.deg2rad(h)) for t in c["target_bearings_deg"] for h in c["initial_relative_headings_deg"]]
    rows = []
    for label, enabled in (("pfl3_plus_pfl2", True), ("pfl3_only", False)):
        for index, (target, heading) in enumerate(cases):
            result, _ = simulate(
                root, c, plant, model, orientation, target, heading, False, False,
                c["scenario"], int(c["scenario"]["seed"]) + index,
                heading_mode="direct", controller_label=label,
                pfl2_controller=pfl2, pfl2_enabled=enabled,
            )
            rows.append(result)
        print(f"{label}: {sum(r['success'] for r in rows if r['controller']==label)}/{len(cases)}", flush=True)
    frame = pd.DataFrame(rows)
    output = root / c["output"]; output.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output / "episodes.csv", index=False)
    summary = frame.groupby("controller", as_index=False).agg(
        episodes=("success", "size"), successes=("success", "sum"),
        median_arrival_time_s=("arrival_time_s", "median"),
        median_path_efficiency=("path_efficiency", "median"),
        median_final_distance_m=("final_distance_m", "median"),
        maximum_tilt_deg=("max_tilt_deg", "max"),
        maximum_motor_saturation_fraction=("motor_saturation_fraction", "max"),
    )
    indexed = summary.set_index("controller")
    report = {
        "created_at": utc_now(), "dataset": "FAFB", "materialization_version": 783,
        "claim": "Development-only paired 6-DoF PFL2 magnitude-modulation ablation; conventional inner-loop stabilization remains active.",
        "configuration": config_path.as_posix(), "configuration_sha256": file_hash(root / config_path),
        "source_sha256": file_hash(Path(__file__)), "episodes": len(frame),
        "arrival_time_improvement_s": float(indexed.loc["pfl3_only", "median_arrival_time_s"] - indexed.loc["pfl3_plus_pfl2", "median_arrival_time_s"]),
        "summary": summary.to_dict(orient="records"),
    }
    report["passes_development_gate"] = bool(
        indexed.loc["pfl3_plus_pfl2", "successes"] == indexed.loc["pfl3_plus_pfl2", "episodes"]
        and report["arrival_time_improvement_s"] > 0
    )
    save_json(output / "report.json", report)
    manifest_path = root / "data/manifest.json"; manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest[c["manifest_key"]] = {"status": "completed", "report": (output / "report.json").relative_to(root).as_posix(), "report_sha256": file_hash(output / "report.json")}
    save_json(manifest_path, manifest)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/quadrotor_pfl2_steering.yaml"))
    run(Path.cwd(), parser.parse_args().config)
