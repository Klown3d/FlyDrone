from pathlib import Path
import numpy as np
from flydrone.simulation.drift_confidence import DriftConfidenceGovernor


ROOT=Path(__file__).parents[1]


def test_confidence_falls_fast_and_recovers_slowly():
    governor=DriftConfidenceGovernor(ROOT/'configs/drift_confidence.yaml');correction=np.array([1.,0.])
    _,lost=governor.update(correction,.5,False,0.,0.,0.,0.,.02)
    after_loss=lost['confidence']
    _,recovered=governor.update(correction,0.,True,0.,0.,0.,0.,.02)
    assert after_loss<1.0
    assert recovered['confidence']>after_loss
    assert recovered['confidence']<0.95


def test_output_rate_and_magnitude_are_limited():
    governor=DriftConfidenceGovernor(ROOT/'configs/drift_confidence.yaml')
    output,_=governor.update(np.array([100.,0.]),0.,True,0.,0.,0.,0.,.02)
    assert np.linalg.norm(output)<=.02*governor.maximum_rate+1e-12
    for _ in range(200):output,_=governor.update(np.array([100.,0.]),0.,True,0.,0.,0.,0.,.02)
    assert np.linalg.norm(output)<=governor.maximum_acceleration+1e-12


def test_heading_and_direction_disagreement_reduce_raw_confidence():
    governor=DriftConfidenceGovernor(ROOT/'configs/drift_confidence.yaml');correction=np.array([.2,0.])
    _,aligned=governor.update(correction,0.,True,0.,0.,0.,0.,.02)
    governor.reset();_,disagreed=governor.update(correction,0.,True,np.pi/2,0.,np.pi/2,0.,.02)
    assert disagreed['raw_confidence']<aligned['raw_confidence']
