from pathlib import Path

from flydrone.simulation.benchmark_integrated_v2 import load_config
from flydrone.simulation.obstacle_navigation_gate_protocol import validate


ROOT = Path(__file__).resolve().parents[1]
CONFIG = Path("configs/free_navigation_obstacles_gate_v1.yaml")


def test_obstacle_gate_matrix_and_new_cases_are_preregistered() -> None:
    summary = validate(ROOT, CONFIG, allow_output=True)
    config = load_config(ROOT, CONFIG)
    assert summary == {"protocol_id": "flydrone_obstacle_navigation_operational_gate_v1",
                       "cases_per_controller": 12, "controllers": 2,
                       "total_episodes": 24}
    assert len(config["scenarios"]) == 3
    assert all(len(scenario["obstacles"]) == 6 for scenario in config["scenarios"])
    assert config["operational_gate"]["minimum_obstacle_clearance_m"] == 0.15
    assert config["conditions"][0]["hdelta_enabled"] is False
    assert all(condition["lateral_velocity_kd_per_s"] == 2.0
               for condition in config["conditions"])
