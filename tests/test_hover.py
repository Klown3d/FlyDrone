from pathlib import Path
import numpy as np
import yaml
from flydrone.simulation.hover import HoverState, update


def test_hover_converges_without_clipping_altitude_to_target():
    c=yaml.safe_load((Path(__file__).resolve().parents[1]/'configs/desktop.yaml').read_text())
    state=HoverState(altitude=.7)
    for _ in range(1000):
        thrust=update(state,0,c,.15,.02)
        assert 0<=thrust<=c['maximum_thrust_n']
        assert state.altitude>0
    assert abs(state.altitude-c['target_altitude_m'])<1e-6
    assert abs(state.vertical_speed)<1e-6


def test_hover_yaw_turn_and_hover_equilibrium():
    c=yaml.safe_load((Path(__file__).resolve().parents[1]/'configs/desktop.yaml').read_text())
    state=HoverState(altitude=c['target_altitude_m'],heading=0)
    for _ in range(100):update(state,1,c,.15,.02)
    assert 1.7<state.heading<2
    assert np.isclose(state.altitude,c['target_altitude_m'])


def test_batch_plant_matches_individual_episode_updates():
    c=yaml.safe_load((Path(__file__).resolve().parents[1]/'configs/desktop.yaml').read_text())
    batch=HoverState(altitude=np.array([.7,3.]),vertical_speed=np.zeros(2),heading=np.array([0.,1.]),yaw_rate=np.zeros(2))
    individuals=[HoverState(altitude=.7,heading=0.),HoverState(altitude=3.,heading=1.)]
    for _ in range(100):
        update(batch,np.array([.5,-.3]),c,.15,.02)
        for state,command in zip(individuals,[.5,-.3]):update(state,command,c,.15,.02)
    for attribute in ('altitude','vertical_speed','heading','yaw_rate'):
        np.testing.assert_allclose(getattr(batch,attribute),[getattr(s,attribute) for s in individuals],atol=1e-14)
