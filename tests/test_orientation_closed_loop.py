import numpy as np
from flydrone.neural.orientation_closed_loop import wrap, yaw_step


def test_yaw_update_has_exact_time_composition_and_no_overshoot():
    first=yaw_step(np.array([0.]),np.array([1.]),.05,.15)
    second=yaw_step(first,np.array([1.]),.05,.15)
    np.testing.assert_allclose(second,yaw_step(np.array([0.]),np.array([1.]),.10,.15))
    assert 0<first[0]<second[0]<1


def test_heading_error_crosses_branch_cut_correctly():
    np.testing.assert_allclose(np.rad2deg(wrap(np.deg2rad([179-(-179),-179-179]))),[-2,2])
