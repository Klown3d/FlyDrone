"""Validate and freeze the prospective EPG→Delta7→PFL3 null gate."""

from __future__ import annotations

import json
from pathlib import Path

from flydrone.data.acquire import file_hash, save_json, utc_now
from flydrone.simulation.benchmark_integrated_v2 import load_config
from flydrone.simulation.integrated_v2_protocol import environment, locked_paths


def validate(root: Path, config_path: Path, allow_output: bool = False) -> dict:
    config = load_config(root, config_path)
    errors: list[str] = []
    seeds = [int(seed) for seed in config.get("steering_null_seeds", [])]
    cases = (
        len(config["scenarios"])
        * len(config["target_bearings_deg"])
        * len(config["initial_relative_headings_deg"])
    )
    frozen_statuses = {
        "prospectively_frozen_v4_steering_side_block_null_attribution",
        "prospectively_frozen_v4_delta_to_pfl3_side_block_null_attribution",
        "prospectively_frozen_v4_epg_to_delta7_side_block_null_attribution",
    }
    if config.get("parameter_status") not in frozen_statuses:
        errors.append("parameter_status is not frozen")
    if config.get("run_once") is not True:
        errors.append("run_once must be true")
    if len(seeds) != 20 or len(set(seeds)) != 20:
        errors.append("exactly 20 unique steering-null seeds are required")
    if cases != 12:
        errors.append("exactly 12 paired cases are required")
    if float(config["primary_gate"]["maximum_empirical_rank_p"]) != 0.05:
        errors.append("empirical rank threshold differs from preregistration")
    if (
        config.get("parameter_status")
        == "prospectively_frozen_v4_delta_to_pfl3_side_block_null_attribution"
        and config.get("steering_null_condition_template", {}).get("steering_null_projection")
        != "delta_to_pfl3"
    ):
        errors.append("projection-specific protocol must rewire only Delta7-to-PFL3")
    if (
        config.get("parameter_status")
        == "prospectively_frozen_v4_epg_to_delta7_side_block_null_attribution"
        and config.get("steering_null_condition_template", {}).get("steering_null_projection")
        != "epg_to_delta"
    ):
        errors.append("projection-specific protocol must rewire only EPG-to-Delta7")
    output = root / config["output"]
    if not allow_output and output.exists() and any(output.iterdir()):
        errors.append("run-once output already exists")
    if errors:
        raise ValueError("Invalid steering-null protocol: " + "; ".join(errors))
    return {
        "protocol_id": config["protocol_id"],
        "cases_per_condition": cases,
        "null_conditions": len(seeds),
        "total_episodes": cases * (len(seeds) + 1),
    }


def freeze(root: Path, config_path: Path) -> dict:
    summary = validate(root, config_path)
    config = load_config(root, config_path)
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
    summary = validate(root, config_path, allow_output)
    config = load_config(root, config_path)
    lock = json.loads((root / config["lock_file"]).read_text(encoding="utf-8"))
    current = {
        path.as_posix(): file_hash(root / path) for path in locked_paths(root, config_path)
    }
    if current != lock.get("files_sha256"):
        raise RuntimeError("Steering-null lock mismatch")
    if environment() != lock.get("environment"):
        raise RuntimeError("Frozen steering-null environment differs")
    if summary["total_episodes"] != lock.get("total_episodes"):
        raise RuntimeError("Frozen steering-null episode count differs")
    return lock
