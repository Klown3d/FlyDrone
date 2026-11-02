"""Evaluate whether explicit FlyWire EPG projections recover PFL3 heading input."""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

from flydrone.data.acquire import file_hash, save_json, utc_now
from flydrone.neural.epg_delta7 import EPGDelta7Candidate
from flydrone.neural.evaluate_connectome import GOALS_DEG, RELATIVE_HEADINGS_DEG, nearest_stable_crossing
from flydrone.neural.pfl3 import PFL3ReferenceModel


def evaluate_steering(
    candidate: EPGDelta7Candidate,
    reference: PFL3ReferenceModel,
    condition: str,
    phase_offset_rad: float,
) -> tuple[dict[str, object], pd.DataFrame]:
    rows: list[dict[str, object]] = []
    errors: list[float] = []
    correct: list[bool] = []
    signals: list[float] = []
    reference_signals: list[float] = []
    for goal_deg in GOALS_DEG:
        goal_signals: list[float] = []
        for relative_deg in RELATIVE_HEADINGS_DEG:
            heading_rad = np.deg2rad(goal_deg + relative_deg)
            goal_rad = np.deg2rad(goal_deg)
            rates = candidate.rates(heading_rad, goal_rad, condition, phase_offset_rad)
            signal = candidate.base.readout(rates)
            reference_signal = reference.readout(reference.rates(heading_rad, goal_rad))["right_minus_left_hz"]
            row: dict[str, object] = {
                "condition": condition,
                "goal_deg": goal_deg,
                "relative_heading_deg": relative_deg,
                "right_minus_left_hz": signal,
                "reference_right_minus_left_hz": reference_signal,
            }
            row.update(
                {f"rate_hz_{root_id}": rate for root_id, rate in zip(candidate.base.pfl3["root_id"], rates)}
            )
            rows.append(row)
            goal_signals.append(signal)
            signals.append(signal)
            reference_signals.append(reference_signal)
            if 5 <= abs(relative_deg) <= 170:
                correct.append(bool(np.sign(signal) == -np.sign(relative_deg)))
        crossing = nearest_stable_crossing(RELATIVE_HEADINGS_DEG, np.asarray(goal_signals))
        if crossing is not None:
            errors.append(abs(crossing))
    return {
        "mean_abs_stable_equilibrium_error_deg": float(np.mean(errors)) if errors else None,
        "maximum_abs_stable_equilibrium_error_deg": float(np.max(errors)) if errors else None,
        "goals_with_detected_equilibrium": len(errors),
        "steering_direction_accuracy": float(np.mean(correct)),
        "correlation_with_published_reference": float(np.corrcoef(signals, reference_signals)[0, 1]),
    }, pd.DataFrame(rows)


