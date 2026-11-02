"""Freeze and execute the prospective v4 PFN-to-hDeltaB null distribution."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from flydrone.data.acquire import file_hash, save_json, utc_now
from flydrone.simulation.benchmark_integrated_v2 import load_config, run
from flydrone.simulation.integrated_v2_protocol import environment, locked_paths


def validate(root: Path, config_path: Path, allow_output: bool = False) -> dict:
    config = load_config(root, config_path)
    errors: list[str] = []
    seeds = [int(seed) for seed in config.get("block_null_seeds", [])]
    cases = len(config["scenarios"]) * len(config["target_bearings_deg"]) * len(config["initial_relative_headings_deg"])
    if config.get("parameter_status") != "prospectively_frozen_v4_hdelta_block_null_attribution":
        errors.append("parameter_status is not frozen")
    if config.get("run_once") is not True:
        errors.append("run_once must be true")
    if len(seeds) != 20 or len(set(seeds)) != 20:
        errors.append("exactly 20 unique null seeds are required")
    if cases != 12:
        errors.append("exactly 12 paired cases are required")
    if float(config["primary_gate"]["maximum_empirical_rank_p"]) != 0.05:
        errors.append("empirical rank threshold differs from preregistration")
    output = root / config["output"]
    if not allow_output and output.exists() and any(output.iterdir()):
        errors.append("run-once output already exists")
    if errors:
        raise ValueError("Invalid connectome-null protocol: " + "; ".join(errors))
    return {"protocol_id": config["protocol_id"], "cases_per_condition": cases,
            "null_conditions": len(seeds), "total_episodes": cases * (len(seeds) + 1)}


def freeze(root: Path, config_path: Path) -> dict:
    summary = validate(root, config_path)
    config = load_config(root, config_path)
    lock_path = root / config["lock_file"]
    if lock_path.exists():
        raise FileExistsError(lock_path)
    lock = {"created_at": utc_now(), "status": "frozen_before_execution", **summary,
            "environment": environment(), "files_sha256": {
                path.as_posix(): file_hash(root / path)
                for path in locked_paths(root, config_path)}}
    save_json(lock_path, lock)
    return lock


def verify(root: Path, config_path: Path, allow_output: bool = False) -> dict:
    summary = validate(root, config_path, allow_output)
    config = load_config(root, config_path)
    lock = json.loads((root / config["lock_file"]).read_text(encoding="utf-8"))
    current = {path.as_posix(): file_hash(root / path) for path in locked_paths(root, config_path)}
    if current != lock.get("files_sha256"):
        raise RuntimeError("Connectome-null lock mismatch")
    if environment() != lock.get("environment") or summary["total_episodes"] != lock.get("total_episodes"):
        raise RuntimeError("Frozen connectome-null environment or episode count differs")
    return lock


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("validate", "freeze", "verify", "run"))
    parser.add_argument("--config", type=Path, default=Path("configs/quadrotor_integrated_v4_connectome_null_prospective.yaml"))
    args = parser.parse_args(); root = Path.cwd()
    if args.action == "validate": result = validate(root, args.config)
    elif args.action == "freeze": result = freeze(root, args.config)
    elif args.action == "verify": result = verify(root, args.config)
    else: verify(root, args.config); result = run(root, args.config)
    print(json.dumps(result, indent=2))
