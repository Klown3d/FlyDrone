from flydrone.morphology.functional_map import GOAL_DEG, HEADING_DEG


def test_published_angle_tables_have_one_value_per_functional_column():
    assert len(GOAL_DEG) == 12
    assert set(HEADING_DEG) == {"left", "right"}
    assert all(len(values) == 12 for values in HEADING_DEG.values())
    assert all(-180 <= value <= 180 for value in GOAL_DEG)
    assert all(-180 <= value <= 180 for values in HEADING_DEG.values() for value in values)
