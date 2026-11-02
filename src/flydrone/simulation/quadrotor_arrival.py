"""Observed-state arrival supervisor for the 6-DoF quadrotor benchmarks.

This is an engineering safety/interface component, not a reconstructed neural
mechanism.  It prevents a drift readout from continuing to accelerate a vehicle
that has already stopped at its goal, and it releases after a real displacement.
"""

from __future__ import annotations

import numpy as np


class QuadrotorArrivalSupervisor:
    """Confirm and release arrival using only noisy observed positions."""

    def __init__(self, config: dict, target_xy_m: np.ndarray):
        self.config = dict(config)
        self.target = np.asarray(target_xy_m, dtype=float)
        if self.target.shape != (2,):
            raise ValueError("target_xy_m must contain two coordinates")
        for key in (
            "position_filter_tau_s",
            "velocity_filter_tau_s",
            "entry_radius_m",
            "exit_radius_m",
            "stop_speed_m_s",
            "confirm_s",
            "departure_confirm_s",
        ):
            if float(self.config[key]) < 0:
                raise ValueError(f"{key} must be non-negative")
        if float(self.config["exit_radius_m"]) <= float(self.config["entry_radius_m"]):
            raise ValueError("exit_radius_m must exceed entry_radius_m")
        for key in (
            "hold_position_kp_per_s2",
            "hold_velocity_kd_per_s",
            "maximum_hold_acceleration_m_s2",
        ):
            if float(self.config.get(key, 0.0)) < 0:
                raise ValueError(f"{key} must be non-negative")
        self.reset()

    def reset(self) -> None:
        self.filtered_position: np.ndarray | None = None
        self.filtered_velocity = np.zeros(2, dtype=float)
        self.arrived = False
        self.arrival_candidate_s = 0.0
        self.departure_candidate_s = 0.0

    @staticmethod
    def _alpha(dt_s: float, tau_s: float) -> float:
        return 1.0 if tau_s <= 0 else float(1.0 - np.exp(-dt_s / tau_s))

    def update(self, observed_position_xy_m: np.ndarray, dt_s: float) -> dict:
        position = np.asarray(observed_position_xy_m, dtype=float)
        dt = float(dt_s)
        if position.shape != (2,) or not np.isfinite(position).all():
            raise ValueError("observed_position_xy_m must contain two finite coordinates")
        if dt <= 0:
            raise ValueError("dt_s must be positive")
        if self.filtered_position is None:
            self.filtered_position = position.copy()
        else:
            previous = self.filtered_position.copy()
            alpha_position = self._alpha(dt, float(self.config["position_filter_tau_s"]))
            self.filtered_position += alpha_position * (position - self.filtered_position)
            raw_velocity = (self.filtered_position - previous) / dt
            alpha_velocity = self._alpha(dt, float(self.config["velocity_filter_tau_s"]))
            self.filtered_velocity += alpha_velocity * (raw_velocity - self.filtered_velocity)

        distance = float(np.linalg.norm(self.target - self.filtered_position))
        speed = float(np.linalg.norm(self.filtered_velocity))
        evidence = (
            distance <= float(self.config["entry_radius_m"])
            and speed <= float(self.config["stop_speed_m_s"])
        )
        self.arrival_candidate_s = self.arrival_candidate_s + dt if evidence else 0.0
        leaving = distance >= float(self.config["exit_radius_m"])
        self.departure_candidate_s = self.departure_candidate_s + dt if leaving else 0.0
        if not self.arrived and evidence and self.arrival_candidate_s + 1e-12 >= float(self.config["confirm_s"]):
            self.arrived = True
            self.departure_candidate_s = 0.0
        if (
            self.arrived
            and bool(self.config.get("recovery_enabled", True))
            and self.departure_candidate_s + 1e-12 >= float(self.config["departure_confirm_s"])
        ):
            self.arrived = False
            self.arrival_candidate_s = 0.0
        return {
            "arrived": self.arrived,
            "filtered_distance_m": distance,
            "estimated_speed_m_s": speed,
            "arrival_candidate_s": self.arrival_candidate_s,
            "departure_candidate_s": self.departure_candidate_s,
        }

    def holding_correction(self) -> np.ndarray:
        """Return a bounded engineering position hold from filtered observations."""
        if not self.arrived or self.filtered_position is None:
            return np.zeros(2, dtype=float)
        correction = (
            float(self.config.get("hold_position_kp_per_s2", 0.0))
            * (self.target - self.filtered_position)
            - float(self.config.get("hold_velocity_kd_per_s", 0.0))
            * self.filtered_velocity
        )
        maximum = float(self.config.get("maximum_hold_acceleration_m_s2", 0.0))
        magnitude = float(np.linalg.norm(correction))
        if maximum <= 0.0:
            return np.zeros(2, dtype=float)
        if magnitude > maximum:
            correction *= maximum / magnitude
        return correction
