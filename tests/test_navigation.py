from pathlib import Path
import numpy as np
import yaml
from flydrone.simulation.navigation import NavigationState, advance, goal_bearing, held_goal_bearing

ROOT=Path(__file__).resolve().parents[1]


def test_navigation_reaches_target_and_stops_without_position_snap():
    plant=yaml.safe_load((ROOT/'configs/desktop.yaml').read_text());nav=yaml.safe_load((ROOT/'configs/navigation.yaml').read_text())
    state=NavigationState(altitude=2.,heading=0.)
    for _ in range(1500):
        bearing=goal_bearing(state,(4.,0.));error=np.angle(np.exp(1j*(state.heading-bearing)))
        old=state.x;advance(state,float(-error),(4.,0.),plant,nav,.15,.02)
        assert abs(state.x-old)<=nav['maximum_speed_m_s']*.02+1e-10
    assert state.arrived
    assert abs(4-state.x)<nav['arrival_radius_m']
    assert np.hypot(state.vx,state.vy)<1e-6
    assert state.x!=4


def test_navigation_waits_for_alignment_and_altitude():
    plant=yaml.safe_load((ROOT/'configs/desktop.yaml').read_text());nav=yaml.safe_load((ROOT/'configs/navigation.yaml').read_text())
    for state in (NavigationState(altitude=2.,heading=np.pi),NavigationState(altitude=.7,heading=0.)):
        advance(state,0,(4.,0.),plant,nav,.15,.02)
        assert state.x==0 and state.y==0


def test_arrival_uses_observation_not_privileged_true_position():
    plant=yaml.safe_load((ROOT/'configs/desktop.yaml').read_text());nav=yaml.safe_load((ROOT/'configs/navigation.yaml').read_text())
    state=NavigationState(altitude=2.,heading=0.,x=0.)
    sensed=NavigationState(altitude=2.,heading=0.,x=4.)
    advance(state,0,(4.,0.),plant,nav,.15,.02,observation=sensed)
    assert state.arrived
    assert state.x==0


def test_confirmed_arrival_requires_time_and_can_resume():
    plant=yaml.safe_load((ROOT/'configs/desktop.yaml').read_text());nav=yaml.safe_load((ROOT/'configs/navigation_confirmed.yaml').read_text())
    state=NavigationState(altitude=2.,heading=0.,x=4.)
    sensed=NavigationState(altitude=2.,heading=0.,x=4.)
    for _ in range(19):
        advance(state,0,(4.,0.),plant,nav,.15,.02,observation=sensed)
        assert not state.arrived
    advance(state,0,(4.,0.),plant,nav,.15,.02,observation=sensed)
    assert state.arrived
    sensed.x=0.
    for _ in range(50):advance(state,0,(4.,0.),plant,nav,.15,.02,observation=sensed)
    assert not state.arrived


def test_brief_false_position_does_not_permanently_stop():
    plant=yaml.safe_load((ROOT/'configs/desktop.yaml').read_text());nav=yaml.safe_load((ROOT/'configs/navigation_confirmed.yaml').read_text())
    state=NavigationState(altitude=2.,heading=0.,x=0.)
    sensed=NavigationState(altitude=2.,heading=0.,x=0.)
    advance(state,0,(4.,0.),plant,nav,.15,.02,observation=sensed)
    sensed.x=4.
    advance(state,0,(4.,0.),plant,nav,.15,.02,observation=sensed)
    assert not state.arrived


def test_goal_bearing_is_held_near_target_and_released_after_departure():
    target=(4.,0.);previous=0.
    near_other_side=NavigationState(x=4.05,y=0.,heading=0.)
    bearing,held=held_goal_bearing(previous,False,near_other_side,target,.3,.4)
    assert held and bearing==previous
    hysteresis=NavigationState(x=4.35,y=0.,heading=0.)
    bearing,held=held_goal_bearing(bearing,held,hysteresis,target,.3,.4)
    assert held and bearing==previous
    displaced=NavigationState(x=4.5,y=0.,heading=0.)
    bearing,held=held_goal_bearing(bearing,held,displaced,target,.3,.4)
    assert not held and np.isclose(abs(bearing),np.pi)


def test_zero_confirmation_still_requires_arrival_evidence():
    plant=yaml.safe_load((ROOT/'configs/desktop.yaml').read_text());nav=yaml.safe_load((ROOT/'configs/navigation_confirmed.yaml').read_text())
    nav['arrival_confirm_s']=0.;state=NavigationState(altitude=2.,heading=0.,x=0.)
    advance(state,0,(4.,0.),plant,nav,.15,.02)
    assert not state.arrived
    at_target=NavigationState(altitude=2.,heading=0.,x=4.)
    advance(at_target,0,(4.,0.),plant,nav,.15,.02)
    assert at_target.arrived


def test_recovery_can_be_disabled_for_ablation():
    plant=yaml.safe_load((ROOT/'configs/desktop.yaml').read_text());nav=yaml.safe_load((ROOT/'configs/navigation_confirmed.yaml').read_text())
    nav['arrival_recovery_enabled']=False;state=NavigationState(altitude=2.,heading=0.,x=4.)
    for _ in range(20):advance(state,0,(4.,0.),plant,nav,.15,.02)
    assert state.arrived
    state.x=5.
    for _ in range(100):advance(state,0,(4.,0.),plant,nav,.15,.02)
    assert state.arrived
