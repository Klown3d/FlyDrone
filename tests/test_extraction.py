"""Synthetic fixtures only: never used as FlyWire experimental data."""
import pytest

from flydrone.connectome.extract import aggregate_pairs, graph_stats, select_nodes
from flydrone.data.acquire import file_hash, verify


def test_neuropils_aggregate_before_threshold_and_preserve_direction():
    rows = [
        {"pre_pt_root_id": "720575940614297640", "post_pt_root_id": "720575940634647732", "neuropil": "PB", "syn_count": 2},
        {"pre_pt_root_id": "720575940614297640", "post_pt_root_id": "720575940634647732", "neuropil": "FB", "syn_count": 3},
        {"pre_pt_root_id": "720575940634647732", "post_pt_root_id": "720575940614297640", "neuropil": "PB", "syn_count": 1},
    ]
    pairs = aggregate_pairs(rows)
    ids = ["720575940614297640", "720575940634647732", "720575940000000001"]
    stats = graph_stats(ids, pairs, 5)
    assert stats["edges"] == 1
    assert stats["synapses"] == 5
    assert stats["per_node"][ids[0]]["out_degree"] == 1
    assert stats["per_node"][ids[1]]["in_degree"] == 1
    assert stats["isolates"] == [ids[2]]
    assert graph_stats(ids, pairs, 1)["reciprocal_pairs_count"] == 1


def test_duplicate_pair_region_is_error():
    row = {"pre_pt_root_id": "1", "post_pt_root_id": "2", "neuropil": "PB", "syn_count": 3}
    with pytest.raises(ValueError, match="Duplicate"):
        aggregate_pairs([row, row.copy()])


@pytest.mark.parametrize("count", [0, -1, 1.5, True])
def test_invalid_counts_rejected(count):
    with pytest.raises(ValueError, match="positive integers"):
        aggregate_pairs([{"pre_pt_root_id": "1", "post_pt_root_id": "2", "neuropil": "PB", "syn_count": count}])


def test_exact_type_selection_no_prefix_expansion():
    annotations = {"10": {"root_id": "10", "hemibrain_type": "EPG"},
                   "11": {"root_id": "11", "hemibrain_type": "EPGt"}}
    cfg = {"type_column": "hemibrain_type", "types": {"EPG": "EPG"}}
    assert list(select_nodes(annotations, cfg)) == ["10"]
    cfg["types"]["PFL3"] = "PFL3"
    with pytest.raises(ValueError, match="absent"):
        select_nodes(annotations, cfg)


def test_corrupt_download_and_git_blob_hash(tmp_path):
    path = tmp_path / "synthetic.txt"
    path.write_bytes(b"test content\n")
    assert file_hash(path, "git-blob-sha1") == "d670460b4b4aece5915caf5c68d12f560a9fe3e4"
    artifact = {"published_size_bytes": path.stat().st_size,
                "published_checksum": {"algorithm": "sha256", "value": file_hash(path)}}
    verify(path, artifact)
    path.write_bytes(b"Test content\n")
    with pytest.raises(ValueError, match="checksum"):
        verify(path, artifact)
