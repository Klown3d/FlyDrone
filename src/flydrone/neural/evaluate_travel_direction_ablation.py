"""Ablate PFN streams and phase correspondence in the Phase 6 model."""
from __future__ import annotations

from pathlib import Path
import argparse
import json

import numpy as np
import pandas as pd
import yaml

from flydrone.data.acquire import file_hash, save_json, utc_now
from flydrone.neural.travel_direction_model import ConnectomeTravelDirection, wrap


def _evaluate(model, headings, motions, weights, phases) -> dict:
    axes = model.egocentric_axes_rad
    angles = model.hdelta_angles_rad

    def raw(heading, motion):
        amplitude = np.maximum(0.0, np.cos(motion - axes))
        activity = amplitude * np.cos(heading - phases)
        hdelta = weights @ activity
        vector = np.sum(hdelta * np.exp(1j * angles))
        denominator = np.sum(np.abs(hdelta))
        return float(np.angle(vector)), float(abs(vector) / denominator) if denominator else 0.0

    anchor = -raw(0.0, 0.0)[0]
    errors = []
    resultants = []
    for heading in headings:
        for motion in motions:
            phase, resultant = raw(heading, motion)
            errors.append(abs(float(wrap(phase + anchor - wrap(heading + motion)))))
            resultants.append(resultant)
    return {
        "median_absolute_error_deg": float(np.rad2deg(np.median(errors))),
        "maximum_absolute_error_deg": float(np.rad2deg(np.max(errors))),
        "within_45deg_fraction": float(np.mean(np.asarray(errors) < np.deg2rad(45.0))),
        "minimum_resultant": float(np.min(resultants)),
    }


def run(root: Path, config_path: Path) -> None:
    c = yaml.safe_load((root / config_path).read_text(encoding="utf-8"))
    model_path = root / c["model_config"]
    spec = yaml.safe_load(model_path.read_text(encoding="utf-8"))
    model = ConnectomeTravelDirection(root, model_path)
    headings = np.deg2rad(spec["development_headings_deg"])
    motions = np.deg2rad(spec["development_egocentric_motion_deg"])
    rows = []
    conditions = {"intact": model.weights.copy(), "without_PFNd": model.weights.copy(), "without_PFNv": model.weights.copy()}
    conditions["without_PFNd"][:, model.pfn["selected_type"].eq("PFNd").to_numpy()] = 0.0
    conditions["without_PFNv"][:, model.pfn["selected_type"].eq("PFNv").to_numpy()] = 0.0
    for name, weights in conditions.items():
        rows.append({"condition": name, "seed": None, **_evaluate(model, headings, motions, weights, model.heading_phase_rad)})
    rows.append({"condition": "collapsed_heading_phase", "seed": None, **_evaluate(model, headings, motions, model.weights, np.zeros_like(model.heading_phase_rad))})
    for seed in c["phase_shuffle_seeds"]:
        rng = np.random.default_rng(seed)
        phases = model.heading_phase_rad.copy()
        for cell_type in ("PFNd", "PFNv"):
            for side in ("left", "right"):
                indices = np.flatnonzero(model.pfn["selected_type"].eq(cell_type).to_numpy() & model.pfn["side"].eq(side).to_numpy())
                phases[indices] = phases[rng.permutation(indices)]
        rows.append({"condition": "phase_shuffled", "seed": seed, **_evaluate(model, headings, motions, model.weights, phases)})
    frame = pd.DataFrame(rows)
    output = root / c["output"]
    output.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output / "scores.csv", index=False)
    intact = frame.loc[frame["condition"].eq("intact")].iloc[0]
    nulls = frame.loc[frame["condition"].eq("phase_shuffled")]
    named_conditions = frame.loc[~frame["condition"].eq("phase_shuffled")]
    report = {
        "created_at": utc_now(), "dataset": "FAFB", "materialization_version": 783,
        "claim": "Post-development computational attribution; ablations and within-group phase permutations are not biological perturbation experiments.",
        "configuration": config_path.as_posix(), "configuration_sha256": file_hash(root / config_path), "source_sha256": file_hash(Path(__file__)),
        "conditions": named_conditions.astype(object).where(pd.notna(named_conditions), None).to_dict(orient="records"),
        "phase_null_count": len(nulls),
        "phase_null_median_error_distribution": {"minimum": float(nulls["median_absolute_error_deg"].min()), "median": float(nulls["median_absolute_error_deg"].median()), "maximum": float(nulls["median_absolute_error_deg"].max())},
        "nulls_matching_or_beating_intact": int((nulls["median_absolute_error_deg"] <= intact["median_absolute_error_deg"]).sum()),
        "empirical_p_upper_bound": float((1 + (nulls["median_absolute_error_deg"] <= intact["median_absolute_error_deg"]).sum()) / (1 + len(nulls))),
    }
    save_json(output / "report.json", report)
    manifest_path = root / "data/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest[c["manifest_key"]] = {"status": "post_development_attribution_completed", "report": (output / "report.json").relative_to(root).as_posix(), "report_sha256": file_hash(output / "report.json"), "phase_nulls": len(nulls)}
    save_json(manifest_path, manifest)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/travel_direction_ablation.yaml"))
    run(Path.cwd(), parser.parse_args().config)
