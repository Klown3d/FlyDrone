from pathlib import Path
import numpy as np
from flydrone.simulation.landmark_heading_sensor import LandmarkHeadingSensor,wrap

ROOT=Path(__file__).resolve().parents[1]


def test_ideal_landmark_recovers_heading_across_wrap() -> None:
    sensor=LandmarkHeadingSensor(ROOT/'configs/landmark_heading_sensor.yaml');rng=np.random.default_rng(1)
    for heading in np.deg2rad([-179,-90,0,90,179]):
        estimated,_=sensor.observe(heading,rng,False)
        assert abs(float(wrap(estimated-heading)))<1e-12


def test_noise_is_applied_to_bearing_not_hidden_heading() -> None:
    sensor=LandmarkHeadingSensor(ROOT/'configs/landmark_heading_sensor.yaml')
    ideal,b0=sensor.observe(.4,np.random.default_rng(7),False);noisy,b1=sensor.observe(.4,np.random.default_rng(7),True)
    assert not np.isclose(b0,b1)
    assert np.isclose(float(wrap((noisy-ideal)+(b1-b0))),0,atol=1e-12)
