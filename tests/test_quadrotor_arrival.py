import numpy as np
from pathlib import Path
import yaml

from flydrone.neural.epg_delta7 import EPGDelta7Candidate
from flydrone.neural.pfl2_steering import PFL2SteeringController
from flydrone.simulation.quadrotor_arrival import QuadrotorArrivalSupervisor


ROOT = Path(__file__).resolve().parents[1]


def configuration() -> dict:
    return {
        "position_filter_tau_s": 0.0,
        "velocity_filter_tau_s": 0.0,
        "entry_radius_m": 0.2,
        "exit_radius_m": 0.45,
        "stop_speed_m_s": 0.2,
        "confirm_s": 0.4,
        "departure_confirm_s": 0.4,
        "recovery_enabled": True,
        "hold_position_kp_per_s2": 1.0,
        "hold_velocity_kd_per_s": 0.5,
        "maximum_hold_acceleration_m_s2": 0.25,
    }


def test_arrival_requires_sustained_observed_evidence() -> None:
    supervisor = QuadrotorArrivalSupervisor(configuration(), np.array([4.0, 0.0]))
    supervisor.update(np.array([0.0, 0.0]), 0.02)
    assert not supervisor.update(np.array([4.0, 0.0]), 0.02)["arrived"]
    supervisor.update(np.array([0.0, 0.0]), 0.02)
    for _ in range(20):
        status = supervisor.update(np.array([4.0, 0.0]), 0.02)
        assert not status["arrived"]
    assert supervisor.update(np.array([4.0, 0.0]), 0.02)["arrived"]


def test_arrival_hysteresis_retains_and_releases_after_displacement() -> None:
    config = configuration()
    config["stop_speed_m_s"] = 10.0
    supervisor = QuadrotorArrivalSupervisor(config, np.array([4.0, 0.0]))
    for _ in range(20):
        status = supervisor.update(np.array([4.0, 0.0]), 0.02)
    assert status["arrived"]
    for _ in range(50):
        status = supervisor.update(np.array([4.3, 0.0]), 0.02)
    assert status["arrived"]
    for _ in range(20):
        status = supervisor.update(np.array([4.6, 0.0]), 0.02)
    assert not status["arrived"]


def test_supervisor_rejects_invalid_hysteresis() -> None:
    config = configuration()
    config["exit_radius_m"] = config["entry_radius_m"]
    try:
        QuadrotorArrivalSupervisor(config, np.array([4.0, 0.0]))
    except ValueError as error:
        assert "exit_radius_m" in str(error)
    else:
        raise AssertionError("invalid hysteresis was accepted")


def test_position_hold_is_zero_before_arrival_and_bounded_after_arrival() -> None:
    config = configuration()
    config["stop_speed_m_s"] = 10.0
    supervisor = QuadrotorArrivalSupervisor(config, np.array([4.0, 0.0]))
    assert np.allclose(supervisor.holding_correction(), 0.0)
    for _ in range(21):
        supervisor.update(np.array([3.81, 0.0]), 0.02)
    correction = supervisor.holding_correction()
    assert supervisor.arrived
    assert correction[0] > 0.0
    assert np.linalg.norm(correction) <= 0.25 + 1e-12


def test_pfl2_wrapper_propagates_delta7_ablation_to_pfl3_readout() -> None:
    orientation = yaml.safe_load((ROOT / "configs/orientation_candidate_v1.yaml").read_text())
    model = EPGDelta7Candidate(ROOT, ROOT / orientation["candidate_config"])
    controller = PFL2SteeringController(ROOT, ROOT / "configs/pfl2_steering.yaml")
    _, intact, *_ = controller.command(model, 0.6, -0.8, orientation)
    _, ablated, *_ = controller.command(
        model, 0.6, -0.8, orientation, circuit_variant={"delta7_enabled": False}
    )
    assert np.any(np.abs(intact[1]) > 0)
    assert np.allclose(ablated[1], 0.0)
    assert not np.allclose(intact[3], ablated[3])
