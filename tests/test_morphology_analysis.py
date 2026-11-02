import numpy as np

from flydrone.morphology.analyze import epg_pb_columns, optimal_1d_clusters


def test_optimal_clusters_are_ordered_and_stable() -> None:
    values = np.array([10.2, 0.1, 20.1, 9.9, 0.0, 19.8])
    assert optimal_1d_clusters(values, 3).tolist() == [2, 1, 3, 2, 1, 3]


def test_epg_pb_columns_follow_a_curved_16_cluster_arc() -> None:
    # The two ends overlap in x but curve toward larger y, as in the FAFB PB.
    center_x = np.linspace(-7.0, 7.0, 16)
    centers = np.column_stack((center_x, 0.12 * center_x**2, np.zeros(16)))
    points = np.vstack([center + [0.01, 0.0, 0.0] for center in centers for _ in range(2)])
    labels = epg_pb_columns(points)
    assert sorted(set(labels)) == list(range(2, 18))
    assert labels[0] == labels[1] == 2
    assert labels[-1] == labels[-2] == 17
