"""Evaluate FlyWire-weighted PFL3 inputs, subtype variants, and ablations."""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

from flydrone.data.acquire import file_hash, save_json, utc_now
from flydrone.neural.connectome_pfl3 import ConnectomeWeightedPFL3
from flydrone.neural.pfl3 import PFL3ReferenceModel


GOALS_DEG = np.arange(-165.0, 180.0, 30.0)
RELATIVE_HEADINGS_DEG = np.arange(-180.0, 181.0, 1.0)


def nearest_stable_crossing(relative_deg: np.ndarray, signal: np.ndarray) -> float | None:
    candidates: list[tuple[float, float]] = []
    for i in range(len(relative_deg) - 1):
        first, second = signal[i], signal[i + 1]
        if first == 0:
            crossing = float(relative_deg[i])
        elif first * second < 0:
            fraction = -first / (second - first)
            crossing = float(relative_deg[i] + fraction * (relative_deg[i + 1] - relative_deg[i]))
        else:
            continue
        slope = float(second - first)
        candidates.append((crossing, slope))
    stable = [value for value, slope in candidates if slope < 0]
    choices = stable or [value for value, _slope in candidates]
    return min(choices, key=abs) if choices else None


def evaluate_condition(
    name: str,
    model: ConnectomeWeightedPFL3,
    reference: PFL3ReferenceModel,
    *,
    delta7_enabled: bool = True,
    fc2_enabled: bool = True,
    delta_weights: np.ndarray | None = None,
    fc2_weights: np.ndarray | None = None,
    include_unit_rates: bool = True,
) -> tuple[dict[str, object], pd.DataFrame]:
    rows: list[dict[str, object]] = []
    errors: list[float] = []
    expected_sign: list[float] = []
    observed_sign: list[float] = []
    model_signals: list[float] = []
    reference_signals: list[float] = []
    for goal_deg in GOALS_DEG:
        goal_signals = []
        for relative_deg in RELATIVE_HEADINGS_DEG:
            heading_deg = goal_deg + relative_deg
            rates = model.rates(
                np.deg2rad(heading_deg), np.deg2rad(goal_deg), delta7_enabled=delta7_enabled,
                fc2_enabled=fc2_enabled, delta_weights=delta_weights, fc2_weights=fc2_weights,
            )
            signal = model.readout(rates)
            reference_rates = reference.rates(np.deg2rad(heading_deg), np.deg2rad(goal_deg))
            reference_signal = reference.readout(reference_rates)["right_minus_left_hz"]
            row: dict[str, object] = {
                "condition": name, "goal_deg": goal_deg, "relative_heading_deg": relative_deg,
                "heading_deg_unwrapped": heading_deg, "right_minus_left_hz": signal,
                "reference_right_minus_left_hz": reference_signal,
            }
            if include_unit_rates:
                row.update({f"rate_hz_{root_id}": rate for root_id, rate in zip(model.pfl3["root_id"], rates)})
            rows.append(row)
            goal_signals.append(signal)
            model_signals.append(signal)
            reference_signals.append(reference_signal)
            if 5 <= abs(relative_deg) <= 170:
                expected_sign.append(-np.sign(relative_deg))
                observed_sign.append(np.sign(signal))
        crossing = nearest_stable_crossing(RELATIVE_HEADINGS_DEG, np.asarray(goal_signals))
        if crossing is not None:
            errors.append(abs(crossing))
    correlation = float(np.corrcoef(model_signals, reference_signals)[0, 1]) if np.std(model_signals) else np.nan
    metrics = {
        "condition": name,
        "fc2_subtypes": list(model.fc2_subtypes),
        "delta7_enabled": delta7_enabled,
        "fc2_enabled": fc2_enabled,
        "mean_abs_stable_equilibrium_error_deg": float(np.mean(errors)) if errors else None,
        "maximum_abs_stable_equilibrium_error_deg": float(np.max(errors)) if errors else None,
        "goals_with_detected_equilibrium": len(errors),
        "steering_direction_accuracy": float(np.mean(np.asarray(expected_sign) == np.asarray(observed_sign))),
        "correlation_with_published_reference": correlation,
        "mean_abs_signal_at_goal_hz": float(np.mean([
            abs(row["right_minus_left_hz"]) for row in rows if row["relative_heading_deg"] == 0
        ])),
        "delta7_stream": asdict(model.delta_audit),
        "fc2_stream": asdict(model.fc2_audit),
    }
    return metrics, pd.DataFrame(rows)


