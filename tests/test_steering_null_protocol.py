from pathlib import Path

from flydrone.simulation.steering_null_protocol import validate

ROOT = Path(__file__).resolve().parents[1]


def test_prospective_steering_null_matrix_is_preregistered() -> None:
    summary = validate(
        ROOT,
        Path("configs/quadrotor_integrated_v4_steering_null_prospective.yaml"),
        allow_output=True,
    )
    assert summary == {
        "protocol_id": "flydrone_integrated_v4_steering_null_prospective_v1",
        "cases_per_condition": 12,
        "null_conditions": 20,
        "total_episodes": 252,
    }


def test_delta_pfl3_projection_specific_matrix_is_preregistered() -> None:
    summary = validate(
        ROOT,
        Path("configs/quadrotor_integrated_v4_delta_pfl3_null_prospective.yaml"),
        allow_output=True,
    )
    assert summary["protocol_id"] == "flydrone_integrated_v4_delta_pfl3_null_prospective_v1"
    assert summary["null_conditions"] == 20
    assert summary["total_episodes"] == 252


def test_epg_delta7_projection_specific_matrix_is_preregistered() -> None:
    summary = validate(
        ROOT,
        Path("configs/quadrotor_integrated_v4_epg_delta7_null_prospective.yaml"),
        allow_output=True,
    )
    assert summary["protocol_id"] == "flydrone_integrated_v4_epg_delta7_null_prospective_v1"
    assert summary["null_conditions"] == 20
    assert summary["total_episodes"] == 252
