from pathlib import Path

import numpy as np
import yaml

from flydrone.neural.epg_delta7 import EPGDelta7Candidate
from flydrone.neural.steering_connectome_nulls import build_steering_null

ROOT = Path(__file__).resolve().parents[1]


def _model() -> EPGDelta7Candidate:
    orientation = yaml.safe_load(
        (ROOT / "configs/orientation_candidate_v1.yaml").read_text(encoding="utf-8")
    )
    return EPGDelta7Candidate(ROOT, ROOT / orientation["candidate_config"])


def _assert_block_invariants(
    original: np.ndarray, changed: np.ndarray, groups: np.ndarray
) -> None:
    for group in np.unique(groups):
        selected = groups == group
        np.testing.assert_array_equal(
            (changed[:, selected] > 0).sum(axis=0),
            (original[:, selected] > 0).sum(axis=0),
        )
        np.testing.assert_array_equal(
            (changed[:, selected] > 0).sum(axis=1),
            (original[:, selected] > 0).sum(axis=1),
        )
        np.testing.assert_allclose(
            np.sort(changed[:, selected], axis=1),
            np.sort(original[:, selected], axis=1),
        )


def test_steering_null_preserves_projection_statistics_and_changes_partners() -> None:
    model = _model()
    null = build_steering_null(model, seed=52011, heading_sign=-1.0)
    epg_changed = np.asarray(null.variant["epg_to_delta"])
    delta_changed = np.asarray(null.variant["delta_to_pfl3"])
    delta_features = model.base.features.set_index("root_id").loc[model.base.delta_ids]

    assert not np.array_equal(epg_changed, model.epg_to_delta)
    assert not np.array_equal(delta_changed, model.delta_to_pfl3)
    _assert_block_invariants(
        model.epg_to_delta,
        epg_changed,
        model.epg["source_side"].to_numpy(str),
    )
    _assert_block_invariants(
        model.delta_to_pfl3,
        delta_changed,
        delta_features["source_side"].to_numpy(str),
    )
    assert null.metadata["epg_to_delta_accepted_swaps"] > 0
    assert null.metadata["delta_to_pfl3_accepted_swaps"] > 0


def test_steering_null_phase_alignment_is_finite_and_deterministic() -> None:
    model = _model()
    first = build_steering_null(model, seed=52021, heading_sign=-1.0)
    second = build_steering_null(model, seed=52021, heading_sign=-1.0)
    np.testing.assert_allclose(first.variant["epg_to_delta"], second.variant["epg_to_delta"])
    np.testing.assert_allclose(first.variant["delta_to_pfl3"], second.variant["delta_to_pfl3"])
    assert np.isfinite(float(first.variant["phase_offset_deg"]))
    assert first.metadata == second.metadata


def test_single_projection_null_leaves_other_projection_intact() -> None:
    model = _model()
    epg_only = build_steering_null(
        model, seed=53011, heading_sign=-1.0, projection_mode="epg_to_delta"
    )
    delta_only = build_steering_null(
        model, seed=53021, heading_sign=-1.0, projection_mode="delta_to_pfl3"
    )
    assert not np.array_equal(epg_only.variant["epg_to_delta"], model.epg_to_delta)
    np.testing.assert_allclose(epg_only.variant["delta_to_pfl3"], model.delta_to_pfl3)
    np.testing.assert_allclose(delta_only.variant["epg_to_delta"], model.epg_to_delta)
    assert not np.array_equal(delta_only.variant["delta_to_pfl3"], model.delta_to_pfl3)
    assert epg_only.metadata["delta_to_pfl3_accepted_swaps"] == 0
    assert delta_only.metadata["epg_to_delta_accepted_swaps"] == 0
