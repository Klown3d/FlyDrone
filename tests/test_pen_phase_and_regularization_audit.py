import numpy as np

from flydrone.neural.pen_phase_audit import shifted_pen_matrices
from flydrone.neural.regularization_audit import matrix_metrics, offset_profile
from flydrone.neural.regularized_phase_nulls import shuffled_phase_series
import pandas as pd


class FakeData(dict):
    @property
    def files(self):
        return list(self.keys())


def test_symmetric_pen_shift_moves_left_and_right_oppositely():
    matrix = np.arange(16).reshape(4, 4)
    data = FakeData({"phases_deg": np.arange(4), "pen_a_left": matrix,
                     "pen_a_right": matrix, "pen_b_left": matrix, "pen_b_right": matrix})
    result = shifted_pen_matrices(data, "a", 1)
    np.testing.assert_array_equal(result["pen_a_left"], np.roll(matrix, -1, axis=0))
    np.testing.assert_array_equal(result["pen_a_right"], np.roll(matrix, 1, axis=0))
    np.testing.assert_array_equal(result["pen_b_left"], matrix)


def test_regularization_metrics_are_zero_for_circulant_matrix():
    first = np.array([1., 2., 3., 4.])
    matrix = np.array([[first[(i-j) % 4] for j in range(4)] for i in range(4)])
    metrics = matrix_metrics(matrix, matrix.copy())
    assert metrics["normalized_frobenius_error"] == 0
    assert metrics["minimum_fraction_weight_relocated"] == 0
    np.testing.assert_allclose(offset_profile(matrix), 4 * first)


def test_phase_null_is_deterministic_and_preserves_labels():
    phases = pd.Series([0., 90., 180., 270.], index=list("abcd"))
    one = shuffled_phase_series(phases, 91000); two = shuffled_phase_series(phases, 91000)
    pd.testing.assert_series_equal(one, two)
    assert sorted(one.tolist()) == sorted(phases.tolist())
