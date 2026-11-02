from pathlib import Path
from flydrone.simulation.sensor_confidence import SensorConfidenceGovernor

ROOT=Path(__file__).resolve().parents[1]


def test_missing_velocity_reduces_but_does_not_reverse_advance():
    governor=SensorConfidenceGovernor(ROOT/'configs/sensor_confidence.yaml')
    for _ in range(100):fraction=governor.update(1.0,False,.02)
    assert .35<=fraction<.37


def test_confidence_recovers_smoothly():
    governor=SensorConfidenceGovernor(ROOT/'configs/sensor_confidence.yaml');governor.fraction=.35
    first=governor.update(1.0,True,.02)
    for _ in range(200):last=governor.update(1.0,True,.02)
    assert .35<first<last<=1.0 and last>.99
