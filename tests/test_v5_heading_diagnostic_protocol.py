from pathlib import Path

from flydrone.simulation.v5_heading_diagnostic_protocol import validate

ROOT = Path(__file__).resolve().parents[1]


def test_v5_heading_diagnostic_has_new_frozen_matrix() -> None:
    summary = validate(ROOT, Path("configs/quadrotor_integrated_v5_heading_diagnostic.yaml"),
                       allow_output=True)
    assert summary == {"protocol_id": "flydrone_v5_heading_oracle_diagnostic_v1",
                       "cases_per_condition": 24, "conditions": 4, "total_episodes": 96}
