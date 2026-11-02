from __future__ import annotations

import pandas as pd

from flydrone.neural.evaluate_travel_direction_prospective import summarize


def test_summarize_circular_errors() -> None:
    frame = pd.DataFrame({"absolute_error_deg": [1.0, 3.0, 5.0, 50.0], "resultant": [0.4, 0.5, 0.6, 0.7]})
    result = summarize(frame)
    assert result["median_absolute_error_deg"] == 4.0
    assert result["maximum_absolute_error_deg"] == 50.0
    assert result["within_45deg_fraction"] == 0.75
    assert result["minimum_resultant"] == 0.4
