from pathlib import Path

from flydrone.neural.travel_direction_audit import audit


ROOT = Path(__file__).parents[1]


def test_travel_direction_population_counts_and_convergence():
    report = audit(ROOT, Path("configs/data_travel_direction.yaml"))
    assert report["counts"]["PFNd"] == 40
    assert report["counts"]["PFNv"] == 21
    assert report["counts"]["hDeltaB"] == 18
    routes = {(r["pre_type"], r["post_type"]): r for r in report["routes"]}
    assert routes[("PFNd", "hDeltaB")]["synapses"] == 15487
    assert routes[("PFNv", "hDeltaB")]["synapses"] == 2720
    assert routes[("PFNd", "hDeltaB")]["postsynaptic_coverage"] == 1.0
    assert routes[("PFNv", "hDeltaB")]["postsynaptic_coverage"] == 1.0


def test_velocity_and_heading_input_routes_are_present():
    report = audit(ROOT, Path("configs/data_travel_direction.yaml"))
    routes = {(r["pre_type"], r["post_type"]): r for r in report["routes"]}
    for route in (("Delta7", "PFNd"), ("Delta7", "PFNv"), ("LNO1", "PFNv"),
                  ("LNO2", "PFNd"), ("IbSpsP", "PFNd")):
        assert routes[route]["synapses"] > 0
