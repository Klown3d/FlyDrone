import numpy as np
from flydrone.simulation.obstacles import CircleObstacle,ObstaclePlanner,point_clearance,segment_clearance


def test_segment_clearance_detects_blocked_and_clear_paths():
    obstacle=CircleObstacle(np.array([2.,0.]),.5)
    assert segment_clearance(np.array([0.,0.]),np.array([4.,0.]),obstacle,.2)<0
    assert segment_clearance(np.array([0.,1.5]),np.array([4.,1.5]),obstacle,.2)>.5


def test_planner_selects_safe_deterministic_waypoint_then_releases_it():
    obstacle=CircleObstacle(np.array([2.,0.]),.5);planner=ObstaclePlanner([obstacle],.25,.15,.35)
    start=np.array([0.,0.]);target=np.array([4.,0.]);waypoint=planner.local_goal(start,target)
    assert planner.activations==1 and waypoint[1]>0
    assert segment_clearance(start,waypoint,obstacle,.25)>=.15
    assert segment_clearance(waypoint,target,obstacle,.25)>=.15
    clear_position=np.array([2.,1.6]);np.testing.assert_allclose(planner.local_goal(clear_position,target),target)


def test_planner_selects_bypass_with_smaller_initial_turn():
    obstacle=CircleObstacle(np.array([2.,0.]),.5);target=np.array([4.,0.]);start=np.array([0.,0.])
    upper=ObstaclePlanner([obstacle],.25,.15,.35).local_goal(start,target,np.deg2rad(120))
    lower=ObstaclePlanner([obstacle],.25,.15,.35).local_goal(start,target,np.deg2rad(-120))
    assert upper[1]>0 and lower[1]<0


def test_point_clearance_includes_vehicle_radius():
    obstacle=CircleObstacle(np.array([0.,0.]),.5)
    assert np.isclose(point_clearance(np.array([1.,0.]),obstacle,.25),.25)
