import numpy as np

from flydrone.visualization.desktop import rate_activity_color


def test_pfl3_rate_palette_separates_low_medium_and_high_activity():
    low = np.array(rate_activity_color(0.0, 40.0)[:3])
    middle = np.array(rate_activity_color(20.0, 40.0)[:3])
    high = np.array(rate_activity_color(40.0, 40.0)[:3])

    assert low[1] > low[0]
    assert middle[0] > low[0] and middle[1] > low[1]
    assert high[0] > high[1]


def test_pfl3_rate_palette_clips_out_of_range_values():
    assert rate_activity_color(-1.0, 40.0) == rate_activity_color(0.0, 40.0)
    assert rate_activity_color(80.0, 40.0) == rate_activity_color(40.0, 40.0)
