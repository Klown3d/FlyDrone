"""Validate, freeze, and execute the PFN-to-hDeltaB confirmatory protocol."""
from __future__ import annotations

from pathlib import Path
import argparse
import importlib.metadata
import json
import platform

import yaml

from flydrone.data.acquire import file_hash, save_json, utc_now
from flydrone.simulation.benchmark_inertial_velocity import run as run_benchmark


DEVELOPMENT_CONFIGS = (
    Path("configs/quadrotor_connectome_null_3d_development.yaml"),
    Path("configs/quadrotor_connectome_block_null_3d_development.yaml"),
)

LOCKED_SOURCES = (
    Path("src/flydrone/simulation/benchmark_inertial_velocity.py"),
    Path("src/flydrone/simulation/benchmark_quadrotor.py"),
    Path("src/flydrone/simulation/benchmark_oracle_diagnostics.py"),
    Path("src/flydrone/simulation/travel_velocity_sensor.py"),
    Path("src/flydrone/neural/travel_direction_model.py"),
    Path("src/flydrone/neural/travel_direction_drift.py"),
    Path("src/flydrone/neural/connectome_nulls.py"),
    Path("src/flydrone/neural/phase_compass_estimator.py"),
    Path("src/flydrone/simulation/analyze_confirmatory_gate.py"),
)


def _load(root: Path, path: Path) -> dict:
    return yaml.safe_load((root / path).read_text(encoding="utf-8"))


def validate(root: Path, config_path: Path, allow_existing_output: bool = False) -> dict:
    config = _load(root, config_path)
    errors: list[str] = []
    bearings = config.get("target_bearings_deg", [])
    headings = config.get("initial_relative_headings_deg", [])
    scenarios = config.get("scenarios", [])
    conditions = config.get("conditions", [])
    cases_per_condition = len(bearings) * len(headings) * len(scenarios)
    if config.get("parameter_status") != "frozen_confirmatory_v1_execute_once":
        errors.append("parameter_status is not frozen_confirmatory_v1_execute_once")
    if cases_per_condition != 100:
        errors.append(f"expected 100 cases per condition, found {cases_per_condition}")
    if len(set(bearings)) != 5 or len(set(headings)) != 5 or len(scenarios) != 4:
        errors.append("the protocol requires 5 unique bearings, 5 unique headings, and 4 scenarios")
    names = [condition.get("name") for condition in conditions]
    if len(names) != len(set(names)):
        errors.append("condition names must be unique")
    required = {"flywire_hdelta_intact", "direct_velocity_matched", "conventional_navigation"}
    if not required.issubset(names):
        errors.append("intact, matched direct, and conventional conditions are required")
    nulls = [condition for condition in conditions if str(condition.get("name", "")).startswith("null_rewire_block_")]
    if len(nulls) != 5:
        errors.append(f"expected five block-preserving nulls, found {len(nulls)}")
    null_seeds = [condition.get("block_weight_rewire_seed") for condition in nulls]
    if None in null_seeds or len(set(null_seeds)) != 5:
        errors.append("null seeds must be present and unique")
    if any(condition.get("circuit_condition") != "type_side_block_rewire" for condition in nulls):
        errors.append("all confirmatory nulls must preserve PFN type and side")
    scenario_seeds = [scenario.get("seed") for scenario in scenarios]
    if None in scenario_seeds or len(set(scenario_seeds)) != 4:
        errors.append("scenario seeds must be present and unique")
    for development_path in DEVELOPMENT_CONFIGS:
        development = _load(root, development_path)
        if set(bearings) & set(development.get("target_bearings_deg", [])):
            errors.append(f"bearing overlap with {development_path.as_posix()}")
        if set(headings) & set(development.get("initial_relative_headings_deg", [])):
            errors.append(f"heading overlap with {development_path.as_posix()}")
        old_scenario_seeds = {scenario.get("seed") for scenario in development.get("scenarios", [])}
        if set(scenario_seeds) & old_scenario_seeds:
            errors.append(f"scenario seed overlap with {development_path.as_posix()}")
        old_null_seeds = {condition.get("block_weight_rewire_seed") for condition in development.get("conditions", [])}
        if set(null_seeds) & old_null_seeds:
            errors.append(f"null seed overlap with {development_path.as_posix()}")
    output = root / config["output"]
    if not allow_existing_output and output.exists() and any(output.iterdir()):
        errors.append("confirmatory output already exists; execute-once protocol refuses overwrite")
    if errors:
        raise ValueError("Invalid confirmatory protocol: " + "; ".join(errors))
    return {
        "protocol_id": config["protocol_id"],
        "cases_per_condition": cases_per_condition,
        "conditions": len(conditions),
        "total_episodes": cases_per_condition * len(conditions),
        "null_seeds": [int(seed) for seed in null_seeds],
        "scenario_seeds": [int(seed) for seed in scenario_seeds],
    }


