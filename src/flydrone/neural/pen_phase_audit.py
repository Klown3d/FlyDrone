"""Audit plausible PEN phase-index offsets before accepting regularization."""
from itertools import product
from pathlib import Path
import json

import numpy as np
import pandas as pd
import yaml

from flydrone.data.acquire import file_hash, save_json, utc_now
from flydrone.neural.phase_resolved_compass import normalize_columns
from flydrone.neural.phase_velocity_validation import evaluate


def shifted_pen_matrices(data, subtype: str, offset: int):
    """Roll PEN target-phase rows with opposite left/right offsets."""
    result = {name: data[name].copy() for name in data.files if name != "phases_deg"}
    affected = ("a", "b") if subtype == "both" else (subtype,)
    for label in affected:
        result[f"pen_{label}_left"] = np.roll(result[f"pen_{label}_left"], -offset, axis=0)
        result[f"pen_{label}_right"] = np.roll(result[f"pen_{label}_right"], offset, axis=0)
    return result


def components(values):
    norm = lambda name: normalize_columns(values[name])
    inhibition = norm("delta7")
    excitation = sum(norm(name) for name in (
        "peg", "pen_b_left", "pen_b_right", "pen_a_left", "pen_a_right"
    )) / 5
    identity = np.eye(len(inhibition))
    operators = {
        "published_one_wedge": (np.roll(identity, 1, axis=0) - np.roll(identity, -1, axis=0)) / 2,
        "pen_a_difference": norm("pen_a_right") - norm("pen_a_left"),
        "pen_b_difference": norm("pen_b_right") - norm("pen_b_left"),
        "pen_combined_difference": (
            norm("pen_a_right") + norm("pen_b_right")
            - norm("pen_a_left") - norm("pen_b_left")
        ) / 2,
    }
    return excitation, inhibition, operators


def run(root: Path, config_path: Path = Path("configs/pen_phase_audit.yaml")) -> None:
    c = yaml.safe_load((root / config_path).read_text(encoding="utf-8"))
    data = np.load(root / c["transfers"]); phases = np.deg2rad(data["phases_deg"]); rows = []
    seen = set()
    for subtype, offset in product(c["shift_subtypes"], c["symmetric_offsets_columns"]):
        key = ("none", 0) if offset == 0 else (subtype, offset)
        if key in seen:
            continue
        seen.add(key); values = shifted_pen_matrices(data, subtype, offset)
        excitation, inhibition, operators = components(values)
        for operator_name, gain, sign in product(c["operators"], c["velocity_gains"], c["angular_signs"]):
            metrics = evaluate(np.deg2rad(c["development_headings_deg"]), c["development_velocities_deg_s"],
                               c, phases, excitation, inhibition, operators[operator_name], gain, sign)
            rows.append({"shift_subtype": key[0], "symmetric_offset_columns": key[1],
                         "operator": operator_name, "velocity_gain": gain,
                         "angular_sign": sign, **metrics})
    frame = pd.DataFrame(rows)
    frame["pass"] = ((frame.median_error_deg <= c["maximum_median_error_deg"])
                     & (frame.p90_error_deg <= c["maximum_p90_error_deg"])
                     & (frame.direction_accuracy == 1)
                     & (frame.minimum_resultant >= c["minimum_resultant"])
                     & (frame.velocity_monotonicity >= c["minimum_velocity_monotonicity"]))
    # If nothing passes, preserve the two qualitative requirements first:
    # correct direction and monotonic response.  A low median can otherwise
    # hide catastrophic errors in the opposite sign or at other velocities.
    frame = frame.sort_values(
        ["pass", "direction_accuracy", "velocity_monotonicity", "median_error_deg", "p90_error_deg"],
        ascending=[False, False, False, True, True],
    )
    output = root / c["output"]; output.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output / "development_grid.csv", index=False)
    best_per_shift = frame.groupby(["shift_subtype", "symmetric_offset_columns"], as_index=False).first()
    best_per_shift.sort_values(
        ["pass", "direction_accuracy", "velocity_monotonicity", "median_error_deg", "p90_error_deg"],
        ascending=[False, False, False, True, True],
    ).to_csv(output / "best_per_shift.csv", index=False)
    winner = frame.iloc[0].to_dict()
    report = {"created_at": utc_now(), "dataset": "FAFB", "materialization_version": 783,
              "claim": "Development-only audit of alternative PEN phase indices; row rolls are diagnostic hypotheses, not corrected anatomy.",
              "configuration": config_path.as_posix(), "configuration_sha256": file_hash(root / config_path),
              "source_sha256": file_hash(Path(__file__)), "candidate_count": len(frame),
              "passing_candidates": int(frame["pass"].sum()), "best": winner}
    save_json(output / "report.json", report)
    manifest_path = root / "data/manifest.json"; manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest[c["manifest_key"]] = {"status": "pen_phase_index_audit_completed",
        "report": (output / "report.json").relative_to(root).as_posix(),
        "report_sha256": file_hash(output / "report.json")}
    save_json(manifest_path, manifest); print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    run(Path.cwd())
