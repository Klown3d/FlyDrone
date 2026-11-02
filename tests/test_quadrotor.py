from pathlib import Path
import numpy as np
import yaml
from flydrone.simulation.quadrotor import (QuadrotorState,euler_to_quaternion,
    mix_motor_thrust,motor_allocation,position_attitude_controller,quaternion_to_rotation,step)

ROOT=Path(__file__).resolve().parents[1]


def config():return yaml.safe_load((ROOT/'configs/quadrotor.yaml').read_text())


def test_motor_mixer_reconstructs_feasible_force_and_torque():
    c=config();demand=np.array([c['mass_kg']*c['gravity_m_s2'],.02,-.015,.005])
    motors=mix_motor_thrust(demand[0],demand[1:],c)
    np.testing.assert_allclose(motor_allocation(c)@motors,demand,atol=1e-12)


def test_quaternion_rotation_is_orthonormal():
    r=quaternion_to_rotation(euler_to_quaternion(.3,-.2,1.1))
    np.testing.assert_allclose(r.T@r,np.eye(3),atol=1e-12);assert np.isclose(np.linalg.det(r),1)


def test_six_dof_controller_recovers_hover_from_tilt():
    c=config();dt=c['dt_s'];state=QuadrotorState(quaternion_wxyz=euler_to_quaternion(.18,-.12,.3))
    for _ in range(round(8/dt)):
        motors,_=position_attitude_controller(state,np.array([0.,0.,2.]),0.,c);step(state,motors,c,dt)
    np.testing.assert_allclose(state.position_m,[0,0,2],atol=.03)
    np.testing.assert_allclose(state.velocity_m_s,0,atol=.03)
    np.testing.assert_allclose(quaternion_to_rotation(state.quaternion_wxyz)[:,2],[0,0,1],atol=.02)
    assert np.isclose(np.linalg.norm(state.quaternion_wxyz),1,atol=1e-12)


def test_yaw_rate_command_turns_without_losing_hover():
    c=config();dt=c['dt_s'];state=QuadrotorState(position_m=np.array([0.,0.,2.]))
    for _ in range(round(3/dt)):
        motors,_=position_attitude_controller(state,np.array([0.,0.,2.]),.5,c);step(state,motors,c,dt)
    assert .35<state.body_rate_rad_s[2]<.65
    assert abs(state.position_m[2]-2)<.03


def test_position_controller_reaches_horizontal_waypoint_by_tilting():
    c=config();dt=c['dt_s'];state=QuadrotorState();target=np.array([3.,2.,2.]);tilted=False
    for _ in range(round(12/dt)):
        motors,_=position_attitude_controller(state,target,0.,c);step(state,motors,c,dt)
        tilted=tilted or abs(quaternion_to_rotation(state.quaternion_wxyz)[2,2])<.995
    assert tilted
    np.testing.assert_allclose(state.position_m,target,atol=.03)
    np.testing.assert_allclose(state.velocity_m_s,0,atol=.03)


def test_external_force_physically_displaces_hovering_vehicle():
    c=config();dt=c['dt_s'];state=QuadrotorState(position_m=np.array([0.,0.,2.]));hover=np.full(4,c['mass_kg']*c['gravity_m_s2']/4)
    state.motor_thrust_n=hover.copy()
    for _ in range(round(1/dt)):step(state,hover,c,dt,external_force_world_n=np.array([.4,0,0]))
    assert state.position_m[0]>.15
    assert abs(state.position_m[2]-2)<1e-9
