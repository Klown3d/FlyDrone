from pathlib import Path

from flydrone.simulation.free_navigation_gate_protocol import validate


ROOT = Path(__file__).resolve().parents[1]


def test_free_navigation_gate_has_held_out_24_episode_matrix():
    result = validate(ROOT, Path("configs/free_navigation_gate_v1.yaml"), allow_output=True)
    assert result["cases_per_controller"] == 12
    assert result["total_episodes"] == 24
