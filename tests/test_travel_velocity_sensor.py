from pathlib import Path
import numpy as np
import pytest

from flydrone.simulation.travel_velocity_sensor import PositionVelocityEstimator,InertialPositionVelocityEstimator

ROOT=Path(__file__).resolve().parents[1]


def estimator(): return PositionVelocityEstimator(ROOT/'configs/travel_velocity_sensor.yaml')


def test_estimator_converges_to_constant_velocity() -> None:
    sensor=estimator();dt=.02;sensor.reset(np.zeros(2));velocity=np.array([.6,-.25])
    for i in range(1,151): result=sensor.update(i*dt*velocity,dt)
    np.testing.assert_allclose(result,velocity,atol=.01)


def test_dropout_decays_without_changing_direction() -> None:
    sensor=estimator();sensor.velocity_world_xy=np.array([.4,.3]);before=np.arctan2(.3,.4)
    after=sensor.update(None,.2)
    assert np.linalg.norm(after)<.5
    assert np.isclose(np.arctan2(after[1],after[0]),before)


def test_reacquisition_does_not_turn_accumulated_displacement_into_a_speed_spike() -> None:
    sensor=estimator();dt=.02;sensor.reset(np.zeros(2))
    for i in range(1,51):sensor.update(np.array([.5*i*dt,0.]),dt)
    decayed=sensor.update(None,1.0)
    reacquired=sensor.update(np.array([1.0,0.]),dt)
    np.testing.assert_allclose(reacquired,decayed)
    next_velocity=sensor.update(np.array([1.01,0.]),dt)
    assert 0.0<next_velocity[0]<sensor.maximum_speed


def test_window_suppresses_velocity_from_stationary_position_noise() -> None:
    sensor=estimator();rng=np.random.default_rng(71);dt=.02;sensor.reset(np.zeros(2));speeds=[]
    for _ in range(500):speeds.append(np.linalg.norm(sensor.update(rng.normal(0,.02,2),dt)))
    assert float(np.median(speeds[-200:]))<.08


def test_invalid_dt_is_rejected() -> None:
    with pytest.raises(ValueError):estimator().update(np.zeros(2),0.)


def test_inertial_estimator_propagates_acceleration_during_dropout() -> None:
    sensor=InertialPositionVelocityEstimator(ROOT/'configs/travel_velocity_inertial.yaml');sensor.reset(np.zeros(2));dt=.02
    for _ in range(50):velocity=sensor.update(None,dt,np.array([.5,0.]))
    assert .45<velocity[0]<.5
    assert velocity[1]==pytest.approx(0.)


def test_inertial_reacquisition_preserves_propagated_velocity_without_spike() -> None:
    sensor=InertialPositionVelocityEstimator(ROOT/'configs/travel_velocity_inertial.yaml');sensor.reset(np.zeros(2));dt=.02
    for _ in range(50):before=sensor.update(None,dt,np.array([.4,0.]))
    after=sensor.update(np.array([2.,0.]),dt,np.zeros(2))
    np.testing.assert_allclose(after,before,atol=.01)
