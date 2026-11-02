import numpy as np
from flydrone.simulation.yaw_pid import YawPID


def controller(**overrides):
    values=dict(kp=1.,ki=.1,kd=.1,maximum_yaw_rate_rad_s=1.5,
                integral_limit_rad_s=.5,derivative_filter_tau_s=.1)
    values.update(overrides)
    return YawPID(**values)


def test_pid_takes_short_wrapped_turn_across_pi_boundary():
    pid=controller(ki=0.,kd=0.)
    output=pid.update(np.deg2rad(179),np.deg2rad(-179),.02)
    assert 0 < output < np.deg2rad(3)


def test_pid_clamps_output_and_prevents_integral_windup():
    pid=controller(kp=10.,ki=2.,kd=0.,maximum_yaw_rate_rad_s=.4)
    for _ in range(100):assert pid.update(0.,np.pi/2,.02)==.4
    assert pid.integral_error_rad_s==0.


def test_pid_derivative_has_no_first_sample_kick_and_is_filtered():
    pid=controller(kp=0.,ki=0.,kd=1.)
    assert pid.update(0.,1.,.02)==0.
    output=pid.update(.1,1.,.02)
    assert -1.5 < output < 0.


def test_pid_rejects_nonpositive_timestep():
    pid=controller()
    try:pid.update(0.,0.,0.)
    except ValueError:pass
    else:raise AssertionError('nonpositive timestep was accepted')
