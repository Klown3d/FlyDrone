"""Engineering hover/yaw plant; horizontal motion and attitude are constrained."""
from dataclasses import dataclass
import numpy as np
from flydrone.neural.orientation_closed_loop import yaw_step


@dataclass
class HoverState:
    altitude: float | np.ndarray = 0.7
    vertical_speed: float | np.ndarray = 0.0
    heading: float | np.ndarray = np.deg2rad(135.0)
    yaw_rate: float | np.ndarray = 0.0


def update(state: HoverState, yaw_command: float | np.ndarray, c: dict, tau: float, dt: float) -> float | np.ndarray:
    """PD altitude stabilization with feedforward gravity; return applied thrust."""
    acceleration=c['altitude_kp_per_s2']*(c['target_altitude_m']-state.altitude)-c['altitude_kd_per_s']*state.vertical_speed
    thrust=np.clip(c['mass_kg']*(c['gravity_m_s2']+acceleration),0,c['maximum_thrust_n'])
    state.vertical_speed+=dt*(thrust/c['mass_kg']-c['gravity_m_s2'])
    state.altitude+=dt*state.vertical_speed
    grounded=state.altitude<0
    state.altitude=np.maximum(0,state.altitude)
    state.vertical_speed=np.where(grounded,np.maximum(0,state.vertical_speed),state.vertical_speed)
    state.yaw_rate=yaw_step(np.asarray(state.yaw_rate),np.asarray(yaw_command),dt,tau)
    state.heading=np.angle(np.exp(1j*(state.heading+dt*state.yaw_rate)))
    if np.ndim(thrust)==0:
        state.altitude=float(state.altitude);state.vertical_speed=float(state.vertical_speed)
        state.heading=float(state.heading);state.yaw_rate=float(state.yaw_rate)
        return float(thrust)
    return thrust
