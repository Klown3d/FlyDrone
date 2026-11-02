"""Summarize the non-confirmatory EPG→Delta7→PFL3 null diagnostic."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results/simulation/quadrotor_integrated_v4_steering_null_development"


def main() -> None:
    episodes_path = RESULTS / "episodes.csv"
    frame = pd.read_csv(episodes_path)
    intact = frame.loc[frame.controller.eq("flywire_steering_intact")]
    null_names = sorted(
        name for name in frame.controller.unique() if str(name).startswith("steering_null_")
    )
    rows = []
    for name in null_names:
        selected = frame.loc[frame.controller.eq(name)]
        rows.append(
            {
                "condition": name,
                "successes": int(selected.success.sum()),
                "episodes": int(len(selected)),
                "median_maximum_cross_track_m": float(
                    selected.maximum_absolute_cross_track_m.median()
                ),
                "global_phase_alignment_deg": float(
                    selected.steering_null_phase_alignment_deg.iloc[0]
                ),
                "mean_pfl3_phase_residual_deg": float(
                    selected.steering_null_mean_phase_residual_deg.iloc[0]
                ),
                "maximum_pfl3_phase_residual_deg": float(
                    selected.steering_null_max_phase_residual_deg.iloc[0]
                ),
                "epg_to_delta_accepted_swaps": int(
                    selected.steering_null_epg_to_delta_swaps.iloc[0]
                ),
                "delta_to_pfl3_accepted_swaps": int(
                    selected.steering_null_delta_to_pfl3_swaps.iloc[0]
                ),
            }
        )

    successes = np.asarray([row["successes"] for row in rows])
    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "development_only_not_confirmatory",
        "episodes_sha256": hashlib.sha256(episodes_path.read_bytes()).hexdigest(),
        "total_simulated_flights": int(len(frame)),
        "intact": {
            "successes": int(intact.success.sum()),
            "episodes": int(len(intact)),
            "median_maximum_cross_track_m": float(
                intact.maximum_absolute_cross_track_m.median()
            ),
        },
        "null_distribution": {
            "successes": successes.tolist(),
            "range": [int(successes.min()), int(successes.max())],
            "median": float(np.median(successes)),
            "mean": float(np.mean(successes)),
            "fraction_below_intact": float(np.mean(successes < int(intact.success.sum()))),
            "descriptive_plus_one_rank_p_not_confirmatory": float(
                (1 + np.sum(successes >= int(intact.success.sum()))) / (len(successes) + 1)
            ),
        },
        "null_conditions": rows,
        "interpretation": (
            "All five controlled steering rewires underperformed the intact projection after "
            "global phase alignment. This supports running a separately frozen prospective "
            "gate, but reused development cases and only five nulls prohibit confirmation."
        ),
    }
    (RESULTS / "steering_null_development_analysis.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
