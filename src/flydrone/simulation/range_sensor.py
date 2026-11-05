"""Deterministic engineering range sensor for circular 2D obstacles."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml

from flydrone.simulation.obstacles import CircleObstacle


@dataclass(frozen=True)
class RangeScan:
    relative_angles_rad: np.ndarray
    ranges_m: np.ndarray
    hit_mask: np.ndarray
    source: str = "engineering_simulated_raycast"


def ray_circle_distance(origin: np.ndarray, direction: np.ndarray,
                        obstacle: CircleObstacle) -> float | None:
    """Return the first non-negative ray intersection, if one exists."""
    origin = np.asarray(origin, dtype=float)
    direction = np.asarray(direction, dtype=float)
    if origin.shape != (2,) or direction.shape != (2,) or not np.isfinite(origin).all() or not np.isfinite(direction).all():
        raise ValueError("origin and direction must be finite 2D vectors")
    norm = float(np.linalg.norm(direction))
    if norm <= 0:
        raise ValueError("direction must be non-zero")
    direction = direction / norm
    offset = origin - obstacle.center_xy_m
    projection = float(offset @ direction)
    discriminant = projection * projection - (float(offset @ offset) - obstacle.radius_m ** 2)
    if discriminant < 0:
        return None
    root = float(np.sqrt(discriminant))
    candidates = (-projection - root, -projection + root)
    nonnegative = [value for value in candidates if value >= 0]
    return min(nonnegative) if nonnegative else None


class SimulatedRangeSensor:
    """Cast reproducible planar rays; no visual semantics are inferred."""

    def __init__(self, config_path: Path):
        self.config_path = Path(config_path)
        self.config = yaml.safe_load(self.config_path.read_text(encoding="utf-8"))
        if self.config.get("parameter_status") != "engineering_simulated_range_sensor_not_neural":
            raise ValueError("Range sensor must declare its engineering status")
        count = int(self.config["ray_count"])
        fov = float(self.config["field_of_view_deg"])
        maximum = float(self.config["maximum_range_m"])
        noise = float(self.config["range_noise_std_m"])
        dropout = float(self.config["dropout_probability"])
        if count < 2 or not 0 < fov <= 360 or maximum <= 0 or noise < 0 or not 0 <= dropout <= 1:
            raise ValueError("Invalid range-sensor configuration")
        # A full circle must not duplicate -180 and +180 degrees.
        self.relative_angles = np.deg2rad(
            np.linspace(-fov / 2, fov / 2, count, endpoint=fov < 360.0)
        )
        self.maximum_range = maximum
        self.noise_std = noise
        self.dropout_probability = dropout
        self.rng = np.random.default_rng(int(self.config["seed"]))

    def reset(self) -> None:
        self.rng = np.random.default_rng(int(self.config["seed"]))

    def scan(self, position_xy_m: tuple[float, float], heading_rad: float,
             obstacles: list[CircleObstacle]) -> RangeScan:
        origin = np.asarray(position_xy_m, dtype=float)
        if origin.shape != (2,) or not np.isfinite(origin).all() or not np.isfinite(heading_rad):
            raise ValueError("Sensor pose must be finite")
        ranges = np.full(len(self.relative_angles), self.maximum_range, dtype=float)
        hit = np.zeros(len(self.relative_angles), dtype=bool)
        for index, relative in enumerate(self.relative_angles):
            angle = float(heading_rad + relative)
            direction = np.array([np.cos(angle), np.sin(angle)])
            distances = [distance for obstacle in obstacles
                         if (distance := ray_circle_distance(origin, direction, obstacle)) is not None]
            if distances and min(distances) <= self.maximum_range:
                ranges[index] = min(distances)
                hit[index] = True
        if self.noise_std > 0:
            ranges[hit] += self.rng.normal(0.0, self.noise_std, int(hit.sum()))
            ranges = np.clip(ranges, 0.0, self.maximum_range)
        if self.dropout_probability > 0:
            dropped = self.rng.random(len(ranges)) < self.dropout_probability
            ranges[dropped] = self.maximum_range
            hit[dropped] = False
        return RangeScan(self.relative_angles.copy(), ranges, hit)

