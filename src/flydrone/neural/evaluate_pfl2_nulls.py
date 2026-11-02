"""Compare the PFL2 contact map with phase-permuted connectivity nulls."""
from __future__ import annotations

from pathlib import Path
import argparse
import json

import numpy as np
import pandas as pd
import yaml

from flydrone.data.acquire import file_hash, save_json, utc_now
from flydrone.neural.connectome_pfl2 import ConnectomeWeightedPFL2


def _population(model: ConnectomeWeightedPFL2, heading: float, goal: float,
                delta_weights: np.ndarray, fc2_weights: np.ndarray) -> float:
    delta = np.cos(heading - model.base.delta_angles_rad)
    fc2 = np.cos(goal - model.base.fc2_angles_rad)
    drive = delta_weights @ delta + fc2_weights @ fc2
    return float(np.clip(np.maximum(0.0, drive) / 2.0, 0.0, 1.0).mean())


def _index(model: ConnectomeWeightedPFL2, heading: float, goal: float,
           delta_weights: np.ndarray, fc2_weights: np.ndarray) -> float:
    aligned = _population(model, goal, goal, delta_weights, fc2_weights)
    antialigned = _population(model, goal + np.pi, goal, delta_weights, fc2_weights)
    current = _population(model, heading, goal, delta_weights, fc2_weights)
    difference = antialigned - aligned
    if abs(difference) < 1e-12:
        return 0.0
    return float(np.clip((current - aligned) / difference, 0.0, 1.0))


def _score(model, goals, errors, delta_weights, fc2_weights) -> tuple[float, float, float]:
    observed = []
    expected = []
    for goal in goals:
        for error in errors:
            observed.append(_index(model, goal + error, goal, delta_weights, fc2_weights))
            expected.append((1.0 - np.cos(error)) / 2.0)
    observed = np.asarray(observed)
    expected = np.asarray(expected)
    correlation = float(np.corrcoef(observed, expected)[0, 1]) if np.std(observed) > 0 else 0.0
    mae = float(np.mean(np.abs(observed - expected)))
    direction_accuracy = float(np.mean((observed >= 0.5) == (expected >= 0.5)))
    return correlation, mae, direction_accuracy


def run(root: Path, config_path: Path) -> None:
    c = yaml.safe_load((root / config_path).read_text(encoding="utf-8"))
    model = ConnectomeWeightedPFL2(root, root / c["pfl2_model_config"])
    goals = np.deg2rad(c["goals_deg"])
    errors = np.deg2rad(c["relative_errors_deg"])
    rows = []
    correlation, mae, accuracy = _score(model, goals, errors, model.delta_weights, model.fc2_weights)
    rows.append({"condition": "flywire", "seed": None, "correlation": correlation,
                 "mean_absolute_error": mae, "large_error_classification_accuracy": accuracy})
    for seed in c["null_seeds"]:
        rng = np.random.default_rng(seed)
        delta = model.delta_weights[:, rng.permutation(model.delta_weights.shape[1])]
        fc2 = model.fc2_weights[:, rng.permutation(model.fc2_weights.shape[1])]
        correlation, mae, accuracy = _score(model, goals, errors, delta, fc2)
        rows.append({"condition": "phase_permuted", "seed": seed, "correlation": correlation,
                     "mean_absolute_error": mae, "large_error_classification_accuracy": accuracy})
    frame = pd.DataFrame(rows)
    output = root / c["output"]
    output.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output / "scores.csv", index=False)
    flywire = frame.iloc[0]
    nulls = frame.iloc[1:]
    report = {
        "created_at": utc_now(), "dataset": "FAFB", "materialization_version": 783,
        "claim": "Post-prospective computational attribution: phase-column permutations preserve every contact matrix value and row total but break presynaptic phase identity.",
        "configuration": config_path.as_posix(), "configuration_sha256": file_hash(root / config_path),
        "source_sha256": file_hash(Path(__file__)), "null_count": len(nulls),
        "flywire": {"correlation": float(flywire["correlation"]), "mean_absolute_error": float(flywire["mean_absolute_error"]), "large_error_classification_accuracy": float(flywire["large_error_classification_accuracy"])},
        "null_distribution": {
            "maximum_correlation": float(nulls["correlation"].max()),
            "median_correlation": float(nulls["correlation"].median()),
            "minimum_mean_absolute_error": float(nulls["mean_absolute_error"].min()),
            "median_mean_absolute_error": float(nulls["mean_absolute_error"].median()),
        },
        "nulls_matching_or_exceeding_flywire_correlation": int((nulls["correlation"] >= flywire["correlation"]).sum()),
        "empirical_p_upper_bound": float((1 + (nulls["correlation"] >= flywire["correlation"]).sum()) / (1 + len(nulls))),
    }
    save_json(output / "report.json", report)
    manifest_path = root / "data/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest[c["manifest_key"]] = {"status": "post_prospective_phase_permutation_control_completed", "report": (output / "report.json").relative_to(root).as_posix(), "report_sha256": file_hash(output / "report.json"), "null_count": len(nulls)}
    save_json(manifest_path, manifest)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/pfl2_connectivity_nulls.yaml"))
    run(Path.cwd(), parser.parse_args().config)
