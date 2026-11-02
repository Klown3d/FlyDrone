"""Engineering six-degree-of-freedom quadrotor plant and conventional inner loop.

World frame is ENU (x east, y north, z up). Body axes are x forward,
y left, z up. Quaternions are [w, x, y, z] and rotate body vectors to world.
Parameters are configurable engineering values, not measurements of a real airframe.
"""
from dataclasses import dataclass, field
import numpy as np


@dataclass
class QuadrotorState:
    position_m: np.ndarray = field(default_factory=lambda: np.array([0.,0.,.7]))
    velocity_m_s: np.ndarray = field(default_factory=lambda: np.zeros(3))
    quaternion_wxyz: np.ndarray = field(default_factory=lambda: np.array([1.,0.,0.,0.]))
    body_rate_rad_s: np.ndarray = field(default_factory=lambda: np.zeros(3))
    motor_thrust_n: np.ndarray = field(default_factory=lambda: np.zeros(4))


def quaternion_multiply(a: np.ndarray,b: np.ndarray) -> np.ndarray:
    aw,ax,ay,az=a;bw,bx,by,bz=b
    return np.array([aw*bw-ax*bx-ay*by-az*bz,
                     aw*bx+ax*bw+ay*bz-az*by,
                     aw*by-ax*bz+ay*bw+az*bx,
                     aw*bz+ax*by-ay*bx+az*bw])


def quaternion_to_rotation(q: np.ndarray) -> np.ndarray:
    w,x,y,z=q/np.linalg.norm(q)
    return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                     [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                     [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])


def euler_to_quaternion(roll: float,pitch: float,yaw: float) -> np.ndarray:
    cr,sr=np.cos(roll/2),np.sin(roll/2);cp,sp=np.cos(pitch/2),np.sin(pitch/2);cy,sy=np.cos(yaw/2),np.sin(yaw/2)
    return np.array([cr*cp*cy+sr*sp*sy,sr*cp*cy-cr*sp*sy,cr*sp*cy+sr*cp*sy,cr*cp*sy-sr*sp*cy])


def yaw_from_quaternion(q: np.ndarray) -> float:
    r=quaternion_to_rotation(q)
    return float(np.arctan2(r[1,0],r[0,0]))


def motor_allocation(config: dict) -> np.ndarray:
    arm=float(config['arm_length_m'])/np.sqrt(2);yaw=float(config['yaw_moment_per_thrust_m'])
    return np.array([[1,1,1,1],[arm,-arm,-arm,arm],[-arm,-arm,arm,arm],[yaw,-yaw,yaw,-yaw]],dtype=float)


def mix_motor_thrust(total_thrust_n: float,torque_body_nm: np.ndarray,config: dict) -> np.ndarray:
    tx,ty,tz=np.asarray(torque_body_nm,float);arm=float(config['arm_length_m'])/np.sqrt(2);yaw=float(config['yaw_moment_per_thrust_m']);total=float(total_thrust_n)
    motors=.25*np.array([total+tx/arm-ty/arm+tz/yaw,total-tx/arm-ty/arm-tz/yaw,
                         total-tx/arm+ty/arm+tz/yaw,total+tx/arm+ty/arm-tz/yaw])
    return np.clip(motors,0,config['maximum_motor_thrust_n'])


