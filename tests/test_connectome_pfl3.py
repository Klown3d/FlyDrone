from pathlib import Path

import numpy as np

from flydrone.neural.connectome_pfl3 import ConnectomeWeightedPFL3, row_normalize, weighted_circular_mean_deg


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/connectome_model.yaml"


def test_weighted_circular_mean_and_concentration():
    angle, concentration = weighted_circular_mean_deg(np.array([-10.0, 10.0]), np.ones(2))
    assert abs(angle) < 1e-12
    assert 0.98 < concentration <= 1.0


def test_row_normalization_preserves_shape_and_rows():
    result = row_normalize(np.array([[1.0, 3.0], [2.0, 2.0]]))
    np.testing.assert_allclose(result.sum(axis=1), 1.0)


def test_primary_connectome_streams_reach_every_pfl3():
    model = ConnectomeWeightedPFL3(ROOT, CONFIG)
    assert model.delta_audit.neuron_count == 40
    assert model.delta_audit.contact_count == 2326
    assert model.fc2_audit.neuron_count == 66  # 68 FC2B/C minus two documented outliers
    assert model.delta_audit.minimum_pfl3_input > 0
    assert model.fc2_audit.minimum_pfl3_input > 0
    assert np.isfinite(model.rates(0.0, 0.0)).all()


def test_weight_shuffle_preserves_each_rows_multiset_and_sum():
    model = ConnectomeWeightedPFL3(ROOT, CONFIG)
    shuffled = model.shuffled_rows(model.fc2_weights, np.random.default_rng(7))
    np.testing.assert_allclose(shuffled.sum(axis=1), model.fc2_weights.sum(axis=1))
    for original, changed in zip(model.fc2_weights, shuffled):
        np.testing.assert_allclose(np.sort(original), np.sort(changed))
