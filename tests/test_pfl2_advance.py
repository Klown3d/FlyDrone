from pathlib import Path
import numpy as np
from flydrone.neural.pfl2_advance import PFL2AdvanceController

ROOT=Path(__file__).resolve().parents[1]


def controller():return PFL2AdvanceController(ROOT/'configs/pfl2_advance.yaml')


def test_speed_fraction_decreases_monotonically() -> None:
    values=[controller().speed_fraction(x) for x in np.linspace(0,1,21)]
    assert values[0]==1 and values[-1]==0
    assert np.all(np.diff(values)<=0)


def test_distance_cap_remains_conventional() -> None:
    speed,fraction=controller().desired_speed(.2,0.,.8,.6)
    assert np.isclose(speed,.12) and fraction==1


def test_antigoal_stops_advance() -> None:
    speed,fraction=controller().desired_speed(4.,1.,.8,.6)
    assert speed==0 and fraction==0
