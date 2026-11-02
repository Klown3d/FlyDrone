"""Preserve the post-hoc OOD oracle diagnosis and the exact model inputs used."""

from pathlib import Path
import zipfile

from flydrone.data.acquire import file_hash, save_json, utc_now


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    output = ROOT / "archive/integrated_v4_ood_failure_oracles"
    output.mkdir(parents=True, exist_ok=True)
    archive = output / "diagnostic_ood_failure_oracle_inputs.zip"
    inputs = list((ROOT / "src/flydrone").rglob("*.py"))
    inputs += [
        ROOT / "configs/quadrotor_integrated_v4_ood_failure_oracles.yaml",
        ROOT / "configs/quadrotor_integrated_v4_prospective.yaml",
        ROOT / "configs/orientation_candidate_v1.yaml",
        ROOT / "configs/pfl2_steering.yaml",
        ROOT / "configs/pfl2_advance.yaml",
        ROOT / "configs/travel_direction_drift.yaml",
        ROOT / "configs/travel_velocity_inertial.yaml",
        ROOT / "docs/research/ood-failure-oracle-diagnosis.md",
        ROOT / "pyproject.toml",
    ]
    for folder in (
        "data/processed/fafb783_travel_direction",
        "data/processed/fafb783_epg_delta7_fc2_pfl3",
    ):
        inputs += [path for path in (ROOT / folder).rglob("*") if path.is_file()]
    inputs = sorted(set(inputs))
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as target:
        for path in inputs:
            target.write(path, path.relative_to(ROOT).as_posix())
    results = ROOT / "results/simulation/quadrotor_integrated_v4_ood_failure_oracles"
    save_json(output / "preservation-manifest.json", {
        "created_at": utc_now(),
        "status": "post_hoc_diagnostic_oracle_preservation_not_preregistration_lock",
        "frozen_input_archive": archive.relative_to(ROOT).as_posix(),
        "frozen_input_archive_sha256": file_hash(archive),
        "input_files_sha256": {
            path.relative_to(ROOT).as_posix(): file_hash(path) for path in inputs
        },
        "result_files_sha256": {
            path.relative_to(ROOT).as_posix(): file_hash(path)
            for path in results.rglob("*") if path.is_file()
        },
    })
    print("Preserved four diagnostic oracle flights, derived analysis, and exact inputs.")


if __name__ == "__main__":
    main()