def run(root: Path, config_path: Path, output_dir: Path) -> None:
    candidate = EPGDelta7Candidate(root, config_path)
    reference = PFL3ReferenceModel.from_config(root, root / "configs/neural_model.yaml")
    output_dir.mkdir(parents=True, exist_ok=True)

    mapping_path = output_dir / "epg-functional-mapping.csv"
    candidate.epg[
        ["root_id", "geometric_column", "preferred_heading_deg", "PB_median_x_nm", "PB_median_y_nm", "PB_median_z_nm"]
    ].to_csv(mapping_path, index=False)

    condition_reports: list[dict[str, object]] = []
    for condition in candidate.CONDITIONS:
        fit = candidate.phase_fit(condition)
        phase_rows = []
        residual_by_index = iter(fit["residual_deg"])
        for index, row in candidate.base.pfl3.iterrows():
            valid = bool(fit["valid_mask"][index])
            phase_rows.append({
                "root_id": row["root_id"],
                "condition": condition,
                "published_proxy_heading_deg": row["preferred_heading_deg"],
                "predicted_heading_deg": fit["predicted_preferred_heading_deg"][index] if valid else np.nan,
                "transfer_amplitude": fit["transfer_amplitude"][index],
                "residual_after_global_phase_deg": next(residual_by_index) if valid else np.nan,
            })
        phase_path = output_dir / f"{condition}-pfl3-phase.csv"
        pd.DataFrame(phase_rows).to_csv(phase_path, index=False)
        uncalibrated, _ = evaluate_steering(candidate, reference, condition, 0.0)
        fitted, trace = evaluate_steering(
            candidate, reference, condition, np.deg2rad(float(fit["phase_offset_deg"]))
        )
        trace_path = output_dir / f"{condition}-calibrated-trace.csv"
        trace.to_csv(trace_path, index=False)
        condition_reports.append({
            "condition": condition,
            "phase_fit": {key: value for key, value in fit.items() if not isinstance(value, np.ndarray)},
            "uncalibrated_steering": uncalibrated,
            "phase_fitted_steering": fitted,
            "phase_table": phase_path.relative_to(root).as_posix(),
            "phase_table_sha256": file_hash(phase_path),
            "activity_trace": trace_path.relative_to(root).as_posix(),
            "activity_trace_sha256": file_hash(trace_path),
        })

    projections = {
        "EPG_to_Delta7": asdict(candidate.audit(candidate.epg_to_delta_raw, len(candidate.epg_to_delta_edges))),
        "Delta7_to_Delta7": asdict(candidate.audit(candidate.delta_to_delta_raw, len(candidate.delta_to_delta_edges))),
        "Delta7_to_PFL3": asdict(candidate.audit(candidate.delta_to_pfl3_raw, len(candidate.delta_to_pfl3_edges))),
        "EPG_to_PFL3": asdict(candidate.audit(candidate.epg_to_pfl3_raw, len(candidate.epg_to_pfl3_edges))),
    }
    report = {
        "created_at": utc_now(),
        "model": "explicit_epg_delta7_feedforward_audit",
        "claim_level": "rejected candidate; useful negative result, not a functional reconstruction",
        "dataset": {"name": "FAFB", "materialization_version": 783},
        "epg_mapping": {
            "occupied_columns": [f"PB{i:02d}" for i in range(2, 18)],
            "neuron_count": len(candidate.epg),
            "status": "3-D geometry inference constrained by the published 16 occupied EPG ROIs",
            "mapping": mapping_path.relative_to(root).as_posix(),
            "mapping_sha256": file_hash(mapping_path),
        },
        "projections": projections,
        "delta7_recurrence": {
            "present_in_connectome": True,
            "simulated": False,
            "reason": "A recurrent gain, leak/time constant, and transfer function are not established by the pairwise contact table.",
        },
        "conditions": condition_reports,
        "decision": "Do not promote explicit EPG propagation into the controller: no tested feedforward signed-contact condition recovers the published PFL3 heading map after one global phase calibration.",
        "required_next_data": [
            "PB synapse coordinates for the selected EPG, Delta7, and PFL3 root IDs",
            "expert or source-provided FAFB glomerular labels for Delta7 arbors",
            "a supported Delta7 recurrent dynamic or physiology-derived response model",
        ],
        "config": config_path.relative_to(root).as_posix(),
        "config_sha256": file_hash(config_path),
    }
    report_path = output_dir / "report.json"
    save_json(report_path, report)
    manifest_path = root / "data/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["neural_model"]["epg_delta7_experiment"] = {
        "status": "candidate_rejected_pending_synapse_coordinates_and_recurrent_dynamics",
        "configuration": config_path.relative_to(root).as_posix(),
        "configuration_sha256": file_hash(config_path),
        "report": report_path.relative_to(root).as_posix(),
        "report_sha256": file_hash(report_path),
    }
    manifest["status"] = "epg_delta7_feedforward_candidate_rejected_data_gate"
    save_json(manifest_path, manifest)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--config", type=Path, default=Path("configs/epg_delta7_audit.yaml"))
    parser.add_argument("--output", type=Path, default=Path("results/neural/epg_delta7_audit"))
    args = parser.parse_args()
    project_root = args.root.resolve()
    run(project_root, (project_root / args.config).resolve(), (project_root / args.output).resolve())
