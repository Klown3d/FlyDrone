"""Create descriptive post-gate artifacts for the frozen integrated v2 run."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results/simulation/quadrotor_integrated_v2_prospective"
FIGURES = ROOT / "docs/research/figures"


def main() -> None:
    frame = pd.read_csv(RESULTS / "episodes.csv")
    report = json.loads((RESULTS / "report.json").read_text(encoding="utf-8"))
    order = [
        "conventional_navigation",
        "direct_velocity_matched",
        "full_flywire_v2",
        "no_pfl2",
        "no_hdelta",
        "delta7_ablated",
    ]
    labels = ["Convencional", "Directo", "FlyWire v2", "Sin PFL2", "Sin hΔB", "Sin Δ7/PFL3"]
    summary = pd.DataFrame(report["summary"]).set_index("controller").loc[order]
    failures = frame[(frame.controller == "full_flywire_v2") & ~frame.success.astype(bool)].copy()
    failures.to_csv(RESULTS / "flywire_failure_audit.csv", index=False)

    fig, axes = plt.subplots(1, 3, figsize=(15, 5), constrained_layout=True)
    colors = ["#64748b", "#0ea5e9", "#22c55e", "#eab308", "#ef4444", "#a855f7"]
    axes[0].bar(labels, summary.success_rate * 100, color=colors)
    axes[0].axhline(90, color="#16a34a", linestyle="--", label="Umbral 90%")
    axes[0].set_ylabel("Llegadas (%)")
    axes[0].set_ylim(0, 105)
    axes[0].tick_params(axis="x", rotation=35)
    axes[0].set_title("A. Resultado funcional")
    axes[0].legend(frameon=False)

    axes[1].bar(labels, summary.median_maximum_cross_track_m, color=colors)
    axes[1].set_ylabel("Desvío transversal máximo mediano (m)")
    axes[1].tick_params(axis="x", rotation=35)
    axes[1].set_title("B. Deriva lateral")

    criteria = report["criteria"]
    names = list(criteria)
    values = [1 if criteria[name] else 0 for name in names]
    axes[2].barh(range(len(names)), values, color=["#22c55e" if value else "#ef4444" for value in values])
    axes[2].set_yticks(range(len(names)), [name.replace("_", " ") for name in names], fontsize=8)
    axes[2].set_xticks([0, 1], ["Falló", "Pasó"])
    axes[2].set_xlim(-0.1, 1.1)
    axes[2].set_title("C. Criterios preregistrados (7/10)")
    fig.suptitle("FlyDrone — gate integrado v2 (180 vuelos simulados)", fontsize=15)
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / "integrated-v2-gate.png", dpi=180)
    fig.savefig(FIGURES / "integrated-v2-gate.svg")
    plt.close(fig)

    diagnostic = {
        "status": "post_gate_descriptive_failure_audit",
        "failures": len(failures),
        "all_failures_had_prior_arrival": bool(failures.arrival_time_s.notna().all()),
        "final_distance_range_m": [
            float(failures.final_distance_m.min()),
            float(failures.final_distance_m.max()),
        ],
        "final_speed_range_m_s": [
            float(failures.final_speed_m_s.min()),
            float(failures.final_speed_m_s.max()),
        ],
        "engineering_diagnosis": (
            "arrival supervisor exit_radius_m=0.45 exceeded the frozen physical success "
            "radius 0.30 m, allowing a latched vehicle to remain stopped outside scoring radius"
        ),
    }
    (RESULTS / "post_gate_failure_diagnosis.json").write_text(
        json.dumps(diagnostic, indent=2), encoding="utf-8"
    )
    print(json.dumps(diagnostic, indent=2))


if __name__ == "__main__":
    main()
