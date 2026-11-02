"""Summarize projection-separated steering nulls without confirmatory inference."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results/simulation/quadrotor_integrated_v4_steering_projection_null_development"


def summarize(frame: pd.DataFrame, prefix: str) -> dict:
    rows = []
    for name in sorted(value for value in frame.controller.unique() if str(value).startswith(prefix)):
        selected = frame.loc[frame.controller.eq(name)]
        rows.append(
            {
                "condition": name,
                "successes": int(selected.success.sum()),
                "median_maximum_cross_track_m": float(selected.maximum_absolute_cross_track_m.median()),
                "mean_pfl3_phase_residual_deg": float(selected.steering_null_mean_phase_residual_deg.iloc[0]),
                "epg_to_delta_accepted_swaps": int(selected.steering_null_epg_to_delta_swaps.iloc[0]),
                "delta_to_pfl3_accepted_swaps": int(selected.steering_null_delta_to_pfl3_swaps.iloc[0]),
            }
        )
    successes = np.asarray([row["successes"] for row in rows])
    cross = np.asarray([row["median_maximum_cross_track_m"] for row in rows])
    residual = np.asarray([row["mean_pfl3_phase_residual_deg"] for row in rows])
    return {
        "conditions": rows,
        "successes": successes.tolist(),
        "success_range": [int(successes.min()), int(successes.max())],
        "success_median": float(np.median(successes)),
        "success_mean": float(np.mean(successes)),
        "median_of_condition_cross_track_medians_m": float(np.median(cross)),
        "phase_residual_range_deg": [float(residual.min()), float(residual.max())],
        "descriptive_plus_one_rank_p_not_confirmatory": float(
            (1 + np.sum(successes >= 12)) / (len(successes) + 1)
        ),
    }


def main() -> None:
    episodes_path = RESULTS / "episodes.csv"
    frame = pd.read_csv(episodes_path)
    intact = frame.loc[frame.controller.eq("flywire_steering_intact")]
    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "development_only_not_confirmatory",
        "episodes_sha256": hashlib.sha256(episodes_path.read_bytes()).hexdigest(),
        "total_simulated_flights": int(len(frame)),
        "intact": {
            "successes": int(intact.success.sum()),
            "episodes": int(len(intact)),
            "median_maximum_cross_track_m": float(intact.maximum_absolute_cross_track_m.median()),
        },
        "epg_to_delta_only": summarize(frame, "epg_delta_null_"),
        "delta_to_pfl3_only": summarize(frame, "delta_pfl3_null_"),
        "interpretation": (
            "Both projections show a consistent development-stage loss relative to intact "
            "when rewired separately after algebraic global-phase alignment. Independent "
            "prospective tests remain necessary before projection-specific attribution."
        ),
    }
    (RESULTS / "projection_null_development_analysis.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
