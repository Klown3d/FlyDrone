"""End-to-end synthetic input only; no network or production data required."""
import csv
import json

import numpy as np
import pyarrow as pa
import pyarrow.feather as feather
import pytest
import yaml

from flydrone.connectome.extract import extract, NT
from flydrone.data.acquire import file_hash, save_json


def test_pipeline_provenance_boundary_and_repeatability(tmp_path):
    root = tmp_path
    raw = root / "data/raw"
    raw.mkdir(parents=True)
    a, b, c = 720575940000000001, 720575940000000002, 720575940000000003
    fields = ["root_id", "hemibrain_type", "cell_type", "side", "status", "top_nt"]
    ann = raw / "Supplemental_file1_neuron_annotations.tsv"
    with ann.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows([dict(zip(fields, [a, "EPG", "", "left", "", "acetylcholine"])),
                         dict(zip(fields, [b, "PFL3", "", "right", "", "acetylcholine"]))])
    np.save(raw / "proofread_root_ids_783.npy", np.array([a, b, c], dtype=np.int64))
    rows = [
        {"pre_pt_root_id": a, "post_pt_root_id": b, "neuropil": "PB", "syn_count": 2},
        {"pre_pt_root_id": a, "post_pt_root_id": b, "neuropil": "FB", "syn_count": 3},
        {"pre_pt_root_id": c, "post_pt_root_id": a, "neuropil": "PB", "syn_count": 10},
        {"pre_pt_root_id": b, "post_pt_root_id": c, "neuropil": "LAL_L", "syn_count": 20},
    ]
    for row in rows:
        row.update({nt: (1.0 if nt == "ach_avg" else 0.0) for nt in NT})
    feather.write_feather(pa.Table.from_pylist(rows), raw / "proofread_connections_783.feather")
    artifacts = [{"name": p.name, "local_path": p.relative_to(root).as_posix(),
                  "published_size_bytes": p.stat().st_size,
                  "published_checksum": {"algorithm": "sha256", "value": file_hash(p)},
                  "local_sha256": file_hash(p), "status": "downloaded_verified", "retrieved_at": "synthetic_fixture"} for p in sorted(raw.iterdir())]
    manifest = {"dataset": {"materialization_version": 783, "annotation_commit": "synthetic", "specimen_dataset": "FAFB"},
                "artifacts": artifacts, "required_citations": ["synthetic fixture, not FlyWire data"]}
    save_json(root / "data/manifest.json", manifest)
    cfg = {"dataset": "FAFB", "materialization_version": 783, "annotation_commit": "synthetic", "types": {"EPG": "EPG", "PFL3": "PFL3"},
           "type_column": "hemibrain_type", "excluded_related_types": {"EPGt": "excluded"},
           "minimum_pair_synapses": 1, "sensitivity_thresholds": [1, 5, 10], "neuropil_filter": None,
           "boundary_hops": 1, "output_dir": "data/processed/synthetic"}
    config_path = root / "config.yaml"
    config_path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    extract(root, config_path)
    out = root / cfg["output_dir"]
    report = json.loads((out / "circuit-report.json").read_text())
    assert report["graph"]["edges"] == 1
    assert report["graph"]["synapses"] == 5
    assert report["boundary_missing_annotations"] == 1
    assert report["boundary_synapses"] == {"incoming": 10, "outgoing": 20}
    assert report["threshold_sensitivity"][1]["edges"] == 1
    assert report["threshold_sensitivity"][2]["edges"] == 0
    with (out / "nodes.csv").open() as stream:
        nodes = {r["root_id"]: r for r in csv.DictReader(stream)}
    assert nodes[str(b)]["dominant_LAL_contact_side"] == "left"
    assert nodes[str(b)]["side"] == "right"  # soma is deliberately opposite
    assert float(nodes[str(a)]["excluded_input_fraction"]) == 1.0
    hashes = {p.name: file_hash(p) for p in out.glob("*.csv")}
    report_hash = file_hash(out / "circuit-report.json")
    extract(root, config_path)
    assert hashes == {p.name: file_hash(p) for p in out.glob("*.csv")}
    assert file_hash(out / "circuit-report.json") == report_hash
    assert not list(out.glob("*.metadata.json.metadata.json"))
    provenance = json.loads((out / "provenance.json").read_text())
    assert len(provenance["outputs"]) == 8
    ann.write_text(ann.read_text() + "corruption", encoding="utf-8")
    with pytest.raises(ValueError, match="Size mismatch"):
        extract(root, config_path)
