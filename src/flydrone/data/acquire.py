"""Acquire only manifest-listed artifacts; refuse unannounced remote changes."""
from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def request(url: str) -> Any:
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "FlyDrone-research/0.1"}), timeout=90)


def fetch_json(url: str) -> dict[str, Any]:
    with request(url) as response:
        return json.load(response)


def file_hash(path: Path, algorithm: str = "sha256") -> str:
    digest = hashlib.new("sha1" if algorithm == "git-blob-sha1" else algorithm)
    if algorithm == "git-blob-sha1":
        digest.update(f"blob {path.stat().st_size}\0".encode())
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(path: Path, artifact: dict[str, Any]) -> str:
    if path.stat().st_size != artifact["published_size_bytes"]:
        raise ValueError(f"Size mismatch: {path.name}")
    expected = artifact["published_checksum"]
    if file_hash(path, expected["algorithm"]) != expected["value"]:
        raise ValueError(f"Published checksum mismatch: {path.name}")
    return file_hash(path)


def download(url: str, path: Path, artifact: dict[str, Any]) -> dict[str, Any]:
    """Download atomically, bounded by expected size; HTML is never accepted."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".part")
    print(f"Downloading {path.name}: {artifact['published_size_bytes']:,} bytes", flush=True)
    with request(url) as response, temp.open("wb") as stream:
        mime = response.headers.get("Content-Type", "")
        if "text/html" in mime:
            raise ValueError(f"HTML returned instead of data: {url}")
        total, last = 0, time.monotonic()
        while chunk := response.read(4 * 1024 * 1024):
            total += len(chunk)
            if total > artifact["published_size_bytes"]:
                raise ValueError("Download exceeds pinned size")
            stream.write(chunk)
            if time.monotonic() - last > 15:
                print(f"  {total / 1e6:.1f} MB", flush=True)
                last = time.monotonic()
        result = {"resolved_download_url": response.url, "content_type": mime,
                  "retrieved_at": utc_now()}
    result["local_sha256"] = verify(temp, artifact)
    temp.replace(path)
    return result


def download_ranges(url: str, path: Path, artifact: dict[str, Any], workers: int) -> dict[str, Any]:
    """Bounded static-file ranges; verify each response range and final hash.

    Completed segments are reusable after interruption. No UI/live queries.
    """
    size = artifact["published_size_bytes"]
    parts = path.parent / (path.name + ".segments")
    parts.mkdir(parents=True, exist_ok=True)
    block = 16 * 1024 * 1024
    ranges = [(start, min(start + block, size) - 1) for start in range(0, size, block)]
    def valid_part(bounds: tuple[int, int]) -> bool:
        start, end = bounds
        target = parts / f"{start:012d}-{end:012d}"
        return target.exists() and target.stat().st_size == end - start + 1

    def fetch(bounds: tuple[int, int]) -> Path:
        start, end = bounds
        target = parts / f"{start:012d}-{end:012d}"
        expected = end - start + 1
        tmp = target.with_suffix(".part")
        for attempt in range(6):
            try:
                req = urllib.request.Request(
                    url,
                    headers={"Range": f"bytes={start}-{end}", "User-Agent": "FlyDrone-research/0.1"},
                )
                with urllib.request.urlopen(req, timeout=90) as response:
                    if response.status != 206 or response.headers.get("Content-Range") != f"bytes {start}-{end}/{size}":
                        raise ValueError("Server did not honor requested byte range")
                    received = 0
                    with tmp.open("wb") as stream:
                        while chunk := response.read(1024 * 1024):
                            received += len(chunk)
                            if received > expected:
                                raise ValueError("Oversized segment")
                            stream.write(chunk)
                    if received != expected:
                        raise ValueError("Incomplete segment")
                    tmp.replace(target)
                return target
            except (OSError, urllib.error.URLError):
                tmp.unlink(missing_ok=True)
                if attempt == 5:
                    raise
                time.sleep(min(2 ** (attempt + 1), 30))
        raise RuntimeError("Unreachable range retry state")
    completed = sum(valid_part(bounds) for bounds in ranges)
    pending = [bounds for bounds in ranges if not valid_part(bounds)]
    print(
        f"Downloading {path.name} in {len(ranges)} ranges, {workers} workers; "
        f"reusing {completed}, pending {len(pending)}",
        flush=True,
    )
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for index, future in enumerate(as_completed([pool.submit(fetch, bounds) for bounds in pending]), completed + 1):
            future.result()
            print(f"  complete ranges {index}/{len(ranges)}", flush=True)
    temp = path.with_suffix(path.suffix + ".part")
    with temp.open("wb") as stream:
        for start, end in ranges:
            with (parts / f"{start:012d}-{end:012d}").open("rb") as part:
                for chunk in iter(lambda: part.read(4 * 1024 * 1024), b""):
                    stream.write(chunk)
    sha = verify(temp, artifact)
    temp.replace(path)
    # Delete only known segment files from this artifact after full verification.
    for start, end in ranges:
        (parts / f"{start:012d}-{end:012d}").unlink()
    parts.rmdir()
    return {"resolved_download_url": url, "content_type": "application/octet-stream",
            "retrieved_at": utc_now(), "local_sha256": sha, "download_method": "verified_http_ranges"}


def acquire(manifest_path: Path, only: str | None = None, workers: int = 1) -> None:
    root = manifest_path.resolve().parent.parent
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    archive_url = "https://zenodo.org/api/records/10676866"
    archive = fetch_json(archive_url)
    if archive["metadata"]["version"] != manifest["dataset"]["connectivity_archive_version"]:
        raise ValueError("Archive version changed")
    metadata_path = root / "data/raw/zenodo-10676866.metadata.json"
    save_json(metadata_path, archive)
    remote = {f["key"]: f for f in archive["files"]}
    for artifact in manifest["artifacts"]:
        if only and artifact["name"] != only:
            continue
        name = artifact["name"]
        if Path(name).name != name:
            raise ValueError("Artifact name must be a basename")
        path = root / "data/raw" / name
        if name in remote:
            info = remote[name]
            expected = artifact["published_checksum"]
            if info["size"] != artifact["published_size_bytes"] or info["checksum"] != f"{expected['algorithm']}:{expected['value']}":
                raise ValueError(f"Pinned metadata changed for {name}")
            url = info["links"]["self"]
            artifact["license_verified"] = archive["metadata"]["license"]["id"]
            artifact["license_source"] = archive_url
        else:
            url = artifact["source_url"]
            commit = manifest["dataset"]["annotation_commit"]
            if commit not in url:
                raise ValueError("Annotation URL is not pinned")
            # No license file was present at the pinned repository root. Do not
            # invent a license or apply the connectivity archive license to it.
            artifact["license_verified"] = None
            artifact["license_note"] = "No explicit license found in pinned repository root; attribution retained; redistribution terms need clarification."
        if path.exists():
            sha = verify(path, artifact)
            if not artifact.get("retrieved_at"):
                raise ValueError(f"Existing file lacks acquisition provenance: {name}")
            artifact["local_sha256"] = sha
            print(f"Verified cache: {name}", flush=True)
        else:
            if workers > 1 and artifact["published_size_bytes"] > 100_000_000:
                artifact.update(download_ranges(url, path, artifact, workers))
            else:
                artifact.update(download(url, path, artifact))
        artifact.update(status="downloaded_verified", local_path=path.relative_to(root).as_posix(),
                        verified_at=utc_now())
        manifest["status"] = "acquisition_in_progress"
        manifest["phase"] = "1_data_acquisition"
        save_json(manifest_path, manifest)
    if all(a["status"] == "downloaded_verified" for a in manifest["artifacts"]):
        manifest["status"] = "acquired_verified_pending_extraction"
    manifest["notes"] = ["Acquisition status is recorded separately for every artifact.",
        "Published checksums and local SHA-256 verified; anatomy and annotation versions pinned separately.",
        "No neural dynamics or simulator implemented. Annotation redistribution license remains unresolved."]
    save_json(manifest_path, manifest)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("data/manifest.json"))
    parser.add_argument("--only", help="Acquire one exact manifest artifact name")
    parser.add_argument("--workers", type=int, choices=range(1, 9), default=1, help="Concurrent static-file ranges for large artifacts (1-8)")
    args = parser.parse_args()
    acquire(args.manifest, args.only, args.workers)
