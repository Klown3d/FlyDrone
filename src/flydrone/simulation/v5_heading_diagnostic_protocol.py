"""Freeze, verify and run the prospective v5 heading-oracle diagnostic."""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
from pathlib import Path

from flydrone.data.acquire import file_hash, save_json, utc_now
from flydrone.simulation.benchmark_integrated_v2 import load_config, run


EXPECTED_CONDITIONS = {
    "observed_v4", "diagnostic_true_heading", "diagnostic_true_velocity",
    "diagnostic_true_heading_velocity",
}
REFERENCE_CONFIGS = (
    Path("configs/quadrotor_integrated_v4_prospective.yaml"),
    Path("configs/quadrotor_integrated_v4_ood_pilot.yaml"),
)


def environment() -> dict:
    packages = ("numpy", "pandas", "scipy", "PyYAML", "pyarrow", "panda3d")
    return {"python": platform.python_version(),
            "packages": {name: importlib.metadata.version(name) for name in packages}}


def locked_paths(root: Path, config_path: Path) -> list[Path]:
    config = load_config(root, config_path)
    paths = [config_path, Path(config["preregistration_doc"]), Path("pyproject.toml")]
    paths.extend(path.relative_to(root) for path in (root / "src/flydrone").rglob("*.py"))
    paths.extend(path.relative_to(root) for path in (root / "configs").glob("*.yaml"))
    for folder in (root / "data/processed/fafb783_travel_direction",
                   root / "data/processed/fafb783_epg_delta7_fc2_pfl3"):
        paths.extend(path.relative_to(root) for path in folder.rglob("*") if path.is_file())
    paths.append(Path("results/neural/phase_resolved_compass_cross_compartment/transfers.npz"))
    return list(dict.fromkeys(paths))


def validate(root: Path, config_path: Path, allow_output: bool = False) -> dict:
    config = load_config(root, config_path)
    errors: list[str] = []
    if config.get("parameter_status") != "prospectively_frozen_v5_heading_diagnostic_not_controller_validation":
        errors.append("parameter_status is not the frozen v5 diagnostic status")
    if config.get("run_once") is not True:
        errors.append("run_once must be true")
    names = {condition["name"] for condition in config["conditions"]}
    if names != EXPECTED_CONDITIONS:
        errors.append("condition set differs from preregistration")
    cases = len(config["scenarios"]) * len(config["target_bearings_deg"]) * len(config["initial_relative_headings_deg"])
    if cases != 24:
        errors.append(f"expected 24 cases per condition, found {cases}")
    bearings = set(config["target_bearings_deg"])
    headings = set(config["initial_relative_headings_deg"])
    seeds = {scenario["seed"] for scenario in config["scenarios"]}
    for reference_path in REFERENCE_CONFIGS:
        reference = load_config(root, reference_path)
        if bearings & set(reference.get("target_bearings_deg", [])):
            errors.append(f"bearing overlap with {reference_path.as_posix()}")
        if headings & set(reference.get("initial_relative_headings_deg", [])):
            errors.append(f"heading overlap with {reference_path.as_posix()}")
        if seeds & {scenario["seed"] for scenario in reference.get("scenarios", [])}:
            errors.append(f"scenario seed overlap with {reference_path.as_posix()}")
    output = root / config["output"]
    if not allow_output and output.exists() and any(output.iterdir()):
        errors.append("run-once output already exists")
    if errors:
        raise ValueError("Invalid v5 heading diagnostic: " + "; ".join(errors))
    return {"protocol_id": config["protocol_id"], "cases_per_condition": cases,
            "conditions": len(names), "total_episodes": cases * len(names)}


def freeze(root: Path, config_path: Path) -> dict:
    summary = validate(root, config_path)
    config = load_config(root, config_path)
    lock_path = root / config["lock_file"]
    if lock_path.exists():
        raise FileExistsError(lock_path)
    lock = {"created_at": utc_now(), "status": "frozen_before_execution", **summary,
            "environment": environment(),
            "files_sha256": {path.as_posix(): file_hash(root / path)
                             for path in locked_paths(root, config_path)}}
    save_json(lock_path, lock)
    return lock


def verify(root: Path, config_path: Path, allow_output: bool = False) -> dict:
    summary = validate(root, config_path, allow_output=allow_output)
    config = load_config(root, config_path)
    lock = json.loads((root / config["lock_file"]).read_text(encoding="utf-8"))
    current = {path.as_posix(): file_hash(root / path) for path in locked_paths(root, config_path)}
    changed = sorted(path for path in set(current) | set(lock.get("files_sha256", {}))
                     if current.get(path) != lock.get("files_sha256", {}).get(path))
    if changed:
        raise RuntimeError("V5 diagnostic lock mismatch: " + ", ".join(changed))
    if environment() != lock.get("environment"):
        raise RuntimeError("Python environment differs from frozen environment")
    if summary["total_episodes"] != lock.get("total_episodes"):
        raise RuntimeError("Episode count differs from lock")
    return lock


def execute(root: Path, config_path: Path) -> dict:
    verify(root, config_path)
    return run(root, config_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("validate", "freeze", "verify", "run"))
    parser.add_argument("--config", type=Path,
                        default=Path("configs/quadrotor_integrated_v5_heading_diagnostic.yaml"))
    args = parser.parse_args()
    root = Path.cwd()
    if args.action == "validate": result = validate(root, args.config)
    elif args.action == "freeze": result = freeze(root, args.config)
    elif args.action == "verify": result = verify(root, args.config)
    else: result = execute(root, args.config)
    print(json.dumps(result, indent=2))
