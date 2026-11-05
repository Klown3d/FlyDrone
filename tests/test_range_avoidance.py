from pathlib import Path

import numpy as np

from flydrone.simulation.obstacles import CircleObstacle
from flydrone.simulation.range_avoidance import (RangeAvoidancePlanner, hit_points_from_scan,
                                                 surface_segments_from_scan)
from flydrone.simulation.range_sensor import RangeScan, SimulatedRangeSensor


ROOT = Path(__file__).resolve().parents[1]


def planner() -> RangeAvoidancePlanner:
    return RangeAvoidancePlanner(ROOT / "configs/range_avoidance.yaml")


def test_clear_scan_preserves_mission_target():
    sensor = SimulatedRangeSensor(ROOT / "configs/range_sensor.yaml")
    result = planner().update(sensor.scan((0., 0.), 0., []), (0., 0.), 0., (4., 0.), .02)
    assert not result.active
    assert result.target_xy_m == (4., 0.)
    assert result.mapped_points == 0


def test_blocked_goal_selects_lateral_local_target_and_maps_hits():
    sensor = SimulatedRangeSensor(ROOT / "configs/range_sensor.yaml")
    scan = sensor.scan((0., 0.), 0., [CircleObstacle(np.array([1.8, 0.]), .55)])
    result = planner().update(scan, (0., 0.), 0., (4., 0.), .02)
    assert result.active
    assert abs(result.target_xy_m[1]) > .1
    assert result.target_xy_m[0] > 0
    assert result.mapped_points > 0
    assert 0 < result.speed_fraction <= .75
    assert result.source == "engineering_range_avoidance"


def test_new_waypoint_keeps_lateral_geometric_clearance():
    sensor = SimulatedRangeSensor(ROOT / "configs/range_sensor.yaml")
    obstacle = CircleObstacle(np.array([1.8, 0.]), .55)
    result = planner().update(sensor.scan((0., 0.), 0., [obstacle]),
                              (0., 0.), 0., (4., 0.), .02)
    waypoint = np.asarray(result.target_xy_m)
    surface_clearance = float(np.linalg.norm(waypoint - obstacle.center_xy_m) - obstacle.radius_m)
    assert surface_clearance >= .45


def test_close_side_obstacle_generates_bounded_away_correction():
    sensor = SimulatedRangeSensor(ROOT / "configs/range_sensor.yaml")
    obstacle = CircleObstacle(np.array([0., -0.8]), .55)
    result = planner().update(sensor.scan((0., 0.), 0., [obstacle]),
                              (0., 0.), 0., (4., 0.), .02)
    correction = np.asarray(result.safety_correction_xy_m_s2)
    assert correction[1] > 0
    assert 0 < np.linalg.norm(correction) <= .90 + 1e-9


def test_predictive_candidate_increases_rejection_only_when_closing():
    sensor = SimulatedRangeSensor(ROOT / "configs/range_sensor_omni_candidate_v16.yaml")
    obstacle = CircleObstacle(np.array([0., -0.8]), .55)
    scan = sensor.scan((0., 0.), 0., [obstacle])
    static = RangeAvoidancePlanner(ROOT / "configs/range_avoidance_candidate_v21.yaml")
    approaching = RangeAvoidancePlanner(ROOT / "configs/range_avoidance_candidate_v21.yaml")
    still = static.update(scan, (0., 0.), 0., (4., 0.), .02, (0., 0.))
    closing = approaching.update(scan, (0., 0.), 0., (4., 0.), .02, (0., -.4))
    assert np.linalg.norm(closing.safety_correction_xy_m_s2) > np.linalg.norm(still.safety_correction_xy_m_s2)
    assert np.linalg.norm(closing.safety_correction_xy_m_s2) <= 1.20 + 1e-9


def test_contour_outward_bias_points_away_from_obstacle():
    unbiased = planner()
    biased = RangeAvoidancePlanner(ROOT / "configs/range_avoidance_candidate_v23.yaml")
    obstacle_angle = .4
    tangent = unbiased._contour_desired_world(obstacle_angle, 1.0)
    outward = biased._contour_desired_world(obstacle_angle, 1.0)
    away = -np.array([np.cos(obstacle_angle), np.sin(obstacle_angle)])
    tangent_vector = np.array([np.cos(tangent), np.sin(tangent)])
    outward_vector = np.array([np.cos(outward), np.sin(outward)])
    assert abs(float(tangent_vector @ away)) < 1e-9
    assert float(outward_vector @ away) > .25


