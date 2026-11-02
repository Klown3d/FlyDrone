"""Explicit engineering velocity sensor for the PFN/hDeltaB interface."""
from __future__ import annotations

from pathlib import Path
from collections import deque
import numpy as np
import yaml


class PositionVelocityEstimator:
    """Estimate world-frame velocity from noisy position differences.

    This replaces privileged simulator velocity at the neural boundary. It is an
    engineering abstraction and does not claim to reconstruct fly optic flow.
    """

    def __init__(self, config_path: Path):
        self.config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        self.tau = float(self.config["filter_time_constant_s"])
        self.window = float(self.config.get("differencing_window_s",self.config["update_period_s"]))
        self.dropout_tau = float(self.config["dropout_decay_time_constant_s"])
        self.maximum_speed = float(self.config["maximum_speed_m_s"])
        if self.window<=0:raise ValueError("differencing_window_s must be positive")
        self.reset()

    def reset(self, position_xy: np.ndarray | None = None) -> None:
        self.previous_position = None if position_xy is None else np.asarray(position_xy, dtype=float).copy()
        self.velocity_world_xy = np.zeros(2, dtype=float)
        self.needs_reacquisition = False
        self.elapsed_s = 0.0
        self.position_history = deque()
        if position_xy is not None:self.position_history.append((0.0,self.previous_position.copy()))

    def update(self, position_xy: np.ndarray | None, dt_s: float) -> np.ndarray:
        dt = float(dt_s)
        if dt <= 0: raise ValueError("dt_s must be positive")
        self.elapsed_s += dt
        if position_xy is None:
            self.velocity_world_xy *= np.exp(-dt / self.dropout_tau)
            self.needs_reacquisition = True
            return self.velocity_world_xy.copy()
        position = np.asarray(position_xy, dtype=float)
        if position.shape != (2,) or not np.isfinite(position).all():
            raise ValueError("position_xy must contain two finite coordinates")
        if self.previous_position is None or self.needs_reacquisition:
            self.previous_position = position.copy()
            self.needs_reacquisition = False
            self.position_history.clear();self.position_history.append((self.elapsed_s,position.copy()))
            return self.velocity_world_xy.copy()
        self.position_history.append((self.elapsed_s,position.copy()))
        while len(self.position_history)>2 and self.elapsed_s-self.position_history[1][0]>=self.window:self.position_history.popleft()
        oldest_time,oldest_position=self.position_history[0];span=self.elapsed_s-oldest_time
        raw=(position-oldest_position)/max(dt,span);self.previous_position=position.copy()
        speed = float(np.linalg.norm(raw))
        if speed > self.maximum_speed: raw *= self.maximum_speed / speed
        alpha = 1.0 - np.exp(-dt / self.tau)
        self.velocity_world_xy += alpha * (raw - self.velocity_world_xy)
        return self.velocity_world_xy.copy()


class InertialPositionVelocityEstimator(PositionVelocityEstimator):
    """Fuse position differences with a simulated world-frame accelerometer.

    The accelerometer and fusion are engineering sensor abstractions.  They are
    not part of the reconstructed PFN/hDeltaB circuit.
    """

    uses_acceleration=True

    def __init__(self,config_path:Path):
        super().__init__(config_path);self.correction_tau=float(self.config['position_correction_time_constant_s']);self.dropout_leak_tau=float(self.config['inertial_dropout_leak_time_constant_s'])
        if self.correction_tau<=0 or self.dropout_leak_tau<=0:raise ValueError('invalid inertial velocity estimator configuration')

    def update(self,position_xy:np.ndarray|None,dt_s:float,acceleration_world_xy:np.ndarray|None=None)->np.ndarray:
        dt=float(dt_s)
        if dt<=0:raise ValueError('dt_s must be positive')
        acceleration=np.zeros(2) if acceleration_world_xy is None else np.asarray(acceleration_world_xy,dtype=float)
        if acceleration.shape!=(2,) or not np.isfinite(acceleration).all():raise ValueError('acceleration_world_xy must contain two finite coordinates')
        self.elapsed_s+=dt;predicted=self.velocity_world_xy+acceleration*dt
        speed=float(np.linalg.norm(predicted))
        if speed>self.maximum_speed:predicted*=self.maximum_speed/speed
        if position_xy is None:
            self.velocity_world_xy=predicted*np.exp(-dt/self.dropout_leak_tau);self.needs_reacquisition=True
            return self.velocity_world_xy.copy()
        position=np.asarray(position_xy,dtype=float)
        if position.shape!=(2,) or not np.isfinite(position).all():raise ValueError('position_xy must contain two finite coordinates')
        if self.previous_position is None or self.needs_reacquisition:
            self.previous_position=position.copy();self.needs_reacquisition=False;self.position_history.clear();self.position_history.append((self.elapsed_s,position.copy()));self.velocity_world_xy=predicted
            return self.velocity_world_xy.copy()
        self.position_history.append((self.elapsed_s,position.copy()))
        while len(self.position_history)>2 and self.elapsed_s-self.position_history[1][0]>=self.window:self.position_history.popleft()
        oldest_time,oldest_position=self.position_history[0];span=self.elapsed_s-oldest_time;raw=(position-oldest_position)/max(dt,span);self.previous_position=position.copy()
        raw_speed=float(np.linalg.norm(raw))
        if raw_speed>self.maximum_speed:raw*=self.maximum_speed/raw_speed
        alpha=1-np.exp(-dt/self.correction_tau);self.velocity_world_xy=predicted+alpha*(raw-predicted)
        return self.velocity_world_xy.copy()
