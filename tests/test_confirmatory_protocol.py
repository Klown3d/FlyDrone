from pathlib import Path

from flydrone.simulation.analyze_confirmatory_gate import wilson
from flydrone.simulation.confirmatory_protocol import validate


ROOT = Path(__file__).resolve().parents[1]
CONFIG = Path("configs/quadrotor_connectome_confirmatory.yaml")


def test_confirmatory_protocol_has_new_paired_cases_and_five_nulls() -> None:
    result = validate(ROOT, CONFIG, allow_existing_output=True)
    assert result["cases_per_condition"] == 100
    assert result["conditions"] == 8
    assert result["total_episodes"] == 800
    assert len(result["null_seeds"]) == 5


def test_wilson_interval_contains_observed_rate() -> None:
    low, high = wilson(90, 100)
    assert low < .9 < high
