from pathlib import Path

from flydrone.visualization.pfl3_viewer import build_payload, generate


ROOT = Path(__file__).resolve().parents[1]


def test_viewer_payload_maps_all_pfl3_skeletons():
    geometry, model = build_payload(ROOT)
    assert len(geometry) == 24
    assert len({item["rootId"] for item in geometry}) == 24
    assert all(item["points"] and item["edges"] for item in geometry)
    assert len(model["headingPreferredDeg"]) == 24
    assert len(model["connectome"]["deltaWeights"]) == 24
    assert len(model["connectome"]["fc2Weights"]) == 24


def test_generated_viewer_has_embedded_data(tmp_path):
    output = generate(ROOT, tmp_path / "viewer.html")
    text = output.read_text(encoding="utf-8")
    assert "__GEOMETRY_JSON__" not in text
    assert "Actividad PFL3" in text
    assert "720575" in text
