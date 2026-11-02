"""Localize the preserved OOD failure with paired diagnostic oracle traces."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from flydrone.data.acquire import file_hash, save_json, utc_now


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results/simulation/quadrotor_integrated_v4_ood_failure_oracles"
PILOT = ROOT / "results/simulation/quadrotor_integrated_v4_ood_pilot/episodes.csv"
EPOCHS = (
    ("before_loss", 0.0, 9.0),
    ("heading_only_loss", 9.0, 11.0),
    ("overlapping_loss", 11.0, 18.0),
    ("velocity_only_loss", 18.0, 20.0),
    ("early_recovery", 20.0, 26.0),
    ("late_flight", 26.0, 45.0),
)


def wrap(values: np.ndarray) -> np.ndarray:
    return np.angle(np.exp(1j * values))


def load_trace(path: Path) -> pd.DataFrame:
    with np.load(path, allow_pickle=False) as archive:
        return pd.DataFrame(archive["values"], columns=archive["columns"].astype(str))


def median(values: np.ndarray) -> float | None:
    finite = np.asarray(values, dtype=float)
    finite = finite[np.isfinite(finite)]
    return None if not finite.size else float(np.median(finite))


def epoch_metrics(controller: str, frame: pd.DataFrame) -> list[dict[str, object]]:
    goal = float(frame.goal_rad.iloc[0])
    target = 6.0 * np.array([np.cos(goal), np.sin(goal)])
    position = frame[["x_m", "y_m"]].to_numpy()
    distance = np.linalg.norm(position - target, axis=1)
    true_speed = np.hypot(frame.vx_m_s, frame.vy_m_s).to_numpy()
    estimated_speed = np.hypot(frame.estimated_vx_m_s, frame.estimated_vy_m_s).to_numpy()
    moving = true_speed > 0.05
    true_direction = np.arctan2(frame.vy_m_s, frame.vx_m_s).to_numpy()
    estimated_direction = np.arctan2(frame.estimated_vy_m_s, frame.estimated_vx_m_s).to_numpy()
    heading_error = np.rad2deg(np.abs(wrap(
        frame.observed_yaw_rad.to_numpy() - frame.yaw_rad.to_numpy()
    )))
    velocity_error = np.rad2deg(np.abs(wrap(estimated_direction - true_direction)))
    relative_speed_error = np.abs(estimated_speed - true_speed) / np.maximum(true_speed, 0.05)
    drift_correction = np.hypot(
        frame.drift_correction_x_m_s2, frame.drift_correction_y_m_s2
    ).to_numpy()
    rows: list[dict[str, object]] = []
    for epoch, start, end in EPOCHS:
        selected = (frame.time_s.to_numpy() >= start) & (frame.time_s.to_numpy() < end)
        moving_selected = selected & moving
        rows.append({
            "controller": controller,
            "epoch": epoch,
            "start_s": start,
            "end_s": end,
            "median_heading_error_deg": median(heading_error[selected]),
            "median_velocity_direction_error_deg": median(velocity_error[moving_selected]),
            "median_relative_speed_error": median(relative_speed_error[moving_selected]),
            "median_distance_to_goal_m": median(distance[selected]),
            "minimum_distance_to_goal_m": float(np.min(distance[selected])),
            "median_absolute_yaw_command_rad_s": median(
                np.abs(frame.yaw_command_rad_s.to_numpy()[selected])
            ),
            "median_drift_correction_m_s2": median(drift_correction[selected]),
            "arrival_latched_fraction": float(frame.arrival_latched.to_numpy()[selected].mean()),
        })
    return rows


def main() -> None:
    episodes = pd.read_csv(RESULTS / "episodes.csv")
    traces: dict[str, pd.DataFrame] = {}
    epoch_rows: list[dict[str, object]] = []
    for path in sorted((RESULTS / "traces").glob("*.npz")):
        controller = path.stem.split("__", 1)[0]
        traces[controller] = load_trace(path)
        epoch_rows.extend(epoch_metrics(controller, traces[controller]))
    epochs = pd.DataFrame(epoch_rows)
    epochs.to_csv(RESULTS / "epoch_metrics.csv", index=False)

    pilot = pd.read_csv(PILOT)
    original = pilot[
        (pilot.controller == "full_flywire_v4")
        & (pilot.scenario == "ood_long_dropout")
        & np.isclose(pilot.target_bearing_deg, 107.0)
    ].iloc[0]
    replicated = episodes[episodes.controller == "observed_failure_replication"].iloc[0]
    reproduction = {
        "original_success": bool(original.success),
        "replicated_success": bool(replicated.success),
        "original_final_distance_m": float(original.final_distance_m),
        "replicated_final_distance_m": float(replicated.final_distance_m),
        "absolute_final_distance_difference_m": float(abs(
            original.final_distance_m - replicated.final_distance_m
        )),
        "original_maximum_cross_track_m": float(original.maximum_absolute_cross_track_m),
        "replicated_maximum_cross_track_m": float(replicated.maximum_absolute_cross_track_m),
    }
    outcomes = {
        row.controller: {
            "success": bool(row.success),
            "final_distance_m": float(row.final_distance_m),
            "maximum_cross_track_m": float(row.maximum_absolute_cross_track_m),
            "arrival_time_s": None if pd.isna(row.arrival_time_s) else float(row.arrival_time_s),
            "dropout_heading_error_deg": float(row.median_dropout_heading_error_deg),
        }
        for row in episodes.itertuples()
    }
    report = {
        "created_at": utc_now(),
        "status": "diagnostic_oracle_causal_localization_not_controller_validation",
        "dataset": "FAFB",
        "materialization_version": 783,
        "question": "Which observed input is sufficient to rescue the preserved long-dropout failure?",
        "reproduction": reproduction,
        "outcomes": outcomes,
        "interpretation": {
            "heading_oracle_sufficient_in_this_case": bool(outcomes["diagnostic_true_heading"]["success"]),
            "velocity_oracle_sufficient_in_this_case": bool(outcomes["diagnostic_true_velocity"]["success"]),
            "combined_oracle_sufficient_in_this_case": bool(outcomes["diagnostic_true_heading_velocity"]["success"]),
            "conclusion": (
                "For this single preserved geometry, replacing heading with simulator truth rescues the flight, "
                "whereas replacing velocity alone does not. This localizes the dominant failure to the heading "
                "path or its downstream use; it does not establish a population-level causal effect."
            ),
        },
        "inputs_sha256": {
            "episodes": file_hash(RESULTS / "episodes.csv"),
            "pilot_episodes": file_hash(PILOT),
            "config": file_hash(ROOT / "configs/quadrotor_integrated_v4_ood_failure_oracles.yaml"),
            "traces": {
                path.name: file_hash(path) for path in sorted((RESULTS / "traces").glob("*.npz"))
            },
        },
    }
    save_json(RESULTS / "diagnosis.json", report)

    order = [
        "observed_failure_replication",
        "diagnostic_true_heading",
        "diagnostic_true_velocity",
        "diagnostic_true_heading_velocity",
    ]
    labels = ["Observed", "True heading", "True velocity", "Both true"]
    colors = ["#d95f5f", "#4daf78", "#d99b39", "#377eb8"]
    figure, axes = plt.subplots(1, 2, figsize=(10.0, 4.2), constrained_layout=True)
    for name, label, color in zip(order, labels, colors, strict=True):
        frame = traces[name]
        goal = float(frame.goal_rad.iloc[0])
        target = 6.0 * np.array([np.cos(goal), np.sin(goal)])
        axes[0].plot(frame.x_m, frame.y_m, label=label, color=color, linewidth=1.7)
        heading_error = np.rad2deg(np.abs(wrap(
            frame.observed_yaw_rad.to_numpy() - frame.yaw_rad.to_numpy()
        )))
        axes[1].plot(frame.time_s, heading_error, label=label, color=color, linewidth=1.4)
    axes[0].scatter([0.0], [0.0], color="black", marker="o", s=25, label="Start")
    axes[0].scatter([target[0]], [target[1]], color="black", marker="*", s=90, label="Goal")
    axes[0].set(title="Paired trajectories", xlabel="x (m)", ylabel="y (m)", aspect="equal")
    axes[1].axvspan(9.0, 18.0, color="#888888", alpha=0.15, label="Heading loss")
    axes[1].axvspan(11.0, 20.0, color="#d8a03b", alpha=0.12, label="Velocity loss")
    axes[1].set(title="Heading estimate error", xlabel="Time (s)", ylabel="Absolute error (deg)", ylim=(0, 180))
    axes[0].legend(fontsize=8, loc="best")
    axes[1].legend(fontsize=8, loc="best")
    figure.suptitle("OOD long-dropout failure: diagnostic oracles (single preserved case)")
    figure.savefig(RESULTS / "oracle_diagnosis.png", dpi=180)
    plt.close(figure)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
