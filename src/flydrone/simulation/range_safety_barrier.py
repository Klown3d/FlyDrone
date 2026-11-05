"""Predictive engineering safety barrier over observed range-hit points."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml


@dataclass(frozen=True)
class BarrierCommand:
    correction_xy_m_s2: tuple[float, float]
    speed_fraction: float
    predicted_clearance_m: float
    active: bool
    source: str = "engineering_predictive_range_barrier"


class InflatedPointBarrier:
    """Protect a swept point-mass path from observed points and inferred surfaces.

    Input points must come from sensing or its short-lived local map. Ground-truth
    obstacle centers are deliberately not accepted by this interface.
    """

    def __init__(self, config_path: Path):
        self.config_path = Path(config_path)
        self.config = yaml.safe_load(self.config_path.read_text(encoding="utf-8"))
        if self.config.get("parameter_status") != "engineering_predictive_range_barrier_not_neural":
            raise ValueError("Range barrier configuration must declare its engineering status")
        horizon = float(self.config["prediction_horizon_s"])
        inflated = float(self.config["inflated_clearance_m"])
        activation = float(self.config["activation_clearance_m"])
        maximum = float(self.config["maximum_correction_m_s2"])
        minimum_speed = float(self.config["minimum_speed_fraction"])
        if horizon <= 0 or inflated <= 0 or activation <= inflated or maximum <= 0:
            raise ValueError("Invalid predictive range barrier geometry")
        if not 0 <= minimum_speed <= 1:
            raise ValueError("minimum_speed_fraction must be in [0, 1]")

    @staticmethod
    def _closest_point(point: np.ndarray, start: np.ndarray,
                       end: np.ndarray) -> np.ndarray:
        segment = end - start
        length_squared = float(segment @ segment)
        if length_squared <= 1e-12:
            return start.copy()
        parameter = float(np.clip((point - start) @ segment / length_squared, 0.0, 1.0))
        return start + parameter * segment

    @classmethod
    def _segment_distance(cls, first_start: np.ndarray, first_end: np.ndarray,
                          second_start: np.ndarray, second_end: np.ndarray) -> float:
        """Exact distance between two closed 2D segments."""
        first = first_end - first_start
        second = second_end - second_start
        cross = float(first[0] * second[1] - first[1] * second[0])
        offset = second_start - first_start
        if abs(cross) > 1e-12:
            first_parameter = float((offset[0] * second[1] - offset[1] * second[0]) / cross)
            second_parameter = float((offset[0] * first[1] - offset[1] * first[0]) / cross)
            if 0.0 <= first_parameter <= 1.0 and 0.0 <= second_parameter <= 1.0:
                return 0.0
        distances = [
            np.linalg.norm(first_start - cls._closest_point(first_start, second_start, second_end)),
            np.linalg.norm(first_end - cls._closest_point(first_end, second_start, second_end)),
            np.linalg.norm(second_start - cls._closest_point(second_start, first_start, first_end)),
            np.linalg.norm(second_end - cls._closest_point(second_end, first_start, first_end)),
        ]
        return float(min(distances))

    def command(self, position_xy_m: tuple[float, float],
                velocity_xy_m_s: tuple[float, float],
                observed_hit_points_xy_m: np.ndarray,
                observed_surface_segments_xy_m: np.ndarray | None = None) -> BarrierCommand:
        position = np.asarray(position_xy_m, dtype=float)
        velocity = np.asarray(velocity_xy_m_s, dtype=float)
        points = np.asarray(observed_hit_points_xy_m, dtype=float)
        if position.shape != (2,) or velocity.shape != (2,) or not np.isfinite(position).all() or not np.isfinite(velocity).all():
            raise ValueError("Barrier pose and velocity must be finite 2D vectors")
        surfaces = (np.empty((0, 2, 2), dtype=float) if observed_surface_segments_xy_m is None
                    else np.asarray(observed_surface_segments_xy_m, dtype=float))
        if points.size == 0 and surfaces.size == 0:
            return BarrierCommand((0.0, 0.0), 1.0, float("inf"), False)
        if points.size and (points.ndim != 2 or points.shape[1] != 2 or not np.isfinite(points).all()):
            raise ValueError("Barrier hit points must be a finite Nx2 array")
        if surfaces.size and (surfaces.ndim != 3 or surfaces.shape[1:] != (2, 2) or
                              not np.isfinite(surfaces).all()):
            raise ValueError("Barrier surfaces must be a finite Nx2x2 array")

        segment = velocity * float(self.config["prediction_horizon_s"])
        length_squared = float(segment @ segment)
        if points.size:
            offsets = points - position
            if length_squared <= 1e-12:
                parameters = np.zeros(len(points))
            else:
                parameters = np.clip((offsets @ segment) / length_squared, 0.0, 1.0)
            closest_path = position + parameters[:, None] * segment
            point_distances = np.linalg.norm(closest_path - points, axis=1)
            nearest = int(np.argmin(point_distances))
            predicted_clearance = float(point_distances[nearest])
            nearest_obstacle = points[nearest]
        else:
            predicted_clearance = float("inf")
            nearest_obstacle = np.zeros(2)
        path_end = position + segment
        for surface in surfaces:
            distance = self._segment_distance(position, path_end, surface[0], surface[1])
            if distance < predicted_clearance:
                predicted_clearance = distance
                nearest_obstacle = self._closest_point(position, surface[0], surface[1])
        activation = float(self.config["activation_clearance_m"])
        if predicted_clearance >= activation:
            return BarrierCommand((0.0, 0.0), 1.0, predicted_clearance, False)

        inflated = float(self.config["inflated_clearance_m"])
        threat = float(np.clip((activation - predicted_clearance) /
                               (activation - inflated), 0.0, 1.0))
        away = position - nearest_obstacle
        norm = float(np.linalg.norm(away))
        if norm <= 1e-9:
            away = -segment
            norm = float(np.linalg.norm(away))
        if norm <= 1e-9:
            away = np.array([1.0, 0.0])
            norm = 1.0
        magnitude = threat * float(self.config["maximum_correction_m_s2"])
        correction = away * (magnitude / norm)
        minimum_speed = float(self.config["minimum_speed_fraction"])
        speed_fraction = max(minimum_speed, 1.0 - threat)
        return BarrierCommand((float(correction[0]), float(correction[1])),
                              float(speed_fraction), predicted_clearance, True)

    def command_for_acceleration(self, position_xy_m: tuple[float, float],
                                 velocity_xy_m_s: tuple[float, float],
                                 nominal_acceleration_xy_m_s2: tuple[float, float],
                                 observed_hit_points_xy_m: np.ndarray,
                                 observed_surface_segments_xy_m: np.ndarray | None = None) -> BarrierCommand:
        """Evaluate the chord implied by the fully composed acceleration command.

        Under constant acceleration, ``v + 0.5*a*T`` produces the exact endpoint
        displacement over the configured horizon.  The chord is conservative only
        with respect to that straight approximation; it is not a dynamics proof.
        """
        acceleration = np.asarray(nominal_acceleration_xy_m_s2, dtype=float)
        if acceleration.shape != (2,) or not np.isfinite(acceleration).all():
            raise ValueError("Barrier acceleration must be one finite 2D vector")
        velocity = np.asarray(velocity_xy_m_s, dtype=float)
        if self.config.get("closing_speed_projection_enabled", False):
            return self._closing_speed_projection(position_xy_m, velocity, acceleration,
                                                  observed_hit_points_xy_m,
                                                  observed_surface_segments_xy_m)
        horizon = float(self.config["prediction_horizon_s"])
        effective_velocity = velocity + 0.5 * horizon * acceleration
        return self.command(position_xy_m, (float(effective_velocity[0]),
                                             float(effective_velocity[1])),
                            observed_hit_points_xy_m,
                            observed_surface_segments_xy_m)

    def _closing_speed_projection(self, position_xy_m: tuple[float, float],
                                  velocity: np.ndarray, acceleration: np.ndarray,
                                  points_input: np.ndarray,
                                  surfaces_input: np.ndarray | None) -> BarrierCommand:
        """Project acceleration away from locally observed closing constraints."""
        position = np.asarray(position_xy_m, dtype=float)
        points = np.asarray(points_input, dtype=float)
        surfaces = (np.empty((0, 2, 2), dtype=float) if surfaces_input is None
                    else np.asarray(surfaces_input, dtype=float))
        # Reuse the public validator and its chord-based clearance diagnostic.
        horizon = float(self.config["prediction_horizon_s"])
        diagnostic = self.command(
            tuple(position), tuple(velocity + 0.5 * horizon * acceleration), points, surfaces
        )
        activation = float(self.config["activation_clearance_m"])
        inflated = float(self.config["inflated_clearance_m"])
        candidates: list[tuple[float, np.ndarray]] = []
        for point in points:
            offset = position - point
            distance = float(np.linalg.norm(offset))
            if distance < activation:
                candidates.append((distance, offset))
        for surface in surfaces:
            nearest = self._closest_point(position, surface[0], surface[1])
            offset = position - nearest
            distance = float(np.linalg.norm(offset))
            if distance < activation:
                candidates.append((distance, offset))
        if not candidates:
            return BarrierCommand((0.0, 0.0), diagnostic.speed_fraction,
                                  diagnostic.predicted_clearance_m, False,
                                  source="engineering_closing_speed_projection")
        filtered = acceleration.copy()
        velocity_norm = float(np.linalg.norm(velocity))
        # Most constrained observations first; two passes reduce order effects at corners.
        candidates.sort(key=lambda item: item[0])
        for _ in range(2):
            for distance, offset in candidates:
                norm = float(np.linalg.norm(offset))
                if norm <= 1e-9:
                    if velocity_norm <= 1e-9:
                        continue
                    normal = -velocity / velocity_norm
                else:
                    normal = offset / norm
                closing_speed = max(0.0, -float(velocity @ normal))
                available = max(distance - inflated, 0.05)
                required_outward = closing_speed * closing_speed / (2.0 * available)
                deficit = required_outward - float(filtered @ normal)
                if deficit > 0.0:
                    filtered += deficit * normal
        correction = filtered - acceleration
        correction_norm = float(np.linalg.norm(correction))
        maximum = float(self.config["maximum_correction_m_s2"])
        if correction_norm > maximum:
            correction *= maximum / correction_norm
            correction_norm = maximum
        return BarrierCommand((float(correction[0]), float(correction[1])),
                              diagnostic.speed_fraction,
                              diagnostic.predicted_clearance_m,
                              correction_norm > 1e-9,
                              source="engineering_closing_speed_projection")
