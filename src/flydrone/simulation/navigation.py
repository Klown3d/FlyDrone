"""Spatial navigation engineering interface around the shared hover plant."""
from dataclasses import dataclass
import numpy as np
from flydrone.simulation.hover import HoverState, update
from flydrone.neural.orientation_closed_loop import wrap


@dataclass
class NavigationState(HoverState):
    x: float | np.ndarray = 0.0
    y: float | np.ndarray = 0.0
    vx: float | np.ndarray = 0.0
    vy: float | np.ndarray = 0.0
    arrived: bool | np.ndarray = False
    arrival_candidate_s: float | np.ndarray = 0.0
    departure_candidate_s: float | np.ndarray = 0.0
    filtered_x: float | np.ndarray | None = None
    filtered_y: float | np.ndarray | None = None


def goal_bearing(state: NavigationState, target: tuple) -> np.ndarray:
    dx=target[0]-state.x;dy=target[1]-state.y
    return np.where(np.hypot(dx,dy)>1e-9,np.arctan2(dy,dx),state.heading)


def held_goal_bearing(previous: float, held: bool, state: NavigationState, target: tuple,
                      hold_radius: float, release_radius: float) -> tuple[float, bool]:
    """Hold the last reliable scalar goal angle near the target; engineering UI interface."""
    distance=float(np.hypot(target[0]-state.x,target[1]-state.y))
    raw=float(goal_bearing(state,target))
    if held:
        if distance>=release_radius:return raw,False
        return float(previous),True
    if distance<=hold_radius:return float(previous),True
    return raw,False


def update_arrival(state: NavigationState,sensed: NavigationState,target: tuple,navigation: dict,dt: float) -> tuple:
    """Update the shared engineering arrival latch from an observed state."""
    distance=np.hypot(target[0]-sensed.x,target[1]-sensed.y);speed=np.hypot(sensed.vx,sensed.vy)
    if navigation.get('arrival_policy','legacy')=='confirmed':
        if state.filtered_x is None:
            state.filtered_x=np.asarray(sensed.x).copy();state.filtered_y=np.asarray(sensed.y).copy()
        filter_tau=navigation['arrival_filter_tau_s'];alpha=1. if filter_tau<=0 else 1-np.exp(-dt/filter_tau)
        state.filtered_x=state.filtered_x+alpha*(sensed.x-state.filtered_x);state.filtered_y=state.filtered_y+alpha*(sensed.y-state.filtered_y)
        filtered_distance=np.hypot(target[0]-state.filtered_x,target[1]-state.filtered_y)
        evidence=(filtered_distance<=navigation['arrival_entry_radius_m'])&(speed<=navigation['stop_speed_m_s'])
        state.arrival_candidate_s=np.where(evidence,state.arrival_candidate_s+dt,0.)
        leaving=filtered_distance>=navigation['arrival_exit_radius_m'];state.departure_candidate_s=np.where(leaving,state.departure_candidate_s+dt,0.)
        enter=evidence&(state.arrival_candidate_s+1e-10>=navigation['arrival_confirm_s'])
        exit=(state.departure_candidate_s+1e-10>=navigation['departure_confirm_s']) if navigation.get('arrival_recovery_enabled',True) else np.zeros_like(leaving,dtype=bool)
        state.arrived=np.where(exit,False,np.logical_or(state.arrived,enter))
    else:
        state.arrived=np.logical_or(state.arrived,(distance<=navigation['arrival_radius_m']*.7)&(speed<=navigation['stop_speed_m_s']))
    return distance,speed


def advance(state: NavigationState, yaw_command: float | np.ndarray, target: tuple,
            plant: dict, navigation: dict, tau: float, dt: float,
            observation: NavigationState | None = None) -> float | np.ndarray:
    """Neural yaw, conventional forward speed/braking; no target position snapping."""
    sensed=state if observation is None else observation
    distance,speed=update_arrival(state,sensed,target,navigation,dt)
    error=wrap(sensed.heading-goal_bearing(sensed,target))
    desired=np.minimum(navigation['maximum_speed_m_s'],navigation['distance_gain_per_s']*distance)
    aligned=np.maximum(0,np.cos(error))
    allowed=(np.abs(error)<=np.deg2rad(navigation['advance_angle_limit_deg'])) & (np.abs(sensed.altitude-plant['target_altitude_m'])<=.2) & ~np.asarray(state.arrived)
    desired=np.where(allowed,desired*aligned,0.)
    thrust=update(state,np.where(state.arrived,0,yaw_command),plant,tau,dt)
    decay=np.exp(-dt/navigation['velocity_tau_s'])
    state.vx=desired*np.cos(state.heading)+(state.vx-desired*np.cos(state.heading))*decay
    state.vy=desired*np.sin(state.heading)+(state.vy-desired*np.sin(state.heading))*decay
    state.x+=dt*state.vx;state.y+=dt*state.vy
    return thrust
