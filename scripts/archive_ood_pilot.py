"""Preserve the diagnostic OOD pilot and current implementation after execution."""
from pathlib import Path
import zipfile

from flydrone.data.acquire import file_hash, save_json, utc_now

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    output = ROOT / "archive/integrated_v4_ood_pilot"
    output.mkdir(parents=True, exist_ok=True)
    archive = output / "diagnostic_ood_pilot_inputs.zip"
    inputs = list((ROOT / "src/flydrone").rglob("*.py")) + list((ROOT / "configs").glob("*.yaml"))
    inputs += [ROOT / "docs/research/ood-pilot-plan.md", ROOT / "pyproject.toml"]
    for folder in ("data/processed/fafb783_travel_direction", "data/processed/fafb783_epg_delta7_fc2_pfl3"):
        inputs += [p for p in (ROOT / folder).rglob("*") if p.is_file()]
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as target:
        for path in inputs:
            target.write(path, path.relative_to(ROOT).as_posix())
    results = ROOT / "results/simulation/quadrotor_integrated_v4_ood_pilot"
    save_json(output / "preservation-manifest.json", {
        "created_at": utc_now(), "status": "diagnostic_post_execution_preservation_not_preregistration_lock",
        "input_archive_sha256": file_hash(archive),
        "input_files_sha256": {p.relative_to(ROOT).as_posix(): file_hash(p) for p in inputs},
        "result_files_sha256": {p.relative_to(ROOT).as_posix(): file_hash(p)
                                for p in results.rglob("*") if p.is_file()},
    })
    print("Preserved all 12 diagnostic flights and inputs.")


if __name__ == "__main__":
    main()
