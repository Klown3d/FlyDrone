"""Native replay viewer for saved FlyDrone confirmatory traces."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Button, Slider
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results/simulation/quadrotor_connectome_confirmatory_v1"
TRACES = RESULTS / "traces"
EPISODES = RESULTS / "episodes.csv"
KEYS = ["scenario", "target_bearing_deg", "initial_relative_heading_deg"]
DT = 0.02


def angle_error_deg(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return np.abs(np.rad2deg(np.angle(np.exp(1j * (a - b)))))


def trace_path(controller: str, scenario: str, index: int) -> Path:
    return TRACES / f"{controller}__{scenario}__{index:02d}.npz"


def load_trace(controller: str, scenario: str, index: int) -> pd.DataFrame:
    archive = np.load(trace_path(controller, scenario, index))
    return pd.DataFrame(archive["values"], columns=archive["columns"].tolist())


class Replay:
    def __init__(self, controller_a: str, controller_b: str, animate: bool = True) -> None:
        self.episodes = pd.read_csv(EPISODES)
        self.controller_a = controller_a
        self.controller_b = controller_b
        self.cases = (
            self.episodes[self.episodes["controller"] == controller_a][KEYS]
            .reset_index(drop=True)
            .copy()
        )
        if len(self.cases) != 100:
            raise ValueError(f"Expected 100 cases for {controller_a}; found {len(self.cases)}")
        self.case_index = 0
        self.frame_index = 0
        self.playing = False
        self.animate = animate
        self._load_case()
        self._build_figure()
        self._draw_case()

    def _load_case(self) -> None:
        case = self.cases.iloc[self.case_index]
        scenario = str(case["scenario"])
        within_scenario = self.case_index % 25
        self.a = load_trace(self.controller_a, scenario, within_scenario)
        self.b = load_trace(self.controller_b, scenario, within_scenario)
        self.row_a = self.episodes[
            (self.episodes["controller"] == self.controller_a)
            & (self.episodes["scenario"] == scenario)
            & (self.episodes["target_bearing_deg"] == case["target_bearing_deg"])
            & (
                self.episodes["initial_relative_heading_deg"]
                == case["initial_relative_heading_deg"]
            )
        ].iloc[0]
        self.row_b = self.episodes[
            (self.episodes["controller"] == self.controller_b)
            & (self.episodes["scenario"] == scenario)
            & (self.episodes["target_bearing_deg"] == case["target_bearing_deg"])
            & (
                self.episodes["initial_relative_heading_deg"]
                == case["initial_relative_heading_deg"]
            )
        ].iloc[0]
        self.frame_index = 0

    def _build_figure(self) -> None:
        self.figure = plt.figure(figsize=(15, 9))
        grid = self.figure.add_gridspec(2, 3, bottom=0.15, hspace=0.34, wspace=0.28)
        self.path_ax = self.figure.add_subplot(grid[:, 0])
        self.error_ax = self.figure.add_subplot(grid[0, 1:])
        self.pfn_ax = self.figure.add_subplot(grid[1, 1])
        self.hdelta_ax = self.figure.add_subplot(grid[1, 2])
        slider_ax = self.figure.add_axes([0.20, 0.065, 0.55, 0.03])
        button_ax = self.figure.add_axes([0.78, 0.052, 0.09, 0.055])
        previous_ax = self.figure.add_axes([0.04, 0.052, 0.06, 0.055])
        next_ax = self.figure.add_axes([0.11, 0.052, 0.06, 0.055])
        self.time_slider = Slider(slider_ax, "Tiempo (s)", 0.0, 35.0, valinit=0.0)
        self.time_slider.on_changed(self._slider_changed)
        self.play_button = Button(button_ax, "Reproducir")
        self.play_button.on_clicked(self._toggle_play)
        self.previous_button = Button(previous_ax, "Caso −")
        self.previous_button.on_clicked(self._previous_case)
        self.next_button = Button(next_ax, "Caso +")
        self.next_button.on_clicked(self._next_case)
        self.animation = (
            FuncAnimation(self.figure, self._tick, interval=40, cache_frame_data=False)
            if self.animate
            else None
        )

    def _draw_case(self) -> None:
        case = self.cases.iloc[self.case_index]
        bearing = float(case["target_bearing_deg"])
        target = 4.0 * np.array(
            [np.cos(np.deg2rad(bearing)), np.sin(np.deg2rad(bearing))]
        )
        self.path_ax.clear()
        self.path_ax.plot(self.a["x_m"], self.a["y_m"], color="#22c55e", alpha=0.35)
        self.path_ax.plot(self.b["x_m"], self.b["y_m"], color="#0ea5e9", alpha=0.35)
        self.path_a, = self.path_ax.plot([], [], color="#16a34a", linewidth=2, label=self.controller_a)
        self.path_b, = self.path_ax.plot([], [], color="#0284c7", linewidth=2, label=self.controller_b)
        self.marker_a, = self.path_ax.plot([], [], "o", color="#16a34a")
        self.marker_b, = self.path_ax.plot([], [], "o", color="#0284c7")
        self.path_ax.scatter(*target, marker="x", s=70, color="#ef4444", label="Meta")
        self.path_ax.add_patch(plt.Circle(target, 0.3, fill=False, color="#ef4444", linestyle="--"))
        self.path_ax.set_aspect("equal", adjustable="datalim")
        self.path_ax.grid(alpha=0.2)
        self.path_ax.set_xlabel("x (m)")
        self.path_ax.set_ylabel("y (m)")
        self.path_ax.legend(frameon=False, fontsize=8)

        self.error_ax.clear()
        error_a = angle_error_deg(
            self.a["decoded_travel_direction_rad"].to_numpy(),
            self.a["true_travel_direction_rad"].to_numpy(),
        )
        error_b = angle_error_deg(
            self.b["decoded_travel_direction_rad"].to_numpy(),
            self.b["true_travel_direction_rad"].to_numpy(),
        )
        moving_a = np.hypot(self.a["vx_m_s"], self.a["vy_m_s"]) >= 0.05
        moving_b = np.hypot(self.b["vx_m_s"], self.b["vy_m_s"]) >= 0.05
        error_a = np.where(moving_a, error_a, np.nan)
        error_b = np.where(moving_b, error_b, np.nan)
        self.error_ax.plot(self.a["time_s"], error_a, color="#16a34a", label=self.controller_a)
        self.error_ax.plot(self.b["time_s"], error_b, color="#0284c7", label=self.controller_b)
        self.time_line = self.error_ax.axvline(0.0, color="#7c3aed", linewidth=1.5)
        self.error_ax.set_ylabel("Error de dirección (°, velocidad ≥0,05 m/s)")
        self.error_ax.set_xlabel("Tiempo (s)")
        self.error_ax.set_ylim(0, 180)
        self.error_ax.grid(alpha=0.2)
        self.error_ax.legend(frameon=False, fontsize=8)

        self.pfn_ax.clear()
        self.hdelta_ax.clear()
        self.pfn_bars = self.pfn_ax.bar(range(61), np.zeros(61), color="#38bdf8")
        self.hdelta_bars = self.hdelta_ax.bar(range(18), np.zeros(18), color="#a855f7")
        self.pfn_ax.set_title("Actividad PFN — FlyWire")
        self.pfn_ax.set_xlabel("Neurona")
        self.pfn_ax.set_ylabel("Tasa normalizada")
        self.hdelta_ax.set_title("Actividad hΔB — FlyWire")
        self.hdelta_ax.set_xlabel("Neurona")
        self.hdelta_ax.set_ylabel("Tasa normalizada")
        self.pfn_ax.set_ylim(0, max(1.0, float(self.a.filter(like="pfn_activity_").max().max()) * 1.05))
        self.hdelta_ax.set_ylim(0, max(1.0, float(self.a.filter(like="hdelta_activity_").max().max()) * 1.05))

        scenario = str(case["scenario"]).replace("confirm_", "").replace("_", " ")
        success_a = "ÉXITO" if bool(self.row_a["success"]) else "FALLO"
        success_b = "ÉXITO" if bool(self.row_b["success"]) else "FALLO"
        self.figure.suptitle(
            f"FlyDrone — replay confirmatorio | caso {self.case_index + 1}/100 | {scenario}\n"
            f"meta {bearing:.0f}°, heading inicial {case['initial_relative_heading_deg']:.0f}° | "
            f"FlyWire: {success_a} · comparación: {success_b}",
            fontsize=14,
        )
        self._draw_frame()

    def _draw_frame(self) -> None:
        index = min(self.frame_index, len(self.a) - 1, len(self.b) - 1)
        self.path_a.set_data(self.a["x_m"].iloc[: index + 1], self.a["y_m"].iloc[: index + 1])
        self.path_b.set_data(self.b["x_m"].iloc[: index + 1], self.b["y_m"].iloc[: index + 1])
        self.marker_a.set_data([self.a["x_m"].iloc[index]], [self.a["y_m"].iloc[index]])
        self.marker_b.set_data([self.b["x_m"].iloc[index]], [self.b["y_m"].iloc[index]])
        now = float(self.a["time_s"].iloc[index])
        self.time_line.set_xdata([now, now])
        pfn = self.a.filter(like="pfn_activity_").iloc[index].to_numpy()
        hdelta = self.a.filter(like="hdelta_activity_").iloc[index].to_numpy()
        for bar, value in zip(self.pfn_bars, pfn):
            bar.set_height(value)
        for bar, value in zip(self.hdelta_bars, hdelta):
            bar.set_height(value)
        self.figure.canvas.draw_idle()

    def _slider_changed(self, value: float) -> None:
        self.frame_index = min(round(float(value) / DT), len(self.a) - 1)
        self._draw_frame()

    def _toggle_play(self, _event: object) -> None:
        self.playing = not self.playing
        self.play_button.label.set_text("Pausar" if self.playing else "Reproducir")

    def _previous_case(self, _event: object) -> None:
        self.case_index = (self.case_index - 1) % len(self.cases)
        self._load_case()
        self.time_slider.set_val(0.0)
        self._draw_case()

    def _next_case(self, _event: object) -> None:
        self.case_index = (self.case_index + 1) % len(self.cases)
        self._load_case()
        self.time_slider.set_val(0.0)
        self._draw_case()

    def _tick(self, _frame: int) -> None:
        if not self.playing:
            return
        next_time = float(self.time_slider.val) + 0.08
        if next_time >= 35.0:
            self.playing = False
            self.play_button.label.set_text("Reproducir")
            next_time = 35.0
        self.time_slider.set_val(next_time)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--controller-a", default="flywire_hdelta_intact")
    parser.add_argument("--controller-b", default="direct_velocity_matched")
    parser.add_argument("--smoke-test", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    replay = Replay(args.controller_a, args.controller_b, animate=not args.smoke_test)
    if args.smoke_test:
        output = ROOT / "docs/research/figures/confirmatory-replay-smoke.png"
        replay.figure.savefig(output, dpi=130)
        print(output)
        plt.close(replay.figure)
    else:
        plt.show()


if __name__ == "__main__":
    main()
