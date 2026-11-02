"""Verified, paired access to preserved steering-gate traces (no rendering)."""
from __future__ import annotations

from dataclasses import dataclass
import json
import hashlib
import sys
import types
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from flydrone.data.acquire import file_hash
from flydrone.simulation.benchmark_integrated_v2 import load_config
from flydrone.neural.steering_connectome_nulls import build_steering_null
from flydrone.neural.steering_interface import activity as steering_activity

GATES = {
    "EPG-Delta7": "epg_delta7",
    "Delta7-PFL3": "delta_pfl3",
    "Steering conjunto": "steering",
    "Piloto OOD": "ood_pilot",
    "Diagnostico OOD": "ood_failure_oracles",
    "Ablaciones v4": "ablations",
}
CASE_KEYS = ["scenario", "target_bearing_deg", "initial_relative_heading_deg"]


@dataclass
class SavedFlight:
    controller: str
    episode: dict
    frame: pd.DataFrame
    path: Path

    def index_at(self, seconds: float) -> int:
        """Hold the last recorded sample; never extrapolate or wrap at the end."""
        return int(np.clip(np.searchsorted(self.frame.time_s, seconds, side="right") - 1,
                           0, len(self.frame) - 1))


class GateArchive:
    """Only expose cases for which both preserved traces actually exist."""

    def __init__(self, root: Path, gate: str):
        self.root = root
        self.slug = GATES[gate]
        self.is_ood = self.slug == "ood_pilot"
        self.is_oracle = self.slug == "ood_failure_oracles"
        self.is_ablation = self.slug == "ablations"
        config_name = ("quadrotor_integrated_v4_ood_failure_oracles.yaml" if self.is_oracle else
                       "quadrotor_integrated_v4_ood_pilot.yaml" if self.is_ood else
                       "quadrotor_integrated_v4_prospective.yaml" if self.is_ablation else
                       f"quadrotor_integrated_v4_{self.slug}_null_prospective.yaml")
        self.config = load_config(
            root, Path("configs") / config_name
        )
        self.folder = root / self.config["output"]
        archive_name = ("integrated_v4_ood_failure_oracles" if self.is_oracle else
                        "integrated_v4_ood_pilot" if self.is_ood else
                        "integrated_v4" if self.is_ablation else
                        f"integrated_v4_{self.slug}_null")
        preservation = root / "archive" / archive_name / "preservation-manifest.json"
        self.manifest = json.loads(preservation.read_text(encoding="utf-8"))
        self.null_builder = build_steering_null
        self.steering_activity = steering_activity
        self._verify_model_inputs()
        self._verify(self.folder / "episodes.csv")
        self.episodes = pd.read_csv(self.folder / "episodes.csv")
        self.intact = ("observed_failure_replication" if self.is_oracle else
                       "full_flywire_v4" if self.is_ood or self.is_ablation else
                       self.config["steering_null_intact_condition"]["name"])
        if self.is_oracle:
            available = set(self.episodes.controller.unique())
            self.nulls = [name for name in (
                "diagnostic_true_heading",
                "diagnostic_true_velocity",
                "diagnostic_true_heading_velocity",
            ) if name in available]
        elif self.is_ablation:
            available = set(self.episodes.controller.unique())
            self.nulls = [name for name in ("delta7_ablated", "no_hdelta", "no_pfl2")
                          if name in available]
        else:
            self.nulls = sorted(name for name in self.episodes.controller.unique() if name != self.intact)
        self._rows: dict[tuple, tuple[dict, Path]] = {}
        for (controller, scenario), group in self.episodes.groupby(["controller", "scenario"], sort=False):
            for index, (_, row) in enumerate(group.iterrows()):
                path = self.folder / "traces" / f"{controller}__{scenario}__{index:02d}.npz"
                if path.is_file():
                    self._rows[(controller, *self.case_key(row))] = (row.to_dict(), path)

    @staticmethod
    def case_key(row) -> tuple:
        return (str(row["scenario"]), round(float(row["target_bearing_deg"]), 8),
                round(float(row["initial_relative_heading_deg"]), 8))

    def _verify(self, path: Path) -> None:
        relative = path.relative_to(self.root).as_posix()
        expected = self.manifest["result_files_sha256"].get(relative)
        if expected is None or file_hash(path) != expected:
            raise ValueError(f"Preserved trace/hash mismatch: {relative}")

    def _verify_model_inputs(self) -> None:
        """Reject changed model code/config/data before assigning activity to root IDs."""
        if self.is_ood or self.is_oracle:
            expected = self.manifest.get("input_files_sha256", {})
        elif "lock_file" in self.config:
            lock = json.loads((self.root / self.config["lock_file"]).read_text(encoding="utf-8"))
            expected = lock["files_sha256"]
        else:
            expected = {}
        prefixes = ("src/flydrone/neural/", "data/processed/", "configs/")
        for relative, digest in expected.items():
            if relative.startswith(prefixes):
                path = self.root / relative
                if not path.is_file() or file_hash(path) != digest:
                    if relative == "src/flydrone/neural/steering_connectome_nulls.py" and not self.is_ood:
                        self.null_builder = self._archived_null_builder(relative, digest)
                        continue
                    if (relative == "src/flydrone/neural/steering_interface.py"
                            and self.is_ablation):
                        self.steering_activity = self._archived_callable(relative, digest, "activity")
                        continue
                    raise ValueError(f"Preserved reconstruction input mismatch: {relative}")

    def _archived_null_builder(self, relative: str, expected: str):
        """Use this project's hashed original generator when its interface evolved."""
        return self._archived_callable(relative, expected, "build_steering_null")

    def _archived_callable(self, relative: str, expected: str, callable_name: str):
        """Load one verified callable from the frozen project input archive."""
        archive_path = self.root / self.manifest["frozen_input_archive"]
        if file_hash(archive_path) != self.manifest["frozen_input_archive_sha256"]:
            raise ValueError("Frozen input archive hash mismatch")
        with zipfile.ZipFile(archive_path) as archive:
            source = archive.read(relative)
        if hashlib.sha256(source).hexdigest() != expected:
            raise ValueError("Frozen null generator hash mismatch")
        name = "_flydrone_frozen_" + expected[:16]
        if name not in sys.modules:
            module = types.ModuleType(name)
            module.__file__ = f"{archive_path.name}/{relative}"
            sys.modules[name] = module
            exec(compile(source, module.__file__, "exec"), module.__dict__)
        return getattr(sys.modules[name], callable_name)

    def paired_cases(self, other: str) -> list[tuple]:
        return [key[1:] for key in self._rows
                if key[0] == self.intact and (other, *key[1:]) in self._rows]

    def load(self, controller: str, case: tuple) -> SavedFlight:
        episode, path = self._rows[(controller, *case)]
        self._verify(path)
        with np.load(path, allow_pickle=False) as archive:
            frame = pd.DataFrame(archive["values"], columns=archive["columns"].tolist())
        required = ["time_s", "x_m", "y_m", "z_m", "yaw_rad", "observed_yaw_rad", "goal_rad"]
        if frame.empty or not all(name in frame for name in required):
            raise ValueError(f"Missing replay columns: {path.name}")
        if not np.isfinite(frame[required].to_numpy()).all() or np.any(np.diff(frame.time_s) <= 0):
            raise ValueError(f"Invalid trace timing/values: {path.name}")
        return SavedFlight(controller, episode, frame, path)
