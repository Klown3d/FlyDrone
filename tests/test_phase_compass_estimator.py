from pathlib import Path

import numpy as np

from flydrone.neural.orientation_closed_loop import wrap
from flydrone.neural.phase_compass_estimator import PhaseCompassEstimator


ROOT = Path(__file__).resolve().parents[1]
CONFIG = Path("configs/phase_compass_dynamics_v2.yaml")
REGULARIZED_CONFIG = Path("configs/phase_compass_symmetry_regularized_v3.yaml")
CROSS_COMPARTMENT_CONFIG = Path("configs/phase_compass_cross_compartment_v4.yaml")


def test_frozen_compass_persists_in_dark():
    estimator = PhaseCompassEstimator(ROOT, CONFIG, np.deg2rad(37.0))
    start, _, _ = estimator.update(np.deg2rad(37.0), 0.0, 0.02)
    for _ in range(150):
        phase, resultant, contrast = estimator.update(None, 0.0, 0.02)
    assert abs(np.rad2deg(wrap(phase - start))) < 1.0
    assert resultant > 0.2 and contrast > 0.05


def test_frozen_compass_tracks_positive_turn_in_dark():
    estimator = PhaseCompassEstimator(ROOT, CONFIG, np.deg2rad(-20.0))
    start, _, _ = estimator.update(np.deg2rad(-20.0), 0.0, 0.02)
    for _ in range(50):
        phase, _, _ = estimator.update(None, np.deg2rad(60.0), 0.02)
    error = abs(np.rad2deg(wrap(phase - (start + np.deg2rad(60.0)))))
    assert error < 10.0


def test_external_cue_calibrates_arbitrary_internal_phase_offset():
    heading = np.deg2rad(63.0)
    estimator = PhaseCompassEstimator(ROOT, CONFIG, heading)
    decoded, _, _ = estimator.update(heading, 0.0, 0.02)
    assert abs(np.rad2deg(wrap(decoded - heading))) < 1e-9


def test_regularized_model_updates_in_both_directions_monotonically():
    displacements = []
    for rate in (-75.0, -45.0, -15.0, 15.0, 45.0, 75.0):
        estimator = PhaseCompassEstimator(ROOT, REGULARIZED_CONFIG, np.deg2rad(17.0))
        start, _, _ = estimator.update(np.deg2rad(17.0), 0.0, 0.02)
        for _ in range(50):
            phase, resultant, _ = estimator.update(None, np.deg2rad(rate), 0.02)
        displacements.append(np.rad2deg(wrap(phase - start)))
        assert np.sign(displacements[-1]) == np.sign(rate) and resultant > 0.2
    assert np.all(np.diff(displacements) > 0)


def test_cross_compartment_pen_a_model_tracks_both_directions():
    for rate in (-75.0,-45.0,-15.0,15.0,45.0,75.0):
        estimator=PhaseCompassEstimator(ROOT,CROSS_COMPARTMENT_CONFIG,np.deg2rad(-41.0))
        start,_,_=estimator.update(np.deg2rad(-41.0),0.0,0.02)
        for _ in range(50):phase,resultant,_=estimator.update(None,np.deg2rad(rate),0.02)
        error=abs(np.rad2deg(wrap(phase-start-np.deg2rad(rate))))
        assert error<20 and resultant>0.2
