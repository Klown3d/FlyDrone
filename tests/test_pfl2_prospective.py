from pathlib import Path

import pytest

from flydrone.simulation.benchmark_pfl2_prospective import _sign


ROOT = Path(__file__).parents[1]


def test_prospective_config_is_frozen_and_uses_new_cases():
    text = (ROOT / "configs/quadrotor_pfl2_prospective.yaml").read_text(encoding="utf-8")
    assert "run_once: true" in text
    assert "parameter_status: frozen_prospective" in text
    assert "-128.0" in text and "-172.0" in text


@pytest.mark.parametrize(("value", "expected"), [(-0.2, -1), (0.0, 0), (0.2, 1), (None, 0)])
def test_sign(value, expected):
    assert _sign(value) == expected
