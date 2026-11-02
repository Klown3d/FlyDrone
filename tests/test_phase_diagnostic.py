"""Synthetic inputs verify mathematical diagnostics, not biological performance."""
import numpy as np
from flydrone.neural.phase_diagnostic import circular_summary, stable_crossing


def test_circular_summary_preserves_amplitude_and_handles_wrap():
    angles = np.deg2rad([179, -179, 40])
    weights = np.array([[2., 2., 0.], [0., 0., 0.]])
    phase, amplitude = circular_summary(weights, angles)
    headings = np.linspace(-np.pi, np.pi, 73)
    actual = np.cos(headings[:, None]-angles) @ (weights/np.array([[4.], [1.]])).T
    np.testing.assert_allclose(actual, amplitude*np.cos(headings[:, None]-phase), atol=1e-14)
    assert abs(abs(np.rad2deg(phase[0]))-180) < 1e-10
    assert amplitude[1] == 0


def test_unstable_crossing_is_not_reported_as_stable():
    x = np.array([-1., 0., 1.])
    assert stable_crossing(x, x) is None
    assert stable_crossing(x, -x) == 0
