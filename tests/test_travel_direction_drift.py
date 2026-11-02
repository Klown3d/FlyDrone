from pathlib import Path
import numpy as np
import pytest

from flydrone.neural.travel_direction_drift import TravelDirectionDriftController,direct_velocity_correction


ROOT = Path(__file__).resolve().parents[1]


def test_leftward_drift_generates_rightward_correction() -> None:
    controller = TravelDirectionDriftController(ROOT, ROOT / "configs/travel_direction_drift.yaml")
    result = controller.command(0.0, np.array([0.0, 0.8]), 0.0)
    assert result["lateral_drift_m_s"] > 0.5
    assert result["correction_world_m_s2"][1] < -1.0
    assert result["resultant"] > 0.3


def test_stationary_input_has_no_correction() -> None:
    controller = TravelDirectionDriftController(ROOT, ROOT / "configs/travel_direction_drift.yaml")
    result = controller.command(0.3, np.zeros(2), 0.0)
    assert np.allclose(result["correction_world_m_s2"], 0.0)


def test_phase_shuffle_changes_direction_readout() -> None:
    intact = TravelDirectionDriftController(ROOT, ROOT / "configs/travel_direction_drift.yaml")
    shuffled = TravelDirectionDriftController(ROOT, ROOT / "configs/travel_direction_drift.yaml", phase_shuffle_seed=91703)
    velocity = np.array([0.4, 0.7])
    a = intact.command(0.5, velocity, 0.1)["decoded_direction_rad"]
    b = shuffled.command(0.5, velocity, 0.1)["decoded_direction_rad"]
    assert abs(np.angle(np.exp(1j * (a - b)))) > 0.1


def test_weight_rewire_null_preserves_degrees_and_row_weights() -> None:
    intact = TravelDirectionDriftController(ROOT, ROOT / "configs/travel_direction_drift.yaml")
    rewired = TravelDirectionDriftController(
        ROOT, ROOT / "configs/travel_direction_drift.yaml", weight_rewire_seed=71903)
    original = intact.model.weights
    changed = rewired.model.weights
    assert rewired.null_metadata["accepted_swaps"] > 0
    assert not np.array_equal(changed, original)
    np.testing.assert_array_equal((changed > 0).sum(axis=0), (original > 0).sum(axis=0))
    np.testing.assert_array_equal((changed > 0).sum(axis=1), (original > 0).sum(axis=1))
    np.testing.assert_allclose(np.sort(changed, axis=1), np.sort(original, axis=1))
    assert rewired.null_metadata["global_phase_recalibrated"]


def test_block_weight_rewire_null_preserves_pfn_type_and_side() -> None:
    intact = TravelDirectionDriftController(ROOT, ROOT / "configs/travel_direction_drift.yaml")
    rewired = TravelDirectionDriftController(
        ROOT, ROOT / "configs/travel_direction_drift.yaml", block_weight_rewire_seed=81903)
    groups=(intact.model.pfn.selected_type.astype(str)+'_'+intact.model.pfn.side.astype(str)).to_numpy()
    for group in np.unique(groups):
        selected=groups==group
        np.testing.assert_array_equal((rewired.model.weights[:,selected]>0).sum(axis=0),(intact.model.weights[:,selected]>0).sum(axis=0))
        np.testing.assert_array_equal((rewired.model.weights[:,selected]>0).sum(axis=1),(intact.model.weights[:,selected]>0).sum(axis=1))
        np.testing.assert_allclose(np.sort(rewired.model.weights[:,selected],axis=1),np.sort(intact.model.weights[:,selected],axis=1))
    assert rewired.null_metadata['accepted_swaps']>0


def test_oracle_egocentric_override_changes_only_model_input() -> None:
    controller=TravelDirectionDriftController(ROOT,ROOT/'configs/travel_direction_drift.yaml')
    ordinary=controller.command(.4,np.array([.7,.2]),.1)
    oracle=controller.command(.4,np.array([.7,.2]),.1,egocentric_motion_override_rad=-1.1,speed_override_m_s=.9)
    assert np.isclose(oracle['egocentric_motion_rad'],-1.1)
    assert not np.allclose(ordinary['pfn_activity'],oracle['pfn_activity'])


def test_direct_velocity_control_uses_same_lateral_rule_without_connectome() -> None:
    result=direct_velocity_correction(0.,np.array([1.,1.]),0.,2.,.01)
    assert result['decoded_direction_rad']==pytest.approx(np.pi/4)
    assert result['lateral_drift_m_s']==pytest.approx(1.)
    np.testing.assert_allclose(result['correction_world_m_s2'],np.array([0.,-2.]))
