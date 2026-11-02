from pathlib import Path

import numpy as np

from flydrone.neural.pfl3 import PFL3ReferenceModel


ROOT = Path(__file__).resolve().parents[1]


def model() -> PFL3ReferenceModel:
    return PFL3ReferenceModel.from_config(ROOT, ROOT / "configs/neural_model.yaml")


def test_model_has_24_mapped_units_split_between_lals():
    instance = model()
    assert len(instance.mapping) == 24
    assert instance.left.sum() == 12
    assert instance.right.sum() == 12


def test_rates_are_finite_nonnegative_and_periodic():
    instance = model()
    first = instance.rates(0.7, -1.1)
    wrapped = instance.rates(0.7 + 2 * np.pi, -1.1 - 2 * np.pi)
    assert np.isfinite(first).all()
    assert (first >= 0).all()
    np.testing.assert_allclose(first, wrapped, atol=1e-10)


def test_readout_is_raw_right_minus_left_sum():
    instance = model()
    rates = np.arange(24, dtype=float)
    result = instance.readout(rates)
    assert result["right_minus_left_hz"] == rates[instance.right].sum() - rates[instance.left].sum()
