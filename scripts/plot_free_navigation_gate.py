"""Plot the preserved free-navigation gate without changing its analysis."""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "results/simulation/free_navigation_gate_v1/episodes.csv"
OUTPUT = ROOT / "docs/research/figures/free-navigation-gate-v1.png"


def main() -> None:
    frame = pd.read_csv(DATA)
    hybrid = frame[frame.controller == "flywire_hybrid"]
    conventional = frame[frame.controller == "conventional_navigation"]
    order = [(mode, scenario) for mode in ("patrol", "explore") for scenario in
             ("free_gate_nominal", "free_gate_positive", "free_gate_negative")]
    labels = [f"{'Patrulla' if mode == 'patrol' else 'Explora'}\n{scenario.removeprefix('free_gate_')}"
              for mode, scenario in order]
    h_targets = [hybrid[(hybrid.behavior_mode == mode) & (hybrid.scenario == scenario)].targets_completed.sum()
                 for mode, scenario in order]
    c_targets = [conventional[(conventional.behavior_mode == mode) & (conventional.scenario == scenario)].targets_completed.sum()
                 for mode, scenario in order]
    h_groups = [hybrid[(hybrid.behavior_mode == mode) & (hybrid.scenario == scenario)]
                for mode, scenario in order]
    capture = [group.engineering_goal_capture_active_fraction.max() * 100 for group in h_groups]
    fence = [group.engineering_geofence_active_fraction.max() * 100 for group in h_groups]
    inertial = [group.engineering_heading_dominant_fraction.max() * 100 for group in h_groups]

    plt.style.use("dark_background")
    fig, axes = plt.subplots(2, 1, figsize=(11.5, 8.2), constrained_layout=True)
    fig.patch.set_facecolor("#0d121b")
    x = np.arange(len(order)); width = .36
    axes[0].bar(x - width / 2, h_targets, width, label="FlyWire híbrido", color="#2ee6a6")
    axes[0].bar(x + width / 2, c_targets, width, label="Convencional", color="#ff7a3d")
    axes[0].set_ylabel("Metas completadas (2 vuelos)")
    axes[0].set_xticks(x, labels)
    axes[0].legend(frameon=False, ncol=2)
    axes[0].set_title("Gate prospectivo de navegación libre v1 — 106 vs 109 metas")
    axes[0].grid(axis="y", alpha=.18)
    axes[1].bar(x - width, capture, width, label="Captura de meta", color="#ffd35a")
    axes[1].bar(x, fence, width, label="Geofence", color="#5ab8ff")
    axes[1].bar(x + width, inertial, width, label="Heading inercial dominante", color="#b886ff")
    axes[1].axhline(20, color="#ffd35a", linestyle="--", alpha=.55, label="límite captura 20%")
    axes[1].axhline(25, color="#5ab8ff", linestyle=":", alpha=.55, label="límite geofence 25%")
    axes[1].set_ylabel("Máximo por condición (% del vuelo)")
    axes[1].set_xticks(x, labels)
    axes[1].set_ylim(0, 28)
    axes[1].legend(frameon=False, ncol=3, fontsize=9)
    axes[1].grid(axis="y", alpha=.18)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT, dpi=170, facecolor=fig.get_facecolor())
    plt.close(fig)


if __name__ == "__main__":
    main()

