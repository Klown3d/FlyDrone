"""Preserve frozen obstacle-gate inputs and hash every output artifact."""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from flydrone.data.acquire import file_hash, save_json, utc_now


ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "configs/free_navigation_obstacles_gate_v1.lock.json"
RESULTS = ROOT / "results/simulation/free_navigation_obstacles_gate_v1"
ARCHIVE = ROOT / "archive/free_navigation_obstacles_gate_v1"


def main() -> None:
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    expected = lock["files_sha256"]
    mismatches = [relative for relative, digest in expected.items()
                  if not (ROOT / relative).is_file() or file_hash(ROOT / relative) != digest]
    if mismatches:
        raise RuntimeError("Frozen obstacle-gate input mismatch: " + ", ".join(mismatches))
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    zip_base = ARCHIVE / "flydrone_obstacle_navigation_gate_v1_frozen_inputs"
    with tempfile.TemporaryDirectory() as temporary:
        staging = Path(temporary) / "flydrone_obstacle_navigation_gate_v1"
        for relative in expected:
            destination = staging / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, destination)
        destination = staging / LOCK.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(LOCK, destination)
        shutil.make_archive(str(zip_base), "zip", staging)
    archive = zip_base.with_suffix(".zip")
    result_hashes = {path.relative_to(ROOT).as_posix(): file_hash(path)
                     for path in sorted(RESULTS.rglob("*")) if path.is_file()}
    save_json(ARCHIVE / "preservation-manifest.json", {
        "created_at": utc_now(),
        "status": "prospective_obstacle_navigation_gate_v1_preserved_after_execution",
        "protocol_id": lock["protocol_id"],
        "frozen_input_files": len(expected),
        "frozen_input_archive": archive.relative_to(ROOT).as_posix(),
        "frozen_input_archive_sha256": file_hash(archive),
        "result_files": len(result_hashes),
        "result_files_sha256": result_hashes,
    })
    print(f"Archived {len(expected)} frozen inputs and hashed {len(result_hashes)} result files.")


if __name__ == "__main__":
    main()
