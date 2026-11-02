from pathlib import Path

from flydrone.simulation.connectome_null_protocol import validate

ROOT = Path(__file__).resolve().parents[1]


def test_prospective_connectome_null_matrix_is_preregistered() -> None:
    summary = validate(
        ROOT,
        Path("configs/quadrotor_integrated_v4_connectome_null_prospective.yaml"),
        allow_output=True,
    )
    assert summary["null_conditions"] == 20
    assert summary["cases_per_condition"] == 12
    assert summary["total_episodes"] == 252
