import numpy as np

from flydrone.neural.evaluate_connectome import nearest_stable_crossing


def test_finds_stable_zero_crossing_nearest_goal():
    relative = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
    signal = np.array([2.0, 1.0, 0.0, -1.0, -2.0])
    assert nearest_stable_crossing(relative, signal) == 0.0


def test_reports_missing_crossing():
    assert nearest_stable_crossing(np.array([-1.0, 0.0, 1.0]), np.ones(3)) is None
