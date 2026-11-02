"""Paired analysis of the integrated PFN-to-hDeltaB rewiring nulls."""
from __future__ import annotations

from pathlib import Path
import argparse
import json
import math

import numpy as np
import pandas as pd

from flydrone.data.acquire import file_hash, save_json, utc_now


KEY = ["scenario", "target_bearing_deg", "initial_relative_heading_deg"]


def bootstrap_median_difference(values: np.ndarray, seed: int = 41027,
                                samples: int = 20_000) -> list[float]:
    """Paired bootstrap interval for the median of null-minus-intact values."""
    values = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(values), size=(samples, len(values)))
    boot = np.median(values[indices], axis=1)
    return [float(v) for v in np.quantile(boot, [0.025, 0.975])]


def analyze(results_dir: Path) -> dict:
    episodes_path = results_dir / "episodes.csv"
    frame = pd.read_csv(episodes_path)
    intact = frame.loc[frame.controller.eq("flywire_hdelta_intact")].set_index(KEY)
    null_names = sorted(name for name in frame.controller.unique()
                        if str(name).startswith("null_rewire_"))
    contrasts = []
    for offset, name in enumerate(null_names):
        null = frame.loc[frame.controller.eq(name)].set_index(KEY).loc[intact.index]
        intact_success = intact.success.astype(bool).to_numpy()
        null_success = null.success.astype(bool).to_numpy()
        intact_only = int(np.sum(intact_success & ~null_success))
        null_only = int(np.sum(~intact_success & null_success))
        discordant = intact_only + null_only
        # With all discordant pairs favoring intact, this is the exact one-sided
        # sign probability. The general tail is computed for completeness.
        probability = sum(math.comb(discordant, k) for k in range(null_only + 1)) / 2**discordant if discordant else 1.0
        cross_track_difference = (null.maximum_absolute_cross_track_m - intact.maximum_absolute_cross_track_m).to_numpy(float)
        contrast = {
            "null_condition": name,
            "paired_episodes": int(len(intact)),
            "intact_successes": int(intact_success.sum()),
            "null_successes": int(null_success.sum()),
            "success_advantage_percentage_points": float(100 * (intact_success.mean() - null_success.mean())),
            "discordant_intact_only": intact_only,
            "discordant_null_only": null_only,
            "exact_one_sided_p_development_only": float(probability),
            "median_cross_track_increase_m": float(np.median(cross_track_difference)),
            "cross_track_increase_bootstrap_95pct_m": bootstrap_median_difference(cross_track_difference, 51027 + offset),
        }
        if "median_decoded_direction_error_deg" in frame.columns:
            direction_difference = (
                null.median_decoded_direction_error_deg
                - intact.median_decoded_direction_error_deg
            ).to_numpy(float)
            contrast.update({
                "median_direction_error_increase_deg": float(np.median(direction_difference)),
                "direction_error_increase_bootstrap_95pct_deg": bootstrap_median_difference(direction_difference, 41027 + offset),
            })
        contrasts.append(contrast)
    null_successes = [item["null_successes"] for item in contrasts]
    at_least_intact = sum(value >= int(intact.success.sum()) for value in null_successes)
    report = {
        "created_at": utc_now(),
        "status": "development_only_not_confirmatory",
        "claim": "Paired computational attribution diagnostic. Rewired matrices preserve PFN-to-hDeltaB binary row and column degrees and each hDeltaB row weight multiset. Reused development scenarios prohibit confirmatory inference.",
        "episodes_sha256": file_hash(episodes_path),
        "intact_successes": int(intact.success.sum()),
        "intact_episodes": int(len(intact)),
        "null_seed_count": len(contrasts),
        "null_successes_range": [int(min(null_successes)), int(max(null_successes))],
        "null_successes": null_successes,
        "fraction_nulls_below_intact": float(np.mean(np.asarray(null_successes) < int(intact.success.sum()))),
        "empirical_rank_p_greater_equal_with_plus_one_correction": float((at_least_intact + 1) / (len(null_successes) + 1)),
        "contrasts": contrasts,
        "interpretation_limit": "Five development rewiring seeds are insufficient to characterize the null distribution; one null tied intact success. Prospective unseen scenarios and at least 19 null seeds remain required.",
    }
    save_json(results_dir / "paired_null_analysis.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results_dir", type=Path)
    print(json.dumps(analyze(parser.parse_args().results_dir), indent=2))
