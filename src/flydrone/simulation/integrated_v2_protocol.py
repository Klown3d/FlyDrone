"""Freeze, verify and execute the integrated FlyDrone v2 prospective gate."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
from pathlib import Path

import yaml

from flydrone.data.acquire import file_hash, save_json, utc_now
from flydrone.simulation.benchmark_integrated_v2 import run as run_gate


def load(root: Path, relative: Path, seen: set[Path] | None = None) -> dict:
    path = Path(relative)
    visited = set() if seen is None else set(seen)
    if path in visited:
        raise ValueError(f"Circular base_config inheritance at {path}")
    visited.add(path)
    spec = yaml.safe_load((root / path).read_text(encoding="utf-8"))
    if "base_config" not in spec:
        return spec
    return {**load(root, Path(spec["base_config"]), visited), **spec}


def locked_paths(root: Path, config_path: Path) -> list[Path]:
    config = load(root, config_path)
    paths: list[Path] = [config_path]
    paths.extend(path.relative_to(root) for path in (root / "src/flydrone").rglob("*.py"))
    paths.extend(path.relative_to(root) for path in (root / "configs").glob("*.yaml"))
    for folder in (
        root / "data/processed/fafb783_travel_direction",
        root / "data/processed/fafb783_epg_delta7_fc2_pfl3",
    ):
        paths.extend(path.relative_to(root) for path in folder.rglob("*") if path.is_file())
    paths.extend(
        [
            Path("results/neural/phase_resolved_compass_cross_compartment/transfers.npz"),
            Path("pyproject.toml"),
            Path(config.get("preregistration_doc", "docs/research/integrated-v2-preregistration.md")),
        ]
    )
    return list(dict.fromkeys(paths))


def environment() -> dict:
    packages = ("numpy", "pandas", "scipy", "PyYAML", "pyarrow", "panda3d")
    return {
        "python": platform.python_version(),
        "packages": {name: importlib.metadata.version(name) for name in packages},
    }


def validate(root: Path, config_path: Path, allow_output: bool = False) -> dict:
    config = load(root, config_path)
    errors: list[str] = []
    frozen_statuses = {
        "prospectively_frozen_integrated_v2_after_one_development_cycle",
        "prospectively_frozen_integrated_v3_after_terminal_development",
        "prospectively_frozen_integrated_v4_after_lateral_development",
    }
    if config.get("parameter_status") not in frozen_statuses:
        errors.append("parameter_status is not frozen")
    if config.get("run_once") is not True:
        errors.append("run_once must be true")
    conditions = {condition["name"] for condition in config["conditions"]}
    full_name = config.get("gate_controller_names", {}).get("full", "full_flywire_v2")
    required = {
        full_name,
        "no_pfl2",
        "no_hdelta",
        "delta7_ablated",
        "direct_velocity_matched",
        "conventional_navigation",
    }
    if conditions != required:
        errors.append("condition set differs from preregistration")
    cases = len(config["scenarios"]) * len(config["target_bearings_deg"]) * len(config["initial_relative_headings_deg"])
    if cases != 30:
        errors.append("expected exactly 30 cases per condition")
    output = root / config["output"]
    if not allow_output and output.exists() and any(output.iterdir()):
        errors.append("run-once output already exists")
    if errors:
        raise ValueError("Invalid integrated protocol: " + "; ".join(errors))
    return {
        "protocol_id": config["protocol_id"],
        "cases_per_condition": cases,
        "conditions": len(conditions),
        "total_episodes": cases * len(conditions),
    }


def freeze(root: Path, config_path: Path) -> dict:
    summary = validate(root, config_path)
    config = load(root, config_path)
    lock_path = root / config["lock_file"]
    if lock_path.exists():
        raise FileExistsError(lock_path)
    lock = {
        "created_at": utc_now(),
        "status": "frozen_before_execution",
        **summary,
        "environment": environment(),
        "files_sha256": {
            path.as_posix(): file_hash(root / path) for path in locked_paths(root, config_path)
        },
    }
    save_json(lock_path, lock)
    return lock


def verify(root: Path, config_path: Path, allow_output: bool = False) -> dict:
    summary = validate(root, config_path, allow_output=allow_output)
    config = load(root, config_path)
    lock = json.loads((root / config["lock_file"]).read_text(encoding="utf-8"))
    current = {
        path.as_posix(): file_hash(root / path) for path in locked_paths(root, config_path)
    }
    if current != lock.get("files_sha256"):
        changed = sorted(
            path
            for path in set(current) | set(lock.get("files_sha256", {}))
            if current.get(path) != lock.get("files_sha256", {}).get(path)
        )
        raise RuntimeError("Integrated protocol lock mismatch: " + ", ".join(changed))
    if environment() != lock.get("environment"):
        raise RuntimeError("Python environment differs from frozen environment")
    if summary["total_episodes"] != lock.get("total_episodes"):
        raise RuntimeError("Episode count differs from lock")
    return lock


def execute(root: Path, config_path: Path) -> dict:
    verify(root, config_path)
    return run_gate(root, config_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("validate", "freeze", "verify", "run"))
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/quadrotor_integrated_v2_prospective.yaml"),
    )
    args = parser.parse_args()
    root = Path.cwd()
    if args.action == "validate":
        result = validate(root, args.config)
    elif args.action == "freeze":
        result = freeze(root, args.config)
    elif args.action == "verify":
        result = verify(root, args.config)
    else:
        result = execute(root, args.config)
    print(json.dumps(result, indent=2))
