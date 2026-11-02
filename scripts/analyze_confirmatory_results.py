"""Create post-confirmatory tables and figures without changing the frozen v1 gate.

This script is descriptive.  It reads the execute-once outputs and writes only to
the result and documentation figure directories; it never changes preregistered
criteria or recomputes the pass/fail decision.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import binomtest


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results/simulation/quadrotor_connectome_confirmatory_v1"
FIGURES = ROOT / "docs/research/figures"
EPISODES = RESULTS / "episodes.csv"
ANALYSIS = RESULTS / "confirmatory_analysis.json"
TRACE_DIR = RESULTS / "traces"

CASE_KEYS = ["scenario", "target_bearing_deg", "initial_relative_heading_deg"]
INTACT = "flywire_hdelta_intact"
DIRECT = "direct_velocity_matched"
CONVENTIONAL = "conventional_navigation"

LABELS = {
    CONVENTIONAL: "Convencional",
    DIRECT: "Directo pareado",
    INTACT: "FlyWire intacto",
    "null_rewire_block_130021": "Nulo 130021",
    "null_rewire_block_130027": "Nulo 130027",
    "null_rewire_block_130043": "Nulo 130043",
    "null_rewire_block_130051": "Nulo 130051",
    "null_rewire_block_130069": "Nulo 130069",
}

SCENARIO_LABELS = {
    "confirm_crosswind_late": "Viento tardío",
    "confirm_heading_long": "Pérdida heading",
    "confirm_velocity_long": "Pérdida velocidad",
    "confirm_combined_shifted": "Combinado",
}


def load_trace(controller: str, scenario: str, index: int) -> pd.DataFrame:
    path = TRACE_DIR / f"{controller}__{scenario}__{index:02d}.npz"
    archive = np.load(path)
    return pd.DataFrame(archive["values"], columns=archive["columns"].tolist())


def terminal_retention(trace: pd.DataFrame, bearing_deg: float) -> dict[str, float]:
    target = 4.0 * np.array(
        [np.cos(np.deg2rad(bearing_deg)), np.sin(np.deg2rad(bearing_deg))]
    )
    distance = np.linalg.norm(trace[["x_m", "y_m"]].to_numpy() - target, axis=1)
    speed = np.linalg.norm(trace[["vx_m_s", "vy_m_s"]].to_numpy(), axis=1)
    stable = (
        (distance <= 0.3)
        & (speed <= 0.12)
        & (np.abs(trace["z_m"].to_numpy() - 2.0) <= 0.1)
    )
    dt = float(np.median(np.diff(trace["time_s"])))
    last_second = max(1, round(1.0 / dt))
    return {
        "stable_fraction_all": float(stable.mean()),
        "stable_fraction_last_second": float(stable[-last_second:].mean()),
        "maximum_distance_last_second_m": float(distance[-last_second:].max()),
        "maximum_speed_last_second_m_s": float(speed[-last_second:].max()),
    }


def make_tables(frame: pd.DataFrame, frozen: dict) -> pd.DataFrame:
    summary = pd.DataFrame(frozen["summary"])
    summary["controller_label"] = summary["controller"].map(LABELS)
    summary.to_csv(RESULTS / "final_controller_summary.csv", index=False)

    by_scenario = (
        frame.groupby(["controller", "scenario"], as_index=False)
        .agg(episodes=("success", "size"), successes=("success", "sum"))
    )
    by_scenario["success_rate"] = by_scenario["successes"] / by_scenario["episodes"]
    by_scenario["controller_label"] = by_scenario["controller"].map(LABELS)
    by_scenario["scenario_label"] = by_scenario["scenario"].map(SCENARIO_LABELS)
    by_scenario.to_csv(RESULTS / "final_scenario_summary.csv", index=False)

    intact = frame[frame["controller"] == INTACT].copy()
    intact["trace_index"] = intact.groupby("scenario").cumcount()
    direct = frame[frame["controller"] == DIRECT].set_index(CASE_KEYS)
    conventional = frame[frame["controller"] == CONVENTIONAL].set_index(CASE_KEYS)
    failures = intact[~intact["success"].astype(bool)].copy()
    for idx, row in failures.iterrows():
        key = tuple(row[k] for k in CASE_KEYS)
        failures.loc[idx, "direct_success_same_case"] = bool(direct.loc[key, "success"])
        failures.loc[idx, "conventional_success_same_case"] = bool(
            conventional.loc[key, "success"]
        )
        trace = load_trace(INTACT, row["scenario"], int(row["trace_index"]))
        for name, value in terminal_retention(trace, float(row["target_bearing_deg"])).items():
            failures.loc[idx, name] = value
    failure_columns = [
        *CASE_KEYS,
        "trace_index",
        "arrival_time_s",
        "final_distance_m",
        "final_speed_m_s",
        "median_decoded_direction_error_deg",
        "direct_success_same_case",
        "conventional_success_same_case",
        "stable_fraction_all",
        "stable_fraction_last_second",
        "maximum_distance_last_second_m",
        "maximum_speed_last_second_m_s",
    ]
    failures[failure_columns].to_csv(RESULTS / "flywire_failure_audit.csv", index=False)

    paired_intact = intact.set_index(CASE_KEYS)["success"].astype(bool)
    paired_direct = direct["success"].astype(bool)
    flywire_only = int((paired_intact & ~paired_direct).sum())
    direct_only = int((~paired_intact & paired_direct).sum())
    discordant = flywire_only + direct_only
    paired = {
        "comparison": "flywire_hdelta_intact_vs_direct_velocity_matched",
        "both_success": int((paired_intact & paired_direct).sum()),
        "both_failure": int((~paired_intact & ~paired_direct).sum()),
        "flywire_only_success": flywire_only,
        "direct_only_success": direct_only,
        "mcnemar_exact_two_sided_p": float(
            binomtest(min(flywire_only, direct_only), discordant, 0.5).pvalue
            if discordant
            else 1.0
        ),
        "interpretation": (
            "descriptive post-confirmatory comparison; the frozen gate used the "
            "preregistered success-deficit margin, not this p-value"
        ),
    }
    (RESULTS / "paired_direct_comparison.json").write_text(
        json.dumps(paired, indent=2), encoding="utf-8"
    )
    return failures


def overview_figure(frame: pd.DataFrame, frozen: dict) -> None:
    order = [CONVENTIONAL, DIRECT, INTACT] + [
        f"null_rewire_block_{seed}" for seed in (130021, 130027, 130043, 130051, 130069)
    ]
    summary = pd.DataFrame(frozen["summary"]).set_index("controller").loc[order]
    colors = ["#64748b", "#0ea5e9", "#22c55e"] + ["#f97316"] * 5

    fig, axes = plt.subplots(2, 2, figsize=(14, 10), constrained_layout=True)

    ax = axes[0, 0]
    rate = summary["success_rate"].to_numpy()
    intervals = np.asarray(summary["success_rate_wilson_95pct"].tolist())
    yerr = np.clip(
        np.vstack([rate - intervals[:, 0], intervals[:, 1] - rate]), 0.0, None
    )
    ax.bar(range(len(order)), rate * 100, color=colors, edgecolor="#0f172a", linewidth=0.5)
    ax.errorbar(range(len(order)), rate * 100, yerr=yerr * 100, fmt="none", ecolor="#0f172a", capsize=3)
    ax.axhline(90, color="#16a34a", linestyle="--", linewidth=1, label="Umbral intacto (90%)")
    ax.set_ylabel("Llegadas (%)")
    ax.set_ylim(0, 105)
    ax.set_xticks(range(len(order)), [LABELS[x] for x in order], rotation=35, ha="right")
    ax.set_title("A. Resultado primario (IC Wilson 95%)")
    ax.legend(frameon=False, fontsize=8)

    ax = axes[0, 1]
    neural_order = [DIRECT, INTACT] + order[3:]
    data = [
        frame.loc[frame["controller"] == name, "median_decoded_direction_error_deg"].dropna()
        for name in neural_order
    ]
    box = ax.boxplot(data, patch_artist=True, showfliers=False)
    for patch, color in zip(box["boxes"], colors[1:]):
        patch.set_facecolor(color)
    ax.set_ylabel("Error de dirección decodificada (°)")
    ax.set_xticks(range(1, len(neural_order) + 1), [LABELS[x] for x in neural_order], rotation=35, ha="right")
    ax.set_title("B. Precisión interna del readout")

    ax = axes[1, 0]
    selected = [CONVENTIONAL, DIRECT, INTACT]
    scenarios = list(SCENARIO_LABELS)
    matrix = np.array(
        [
            [
                frame.loc[(frame.controller == controller) & (frame.scenario == scenario), "success"].mean()
                for scenario in scenarios
            ]
            for controller in selected
        ]
    )
    image = ax.imshow(matrix * 100, vmin=0, vmax=100, cmap="YlGn")
    for row in range(matrix.shape[0]):
        for column in range(matrix.shape[1]):
            ax.text(column, row, f"{matrix[row, column] * 100:.0f}%", ha="center", va="center", color="#0f172a")
    ax.set_xticks(range(len(scenarios)), [SCENARIO_LABELS[x] for x in scenarios], rotation=25, ha="right")
    ax.set_yticks(range(len(selected)), [LABELS[x] for x in selected])
    ax.set_title("C. Generalización por escenario")
    fig.colorbar(image, ax=ax, label="Llegadas (%)", fraction=0.046, pad=0.04)

    ax = axes[1, 1]
    nulls = summary.loc[order[3:], "success_rate"].to_numpy() * 100
    ax.scatter(range(1, 6), nulls, s=75, color="#f97316", edgecolor="#0f172a", label="Nulos preservando tipo/lado/grado/pesos")
    ax.axhline(summary.loc[INTACT, "success_rate"] * 100, color="#22c55e", linewidth=2, label="FlyWire intacto")
    ax.axhline(np.median(nulls), color="#c2410c", linestyle="--", label=f"Mediana nulos ({np.median(nulls):.0f}%)")
    ax.set_xticks(range(1, 6), ["130021", "130027", "130043", "130051", "130069"])
    ax.set_xlabel("Semilla de reconexión")
    ax.set_ylabel("Llegadas (%)")
    ax.set_ylim(-3, 103)
    ax.set_title("D. Atribución a la organización del connectoma")
    ax.legend(frameon=False, fontsize=8)

    fig.suptitle("FlyDrone — gate confirmatorio PFN→hΔB v1 (800 vuelos simulados)", fontsize=16)
    for suffix in ("png", "svg"):
        fig.savefig(FIGURES / f"confirmatory-gate-overview.{suffix}", dpi=180)
    plt.close(fig)


def failure_figure(failures: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(14, 8.5), constrained_layout=True)
    for ax, (_, row) in zip(axes.flat, failures.iterrows()):
        trace = load_trace(INTACT, row["scenario"], int(row["trace_index"]))
        target = 4.0 * np.array(
            [
                np.cos(np.deg2rad(row["target_bearing_deg"])),
                np.sin(np.deg2rad(row["target_bearing_deg"])),
            ]
        )
        ax.plot(trace["x_m"], trace["y_m"], color="#16a34a", linewidth=1.3)
        ax.scatter([0], [0], color="#0f172a", s=25, label="Inicio")
        ax.scatter([target[0]], [target[1]], color="#ef4444", marker="x", s=45, label="Meta")
        ax.add_patch(plt.Circle(target, 0.3, fill=False, color="#ef4444", linestyle="--"))
        ax.scatter([trace["x_m"].iloc[-1]], [trace["y_m"].iloc[-1]], color="#8b5cf6", s=30, label="Final")
        ax.set_aspect("equal", adjustable="box")
        ax.grid(alpha=0.2)
        ax.set_title(
            f"{SCENARIO_LABELS[row['scenario']]}\n"
            f"meta {row['target_bearing_deg']:.0f}°, heading {row['initial_relative_heading_deg']:.0f}°"
        )
        ax.set_xlabel("x (m)")
        ax.set_ylabel("y (m)")
    axes.flat[-1].axis("off")
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower right", bbox_to_anchor=(0.95, 0.08), frameon=False)
    fig.suptitle("Cinco fallos FlyWire: llegada transitoria seguida de salida del radio", fontsize=15)
    for suffix in ("png", "svg"):
        fig.savefig(FIGURES / f"confirmatory-flywire-failures.{suffix}", dpi=180)
    plt.close(fig)


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(EPISODES)
    frozen = json.loads(ANALYSIS.read_text(encoding="utf-8"))
    if len(frame) != 800 or not frozen.get("overall_gate_passed"):
        raise RuntimeError("Unexpected or incomplete confirmatory result set")
    failures = make_tables(frame, frozen)
    overview_figure(frame, frozen)
    failure_figure(failures)
    print(f"Wrote final confirmatory artifacts; audited {len(failures)} FlyWire failures.")


if __name__ == "__main__":
    main()
