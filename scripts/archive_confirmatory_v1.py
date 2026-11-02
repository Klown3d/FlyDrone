"""Archive frozen v1 inputs and hash all execute-once outputs.

The archive permits later v2 development without losing the exact source and
data state that generated the confirmatory result. Large trace files are not
duplicated; their hashes are recorded in a separate immutable manifest.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "configs/quadrotor_connectome_confirmatory.lock.json"
RESULTS = ROOT / "results/simulation/quadrotor_connectome_confirmatory_v1"
ARCHIVE_DIR = ROOT / "archive/confirmatory_v1"


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def main() -> None:
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    expected = lock["files_sha256"]
    mismatches = [
        relative
        for relative, sha256 in expected.items()
        if not (ROOT / relative).is_file() or digest(ROOT / relative) != sha256
    ]
    if mismatches:
        raise RuntimeError("Frozen input mismatch: " + ", ".join(mismatches))

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    zip_base = ARCHIVE_DIR / "flydrone_pfn_hdelta_confirmatory_v1_frozen_inputs"
    with tempfile.TemporaryDirectory() as temporary:
        staging = Path(temporary) / "flydrone_pfn_hdelta_confirmatory_v1"
        for relative in expected:
            destination = staging / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, destination)
        lock_destination = staging / LOCK_PATH.relative_to(ROOT)
        lock_destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(LOCK_PATH, lock_destination)
        shutil.make_archive(str(zip_base), "zip", staging)

    zip_path = zip_base.with_suffix(".zip")
    zip_hash = digest(zip_path)
    zip_path.with_suffix(".zip.sha256").write_text(
        f"{zip_hash}  {zip_path.name}\n", encoding="utf-8"
    )

    output_hashes = {
        path.relative_to(ROOT).as_posix(): digest(path)
        for path in sorted(RESULTS.rglob("*"))
        if path.is_file()
    }
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "protocol_id": lock["protocol_id"],
        "purpose": "post-execution preservation; does not alter the frozen gate",
        "frozen_input_files": len(expected),
        "frozen_input_archive": zip_path.relative_to(ROOT).as_posix(),
        "frozen_input_archive_sha256": zip_hash,
        "result_files": len(output_hashes),
        "result_files_sha256": output_hashes,
    }
    (ARCHIVE_DIR / "preservation-manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(
        f"Archived {len(expected)} frozen inputs and hashed "
        f"{len(output_hashes)} result files."
    )


if __name__ == "__main__":
    main()