def step(state: QuadrotorState,motor_command_n: np.ndarray,config: dict,dt: float,
         external_force_world_n: np.ndarray|None=None,external_torque_body_nm: np.ndarray|None=None) -> None:
    """Advance rigid-body and first-order motor dynamics one semi-implicit step."""
    command=np.clip(np.asarray(motor_command_n,float),0,config['maximum_motor_thrust_n'])
    alpha=1-np.exp(-dt/config['motor_time_constant_s'])
    state.motor_thrust_n+=alpha*(command-state.motor_thrust_n)
    rotation=quaternion_to_rotation(state.quaternion_wxyz);mass=float(config['mass_kg'])
    force_world=rotation@np.array([0.,0.,state.motor_thrust_n.sum()])
    force_world-=np.asarray(config['linear_drag_n_per_m_s'])*state.velocity_m_s
    if external_force_world_n is not None:force_world+=np.asarray(external_force_world_n,float)
    acceleration=force_world/mass-np.array([0.,0.,config['gravity_m_s2']])
    state.velocity_m_s+=dt*acceleration;state.position_m+=dt*state.velocity_m_s
    arm=float(config['arm_length_m'])/np.sqrt(2);yaw=float(config['yaw_moment_per_thrust_m']);f0,f1,f2,f3=state.motor_thrust_n
    torque=np.array([arm*(f0-f1-f2+f3),arm*(-f0-f1+f2+f3),yaw*(f0-f1+f2-f3)])
    if external_torque_body_nm is not None:torque+=np.asarray(external_torque_body_nm,float)
    inertia=np.asarray(config['inertia_kg_m2']);omega=state.body_rate_rad_s
    torque-=np.asarray(config['angular_drag_nm_per_rad_s'])*omega
    angular_acceleration=(torque-np.cross(omega,inertia*omega))/inertia
    state.body_rate_rad_s+=dt*angular_acceleration
    qdot=.5*quaternion_multiply(state.quaternion_wxyz,np.r_[0.,state.body_rate_rad_s])
    state.quaternion_wxyz+=dt*qdot;state.quaternion_wxyz/=np.linalg.norm(state.quaternion_wxyz)
    if state.position_m[2]<0:
        state.position_m[2]=0.;state.velocity_m_s[2]=max(0.,state.velocity_m_s[2])


def _vee(skew: np.ndarray) -> np.ndarray:
    return np.array([skew[2,1],skew[0,2],skew[1,0]])


def acceleration_attitude_controller(state: QuadrotorState,desired_acceleration_m_s2: np.ndarray,
                                     yaw_rate_command_rad_s: float,config: dict) -> tuple[np.ndarray,dict]:
    """Map a world-frame acceleration and yaw rate to conventional motor commands."""
    desired_acceleration=np.asarray(desired_acceleration_m_s2,float).copy()
    horizontal=desired_acceleration[:2];norm=float(np.linalg.norm(horizontal));limit=float(config['maximum_horizontal_acceleration_m_s2'])
    if norm>limit:desired_acceleration[:2]*=limit/norm
    desired_force=config['mass_kg']*(desired_acceleration+np.array([0.,0.,config['gravity_m_s2']]))
    b3=desired_force/np.linalg.norm(desired_force);yaw=yaw_from_quaternion(state.quaternion_wxyz)
    heading=np.array([np.cos(yaw),np.sin(yaw),0.]);b2=np.cross(b3,heading);b2/=np.linalg.norm(b2);b1=np.cross(b2,b3)
    desired_rotation=np.column_stack([b1,b2,b3]);rotation=quaternion_to_rotation(state.quaternion_wxyz)
    attitude_error=.5*_vee(desired_rotation.T@rotation-rotation.T@desired_rotation)
    desired_rate=np.array([0.,0.,np.clip(yaw_rate_command_rad_s,-config['maximum_yaw_rate_rad_s'],config['maximum_yaw_rate_rad_s'])])
    rate_error=state.body_rate_rad_s-desired_rate
    torque=-np.asarray(config['attitude_kp_nm'])*attitude_error-np.asarray(config['rate_kd_nm_s'])*rate_error
    total_thrust=float(np.clip(desired_force@rotation[:,2],0,4*config['maximum_motor_thrust_n']))
    motors=mix_motor_thrust(total_thrust,torque,config)
    return motors,{'desired_acceleration_m_s2':desired_acceleration,'total_thrust_n':total_thrust,
                   'torque_body_nm':torque,'attitude_error':attitude_error}


def position_attitude_controller(state: QuadrotorState,target_position_m: np.ndarray,
                                 yaw_rate_command_rad_s: float,config: dict) -> tuple[np.ndarray,dict]:
    """Conventional position/attitude controller; neural input is yaw-rate only."""
    error=np.asarray(target_position_m,float)-state.position_m
    desired_acceleration=np.array([config['position_kp_per_s2']*error[0]-config['velocity_kd_per_s']*state.velocity_m_s[0],
                                   config['position_kp_per_s2']*error[1]-config['velocity_kd_per_s']*state.velocity_m_s[1],
                                   config['altitude_kp_per_s2']*error[2]-config['altitude_kd_per_s']*state.velocity_m_s[2]])
    motors,diagnostics=acceleration_attitude_controller(state,desired_acceleration,yaw_rate_command_rad_s,config)
    diagnostics['position_error_m']=error
    return motors,diagnostics
