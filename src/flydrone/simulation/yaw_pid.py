"""Conventional stateful PID baseline for wrapped yaw errors."""
from dataclasses import dataclass
import numpy as np
from flydrone.neural.orientation_closed_loop import wrap


@dataclass
class YawPID:
    """PID yaw-rate controller with derivative filtering and integral limiting."""

    kp: float
    ki: float
    kd: float
    maximum_yaw_rate_rad_s: float
    integral_limit_rad_s: float
    derivative_filter_tau_s: float
    integral_error_rad_s: float = 0.0
    previous_error_rad: float | None = None
    derivative_rad_s: float = 0.0

    def update(self, heading_rad: float, goal_rad: float, dt_s: float) -> float:
        if dt_s <= 0:
            raise ValueError('dt_s must be positive')
        error = float(wrap(goal_rad-heading_rad))
        candidate = float(np.clip(
            self.integral_error_rad_s+error*dt_s,
            -self.integral_limit_rad_s,
            self.integral_limit_rad_s,
        ))
        if self.previous_error_rad is None:
            raw_derivative = 0.0
        else:
            raw_derivative = float(wrap(error-self.previous_error_rad))/dt_s
        alpha = dt_s/(self.derivative_filter_tau_s+dt_s)
        self.derivative_rad_s += alpha*(raw_derivative-self.derivative_rad_s)
        unconstrained = self.kp*error+self.ki*candidate+self.kd*self.derivative_rad_s
        output = float(np.clip(
            unconstrained,
            -self.maximum_yaw_rate_rad_s,
            self.maximum_yaw_rate_rad_s,
        ))
        # Conditional integration avoids accumulating error farther into saturation.
        if output == unconstrained or np.sign(error) != np.sign(unconstrained):
            self.integral_error_rad_s = candidate
        self.previous_error_rad = error
        return output


def from_config(config: dict) -> YawPID:
    return YawPID(
        kp=float(config['kp_per_s']),
        ki=float(config['ki_per_s2']),
        kd=float(config['kd']),
        maximum_yaw_rate_rad_s=float(config['maximum_yaw_rate_rad_s']),
        integral_limit_rad_s=float(config['integral_limit_rad_s']),
        derivative_filter_tau_s=float(config['derivative_filter_tau_s']),
    )
