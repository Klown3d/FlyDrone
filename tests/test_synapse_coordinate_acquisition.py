from pathlib import Path

import pandas as pd

from flydrone.data.acquire_synapse_coordinates import select_internal_pb, selected_root_ids


ROOT = Path(__file__).resolve().parents[1]


def test_selected_root_ids_uses_pinned_circuit_nodes() -> None:
    ids = selected_root_ids(ROOT / "data/processed/fafb783_epg_delta7_fc2_pfl3/nodes.csv")
    assert len(ids) == 195
    assert ids == sorted(set(ids))


def test_select_internal_pb_filters_partner_and_neuropil() -> None:
    frame = pd.DataFrame({
        "id": [1, 2, 3],
        "pre_pt_root_id": [10, 10, 99],
        "post_pt_root_id": [20, 20, 20],
        "neuropil": ["PB", "FB", "PB"],
    })
    selected = select_internal_pb(frame, {10, 20})
    assert selected["id"].tolist() == [1]
