"""Replay pairing, preserved hashes and time indexing must not distort evidence."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from flydrone.data.acquire import file_hash
from flydrone.visualization.gate_replay_data import GateArchive, SavedFlight


def test_replay_uses_last_sample_and_clamps_to_recorded_time():
    flight = SavedFlight("test", {}, pd.DataFrame({"time_s": [0., .02, .04]}), Path("unused"))
    assert [flight.index_at(t) for t in [-1., 0., .019, .02, .039, 10.]] == [0, 0, 0, 1, 1, 2]


def test_gate_pairs_by_case_and_rejects_changed_preserved_trace(tmp_path):
    config = {"output": "results/gate", "steering_null_intact_condition": {"name": "intact"}}
    configs = tmp_path / "configs"
    configs.mkdir()
    (configs / "quadrotor_integrated_v4_epg_delta7_null_prospective.yaml").write_text(yaml.safe_dump(config))
    folder = tmp_path / "results/gate"
    traces = folder / "traces"
    traces.mkdir(parents=True)
    rows = [{"controller": name, "scenario": "paired", "target_bearing_deg": target,
             "initial_relative_heading_deg": 15., "success": True}
            for name in ("intact", "null_1") for target in (10., 20.)]
    pd.DataFrame(rows).to_csv(folder / "episodes.csv", index=False)
    columns = np.array(["time_s", "x_m", "y_m", "z_m", "yaw_rad", "observed_yaw_rad", "goal_rad"])
    for name in ("intact", "null_1"):
        np.savez(traces / f"{name}__paired__00.npz", columns=columns, values=np.array([[0., 0., 0., 1., 0., 0., 0.]]))
    manifest_path = tmp_path / "archive/integrated_v4_epg_delta7_null/preservation-manifest.json"
    manifest_path.parent.mkdir(parents=True)
    hashes = {p.relative_to(tmp_path).as_posix(): file_hash(p) for p in folder.rglob("*") if p.is_file()}
    manifest_path.write_text(json.dumps({"result_files_sha256": hashes}))
    archive = GateArchive(tmp_path, "EPG-Delta7")
    assert archive.paired_cases("null_1") == [("paired", 10., 15.)]
    flight = archive.load("null_1", archive.paired_cases("null_1")[0])
    assert flight.episode["target_bearing_deg"] == 10.
    flight.path.write_bytes(b"changed")
    with pytest.raises(ValueError, match="hash mismatch"):
        archive.load("null_1", archive.paired_cases("null_1")[0])
