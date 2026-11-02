from pathlib import Path

import numpy as np

from flydrone.neural.travel_direction_model import ConnectomeTravelDirection, wrap


ROOT = Path(__file__).parents[1]
CONFIG = ROOT / "configs/travel_direction_model.yaml"


def test_model_uses_all_real_pfn_and_hdelta_neurons():
    model = ConnectomeTravelDirection(ROOT, CONFIG)
    assert model.weights.shape == (18, 61)
    assert np.all(model.weights.sum(axis=0) > 0)
    assert np.all(model.weights.sum(axis=1) > 0)


def test_allocentric_output_rotates_with_heading():
    model = ConnectomeTravelDirection(ROOT, CONFIG)
    ego = np.deg2rad(35.0)
    first = model.decode(np.deg2rad(-60.0), ego)[0]
    second = model.decode(np.deg2rad(30.0), ego)[0]
    assert abs(float(wrap((second - first) - np.deg2rad(90.0)))) < np.deg2rad(25.0)


def test_speed_scales_activity_without_changing_phase():
    model = ConnectomeTravelDirection(ROOT, CONFIG)
    slow = model.decode(0.4, -0.7, speed=0.3)
    fast = model.decode(0.4, -0.7, speed=0.9)
    assert abs(float(wrap(slow[0] - fast[0]))) < 1e-10
    assert np.allclose(fast[2], slow[2] * 3.0)
