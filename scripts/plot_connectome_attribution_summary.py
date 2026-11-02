"""Plot the four prospective connectome-attribution gates."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "docs/research/figures"
SOURCES = [
    (
        "PFN→hΔB",
        ROOT / "results/simulation/quadrotor_integrated_v4_connectome_null_prospective/prospective_null_analysis.json",
    ),
    (
        "Steering joint",
        ROOT / "results/simulation/quadrotor_integrated_v4_steering_null_prospective/prospective_steering_null_analysis.json",
    ),
    (
        "Δ7→PFL3",
        ROOT / "results/simulation/quadrotor_integrated_v4_delta_pfl3_null_prospective/prospective_delta_pfl3_null_analysis.json",
    ),
    (
        "EPG→Δ7",
        ROOT / "results/simulation/quadrotor_integrated_v4_epg_delta7_null_prospective/prospective_epg_delta7_null_analysis.json",
    ),
]


def main() -> None:
    reports = [(label, json.loads(path.read_text(encoding="utf-8"))) for label, path in SOURCES]
    labels = [label for label, _ in reports]
    intact = np.asarray([report["primary_gate"]["intact_successes"] for _, report in reports])
    null_medians = np.asarray([report["null_distribution"]["median"] for _, report in reports])
    null_maxima = np.asarray([report["null_distribution"]["maximum"] for _, report in reports])
    intact_cross = np.asarray([
        report["secondary_cross_track"]["intact_median_maximum_cross_track_m"]
        for _, report in reports
    ])
    null_cross = np.asarray([
        report["secondary_cross_track"]["median_of_null_condition_medians_m"]
        for _, report in reports
    ])

    x = np.arange(len(labels))
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.8), constrained_layout=True)
    width = 0.25
    axes[0].bar(x - width, intact, width, label="FlyWire intact", color="#00a6a6")
    axes[0].bar(x, null_medians, width, label="Null median", color="#7d858e")
    axes[0].bar(x + width, null_maxima, width, label="Best null", color="#b2b7bd")
    axes[0].set(ylabel="Successful arrivals / 12", ylim=(0, 13), xticks=x, xticklabels=labels)
    axes[0].legend(frameon=False, ncols=3, loc="upper center")

    axes[1].bar(x - width / 2, intact_cross, width, label="FlyWire intact", color="#00a6a6")
    axes[1].bar(x + width / 2, null_cross, width, label="Null median", color="#7d858e")
    axes[1].set(ylabel="Median maximum cross-track (m)", xticks=x, xticklabels=labels)
    axes[1].legend(frameon=False)

    for axis in axes:
        axis.spines[["top", "right"]].set_visible(False)
        axis.grid(axis="y", alpha=0.18)
        axis.tick_params(axis="x", rotation=12)
    fig.suptitle(
        "Prospective connectome-attribution gates",
        fontsize=15,
        fontweight="bold",
    )
    FIGURES.mkdir(parents=True, exist_ok=True)
    for suffix in ("png", "svg"):
        fig.savefig(FIGURES / f"connectome-attribution-summary.{suffix}", dpi=220)
    plt.close(fig)


if __name__ == "__main__":
    main()
