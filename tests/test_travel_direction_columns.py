from pathlib import Path

from flydrone.neural.travel_direction_columns import infer


ROOT = Path(__file__).parents[1]


def test_pfn_and_hdelta_geometric_columns_match_published_counts():
    frame, report = infer(ROOT, Path("configs/data_travel_direction.yaml"))
    for cell_type in ("PFNd", "PFNv"):
        assert frame.loc[frame["selected_type"].eq(cell_type), "fb_output_column"].nunique() == 8
    hdelta = frame.loc[frame["selected_type"].eq("hDeltaB")]
    assert hdelta["fb_axon_column"].nunique() == 12
    assert hdelta["fb_dendrite_column"].nunique() == 12
    assert report["hdeltaB_half_width_offset"]["median_offset_columns"] == 6.0
    assert report["hdeltaB_half_width_offset"]["fraction_within_one_column_of_half_width"] > 0.9


def test_every_pfn_has_contact_grounded_phase_and_output_column():
    frame, _ = infer(ROOT, Path("configs/data_travel_direction.yaml"))
    pfn = frame.loc[frame["selected_type"].isin(["PFNd", "PFNv"])]
    assert len(pfn) == 61
    assert pfn["fb_output_contacts_to_hdeltaB"].min() > 0
    assert pfn["delta7_input_contacts_pb"].min() > 0
    assert pfn["inherited_heading_phase_deg"].notna().all()
