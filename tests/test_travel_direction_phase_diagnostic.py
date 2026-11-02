from pathlib import Path

from flydrone.neural.travel_direction_phase_diagnostic import diagnose


ROOT = Path(__file__).parents[1]


def test_naive_hdelta_phase_shortcut_is_rejected():
    report = diagnose(ROOT, Path("configs/data_travel_direction.yaml"))
    assert report["pfn_phase_resultants"]["PFNd"]["median"] > 0.9
    assert report["pfn_phase_resultants"]["PFNv"]["median"] > 0.9
    assert report["naive_hdelta_input_phase_resultants"]["PFNd"]["median"] < 0.25
    assert report["naive_single_phase_mapping_accepted"] is False
