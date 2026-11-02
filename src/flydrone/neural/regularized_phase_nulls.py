"""Compare regularized FlyWire phase structure with phase-label nulls."""
from itertools import product
from pathlib import Path
import json

import numpy as np
import pandas as pd
import yaml

from flydrone.data.acquire import file_hash, save_json, utc_now
from flydrone.neural.phase_resolved_compass import projection_matrix
from flydrone.neural.phase_velocity_validation import evaluate, matrices


SPECS = [
    ("delta7", "Delta7", "PB", None), ("peg", "PEG", "EB", None),
    ("pen_a_left", "PEN_a(PEN1)", "EB", "left"),
    ("pen_a_right", "PEN_a(PEN1)", "EB", "right"),
    ("pen_b_left", "PEN_b(PEN2)", "EB", "left"),
    ("pen_b_right", "PEN_b(PEN2)", "EB", "right"),
]


def shuffled_phase_series(phases: pd.Series, seed: int) -> pd.Series:
    values = phases.to_numpy(copy=True); np.random.default_rng(seed).shuffle(values)
    return pd.Series(values, index=phases.index, name=phases.name)


def build_transfers(edges, nodes, phase_by_id, projection_compartments=None):
    projection_compartments = projection_compartments or {}
    result = {}
    for label, cell_type, neuropil, side in SPECS:
        compartments = projection_compartments.get(label, {})
        input_neuropil = compartments.get("input", neuropil)
        output_neuropil = compartments.get("output", neuropil)
        result[label] = projection_matrix(
            edges, nodes, phase_by_id, cell_type, input_neuropil, side, output_neuropil
        )[0]
    return result


def tune(values, c, phases):
    excitation, inhibition, operators = matrices(
        values, "circularized", c.get("excitation_components")
    ); rows = []
    for operator_name, gain, sign in product(c["operators"], c["velocity_gains"], c["angular_signs"]):
        metric = evaluate(np.deg2rad(c["development_headings_deg"]), c["development_velocities_deg_s"],
                          c, phases, excitation, inhibition, operators[operator_name], gain, sign)
        passed = (metric["median_error_deg"] <= c["maximum_median_error_deg"]
                  and metric["p90_error_deg"] <= c["maximum_p90_error_deg"]
                  and metric["direction_accuracy"] == 1
                  and metric["minimum_resultant"] >= c["minimum_resultant"]
                  and metric["velocity_monotonicity"] >= c["minimum_velocity_monotonicity"])
        rows.append({"operator": operator_name, "velocity_gain": gain, "angular_sign": sign,
                     "pass": passed, **metric})
    return sorted(rows, key=lambda row: (not row["pass"], row["median_error_deg"], row["p90_error_deg"]))[0]


def run(root: Path, config_path: Path = Path("configs/regularized_phase_nulls.yaml")) -> None:
    c = yaml.safe_load((root / config_path).read_text(encoding="utf-8"))
    source = yaml.safe_load((root / c["phase_transfer_config"]).read_text(encoding="utf-8"))
    extraction = root / source["extraction"]
    nodes = pd.read_csv(extraction / "nodes.csv", dtype={"root_id": str})
    edges = pd.read_csv(extraction / "edges.csv", dtype={"pre_pt_root_id": str, "post_pt_root_id": str})
    features = pd.read_csv(root / source["steering_features"], dtype={"root_id": str})
    phase_config = yaml.safe_load((root / source["epg_phase_config"]).read_text(encoding="utf-8"))
    phase_by_id = features.loc[features.selected_type.eq("EPG")].set_index("root_id").geometric_column.map(phase_config["epg_preferred_heading_deg"])
    phases = np.deg2rad(np.array(sorted(phase_by_id.unique()), float))
    compartments = source.get("projection_compartments", {})
    true_best = tune(build_transfers(edges, nodes, phase_by_id, compartments), c, phases)
    rows = []
    for seed in c["null_seeds"]:
        best = tune(build_transfers(
            edges, nodes, shuffled_phase_series(phase_by_id, seed), compartments
        ), c, phases)
        rows.append({"seed": seed, **best}); print(f"null {seed}: median {best['median_error_deg']:.2f} deg", flush=True)
    frame = pd.DataFrame(rows); output = root / c["output"]; output.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output / "null_best_models.csv", index=False)
    better_or_equal = int((frame.median_error_deg <= true_best["median_error_deg"]).sum())
    passing_nulls = int(frame["pass"].sum())
    report = {"created_at": utc_now(), "dataset": "FAFB", "materialization_version": 783,
              "claim": c.get("claim", "Development attribution test: identical circularization and tuning applied after EPG phase labels are shuffled while the neuron graph and contacts remain fixed."),
              "configuration": config_path.as_posix(), "configuration_sha256": file_hash(root / config_path),
              "source_sha256": file_hash(Path(__file__)), "flywire_regularized_best": true_best,
              "null_count": len(frame), "nulls_better_or_equal_median": better_or_equal,
              "empirical_one_sided_p": (1 + better_or_equal) / (1 + len(frame)),
              "nulls_passing_all_criteria": passing_nulls,
              "empirical_p_all_criteria": (1 + passing_nulls) / (1 + len(frame)),
              "null_median_of_median_error_deg": float(frame.median_error_deg.median()),
              "null_minimum_median_error_deg": float(frame.median_error_deg.min())}
    save_json(output / "report.json", report)
    manifest_path = root / "data/manifest.json"; manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest[c["manifest_key"]] = {"status": "regularized_phase_null_development_test_completed",
        "report": (output / "report.json").relative_to(root).as_posix(),
        "report_sha256": file_hash(output / "report.json")}
    save_json(manifest_path, manifest); print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/regularized_phase_nulls.yaml"))
    run(Path.cwd(), parser.parse_args().config)
