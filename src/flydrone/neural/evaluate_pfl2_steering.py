"""Development gate for PFL2 magnitude modulation of PFL3 steering."""
from pathlib import Path
import argparse
import json

import numpy as np
import pandas as pd
import yaml

from flydrone.data.acquire import file_hash, save_json, utc_now
from flydrone.neural.epg_delta7 import EPGDelta7Candidate
from flydrone.neural.orientation_closed_loop import wrap, yaw_step
from flydrone.neural.pfl2_steering import PFL2SteeringController


def run(root: Path, config_path: Path = Path("configs/pfl2_steering.yaml")) -> None:
    c = yaml.safe_load((root / config_path).read_text(encoding="utf-8"))
    orientation_path = root / "configs/orientation_candidate_v1.yaml"
    orientation = yaml.safe_load(orientation_path.read_text(encoding="utf-8"))
    model = EPGDelta7Candidate(root, root / orientation["candidate_config"])
    controller = PFL2SteeringController(root, root / config_path)
    steps = round(c["duration_s"] / c["dt_s"])
    hold = round(c["success_hold_s"] / c["dt_s"])
    rows = []
    for condition, enabled in (("pfl3_plus_pfl2", True), ("pfl3_only", False)):
        for goal_deg in c["goals_deg"]:
            for initial_error_deg in c["initial_errors_deg"]:
                goal = np.deg2rad(goal_deg)
                heading = float(wrap(goal + np.deg2rad(initial_error_deg)))
                rate = 0.0
                errors, commands, indices = [], [], []
                for _ in range(steps):
                    command, _, _, index, _, _ = controller.command(
                        model, heading, goal, orientation, enabled=enabled
                    )
                    rate = float(yaw_step(np.asarray(rate), np.asarray(command), c["dt_s"], c["yaw_response_tau_s"]))
                    heading = float(wrap(heading + c["dt_s"] * rate))
                    errors.append(float(np.rad2deg(wrap(heading - goal))))
                    commands.append(command); indices.append(index)
                valid = np.abs(errors) <= c["success_error_deg"]
                windows = np.convolve(valid.astype(int), np.ones(hold, dtype=int), mode="valid")
                matches = np.flatnonzero(windows == hold)
                initial_command = commands[0]
                rows.append({
                    "condition": condition,
                    "goal_deg": goal_deg,
                    "initial_error_deg": initial_error_deg,
                    "success": bool(len(matches)),
                    "first_hold_start_s": None if not len(matches) else float(matches[0] * c["dt_s"]),
                    "final_abs_error_deg": abs(errors[-1]),
                    "initial_direction_correct": bool(initial_command * -initial_error_deg > 0),
                    "initial_command_rad_s": initial_command,
                    "initial_pfl2_index": indices[0],
                    "maximum_abs_command_rad_s": float(np.max(np.abs(commands))),
                })
    frame = pd.DataFrame(rows)
    output = root / c["output"]; output.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output / "episodes.csv", index=False)
    summary = frame.groupby("condition", as_index=False).agg(
        episodes=("success", "size"), successes=("success", "sum"),
        direction_accuracy=("initial_direction_correct", "mean"),
        median_settle_s=("first_hold_start_s", "median"),
        maximum_final_error_deg=("final_abs_error_deg", "max"),
    )
    large = frame.loc[frame["initial_error_deg"].abs() >= 150].groupby("condition")["first_hold_start_s"].median()
    intact = summary.set_index("condition").loc["pfl3_plus_pfl2"]
    improvement = float(large["pfl3_only"] - large["pfl3_plus_pfl2"])
    keys = ["goal_deg", "initial_error_deg"]
    paired = frame.loc[frame["condition"].eq("pfl3_plus_pfl2")].merge(
        frame.loc[frame["condition"].eq("pfl3_only")], on=keys, suffixes=("_intact", "_ablated")
    )
    changed_direction = int((np.sign(paired["initial_command_rad_s_intact"]) != np.sign(paired["initial_command_rad_s_ablated"])).sum())
    report = {
        "created_at": utc_now(), "dataset": "FAFB", "materialization_version": 783,
        "claim": "Development-only PFL2 drone-interface test; PFL3 selects sign and contact-weighted PFL2 only scales magnitude through an engineering gain.",
        "configuration": config_path.as_posix(), "configuration_sha256": file_hash(root / config_path),
        "source_sha256": file_hash(Path(__file__)), "episodes": len(frame),
        "large_error_median_settle_s": {k: float(v) for k, v in large.items()},
        "large_error_settle_improvement_s": improvement,
        "pfl2_changed_initial_turn_direction_cases": changed_direction,
        "summary": summary.to_dict(orient="records"),
        "passes_development_gate": bool(intact.successes == intact.episodes and changed_direction == 0 and improvement > 0),
    }
    save_json(output / "report.json", report)
    manifest_path = root / "data/manifest.json"; manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["pfl2_steering_development"] = {"status": "completed", "report": (output / "report.json").relative_to(root).as_posix(), "report_sha256": file_hash(output / "report.json")}
    save_json(manifest_path, manifest)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/pfl2_steering.yaml"))
    run(Path.cwd(), parser.parse_args().config)
