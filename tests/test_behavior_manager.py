from pathlib import Path

import numpy as np
import pytest

from flydrone.simulation.behavior_manager import MODES, NavigationBehaviorManager


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/behavior_manager.yaml"


def manager() -> NavigationBehaviorManager:
    result = NavigationBehaviorManager(CONFIG)
    result.reset((3.5, 2.0), heading_rad=0.0)
    return result


def test_point_mode_preserves_user_goal():
    behavior = manager()
    first = behavior.update((0.0, 0.0), 0.0)
    second = behavior.update((1.0, 0.0), 0.0)
    assert first.target_xy_m == second.target_xy_m == (3.5, 2.0)
    assert first.changed and not second.changed
    assert first.source == "engineering_behavior_manager"


def test_manual_mode_projects_goal_ahead_and_rotates():
    behavior = manager()
    behavior.set_mode("manual", (1.0, 2.0), 0.0)
    assert np.allclose(behavior.update((1.0, 2.0), 0.0).target_xy_m, (4.0, 2.0))
    behavior.rotate_manual_direction(np.pi / 2)
    assert np.allclose(behavior.update((2.0, 3.0), 0.0).target_xy_m, (2.0, 6.0))


def test_patrol_advances_only_inside_acceptance_radius():
    behavior = manager()
    initial = behavior.set_mode("patrol", (0.0, 0.0), 0.0)
    assert initial.target_index == 0
    reached = behavior.update(initial.target_xy_m, 0.0)
    assert reached.target_index == 1 and reached.visited_targets == 1 and reached.changed
    assert reached.completed_targets_total == 1 and reached.completed_cycles == 0
    behavior.skip_current_target()
    assert behavior.update((0.0, 0.0), 0.0).target_index == 2


def test_exploration_sequence_is_deterministic_and_cycles():
    first, second = manager(), manager()
    a = first.set_mode("explore", (0.0, 0.0), 0.0)
    b = second.set_mode("explore", (0.0, 0.0), 0.0)
    assert a.target_xy_m == b.target_xy_m and a.total_targets == 25
    seen = []
    current = a
    for _ in range(a.total_targets):
        seen.append(current.target_xy_m)
        current = first.update(current.target_xy_m, 0.0)
    assert len(set(seen)) == a.total_targets
    assert current.completed_targets_total == a.total_targets
    assert current.completed_cycles == 1


def test_unknown_mode_is_rejected():
    behavior = manager()
    assert MODES == ("point", "manual", "patrol", "explore")
    with pytest.raises(ValueError, match="Unknown behavior mode"):
        behavior.set_mode("vision", (0.0, 0.0), 0.0)


def test_nearest_exploration_avoids_long_random_jumps():
    behavior = NavigationBehaviorManager(ROOT / "configs/behavior_manager_nearest.yaml")
    current = behavior.set_mode("explore", (0.0, 0.0), 0.0)
    assert current.completed_targets_total == 0
    assert np.isclose(np.linalg.norm(np.asarray(current.target_xy_m)), 2.0)
    targets = [np.asarray(current.target_xy_m)]
    for _ in range(5):
        current = behavior.update(current.target_xy_m, 0.0)
        targets.append(np.asarray(current.target_xy_m))
    steps = np.linalg.norm(np.diff(np.asarray(targets), axis=0), axis=1)
    assert np.all(steps <= np.sqrt(8.0) + 1e-9)
    second = NavigationBehaviorManager(ROOT / "configs/behavior_manager_nearest.yaml")
    assert second.set_mode("explore", (0.0, 0.0), 0.0).target_xy_m == tuple(targets[0])


def test_abandoning_unreachable_target_does_not_count_completion():
    behavior = NavigationBehaviorManager(ROOT / "configs/behavior_manager_nearest.yaml")
    first = behavior.set_mode("explore", (0.0, 0.0), 0.0)
    behavior.abandon_current_target((0.0, 0.0))
    second = behavior.update((0.0, 0.0), 0.0)
    assert second.target_xy_m != first.target_xy_m
    assert second.completed_targets_total == 0
    assert second.abandoned_targets_total == 1
