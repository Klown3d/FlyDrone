from pathlib import Path

from flydrone.simulation.v5_hybrid_gate_protocol import validate


ROOT = Path(__file__).resolve().parents[1]
CONFIG = Path("configs/quadrotor_integrated_v5_hybrid_gate.yaml")


def test_v5_hybrid_gate_has_disjoint_24_case_matrix():
    summary = validate(ROOT, CONFIG, allow_output=True)
    assert summary == {
        "protocol_id": "flydrone_v5_hybrid_operational_gate_v1",
        "cases_per_condition": 24,
        "conditions": 4,
        "total_episodes": 96,
    }