def test_integrated_predictive_barrier_limits_speed_before_swept_collision():
    sensor = SimulatedRangeSensor(ROOT / "configs/range_sensor_omni_candidate_v16.yaml")
    plan = RangeAvoidancePlanner(ROOT / "configs/range_avoidance_candidate_v16.yaml",
                                 ROOT / "configs/range_safety_barrier.yaml")
    obstacle = CircleObstacle(np.array([1.8, 0.0]), .55)
    result = plan.update(sensor.scan((0., 0.), 0., [obstacle]),
                         (0., 0.), 0., (4., 0.), .02, (1., 0.))
    assert result.barrier_active
    assert result.predicted_clearance_m < .70
    assert result.barrier_speed_fraction < 1.
    assert result.speed_fraction <= result.barrier_speed_fraction


def test_blocked_goal_keeps_world_frame_waypoint_while_vehicle_moves():
    sensor = SimulatedRangeSensor(ROOT / "configs/range_sensor.yaml")
    plan = planner()
    obstacles = [CircleObstacle(np.array([1.8, 0.]), .55)]
    first = plan.update(sensor.scan((0., 0.), 0., obstacles),
                        (0., 0.), 0., (4., 0.), .02)
    second_pose = (.12, .04)
    second = plan.update(sensor.scan(second_pose, .08, obstacles),
                         second_pose, .08, (4., 0.), .02)
    assert first.active and second.active
    assert np.allclose(second.target_xy_m, first.target_xy_m)
    assert second.strategy == "contour_follow"


def test_persistent_waypoint_releases_when_mission_corridor_is_clear():
    sensor = SimulatedRangeSensor(ROOT / "configs/range_sensor.yaml")
    plan = planner()
    blocked = sensor.scan((0., 0.), 0., [CircleObstacle(np.array([1.8, 0.]), .55)])
    assert plan.update(blocked, (0., 0.), 0., (4., 0.), .02).active
    clear = plan.update(sensor.scan((0., 0.), 0., []),
                        (0., 0.), 0., (4., 0.), 3.0)
    assert not clear.active
    assert clear.target_xy_m == (4., 0.)


def test_local_map_memory_expires_after_configured_time():
    sensor = SimulatedRangeSensor(ROOT / "configs/range_sensor.yaml")
    plan = planner()
    hit = sensor.scan((0., 0.), 0., [CircleObstacle(np.array([1.8, 0.]), .55)])
    assert plan.update(hit, (0., 0.), 0., (4., 0.), .02).mapped_points > 0
    empty = RangeScan(hit.relative_angles_rad, np.full_like(hit.ranges_m, 6.),
                      np.zeros_like(hit.hit_mask))
    remembered = plan.update(empty, (0., 0.), 0., (4., 0.), 1.0)
    assert remembered.mapped_points > 0
    expired = plan.update(empty, (0., 0.), 0., (4., 0.), 2.0)
    assert expired.mapped_points == 0
    assert not expired.active


def test_contour_following_makes_progress_around_single_obstacle():
    sensor = SimulatedRangeSensor(ROOT / "configs/range_sensor.yaml")
    plan = planner()
    obstacle = CircleObstacle(np.array([2.0, 0.0]), .60)
    position = np.array([0.0, 0.0])
    mission = np.array([4.5, 0.0])
    minimum_surface_clearance = float("inf")
    released_after_activation = False
    for _ in range(300):
        bearing = float(np.arctan2(mission[1] - position[1], mission[0] - position[0]))
        scan = sensor.scan(tuple(position), bearing, [obstacle])
        result = plan.update(scan, tuple(position), bearing, tuple(mission), .05)
        target = np.asarray(result.target_xy_m)
        delta = target - position
        distance = float(np.linalg.norm(delta))
        if distance > 1e-9:
            position += min(.08, distance) * delta / distance
        minimum_surface_clearance = min(
            minimum_surface_clearance,
            float(np.linalg.norm(position - obstacle.center_xy_m) - obstacle.radius_m),
        )
        released_after_activation |= plan.activations > 0 and not result.active
        if np.linalg.norm(position - mission) < .2:
            break
    assert minimum_surface_clearance > .20
    assert position[0] > 4.0
    assert released_after_activation
    assert plan.contour_waypoints >= 2


