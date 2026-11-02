from pathlib import Path

import numpy as np

from flydrone.neural.epg_delta7 import EPGDelta7Candidate, normalize_nonzero_rows


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/epg_delta7_audit.yaml"


def test_nonzero_row_normalization_keeps_empty_rows() -> None:
    result = normalize_nonzero_rows(np.array([[1.0, 3.0], [0.0, 0.0]]))
    np.testing.assert_allclose(result, [[0.25, 0.75], [0.0, 0.0]])


def test_epg_mapping_and_real_projection_counts() -> None:
    model = EPGDelta7Candidate(ROOT, CONFIG)
    assert len(model.epg) == 47
    assert set(model.epg["geometric_column"]) == {f"PB{i:02d}" for i in range(2, 18)}
    assert int(model.epg_to_delta_raw.sum()) == 3582
    assert int(model.delta_to_delta_raw.sum()) == 3158
    assert int(model.delta_to_pfl3_raw.sum()) == 2303
    assert int(model.epg_to_pfl3_raw.sum()) == 654
    assert np.isfinite(model.rates(0.0, 0.0, "via_delta7")).all()


def test_phase_fit_is_not_silently_accepted() -> None:
    model = EPGDelta7Candidate(ROOT, CONFIG)
    result = model.phase_fit("via_delta7")
    assert 0 < result["valid_pfl3"] <= 24
    assert result["mean_abs_residual_deg"] > 20
