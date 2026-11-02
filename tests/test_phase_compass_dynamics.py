import numpy as np
from flydrone.neural.phase_compass_dynamics import readout


def test_phase_readout_recovers_single_bump():
    state=np.array([[0.,1.,0.,0.]])
    phase,resultant,contrast=readout(state,np.deg2rad([-180,-90,0,90]))
    assert np.isclose(np.rad2deg(phase[0]),-90) and np.isclose(resultant[0],1) and np.isclose(contrast[0],1)
