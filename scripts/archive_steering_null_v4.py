"""Preserve frozen v4 steering-null inputs and hash every result."""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "configs/quadrotor_integrated_v4_steering_null_prospective.lock.json"
RESULTS = ROOT / "results/simulation/quadrotor_integrated_v4_steering_null_prospective"
ARCHIVE = ROOT / "archive/integrated_v4_steering_null"


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def main() -> None:
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    expected = lock["files_sha256"]
    mismatches = [
        relative
        for relative, sha256 in expected.items()
        if not (ROOT / relative).is_file() or digest(ROOT / relative) != sha256
    ]
    if mismatches:
        raise RuntimeError("Frozen steering-null input mismatch: " + ", ".join(mismatches))

    ARCHIVE.mkdir(parents=True, exist_ok=True)
    zip_base = ARCHIVE / "flydrone_integrated_v4_steering_null_frozen_inputs"
    with tempfile.TemporaryDirectory() as temporary:
        staging = Path(temporary) / "flydrone_integrated_v4_steering_null"
        for relative in expected:
            destination = staging / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, destination)
        lock_destination = staging / LOCK.relative_to(ROOT)
        lock_destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(LOCK, lock_destination)
        shutil.make_archive(str(zip_base), "zip", staging)

    zip_path = zip_base.with_suffix(".zip")
    result_hashes = {
        path.relative_to(ROOT).as_posix(): digest(path)
        for path in sorted(RESULTS.rglob("*"))
        if path.is_file()
    }
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "protocol_id": lock["protocol_id"],
        "frozen_input_files": len(expected),
        "frozen_input_archive": zip_path.relative_to(ROOT).as_posix(),
        "frozen_input_archive_sha256": digest(zip_path),
        "result_files": len(result_hashes),
        "result_files_sha256": result_hashes,
    }
    (ARCHIVE / "preservation-manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(
        f"Archived {len(expected)} frozen steering-null inputs and "
        f"hashed {len(result_hashes)} results."
    )


if __name__ == "__main__":
    main()
