from pathlib import Path

import numpy as np
import pytest

from flydrone.simulation.obstacles import CircleObstacle
from flydrone.simulation.range_sensor import SimulatedRangeSensor, ray_circle_distance


ROOT = Path(__file__).resolve().parents[1]


def test_ray_circle_distance_hits_nearest_surface_and_misses_behind():
    obstacle = CircleObstacle(np.array([3.0, 0.0]), 1.0)
    assert ray_circle_distance(np.zeros(2), np.array([1.0, 0.0]), obstacle) == pytest.approx(2.0)
    assert ray_circle_distance(np.zeros(2), np.array([-1.0, 0.0]), obstacle) is None


def test_scan_detects_nearest_of_multiple_obstacles_and_is_reproducible():
    sensor = SimulatedRangeSensor(ROOT / "configs/range_sensor.yaml")
    obstacles = [CircleObstacle(np.array([4.0, 0.0]), 1.0),
                 CircleObstacle(np.array([2.0, 0.0]), 0.5)]
    first = sensor.scan((0.0, 0.0), 0.0, obstacles)
    center = len(first.ranges_m) // 2
    assert first.hit_mask[center]
    assert first.ranges_m[center] == pytest.approx(1.5, abs=.08)
    sensor.reset()
    second = sensor.scan((0.0, 0.0), 0.0, obstacles)
    assert np.array_equal(first.hit_mask, second.hit_mask)
    assert np.allclose(first.ranges_m, second.ranges_m)
    assert first.source == "engineering_simulated_raycast"


def test_scan_returns_maximum_range_without_obstacles():
    sensor = SimulatedRangeSensor(ROOT / "configs/range_sensor.yaml")
    scan = sensor.scan((1.0, -2.0), 0.7, [])
    assert not scan.hit_mask.any()
    assert np.all(scan.ranges_m == sensor.maximum_range)


def test_omnidirectional_candidate_detects_rear_obstacle_without_duplicate_ray():
    sensor = SimulatedRangeSensor(ROOT / "configs/range_sensor_omni_candidate_v16.yaml")
    obstacle = CircleObstacle(np.array([-1.0, 0.0]), .4)
    scan = sensor.scan((0.0, 0.0), 0.0, [obstacle])
    assert scan.hit_mask.any()
    assert float(np.min(scan.ranges_m)) == pytest.approx(.6, abs=.08)
    wrapped = np.round(np.angle(np.exp(1j * scan.relative_angles_rad)), 10)
    assert len(np.unique(wrapped)) == len(wrapped)

