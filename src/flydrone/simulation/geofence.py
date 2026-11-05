"""Bounded engineering geofence for simulated mission safety."""
from __future__ import annotations

import numpy as np


def correction(position_xy_m: np.ndarray, velocity_xy_m_s: np.ndarray, config: dict) -> np.ndarray:
    """Return an inward acceleration near rectangular workspace limits.

    This is a conventional safety layer, not a neuron model.  It is inactive
    inside the soft boundary and bounded by ``maximum_acceleration_m_s2``.
    """
    position = np.asarray(position_xy_m, dtype=float)
    velocity = np.asarray(velocity_xy_m_s, dtype=float)
    bounds = np.asarray(config["bounds_xy_m"], dtype=float)
    if position.shape != (2,) or velocity.shape != (2,) or not np.isfinite(position).all() or not np.isfinite(velocity).all():
        raise ValueError("geofence position and velocity must be finite 2D vectors")
    if bounds.shape != (2, 2) or np.any(bounds[:, 0] >= bounds[:, 1]):
        raise ValueError("bounds_xy_m must be [[xmin,xmax],[ymin,ymax]]")
    margin = float(config["activation_margin_m"])
    kp = float(config["position_kp_per_s2"])
    kd = float(config["outward_velocity_kd_per_s"])
    maximum = float(config["maximum_acceleration_m_s2"])
    if min(margin, kp, kd, maximum) < 0:
        raise ValueError("geofence gains, margin and bound must be non-negative")
    if margin * 2 >= float(np.min(bounds[:, 1] - bounds[:, 0])):
        raise ValueError("activation_margin_m leaves no geofence interior")
    result = np.zeros(2, dtype=float)
    for axis in range(2):
        low = bounds[axis, 0] + margin
        high = bounds[axis, 1] - margin
        if position[axis] < low:
            result[axis] = kp * (low - position[axis]) - kd * min(velocity[axis], 0.0)
        elif position[axis] > high:
            result[axis] = kp * (high - position[axis]) - kd * max(velocity[axis], 0.0)
    magnitude = float(np.linalg.norm(result))
    if maximum <= 0.0:
        return np.zeros(2, dtype=float)
    if magnitude > maximum:
        result *= maximum / magnitude
    return result