def test_blocked_waypoint_is_replanned_instead_of_held_forever():
    sensor = SimulatedRangeSensor(ROOT / "configs/range_sensor.yaml")
    plan = planner()
    obstacle = CircleObstacle(np.array([1.8, 0.0]), .55)
    first = plan.update(sensor.scan((0., 0.), 0., [obstacle]),
                        (0., 0.), 0., (4., 0.), .02)
    original = np.asarray(first.target_xy_m)
    blocked = RangeScan(
        sensor.relative_angles.copy(),
        np.full_like(sensor.relative_angles, .85),
        np.ones_like(sensor.relative_angles, dtype=bool),
    )
    result = first
    for _ in range(4):
        result = plan.update(blocked, (0., 0.), 0., (4., 0.), .20)
    assert plan.blocked_waypoint_replans >= 1
    assert not np.allclose(result.target_xy_m, original)


def test_sustained_clear_direct_path_releases_even_after_detour():
    sensor = SimulatedRangeSensor(ROOT / "configs/range_sensor.yaml")
    plan = planner()
    front = CircleObstacle(np.array([1.8, 0.0]), .55)
    assert plan.update(sensor.scan((0., 0.), 0., [front]),
                       (0., 0.), 0., (4., 0.), .02).active
    angles = sensor.relative_angles.copy()
    ranges = np.full_like(angles, sensor.maximum_range)
    hits = np.zeros_like(angles, dtype=bool)
    ranges[0] = 1.0
    hits[0] = True
    side_hit = RangeScan(angles, ranges, hits)
    plan.local_map.reset()
    result = None
    for _ in range(4):
        result = plan.update(side_hit, (-.5, 0.), 0., (4., 0.), .20)
    assert result is not None and not result.active
    assert result.target_xy_m == (4., 0.)


def test_persistent_avoidance_without_progress_marks_mission_blocked():
    sensor = SimulatedRangeSensor(ROOT / "configs/range_sensor_omni_candidate_v16.yaml")
    plan = RangeAvoidancePlanner(
        ROOT / "configs/range_avoidance_candidate_v36_blocked_targets.yaml"
    )
    obstacle = CircleObstacle(np.array([1.8, 0.0]), .55)
    scan = sensor.scan((0., 0.), 0., [obstacle])
    result = None
    for _ in range(90):
        result = plan.update(scan, (0., 0.), 0., (4., 0.), .10)
    assert result is not None
    assert result.active
    assert result.mission_target_blocked


def test_adjacent_compatible_hits_form_surface_without_bridging_range_jump():
    angles = np.deg2rad(np.array([-10., 0., 10., 20.]))
    scan = RangeScan(angles, np.array([1., 1.02, 1.04, 3.]),
                     np.ones(4, dtype=bool))
    segments = surface_segments_from_scan(scan, np.zeros(2), 0., .35, .25,
                                          np.deg2rad(12.))
    assert segments.shape == (2, 2, 2)
    assert np.all(np.linalg.norm(segments[:, 0] - segments[:, 1], axis=1) < .35)


def test_current_hit_points_exclude_missed_rays():
    scan = RangeScan(np.array([0., np.pi / 2]), np.array([1., 4.]),
                     np.array([True, False]))
    points = hit_points_from_scan(scan, np.array([2., 3.]), 0.)
    assert points.shape == (1, 2)
    assert np.allclose(points[0], [3., 3.])


def test_selective_memory_drops_point_contradicted_by_clear_current_ray():
    memory = planner().local_map
    hit = RangeScan(np.array([0., np.pi / 2]), np.array([1., 4.]),
                    np.array([True, False]))
    memory.update(hit, np.zeros(2), 0., .1)
    clear = RangeScan(hit.relative_angles_rad, np.array([4., 4.]),
                      np.array([False, False]))
    selected = memory.visible_recent_points(clear, np.zeros(2), 0., 1., .2,
                                            np.deg2rad(50.))
    assert selected.shape == (0, 2)


def test_selective_memory_keeps_point_occluded_by_nearer_return():
    memory = planner().local_map
    original = RangeScan(np.array([0., np.pi / 2]), np.array([1., 4.]),
                         np.array([True, False]))
    memory.update(original, np.zeros(2), 0., .1)
    nearer = RangeScan(original.relative_angles_rad, np.array([.7, 4.]),
                       np.array([True, False]))
    selected = memory.visible_recent_points(nearer, np.zeros(2), 0., 1., .2,
                                            np.deg2rad(50.))
    assert selected.shape == (1, 2)
