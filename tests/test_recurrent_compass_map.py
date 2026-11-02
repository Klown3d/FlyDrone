import numpy as np
from flydrone.neural.recurrent_compass_map import circular_difference,weighted_phase


def test_weighted_phase_handles_wrap_boundary():
    phase,resultant=weighted_phase(np.deg2rad([179.,-179.]),np.array([1.,1.]))
    assert abs(abs(np.rad2deg(phase))-180)<1e-9
    assert resultant>.99


def test_weighted_phase_respects_contact_multiplicity():
    phase,_=weighted_phase(np.deg2rad([0.,90.]),np.array([3.,1.]))
    assert 0<np.rad2deg(phase)<30


def test_circular_phase_shift_uses_short_difference():
    shift=circular_difference(np.deg2rad(-170),np.deg2rad(170))
    assert np.isclose(np.rad2deg(shift),20)
