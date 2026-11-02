"""Quantify how much circular symmetry regularization changes FlyWire transfers."""
from pathlib import Path
import json

import numpy as np
import pandas as pd
import yaml

from flydrone.data.acquire import file_hash, save_json, utc_now
from flydrone.neural.phase_velocity_validation import circularize


def matrix_metrics(original: np.ndarray, regularized: np.ndarray) -> dict:
    flat_a, flat_b = original.ravel(), regularized.ravel()
    correlation = float(np.corrcoef(flat_a, flat_b)[0, 1]) if np.std(flat_a) and np.std(flat_b) else 0.0
    denominator = float(np.linalg.norm(original))
    moved = float(np.abs(regularized - original).sum() / (2 * original.sum())) if original.sum() else 0.0
    return {"entry_correlation": correlation,
            "normalized_frobenius_error": float(np.linalg.norm(regularized - original) / denominator) if denominator else 0.0,
            "minimum_fraction_weight_relocated": moved,
            "maximum_row_sum_change": float(np.max(np.abs(regularized.sum(axis=1) - original.sum(axis=1)))),
            "maximum_column_sum_change": float(np.max(np.abs(regularized.sum(axis=0) - original.sum(axis=0))))}


def offset_profile(matrix: np.ndarray) -> np.ndarray:
    n = len(matrix)
    return np.array([sum(matrix[(source + offset) % n, source] for source in range(n)) for offset in range(n)])


def run(root: Path, config_path: Path = Path("configs/regularization_audit.yaml")) -> None:
    c = yaml.safe_load((root / config_path).read_text(encoding="utf-8")); data = np.load(root / c["transfers"])
    rows, profiles = [], []
    for name in c["matrices"]:
        original = data[name]; regularized = circularize(original)
        rows.append({"matrix": name, **matrix_metrics(original, regularized)})
        before, after = offset_profile(original), offset_profile(regularized)
        for offset, (a, b) in enumerate(zip(before, after)):
            profiles.append({"matrix": name, "offset_columns": offset, "original_weight": a, "regularized_weight": b})
    output = root / c["output"]; output.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(rows); frame.to_csv(output / "matrix_distance.csv", index=False)
    pd.DataFrame(profiles).to_csv(output / "offset_profiles.csv", index=False)
    report = {"created_at": utc_now(), "dataset": "FAFB", "materialization_version": 783,
              "claim": "Descriptive distance between provisional FlyWire phase transfers and their circularized engineering controls.",
              "configuration": config_path.as_posix(), "configuration_sha256": file_hash(root / config_path),
              "source_sha256": file_hash(Path(__file__)), "matrices": rows}
    save_json(output / "report.json", report)
    manifest_path = root / "data/manifest.json"; manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest[c["manifest_key"]] = {"status": "regularization_distance_audit_completed",
        "report": (output / "report.json").relative_to(root).as_posix(),
        "report_sha256": file_hash(output / "report.json")}
    save_json(manifest_path, manifest); print(frame.to_string(index=False), flush=True)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/regularization_audit.yaml"))
    run(Path.cwd(), parser.parse_args().config)
