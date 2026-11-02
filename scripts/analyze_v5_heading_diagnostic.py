"""Analyze the frozen prospective v5 heading-oracle diagnostic."""
from pathlib import Path
import json
import numpy as np
import pandas as pd

from flydrone.data.acquire import file_hash, save_json, utc_now

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "results/simulation/quadrotor_integrated_v5_heading_diagnostic"
KEYS = ["scenario", "target_bearing_deg", "initial_relative_heading_deg"]


def main() -> None:
    episodes = pd.read_csv(FOLDER / "episodes.csv")
    indexed = {name: group.set_index(KEYS).sort_index()
               for name, group in episodes.groupby("controller")}
    observed = indexed["observed_v4"]
    failures = ~observed.success.astype(bool)
    failure_count = int(failures.sum())
    rescue = {}
    for name in ("diagnostic_true_heading", "diagnostic_true_velocity",
                 "diagnostic_true_heading_velocity"):
        paired = indexed[name].reindex(observed.index)
        rescue[name] = int((failures & paired.success.astype(bool)).sum())
    summary = episodes.groupby("controller", as_index=False).agg(
        episodes=("success", "size"), successes=("success", "sum"),
        success_rate=("success", "mean"), median_final_distance_m=("final_distance_m", "median"),
        median_maximum_cross_track_m=("maximum_absolute_cross_track_m", "median"),
        median_dropout_heading_error_deg=("median_dropout_heading_error_deg", "median"),
        collisions=("collision", "sum"), maximum_motor_saturation=("motor_saturation_fraction", "max"),
    )
    summary["rescued_observed_failures"] = summary.controller.map(rescue).fillna(0).astype(int)
    summary.to_csv(FOLDER / "diagnostic_summary.csv", index=False)
    success = dict(zip(summary.controller, summary.successes.astype(int)))
    criteria = {
        "informative_observed_failures": failure_count >= 4,
        "heading_rescues_at_least_half": failure_count > 0 and rescue["diagnostic_true_heading"] * 2 >= failure_count,
        "heading_rescues_more_than_velocity": rescue["diagnostic_true_heading"] > rescue["diagnostic_true_velocity"],
        "combined_not_worse_than_heading_by_more_than_one": success["diagnostic_true_heading_velocity"] + 1 >= success["diagnostic_true_heading"],
        "no_collisions_or_saturation": bool((summary.collisions == 0).all() and np.isclose(summary.maximum_motor_saturation.max(), 0.0)),
    }
    report = {
        "created_at": utc_now(), "status": "prospective_v5_heading_diagnostic_completed",
        "dataset": "FAFB", "materialization_version": 783,
        "claim": "Privileged oracle diagnosis only; not controller validation.",
        "episodes": int(len(episodes)), "observed_failures": failure_count,
        "rescued_observed_failures": rescue, "criteria": criteria,
        "supports_heading_localization_generalization": bool(all(criteria.values())),
        "summary": summary.astype(object).where(pd.notna(summary), None).to_dict(orient="records"),
        "inputs_sha256": {"episodes": file_hash(FOLDER / "episodes.csv"),
                          "lock": file_hash(ROOT / "configs/quadrotor_integrated_v5_heading_diagnostic.lock.json")},
    }
    save_json(FOLDER / "diagnostic_report.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__": main()
