"""FlyWire-weighted PFL2 goal-misalignment audit model."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from flydrone.neural.connectome_pfl3 import (
    ConnectomeWeightedPFL3,
    row_normalize,
    weighted_circular_mean_deg,
)


@dataclass(frozen=True)
class PFL2StreamAudit:
    presynaptic_neurons: int
    contact_count: int
    minimum_contacts_per_pfl2: int
    maximum_contacts_per_pfl2: int


class ConnectomeWeightedPFL2:
    """Compare heading and goal through FAFB Δ7/FC2→PFL2 contacts.

    Contact matrices and cell identities are anatomical. Presynaptic phase
    assignments are inherited from the provisional PFL3 model. Half-wave
    rectification and population calibration are engineering abstractions, not
    measured PFL2 firing rates or synaptic gains.
    """

    def __init__(self, root: Path, config_path: Path):
        self.config_path = config_path
        self.config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        if self.config["dataset"] != "FAFB" or self.config["materialization_version"] != 783:
            raise ValueError("PFL2 model must use the pinned FAFB 783 dataset")
        self.base = ConnectomeWeightedPFL3(root, root / self.config["base_pfl3_config"])
        self.nodes = pd.read_csv(root / self.config["nodes"], dtype={"root_id": str})
        edges = pd.read_csv(
            root / self.config["edges"],
            dtype={"pre_pt_root_id": str, "post_pt_root_id": str},
        )
        types = dict(zip(self.nodes["root_id"], self.nodes["selected_type"]))
        edges["pre_type"] = edges["pre_pt_root_id"].map(types)
        edges["post_type"] = edges["post_pt_root_id"].map(types)

        self.pfl2 = self.nodes.loc[self.nodes["selected_type"].eq("PFL2")].copy()
        self.pfl2 = self.pfl2.sort_values("root_id", key=lambda x: x.astype("uint64")).reset_index(drop=True)
        self.pfl2_ids = self.pfl2["root_id"].tolist()
        pfl2_index = {root_id: i for i, root_id in enumerate(self.pfl2_ids)}

        self.delta_ids = self.base.delta_ids
        delta_index = {root_id: i for i, root_id in enumerate(self.delta_ids)}
        self.fc2_ids = self.base.fc2_ids
        fc2_index = {root_id: i for i, root_id in enumerate(self.fc2_ids)}

        delta_edges = edges.loc[
            edges["pre_pt_root_id"].isin(delta_index) & edges["post_pt_root_id"].isin(pfl2_index)
        ]
        fc2_edges = edges.loc[
            edges["pre_pt_root_id"].isin(fc2_index) & edges["post_pt_root_id"].isin(pfl2_index)
        ]
        self.delta_weights_raw = self._matrix(delta_edges, pfl2_index, delta_index)
        self.fc2_weights_raw = self._matrix(fc2_edges, pfl2_index, fc2_index)
        self.delta_weights = row_normalize(self.delta_weights_raw)
        self.fc2_weights = row_normalize(self.fc2_weights_raw)
        self.delta_audit = self._audit(self.delta_weights_raw)
        self.fc2_audit = self._audit(self.fc2_weights_raw)
        self.phase_audit = self._phase_audit()

    @staticmethod
    def _matrix(edges: pd.DataFrame, post_index: dict[str, int], pre_index: dict[str, int]) -> np.ndarray:
        result = np.zeros((len(post_index), len(pre_index)), dtype=float)
        for row in edges.itertuples(index=False):
            result[post_index[row.post_pt_root_id], pre_index[row.pre_pt_root_id]] += row.syn_count
        return result

    @staticmethod
    def _audit(matrix: np.ndarray) -> PFL2StreamAudit:
        totals = matrix.sum(axis=1)
        return PFL2StreamAudit(
            presynaptic_neurons=int(np.sum(matrix.sum(axis=0) > 0)),
            contact_count=int(matrix.sum()),
            minimum_contacts_per_pfl2=int(totals.min()),
            maximum_contacts_per_pfl2=int(totals.max()),
        )

    def _phase_audit(self) -> pd.DataFrame:
        delta_deg = np.rad2deg(self.base.delta_angles_rad)
        fc2_deg = np.rad2deg(self.base.fc2_angles_rad)
        rows = []
        for i, root_id in enumerate(self.pfl2_ids):
            delta_phase, delta_r = weighted_circular_mean_deg(delta_deg, self.delta_weights_raw[i])
            fc2_phase, fc2_r = weighted_circular_mean_deg(fc2_deg, self.fc2_weights_raw[i])
            relation = float(np.rad2deg(np.angle(np.exp(1j * np.deg2rad(delta_phase - fc2_phase)))))
            rows.append({
                "root_id": root_id,
                "soma_side": self.pfl2.loc[i, "side"],
                "delta_phase_deg": delta_phase,
                "delta_resultant": delta_r,
                "fc2_phase_deg": fc2_phase,
                "fc2_resultant": fc2_r,
                "delta_minus_fc2_deg": relation,
                "delta_contacts": int(self.delta_weights_raw[i].sum()),
                "fc2_contacts": int(self.fc2_weights_raw[i].sum()),
            })
        return pd.DataFrame(rows)

    def activity(self, heading_rad: float, goal_rad: float) -> np.ndarray:
        """Return a dimensionless engineering activation in [0, 1]."""
        heading = np.cos(heading_rad - self.base.delta_angles_rad)
        goal = np.cos(goal_rad - self.base.fc2_angles_rad)
        drive = self.delta_weights @ heading + self.fc2_weights @ goal
        return np.clip(np.maximum(0.0, drive) / 2.0, 0.0, 1.0)

    def population_activity(self, heading_rad: float, goal_rad: float) -> float:
        return float(self.activity(heading_rad, goal_rad).mean())

    def anti_goal_index(self, heading_rad: float, goal_rad: float) -> float:
        """Calibrate population activity between aligned=0 and antialigned=1."""
        aligned = self.population_activity(goal_rad, goal_rad)
        antialigned = self.population_activity(goal_rad + np.pi, goal_rad)
        current = self.population_activity(heading_rad, goal_rad)
        if antialigned <= aligned:
            raise ValueError("PFL2 contact model does not activate more strongly at the antimeta")
        return float(np.clip((current - aligned) / (antialigned - aligned), 0.0, 1.0))
