"""Plot prospective PFL2 effects and post-prospective attribution controls."""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def run(root: Path) -> Path:
    prospective = pd.read_csv(root / "results/simulation/quadrotor_pfl2_steering_prospective/episodes.csv")
    nulls = pd.read_csv(root / "results/neural/pfl2_connectivity_nulls/scores.csv")
    analytic = pd.read_csv(root / "results/simulation/quadrotor_pfl2_analytic_control/combined_episodes.csv")
    pivot = prospective.pivot(index="case_id", columns="controller", values="arrival_time_s")
    differences = pivot["pfl3_only"] - pivot["pfl3_plus_pfl2"]
    scenario = prospective.pivot(index="case_id", columns="controller", values=["arrival_time_s", "scenario"])
    labels = prospective.drop_duplicates("case_id").set_index("case_id")["scenario"]
    scenario_values = differences.groupby(labels).median().sort_values()
    controller_summary = analytic.groupby("controller")["arrival_time_s"].median().reindex(
        ["pfl3_only", "analytic_error_gain", "pfl3_plus_pfl2"]
    )

    plt.style.use("seaborn-v0_8-whitegrid")
    figure, axes = plt.subplots(1, 3, figsize=(13.5, 4.2), constrained_layout=True)
    axes[0].axvline(0, color="#334155", linewidth=1)
    axes[0].scatter(differences, np.arange(len(differences)), s=24, color="#0891b2", alpha=.85)
    axes[0].axvline(float(differences.median()), color="#dc2626", linewidth=2,
                    label=f"mediana {differences.median():.3f} s")
    axes[0].set(title="Efecto pareado prospectivo", xlabel="PFL2 más rápido (s)", ylabel="36 vuelos")
    axes[0].set_yticks([])
    axes[0].legend(frameon=False, loc="lower right")

    colors = ["#7c3aed", "#2563eb", "#0891b2"]
    axes[1].barh([name.replace("_", " ") for name in scenario_values.index], scenario_values, color=colors)
    axes[1].axvline(0, color="#334155", linewidth=1)
    axes[1].set(title="Consistencia por escenario", xlabel="mejora mediana de llegada (s)")

    shuffled = nulls.loc[nulls["condition"].eq("phase_permuted"), "correlation"]
    flywire = float(nulls.loc[nulls["condition"].eq("flywire"), "correlation"].iloc[0])
    axes[2].hist(shuffled, bins=10, color="#94a3b8", edgecolor="white", label="30 fases permutadas")
    axes[2].axvline(flywire, color="#dc2626", linewidth=2, label=f"FlyWire {flywire:.3f}")
    axes[2].set(title="Estructura de fase PFL2", xlabel="correlación con magnitud angular", ylabel="controles")
    axes[2].legend(frameon=False)

    figure.suptitle(
        "PFL2 mejora de forma consistente, pero el control angular iguala su navegación\n"
        f"medianas: PFL3 {controller_summary.iloc[0]:.3f} s · fórmula {controller_summary.iloc[1]:.3f} s · FlyWire {controller_summary.iloc[2]:.3f} s",
        fontsize=12,
    )
    output = root / "results/neural/pfl2-validation-summary.png"
    figure.savefig(output, dpi=180)
    plt.close(figure)
    return output


if __name__ == "__main__":
    print(run(Path.cwd()))
