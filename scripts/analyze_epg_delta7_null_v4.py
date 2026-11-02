"""Analyze the prospectively frozen v4 EPG-to-Delta7-only null gate."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results/simulation/quadrotor_integrated_v4_epg_delta7_null_prospective"
FIGURES = ROOT / "docs/research/figures"


def analyze() -> dict:
    episodes_path = RESULTS / "episodes.csv"
    frame = pd.read_csv(episodes_path)
    intact = frame.loc[frame.controller.eq("flywire_epg_delta7_intact")]
    names = sorted(
        str(name) for name in frame.controller.unique() if str(name).startswith("steering_null_")
    )
    rows: list[dict] = []
    for name in names:
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

    intact_successes = int(intact.success.sum())
    successes = np.asarray([row["successes"] for row in rows])
    cross_track = np.asarray([row["median_maximum_cross_track_m"] for row in rows])
    residual = np.asarray([row["mean_pfl3_phase_residual_deg"] for row in rows])
    intact_cross = float(intact.maximum_absolute_cross_track_m.median())
    rank_p = float((1 + np.sum(successes >= intact_successes)) / (len(rows) + 1))
    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "prospective_epg_to_delta7_connectome_null_gate_complete",
        "protocol_id": "flydrone_integrated_v4_epg_delta7_null_prospective_v1",
        "episodes_sha256": hashlib.sha256(episodes_path.read_bytes()).hexdigest(),
        "design": {
            "projection_rewired": "EPG-to-Delta7",
            "projection_left_exactly_intact": "Delta7-to-PFL3",
            "paired_cases_per_condition": int(len(intact)),
            "null_conditions": int(len(rows)),
            "total_simulated_flights": int(len(frame)),
            "preserved_statistics": [
                "binary row degree within each presynaptic source-side block",
                "binary column degree within each presynaptic source-side block",
                "each postsynaptic row's exact nonzero raw-weight multiset within each block",
            ],
            "phase_control": (
                "one algebraic global phase alignment to the intact transfer; "
                "flight outcomes were not used"
            ),
            "not_preserved": ["weighted column sums", "exact EPG-to-Delta7 partner identity"],
        },
        "primary_gate": {
            "minimum_intact_successes": 10,
            "maximum_empirical_rank_p": 0.05,
            "intact_successes": intact_successes,
            "intact_episodes": int(len(intact)),
            "nulls_matching_or_exceeding_intact": int(np.sum(successes >= intact_successes)),
            "empirical_rank_p_plus_one": rank_p,
            "passes_intact_minimum": bool(intact_successes >= 10),
            "passes_rank_test": bool(rank_p <= 0.05),
            "passes_all": bool(intact_successes >= 10 and rank_p <= 0.05),
        },
        "null_distribution": {
            "successes": successes.tolist(),
            "minimum": int(successes.min()),
            "median": float(np.median(successes)),
            "mean": float(np.mean(successes)),
            "maximum": int(successes.max()),
            "zero_success_nulls": int(np.sum(successes == 0)),
            "nulls_below_intact": int(np.sum(successes < intact_successes)),
        },
        "secondary_cross_track": {
            "intact_median_maximum_cross_track_m": intact_cross,
            "median_of_null_condition_medians_m": float(np.median(cross_track)),
            "range_of_null_condition_medians_m": [float(cross_track.min()), float(cross_track.max())],
            "nulls_worse_than_intact_by_condition_median": int(np.sum(cross_track > intact_cross)),
        },
        "phase_residuals": {
            "mean_residual_range_deg": [float(residual.min()), float(residual.max())],
            "median_mean_residual_deg": float(np.median(residual)),
        },
        "structural_checks": {
            "all_epg_to_delta_swaps_positive": bool(
                all(row["epg_to_delta_accepted_swaps"] > 0 for row in rows)
            ),
            "all_delta_to_pfl3_swaps_zero": bool(
                all(row["delta_to_pfl3_accepted_swaps"] == 0 for row in rows)
            ),
        },
        "null_conditions": rows,
        "supported_claim": (
            "In this computational model and these prospectively frozen simulated scenarios, "
            "the specific FlyWire-grounded EPG-to-Delta7 partner arrangement contributes to "
            "successful navigation beyond the preserved block-wise degree and row-weight "
            "statistics, while Delta7-to-PFL3 is held exactly intact."
        ),
        "limits": [
            "This is computational attribution, not evidence of biological causality in a living fly.",
            "The nulls preserve selected graph statistics but not every higher-order network property.",
            "This does not establish superiority over conventional drone control.",
            "The rank p-value has the minimum attainable resolution of 1/21 with 20 null networks.",
            "Engineering sensor fusion, arrival supervision, stabilization and dynamics remain in the stack.",
        ],
    }
    (RESULTS / "prospective_epg_delta7_null_analysis.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def plot(report: dict) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    rows = report["null_conditions"]
    successes = np.sort([row["successes"] for row in rows])
    cross = np.sort([row["median_maximum_cross_track_m"] for row in rows])
    residual = np.sort([row["mean_pfl3_phase_residual_deg"] for row in rows])
    positions = np.arange(1, len(rows) + 1)

    fig, axes = plt.subplots(1, 3, figsize=(14.5, 4.5), constrained_layout=True)
    axes[0].bar(positions, successes, color="#777f89", width=0.78)
    axes[0].axhline(12, color="#00a6a6", linewidth=2.5, label="Intact: 12/12")
    axes[0].set(xlabel="Null network (ordered)", ylabel="Successful arrivals / 12", ylim=(0, 12.8))
    axes[0].legend(frameon=False, loc="upper left")
    axes[0].text(20, 10.7, "rank p = 1/21 = 0.0476", ha="right", fontsize=9)

    axes[1].scatter(positions, cross, color="#777f89", s=40)
    axes[1].axhline(
        report["secondary_cross_track"]["intact_median_maximum_cross_track_m"],
        color="#00a6a6", linewidth=2.5, label="Intact",
    )
    axes[1].set(xlabel="Null network (ordered)", ylabel="Median maximum cross-track (m)")
    axes[1].legend(frameon=False)

    axes[2].scatter(positions, residual, color="#9a62c7", s=40)
    axes[2].set(xlabel="Null network (ordered)", ylabel="Mean PFL3 phase residual (deg)")
    for axis in axes:
        axis.set_xticks([1, 5, 10, 15, 20])
        axis.spines[["top", "right"]].set_visible(False)
        axis.grid(axis="y", alpha=0.18)
    fig.suptitle("Prospective EPG→Delta7-only connectome-null gate", fontsize=14, fontweight="bold")
    for suffix in ("png", "svg"):
        fig.savefig(FIGURES / f"integrated-v4-epg-delta7-null-gate.{suffix}", dpi=220)
    plt.close(fig)


if __name__ == "__main__":
    result = analyze()
    plot(result)
    print(json.dumps(result["primary_gate"], indent=2))
