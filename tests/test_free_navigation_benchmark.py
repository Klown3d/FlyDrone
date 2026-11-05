import numpy as np

from flydrone.simulation.benchmark_free_navigation import development_success, trace_metrics


def test_development_success_is_mode_specific_and_safety_bounded():
    heuristic = {"patrol_minimum_targets": 4, "explore_minimum_targets": 6,
                 "explore_minimum_spatial_coverage_fraction": .3,
                 "maximum_workspace_escape_fraction": .02}
    assert development_success({"behavior_mode": "patrol", "targets_completed": 4,
                                "workspace_escape_fraction": 0., "spatial_coverage_fraction": .1}, heuristic)
    assert development_success({"behavior_mode": "explore", "targets_completed": 6,
                                "workspace_escape_fraction": 0., "spatial_coverage_fraction": .3}, heuristic)
    assert not development_success({"behavior_mode": "explore", "targets_completed": 12,
                                    "workspace_escape_fraction": .03, "spatial_coverage_fraction": .8}, heuristic)


def test_trace_metrics_measure_coverage_stall_and_neural_participation():
    columns = np.asarray(["x_m", "y_m", "vx_m_s", "vy_m_s", "target_x_m", "target_y_m",
                          "yaw_command_rad_s", "compass_neural_weight", "hdelta_activity_0",
                          "arrival_hold_correction_x_m_s2", "arrival_hold_correction_y_m_s2"])
    columns = np.r_[columns, ["geofence_correction_x_m_s2", "geofence_correction_y_m_s2"]]
    values = np.asarray([[0., 0., 0., 0., 3., 0., .2, .2, 1., .1, 0., .2, 0.],
                         [2., 0., 1., 0., 3., 0., 0., .8, 1., 0., 0., 0., 0.]])
    result = trace_metrics({"columns": columns, "values": values},
                           {"exploration_bounds_xy_m": [[-4., 4.], [-4., 4.]],
                            "exploration_grid_spacing_m": 2.}, True)
    assert result["spatial_coverage_fraction"] == 2 / 25
    assert result["stalled_fraction"] == .5
    assert result["neural_yaw_command_active_fraction"] == .5
    assert result["hdelta_activity_active_fraction"] == 1.
    assert result["engineering_heading_dominant_fraction"] == .5
    assert result["engineering_goal_capture_active_fraction"] == .5
    assert result["engineering_geofence_active_fraction"] == .5
