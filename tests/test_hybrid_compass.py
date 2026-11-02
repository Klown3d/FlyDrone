from pathlib import Path
import numpy as np
from flydrone.neural.orientation_closed_loop import wrap
from flydrone.neural.phase_compass_estimator import HybridCompassEstimator

ROOT=Path(__file__).resolve().parents[1]


def test_hybrid_limits_neural_phase_error_during_cue_loss():
    estimator=HybridCompassEstimator(ROOT,Path('configs/hybrid_compass.yaml'),np.deg2rad(-30.0));truth=np.deg2rad(-30.0);dt=.02
    estimator.update(truth,0.,dt)
    for _ in range(200):
        rate=np.deg2rad(55.0);truth=float(wrap(truth+rate*dt));fused,confidence,_=estimator.update(None,rate,dt)
    fused_error=abs(float(wrap(fused-truth)));neural_error=abs(float(wrap(estimator.last_neural_heading-truth)))
    assert fused_error<=neural_error+1e-12 and estimator.last_neural_weight<=.25 and 0<=confidence<=1


def test_external_cue_reanchors_both_estimates():
    estimator=HybridCompassEstimator(ROOT,Path('configs/hybrid_compass.yaml'),0.)
    fused,confidence,_=estimator.update(np.deg2rad(83.),np.deg2rad(10.),.02)
    assert abs(np.rad2deg(wrap(fused-np.deg2rad(83.))))<1e-9 and confidence==1.0


def test_v5_development_config_keeps_neural_state_in_the_fusion():
    estimator=HybridCompassEstimator(
        ROOT,Path('configs/hybrid_compass_v5_development.yaml'),np.deg2rad(12.0)
    )
    estimator.update(np.deg2rad(12.0),0.0,.02)
    _,confidence,_=estimator.update(None,np.deg2rad(30.0),.02)
    assert 0.0 < estimator.maximum_neural_weight <= 0.25
    assert 0.0 <= estimator.last_neural_weight <= estimator.maximum_neural_weight
    assert 0.0 <= confidence <= 1.0
