import numpy as np

from flydrone.neural.phase_velocity_validation import circularize


def test_circularize_is_rotation_equivariant_and_preserves_total_weight():
    matrix = np.arange(25, dtype=float).reshape(5, 5)
    result = circularize(matrix)
    np.testing.assert_allclose(np.roll(result, 1, axis=(0, 1)), result)
    assert np.isclose(result.sum(), matrix.sum())
