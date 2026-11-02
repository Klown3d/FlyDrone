from pathlib import Path

from flydrone.simulation.integrated_v2_protocol import validate
from flydrone.simulation.benchmark_integrated_v2 import load_config


ROOT = Path(__file__).resolve().parents[1]


def test_integrated_v2_protocol_has_preregistered_episode_matrix() -> None:
    # The preregistered run is now complete and its run-once output is preserved.
    summary = validate(
        ROOT, Path("configs/quadrotor_integrated_v2_prospective.yaml"), allow_output=True
    )
    assert summary["cases_per_condition"] == 30
    assert summary["conditions"] == 6
    assert summary["total_episodes"] == 180


def test_integrated_v3_protocol_has_new_sealed_episode_matrix() -> None:
    # The sealed v3 run has completed and its run-once output is preserved.
    summary = validate(
        ROOT, Path("configs/quadrotor_integrated_v3_prospective.yaml"), allow_output=True
    )
    assert summary["protocol_id"] == "flydrone_integrated_v3_prospective_v1"
    assert summary["cases_per_condition"] == 30
    assert summary["conditions"] == 6
    assert summary["total_episodes"] == 180


def test_integrated_runner_resolves_recursive_base_configs() -> None:
    config = load_config(
        ROOT, Path("configs/quadrotor_integrated_v4_lateral_fine_development.yaml")
    )
    assert config["neural_update_period_s"] > 0
    assert config["conditions"][0]["name"] == "full_kd_0_10"


def test_integrated_v4_protocol_has_new_sealed_episode_matrix() -> None:
    # The sealed v4 run has completed and its run-once output is preserved.
    summary = validate(
        ROOT, Path("configs/quadrotor_integrated_v4_prospective.yaml"), allow_output=True
    )
    assert summary["protocol_id"] == "flydrone_integrated_v4_prospective_v1"
    assert summary["cases_per_condition"] == 30
    assert summary["total_episodes"] == 180
