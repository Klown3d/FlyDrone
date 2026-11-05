from pathlib import Path

import numpy as np
import pytest

from flydrone.simulation.range_safety_barrier import InflatedPointBarrier


ROOT = Path(__file__).resolve().parents[1]


def barrier() -> InflatedPointBarrier:
    return InflatedPointBarrier(ROOT / "configs/range_safety_barrier.yaml")


def projected_barrier() -> InflatedPointBarrier:
    return InflatedPointBarrier(ROOT / "configs/range_safety_barrier_v39_closing_projection.yaml")


def test_empty_map_does_not_intervene():
    result = barrier().command((0., 0.), (1., 0.), np.empty((0, 2)))
    assert not result.active
    assert result.speed_fraction == 1.
    assert result.predicted_clearance_m == float("inf")


def test_swept_path_detects_hit_point_before_current_position_is_close():
    result = barrier().command((0., 0.), (1., 0.), np.array([[.8, .2]]))
    assert result.active
    assert result.predicted_clearance_m == pytest.approx(.2)
    assert result.speed_fraction == 0.
    assert result.correction_xy_m_s2[1] < 0
    assert np.linalg.norm(result.correction_xy_m_s2) == pytest.approx(1.2)


def test_parallel_path_outside_activation_is_unchanged():
    result = barrier().command((0., 0.), (1., 0.), np.array([[.8, .8]]))
    assert not result.active
    assert result.predicted_clearance_m == pytest.approx(.8)


def test_invalid_hit_matrix_is_rejected():
    with pytest.raises(ValueError, match="Nx2"):
        barrier().command((0., 0.), (1., 0.), np.ones((3, 3)))


def test_continuous_surface_closes_gap_between_sparse_hit_points():
    points = np.array([[.8, -.8], [.8, .8]])
    point_only = barrier().command((0., 0.), (1., 0.), points)
    surface = barrier().command((0., 0.), (1., 0.), points, points.reshape(1, 2, 2))
    assert not point_only.active
    assert surface.active
    assert surface.predicted_clearance_m == pytest.approx(0.)
    assert surface.speed_fraction == 0.


def test_invalid_surface_matrix_is_rejected():
    with pytest.raises(ValueError, match="Nx2x2"):
        barrier().command((0., 0.), (1., 0.), np.empty((0, 2)), np.ones((3, 2)))


def test_final_acceleration_is_checked_when_current_velocity_is_zero():
    points = np.array([[.8, -.8], [.8, .8]])
    surfaces = points.reshape(1, 2, 2)
    assert not barrier().command((0., 0.), (0., 0.), points, surfaces).active
    result = barrier().command_for_acceleration((0., 0.), (0., 0.), (3., 0.),
                                                points, surfaces)
    assert result.active
    assert result.correction_xy_m_s2[0] < 0.


def test_closing_projection_cancels_inward_but_not_outward_acceleration():
    points = np.array([[.6, -.3], [.6, .3]])
    surfaces = points.reshape(1, 2, 2)
    inward = projected_barrier().command_for_acceleration(
        (0., 0.), (0., 0.), (1., 0.), points, surfaces)
    outward = projected_barrier().command_for_acceleration(
        (0., 0.), (-.2, 0.), (-1., 0.), points, surfaces)
    assert inward.active and inward.correction_xy_m_s2[0] < 0.
    assert not outward.active
