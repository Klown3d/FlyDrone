from pathlib import Path

import numpy as np

from flydrone.neural.connectome_pfl2 import ConnectomeWeightedPFL2


ROOT = Path(__file__).parents[1]
CONFIG = ROOT / "configs/pfl2_model.yaml"


def test_pfl2_extraction_and_streams_are_complete():
    model = ConnectomeWeightedPFL2(ROOT, CONFIG)
    assert len(model.pfl2_ids) == 12
    assert model.delta_audit.contact_count == 1332
    assert model.fc2_audit.contact_count == 1177
    assert model.delta_audit.minimum_contacts_per_pfl2 > 0
    assert model.fc2_audit.minimum_contacts_per_pfl2 > 0


def test_pfl2_contact_model_activates_more_at_antigoal():
    model = ConnectomeWeightedPFL2(ROOT, CONFIG)
    for goal in np.deg2rad([-135, -45, 45, 135]):
        aligned = model.population_activity(goal, goal)
        antialigned = model.population_activity(goal + np.pi, goal)
        assert antialigned > aligned
        assert model.anti_goal_index(goal, goal) == 0.0
        assert np.isclose(model.anti_goal_index(goal + np.pi, goal), 1.0)


def test_pfl2_phase_inputs_are_concentrated_and_opposed():
    model = ConnectomeWeightedPFL2(ROOT, CONFIG)
    assert model.phase_audit["delta_resultant"].min() > 0.75
    assert model.phase_audit["fc2_resultant"].min() > 0.75
    assert model.phase_audit["delta_minus_fc2_deg"].abs().median() > 140.0
