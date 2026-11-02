import numpy as np
from flydrone.neural.orientation_sensitivity import harmonic_transfer


def test_harmonic_optimization_preserves_signed_connectivity():
    rng=np.random.default_rng(783)
    weights=rng.normal(size=(24,47))
    angles=rng.uniform(-np.pi,np.pi,size=47)
    headings=np.linspace(-np.pi,np.pi,129)
    expected=np.cos(headings[:,None]-angles)@weights.T
    np.testing.assert_allclose(harmonic_transfer(weights,angles,headings),expected,atol=1e-13)
