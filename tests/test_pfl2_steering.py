from pathlib import Path

import numpy as np

from flydrone.neural.pfl2_steering import PFL2SteeringController


ROOT = Path(__file__).parents[1]
CONFIG = ROOT / "configs/pfl2_steering.yaml"


def test_pfl2_modulation_preserves_turn_sign_and_increases_antigoal_magnitude():
    controller = PFL2SteeringController(ROOT, CONFIG)
    goal = 0.4
    near, _, near_index, near_scale = controller.modulate(0.3, goal, goal)
    far, _, far_index, far_scale = controller.modulate(0.3, goal + np.pi, goal)
    assert near > 0 and far > 0
    assert near_index == 0.0 and np.isclose(far_index, 1.0)
    assert near_scale == 1.0 and far_scale == 1.5
    assert far > near


def test_pfl2_ablation_returns_unmodified_command():
    controller = PFL2SteeringController(ROOT, CONFIG)
    result, _, _, scale = controller.modulate(-0.42, 2.0, 0.0, enabled=False)
    assert result == -0.42
    assert scale == 1.0


def test_analytic_control_matches_angular_error_without_connectome_index():
    controller = PFL2SteeringController(ROOT, ROOT / "configs/pfl2_steering_analytic_control.yaml")
    _, _, aligned, aligned_scale = controller.modulate(0.4, 0.2, 0.2)
    _, _, orthogonal, _ = controller.modulate(0.4, 0.2 + np.pi / 2, 0.2)
    _, _, opposite, opposite_scale = controller.modulate(0.4, 0.2 + np.pi, 0.2)
    assert np.isclose(aligned, 0.0) and np.isclose(orthogonal, 0.5) and np.isclose(opposite, 1.0)
    assert aligned_scale == 1.0 and opposite_scale == 1.5