def run(root: Path, config_path: Path, output_dir: Path, shuffle_seeds: int) -> None:
    reference = PFL3ReferenceModel.from_config(root, root / "configs/neural_model.yaml")
    definitions = [
        ("FC2B+FC2C", ("FC2B", "FC2C"), True, True),
        ("FC2B_only", ("FC2B",), True, True),
        ("FC2C_only", ("FC2C",), True, True),
        ("FC2A_comparison", ("FC2A",), True, True),
        ("Delta7_ablated", ("FC2B", "FC2C"), False, True),
        ("FC2_ablated", ("FC2B", "FC2C"), True, False),
    ]
    output_dir.mkdir(parents=True, exist_ok=True)
    summaries: list[dict[str, object]] = []
    for name, subtypes, delta_enabled, fc_enabled in definitions:
        model = ConnectomeWeightedPFL3(root, config_path, subtypes)
        metrics, trace = evaluate_condition(
            name, model, reference, delta7_enabled=delta_enabled, fc2_enabled=fc_enabled
        )
        trace_path = output_dir / f"{name.lower().replace('+', '_plus_')}-trace.csv"
        trace.to_csv(trace_path, index=False)
        metrics["trace"] = trace_path.relative_to(root).as_posix()
        metrics["trace_sha256"] = file_hash(trace_path)
        summaries.append(metrics)

    primary = ConnectomeWeightedPFL3(root, config_path)
    shuffle_rows: list[dict[str, object]] = []
    for seed in range(shuffle_seeds):
        rng = np.random.default_rng(seed)
        dw = primary.shuffled_rows(primary.delta_weights, rng)
        fw = primary.shuffled_rows(primary.fc2_weights, rng)
        metrics, trace = evaluate_condition(
            f"weights_shuffled_seed_{seed}", primary, reference,
            delta_weights=dw, fc2_weights=fw, include_unit_rates=False,
        )
        shuffle_rows.append({"seed": seed, **{key: value for key, value in metrics.items() if not isinstance(value, (dict, list))}})
        trace[["condition", "goal_deg", "relative_heading_deg", "right_minus_left_hz"]].to_csv(
            output_dir / f"weights-shuffled-seed-{seed}-trace.csv", index=False
        )
    summary_path = output_dir / "conditions.csv"
    pd.json_normalize(summaries).to_csv(summary_path, index=False)
    shuffle_path = output_dir / "weight-shuffles.csv"
    pd.DataFrame(shuffle_rows).to_csv(shuffle_path, index=False)
    primary_summary = next(item for item in summaries if item["condition"] == "FC2B+FC2C")
    shuffle_frame = pd.DataFrame(shuffle_rows)
    def distribution(column: str) -> dict[str, float]:
        values = shuffle_frame[column]
        return {
            "mean": float(values.mean()), "std": float(values.std(ddof=1)), "min": float(values.min()),
            "p05": float(values.quantile(0.05)), "median": float(values.median()),
            "p95": float(values.quantile(0.95)), "max": float(values.max()),
        }
    report = {
        "created_at": utc_now(),
        "model": "flywire_weighted_pfl3_feedforward",
        "claim_level": "experimental connectome-weighted feedforward model; not a full functional reconstruction",
        "dataset": {"name": "FAFB", "materialization_version": 783},
        "primary_condition": primary_summary,
        "weight_shuffle_seeds": shuffle_seeds,
        "weight_shuffle_mean_equilibrium_error_deg": float(shuffle_frame["mean_abs_stable_equilibrium_error_deg"].mean()),
        "weight_shuffle_mean_direction_accuracy": float(shuffle_frame["steering_direction_accuracy"].mean()),
        "weight_shuffle_equilibrium_error_deg": distribution("mean_abs_stable_equilibrium_error_deg"),
        "weight_shuffle_direction_accuracy": distribution("steering_direction_accuracy"),
        "weight_shuffle_reference_correlation": distribution("correlation_with_published_reference"),
        "primary_lower_error_than_all_shuffles": bool(
            (shuffle_frame["mean_abs_stable_equilibrium_error_deg"] > primary_summary["mean_abs_stable_equilibrium_error_deg"]).all()
        ),
        "primary_higher_direction_accuracy_than_all_shuffles": bool(
            (shuffle_frame["steering_direction_accuracy"] < primary_summary["steering_direction_accuracy"]).all()
        ),
        "config": config_path.relative_to(root).as_posix(),
        "config_sha256": file_hash(config_path),
        "conditions": summary_path.relative_to(root).as_posix(),
        "conditions_sha256": file_hash(summary_path),
        "weight_shuffles": shuffle_path.relative_to(root).as_posix(),
        "weight_shuffles_sha256": file_hash(shuffle_path),
    }
    report_path = output_dir / "report.json"
    save_json(report_path, report)
    manifest_path = root / "data/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["neural_model"]["connectome_weighted_experiment"] = {
        "status": "evaluated",
        "scope": "Delta7/FC2-to-PFL3 feedforward",
        "configuration": config_path.relative_to(root).as_posix(),
        "configuration_sha256": file_hash(config_path),
        "report": report_path.relative_to(root).as_posix(),
        "report_sha256": file_hash(report_path),
    }
    manifest["status"] = "connectome_weighted_pfl3_feedforward_evaluated_full_circuit_pending"
    save_json(manifest_path, manifest)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--config", type=Path, default=Path("configs/connectome_model.yaml"))
    parser.add_argument("--output", type=Path, default=Path("results/neural/connectome_weighted_pfl3"))
    parser.add_argument("--shuffle-seeds", type=int, default=20)
    args = parser.parse_args()
    root = args.root.resolve()
    run(root, (root / args.config).resolve(), (root / args.output).resolve(), args.shuffle_seeds)
