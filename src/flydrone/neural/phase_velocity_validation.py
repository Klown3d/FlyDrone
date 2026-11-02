"""Validate angular-velocity updates across signs, rates and PEN operators."""
from itertools import product
from pathlib import Path
import json

import numpy as np
import pandas as pd
import yaml

from flydrone.data.acquire import file_hash, save_json, utc_now
from flydrone.neural.phase_compass_dynamics import advance, readout, wrap
from flydrone.neural.phase_resolved_compass import normalize_columns


def circularize(matrix: np.ndarray) -> np.ndarray:
    """Average contacts with the same target-minus-source phase offset."""
    n = matrix.shape[0]
    if matrix.shape != (n, n):
        raise ValueError("matrix must be square")
    offsets = np.empty(n)
    for offset in range(n):
        offsets[offset] = np.mean([matrix[(source + offset) % n, source] for source in range(n)])
    return np.array([[offsets[(target - source) % n] for source in range(n)] for target in range(n)])


def matrices(data, condition: str, excitation_components=None):
    transform = circularize if condition == "circularized" else lambda value: value
    norm = lambda name: normalize_columns(transform(data[name]))
    inhibition = norm("delta7")
    excitation_components=("peg", "pen_b_left", "pen_b_right", "pen_a_left", "pen_a_right") if excitation_components is None else tuple(excitation_components)
    excitation = sum(norm(name) for name in excitation_components) / len(excitation_components)
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


def evaluate(headings, velocities, c, phases, excitation, inhibition, operator, gain, sign):
    headings = np.asarray(headings)
    cue = c["cue_gain"] * np.exp(c["cue_concentration"] * (np.cos(headings[:, None] - phases) - 1))
    state = advance(np.zeros_like(cue), round(c["cue_duration_s"] / c["dt_s"]), c,
                    excitation, inhibition, operator, c["excitation_gain"],
                    c["inhibition_gain"], c["bias"], 0.0, cue)
    cue_phase, _, _ = readout(state, phases)
    errors, directions, resultants, contrasts, observed = [], [], [], [], []
    for velocity_deg_s in velocities:
        turned = advance(state.copy(), round(c["turn_duration_s"] / c["dt_s"]), c,
                         excitation, inhibition, operator, c["excitation_gain"],
                         c["inhibition_gain"], c["bias"],
                         gain * sign * np.deg2rad(velocity_deg_s), np.zeros_like(state))
        phase, resultant, contrast = readout(turned, phases)
        displacement = wrap(phase - cue_phase)
        expected = np.deg2rad(velocity_deg_s) * c["turn_duration_s"]
        errors.extend(np.abs(np.rad2deg(wrap(displacement - expected))))
        directions.extend(np.sign(displacement) == np.sign(velocity_deg_s))
        resultants.extend(resultant); contrasts.extend(contrast)
        observed.append(float(np.median(np.rad2deg(displacement))))
    monotonicity = pd.Series(observed).corr(pd.Series(velocities), method="spearman")
    return {
        "median_error_deg": float(np.median(errors)), "p90_error_deg": float(np.percentile(errors, 90)),
        "maximum_error_deg": float(np.max(errors)), "direction_accuracy": float(np.mean(directions)),
        "minimum_resultant": float(np.min(resultants)), "minimum_contrast": float(np.min(contrasts)),
        "velocity_monotonicity": float(monotonicity),
    }


def run(root: Path, config_path: Path = Path("configs/phase_velocity_validation.yaml")) -> None:
    c = yaml.safe_load((root / config_path).read_text(encoding="utf-8"))
    data = np.load(root / c["transfers"]); phases = np.deg2rad(data["phases_deg"]); rows = []
    excitation_models=c.get("excitation_models",{"all":["peg","pen_b_left","pen_b_right","pen_a_left","pen_a_right"]})
    for condition in c["matrix_conditions"]:
      for excitation_name,excitation_components in excitation_models.items():
        excitation, inhibition, operators = matrices(data, condition,excitation_components)
        for operator_name, gain, sign in product(c["operators"], c["velocity_gains"], c["angular_signs"]):
            metrics = evaluate(np.deg2rad(c["development_headings_deg"]), c["development_velocities_deg_s"],
                               c, phases, excitation, inhibition, operators[operator_name], gain, sign)
            rows.append({"matrix_condition": condition, "excitation_model":excitation_name,"operator": operator_name,
                         "velocity_gain": gain, "angular_sign": sign, **metrics})
    frame = pd.DataFrame(rows)
    frame["pass"] = ((frame.median_error_deg <= c["maximum_median_error_deg"])
                     & (frame.p90_error_deg <= c["maximum_p90_error_deg"])
                     & (frame.direction_accuracy == 1) & (frame.minimum_resultant >= c["minimum_resultant"])
                     & (frame.velocity_monotonicity >= c["minimum_velocity_monotonicity"]))
    frame = frame.sort_values(["pass", "median_error_deg", "p90_error_deg"], ascending=[False, True, True])
    output = root / c["output"]; output.mkdir(parents=True, exist_ok=True); frame.to_csv(output / "development_grid.csv", index=False)
    winner = frame.iloc[0]
    preferred = c.get("selected_candidate")
    if preferred:
        mask = np.ones(len(frame), dtype=bool)
        for key, value in preferred.items():
            mask &= np.isclose(frame[key].astype(float), float(value)) if key in {"velocity_gain", "angular_sign"} else frame[key].eq(value)
        matches = frame.loc[mask]
        if len(matches) != 1:
            raise ValueError(f"selected_candidate must identify exactly one row; found {len(matches)}")
        winner = matches.iloc[0]
        if not bool(winner["pass"]):
            raise ValueError("selected_candidate does not pass the configured development criteria")
    excitation, inhibition, operators = matrices(data, winner.matrix_condition,excitation_models[winner.excitation_model])
    held = evaluate(np.deg2rad(c["held_out_headings_deg"]), c["held_out_velocities_deg_s"], c, phases,
                    excitation, inhibition, operators[winner.operator], winner.velocity_gain, winner.angular_sign)
    selected = {"matrix_condition": winner.matrix_condition, "excitation_model":winner.excitation_model,"operator": winner.operator,
                "velocity_gain": float(winner.velocity_gain), "angular_sign": float(winner.angular_sign)}
    pd.DataFrame([{**selected, **held}]).to_csv(output / "held_out.csv", index=False)
    report = {"created_at": utc_now(), "dataset": "FAFB", "materialization_version": 783,
              "claim": "Multi-velocity development audit; circularized matrices are an engineering symmetry control, not measured anatomy.",
              "configuration": config_path.as_posix(), "configuration_sha256": file_hash(root / config_path),
              "source_sha256": file_hash(Path(__file__)), "candidate_count": len(frame),
              "development_passes": int(frame["pass"].sum()), "selected": selected, "held_out": held}
    save_json(output / "report.json", report)
    manifest_path = root / "data/manifest.json"; manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest[c["manifest_key"]] = {"status": "multi_velocity_validation_completed", "report": (output / "report.json").relative_to(root).as_posix(), "report_sha256": file_hash(output / "report.json")}
    save_json(manifest_path, manifest); print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=Path('configs/phase_velocity_validation.yaml'))
    run(Path.cwd(),parser.parse_args().config)
