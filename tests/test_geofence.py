import numpy as np
import pytest

from flydrone.simulation.geofence import correction


def config():
    return {"bounds_xy_m": [[-5.5, 5.5], [-5.5, 5.5]], "activation_margin_m": 1.0,
            "position_kp_per_s2": 1.2, "outward_velocity_kd_per_s": .8,
            "maximum_acceleration_m_s2": 1.5}


def test_geofence_is_zero_inside_and_pushes_inward_near_limits():
    assert np.allclose(correction(np.array([0., 0.]), np.zeros(2), config()), 0.)
    low = correction(np.array([-5., 0.]), np.array([-1., 0.]), config())
    high = correction(np.array([0., 5.]), np.array([0., 1.]), config())
    assert low[0] > 0 and high[1] < 0
    assert np.linalg.norm(low) <= 1.5 + 1e-12


def test_geofence_rejects_invalid_bounds():
    bad = config(); bad["activation_margin_m"] = 6.
    with pytest.raises(ValueError, match="interior"):
        correction(np.zeros(2), np.zeros(2), bad)