def locked_paths(root: Path, config_path: Path) -> list[Path]:
    config = _load(root, config_path)
    paths = [config_path, *LOCKED_SOURCES]
    for key in ("base_config", "plant_config", "orientation_config", "phase_compass_config",
                "travel_direction_drift_config", "travel_velocity_sensor_config",
                "travel_velocity_inertial_config"):
        paths.append(Path(config[key]))
    drift = _load(root, Path(config["travel_direction_drift_config"]))
    model_path = Path(drift["model_config"])
    paths.append(model_path)
    model = _load(root, model_path)
    paths.extend((Path(model["column_mapping"]), Path(model["edges"])))
    paths.extend(path.relative_to(root) for path in (root / "src/flydrone").rglob("*.py"))
    paths.extend(path.relative_to(root) for path in (root / "configs").glob("*.yaml"))
    for folder in (root / "data/processed/fafb783_travel_direction",
                   root / "data/processed/fafb783_epg_delta7_fc2_pfl3"):
        paths.extend(path.relative_to(root) for path in folder.rglob("*") if path.is_file())
    paths.extend((Path("results/neural/phase_resolved_compass_cross_compartment/transfers.npz"),
                  Path("pyproject.toml"), Path("docs/research/confirmatory-gate-preregistration.md")))
    return list(dict.fromkeys(paths))


def environment_versions() -> dict:
    packages = ("numpy", "pandas", "scipy", "PyYAML", "pyarrow", "panda3d")
    return {"python": platform.python_version(),
            "packages": {name: importlib.metadata.version(name) for name in packages}}


def freeze(root: Path, config_path: Path) -> dict:
    summary = validate(root, config_path)
    config = _load(root, config_path)
    lock_path = root / config["lock_file"]
    if lock_path.exists():
        raise FileExistsError(f"Lock already exists: {lock_path}")
    hashes = {path.as_posix(): file_hash(root / path) for path in locked_paths(root, config_path)}
    lock = {"created_at": utc_now(), "status": "frozen_before_execution", **summary,
            "environment": environment_versions(),
            "files_sha256": hashes}
    save_json(lock_path, lock)
    return lock


def verify_lock(root: Path, config_path: Path, allow_existing_output: bool = False) -> dict:
    summary = validate(root, config_path, allow_existing_output=allow_existing_output)
    config = _load(root, config_path)
    lock_path = root / config["lock_file"]
    if not lock_path.exists():
        raise FileNotFoundError("Freeze the protocol before execution")
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    current = {path.as_posix(): file_hash(root / path) for path in locked_paths(root, config_path)}
    if current != lock.get("files_sha256"):
        changed = sorted(set(current) | set(lock.get("files_sha256", {})))
        changed = [path for path in changed if current.get(path) != lock.get("files_sha256", {}).get(path)]
        raise RuntimeError("Confirmatory lock mismatch: " + ", ".join(changed))
    if environment_versions() != lock.get("environment"):
        raise RuntimeError("Confirmatory Python environment differs from lock")
    if summary["total_episodes"] != lock.get("total_episodes"):
        raise RuntimeError("Confirmatory episode count differs from lock")
    return lock


def execute(root: Path, config_path: Path) -> None:
    verify_lock(root, config_path)
    run_benchmark(root, config_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("validate", "freeze", "verify", "run"))
    parser.add_argument("--config", type=Path, default=Path("configs/quadrotor_connectome_confirmatory.yaml"))
    args = parser.parse_args()
    root = Path.cwd()
    if args.action == "validate":
        result = validate(root, args.config)
    elif args.action == "freeze":
        result = freeze(root, args.config)
    elif args.action == "verify":
        result = verify_lock(root, args.config)
    else:
        execute(root, args.config)
        result = {"status": "completed"}
    print(json.dumps(result, indent=2))
