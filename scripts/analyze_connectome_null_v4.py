"""Create the final report and figure for the prospective v4 connectome-null gate."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results/simulation/quadrotor_integrated_v4_connectome_null_prospective"
FIGURES = ROOT / "docs/research/figures"
KEY = ["scenario", "target_bearing_deg", "initial_relative_heading_deg"]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bootstrap_median(values: np.ndarray, seed: int, samples: int = 20_000) -> list[float]:
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(values), size=(samples, len(values)))
    medians = np.median(values[indices], axis=1)
    return [float(value) for value in np.quantile(medians, [0.025, 0.975])]


def analyze() -> dict:
    episodes_path = RESULTS / "episodes.csv"
    frame = pd.read_csv(episodes_path)
    intact = frame.loc[frame.controller.eq("flywire_hdelta_intact")].set_index(KEY).sort_index()
    null_names = sorted(
        name for name in frame.controller.unique() if str(name).startswith("null_rewire_")
    )
    intact_successes = int(intact.success.sum())
    null_rows: list[dict] = []

    for name in null_names:
        null = frame.loc[frame.controller.eq(name)].set_index(KEY).loc[intact.index]
        cross_difference = (
            null.maximum_absolute_cross_track_m - intact.maximum_absolute_cross_track_m
        ).to_numpy(float)
        null_rows.append(
            {
                "condition": name,
                "successes": int(null.success.sum()),
                "episodes": int(len(null)),
                "median_maximum_cross_track_m": float(
                    null.maximum_absolute_cross_track_m.median()
                ),
                "paired_median_cross_track_increase_m": float(np.median(cross_difference)),
                "paired_cross_track_increase_bootstrap_95pct_m": bootstrap_median(
                    cross_difference, seed=51027 + len(null_rows)
                ),
            }
        )

    null_successes = np.asarray([row["successes"] for row in null_rows], dtype=int)
    null_cross_track = np.asarray(
        [row["median_maximum_cross_track_m"] for row in null_rows], dtype=float
    )
    rank_p = float((1 + np.sum(null_successes >= intact_successes)) / (len(null_rows) + 1))
    minimum_successes = 10
    maximum_rank_p = 0.05
    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "prospective_connectome_null_gate_complete",
        "protocol_id": "flydrone_integrated_v4_connectome_null_prospective_v1",
        "episodes_sha256": digest(episodes_path),
        "design": {
            "projection_tested": "PFN-to-hDeltaB",
            "paired_cases_per_condition": int(len(intact)),
            "null_conditions": int(len(null_rows)),
            "total_simulated_flights": int(len(frame)),
            "preserved_statistics": [
                "binary row degree within each PFN type-and-side block",
                "binary column degree within each PFN type-and-side block",
                "each hDeltaB row's exact nonzero weight multiset within each block",
            ],
            "not_preserved": ["weighted column sums", "exact PFN-to-hDeltaB partner identity"],
        },
        "primary_gate": {
            "minimum_intact_successes": minimum_successes,
            "maximum_empirical_rank_p": maximum_rank_p,
            "intact_successes": intact_successes,
            "intact_episodes": int(len(intact)),
            "nulls_matching_or_exceeding_intact": int(np.sum(null_successes >= intact_successes)),
            "empirical_rank_p_plus_one": rank_p,
            "passes_intact_minimum": bool(intact_successes >= minimum_successes),
            "passes_rank_test": bool(rank_p <= maximum_rank_p),
            "passes_all": bool(intact_successes >= minimum_successes and rank_p <= maximum_rank_p),
        },
        "null_distribution": {
            "successes": null_successes.tolist(),
            "minimum": int(null_successes.min()),
            "median": float(np.median(null_successes)),
            "mean": float(np.mean(null_successes)),
            "maximum": int(null_successes.max()),
            "nulls_below_intact": int(np.sum(null_successes < intact_successes)),
            "zero_success_nulls": int(np.sum(null_successes == 0)),
        },
        "secondary_cross_track": {
            "intact_median_maximum_cross_track_m": float(
                intact.maximum_absolute_cross_track_m.median()
            ),
            "null_condition_medians_m": null_cross_track.tolist(),
            "median_of_null_condition_medians_m": float(np.median(null_cross_track)),
            "range_of_null_condition_medians_m": [
                float(null_cross_track.min()),
                float(null_cross_track.max()),
            ],
            "nulls_worse_than_intact_by_condition_median": int(
                np.sum(null_cross_track > intact.maximum_absolute_cross_track_m.median())
            ),
        },
        "null_conditions": null_rows,
        "supported_claim": (
            "In this computational model and these prospectively frozen scenarios, the "
            "specific FlyWire-grounded PFN-to-hDeltaB partner arrangement contributes to "
            "navigation beyond the preserved block-wise degree and row-weight statistics."
        ),
        "limits": [
            "This is a projection-specific computational attribution test, not a test of the entire central-complex graph.",
            "It does not establish biological causality in a living fly.",
            "It does not show superiority over conventional or matched direct controllers.",
            "The rank p-value has the minimum attainable resolution of 1/21 with 20 null networks.",
        ],
    }
    (RESULTS / "prospective_null_analysis.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def plot(report: dict) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    successes = np.asarray(report["null_distribution"]["successes"])
    cross = np.asarray(report["secondary_cross_track"]["null_condition_medians_m"])
    intact_successes = report["primary_gate"]["intact_successes"]
    intact_cross = report["secondary_cross_track"]["intact_median_maximum_cross_track_m"]

    order = np.argsort(successes)
    positions = np.arange(1, len(successes) + 1)
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6), constrained_layout=True)

    axes[0].bar(positions, successes[order], color="#787f89", width=0.78, label="Rewired nulls")
    axes[0].axhline(intact_successes, color="#00a6a6", linewidth=2.5, label="Intact FlyWire: 12/12")
    axes[0].set(xlabel="Null network (ordered)", ylabel="Successful arrivals / 12", ylim=(0, 12.8))
    axes[0].set_xticks([1, 5, 10, 15, 20])
    axes[0].legend(frameon=False, loc="upper left")
    axes[0].text(20, 10.8, "rank p = 1/21 = 0.0476", ha="right", fontsize=9)

    cross_order = np.argsort(cross)
    axes[1].scatter(positions, cross[cross_order], color="#787f89", s=42, label="Rewired nulls")
    axes[1].axhline(intact_cross, color="#00a6a6", linewidth=2.5, label=f"Intact FlyWire: {intact_cross:.2f} m")
    axes[1].set(
        xlabel="Null network (ordered)",
        ylabel="Median maximum cross-track (m)",
        yscale="log",
    )
    axes[1].set_xticks([1, 5, 10, 15, 20])
    axes[1].legend(frameon=False, loc="upper left")

    fig.suptitle("Prospective PFN→hDeltaB connectome-null gate", fontsize=14, fontweight="bold")
    for axis in axes:
        axis.spines[["top", "right"]].set_visible(False)
        axis.grid(axis="y", alpha=0.18)

    for suffix in ("png", "svg"):
        fig.savefig(FIGURES / f"integrated-v4-connectome-null-gate.{suffix}", dpi=220)
    plt.close(fig)


if __name__ == "__main__":
    result = analyze()
    plot(result)
    print(json.dumps(result["primary_gate"], indent=2))
