"""Auditable feedforward EPG→Delta7→PFL3 reconstruction candidate."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from flydrone.neural.connectome_pfl3 import ConnectomeWeightedPFL3


def normalize_nonzero_rows(weights: np.ndarray) -> np.ndarray:
    """Normalize populated rows and retain all-zero rows for sparse streams."""
    totals = weights.sum(axis=1, keepdims=True)
    return np.divide(weights, totals, out=np.zeros_like(weights, dtype=float), where=totals > 0)


@dataclass(frozen=True)
class ProjectionAudit:
    edge_count: int
    contact_count: int
    receiving_neurons: int
    minimum_contacts_per_receiving_neuron: int
    maximum_contacts_per_receiving_neuron: int


class EPGDelta7Candidate:
    """Linear signed projection audit using FlyWire contact counts.

    This candidate intentionally omits Delta7 recurrence: anatomy establishes
    those edges and their predicted transmitter, but not a stable recurrent
    gain or time constant. It is an audit model, not an accepted controller.
    """

    CONDITIONS = ("via_delta7", "direct_epg", "contact_fraction_combined")

    def __init__(self, root: Path, config_path: Path):
        self.root = root
        self.config_path = config_path
        self.config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        if self.config["dataset"] != "FAFB" or self.config["materialization_version"] != 783:
            raise ValueError("EPG audit must use the pinned FAFB 783 dataset")
        self.base = ConnectomeWeightedPFL3(root, root / self.config["base_model_config"])
        features = self.base.features
        self.epg = features.loc[features["selected_type"].eq("EPG")].copy()
        angle_by_column = self.config["epg_preferred_heading_deg"]
        if set(self.epg["geometric_column"]) != set(angle_by_column):
            raise ValueError("EPG geometric columns do not match the published 16-column angle map")
        self.epg["preferred_heading_deg"] = self.epg["geometric_column"].map(angle_by_column)
        self.epg = self.epg.sort_values("root_id", key=lambda values: values.astype("uint64")).reset_index(drop=True)
        self.epg_ids = self.epg["root_id"].tolist()
        self.epg_angles_rad = np.deg2rad(self.epg["preferred_heading_deg"].to_numpy(float))

        edges = pd.read_csv(
            root / self.config["neuropil_edges"],
            dtype={"pre_pt_root_id": str, "post_pt_root_id": str},
        )
        edges = edges.loc[edges["neuropil"].eq(self.config["neuropil"])].copy()
        epg_index = {root_id: i for i, root_id in enumerate(self.epg_ids)}
        delta_index = {root_id: i for i, root_id in enumerate(self.base.delta_ids)}
        pfl3_index = self.base.pfl3_index
        self.epg_to_delta_raw, self.epg_to_delta_edges = self._matrix(edges, epg_index, delta_index)
        self.delta_to_delta_raw, self.delta_to_delta_edges = self._matrix(edges, delta_index, delta_index)
        self.delta_to_pfl3_raw, self.delta_to_pfl3_edges = self._matrix(edges, delta_index, pfl3_index)
        self.epg_to_pfl3_raw, self.epg_to_pfl3_edges = self._matrix(edges, epg_index, pfl3_index)

        self.epg_to_delta = normalize_nonzero_rows(self.epg_to_delta_raw)
        self.delta_to_pfl3 = normalize_nonzero_rows(self.delta_to_pfl3_raw)
        self.epg_to_pfl3 = normalize_nonzero_rows(self.epg_to_pfl3_raw)
        signs = self.config["projection_signs"]
        self.via_delta7 = (
            signs["Delta7_to_PFL3"] * self.delta_to_pfl3
            @ (signs["EPG_to_Delta7"] * self.epg_to_delta)
        )
        self.direct_epg = signs["EPG_to_PFL3"] * self.epg_to_pfl3
        direct_contacts = self.epg_to_pfl3_raw.sum(axis=1, keepdims=True)
        delta_contacts = self.delta_to_pfl3_raw.sum(axis=1, keepdims=True)
        total = direct_contacts + delta_contacts
        self.contact_fraction_combined = np.divide(
            direct_contacts * self.direct_epg + delta_contacts * self.via_delta7,
            total,
            out=np.zeros_like(self.direct_epg),
            where=total > 0,
        )

    @staticmethod
    def _matrix(
        edges: pd.DataFrame,
        pre_index: dict[str, int],
        post_index: dict[str, int],
    ) -> tuple[np.ndarray, pd.DataFrame]:
        selected = edges.loc[
            edges["pre_pt_root_id"].isin(pre_index) & edges["post_pt_root_id"].isin(post_index)
        ]
        matrix = np.zeros((len(post_index), len(pre_index)), dtype=float)
        for row in selected.itertuples(index=False):
            matrix[post_index[row.post_pt_root_id], pre_index[row.pre_pt_root_id]] += row.syn_count
        return matrix, selected

    @staticmethod
    def audit(matrix: np.ndarray, edge_count: int) -> ProjectionAudit:
        totals = matrix.sum(axis=1)
        populated = totals[totals > 0]
        return ProjectionAudit(
            edge_count=edge_count,
            contact_count=int(totals.sum()),
            receiving_neurons=int(len(populated)),
            minimum_contacts_per_receiving_neuron=int(populated.min()) if len(populated) else 0,
            maximum_contacts_per_receiving_neuron=int(populated.max()) if len(populated) else 0,
        )

    def transfer(self, condition: str) -> np.ndarray:
        if condition not in self.CONDITIONS:
            raise ValueError(f"Unknown EPG condition: {condition}")
        return getattr(self, condition)

    def effective_heading_drive(
        self, heading_rad: float, condition: str, phase_offset_rad: float = 0.0
    ) -> np.ndarray:
        epg_activity = np.cos(heading_rad - (self.epg_angles_rad + phase_offset_rad))
        return self.transfer(condition) @ epg_activity

    def rates(
        self,
        heading_rad: float,
        goal_rad: float,
        condition: str,
        phase_offset_rad: float = 0.0,
    ) -> np.ndarray:
        heading_drive = self.effective_heading_drive(heading_rad, condition, phase_offset_rad)
        goal = np.cos(goal_rad - self.base.fc2_angles_rad)
        goal_drive = self.base.fc2_weights @ goal
        p = self.base.parameters
        drive = heading_drive + p.goal_input_gain_d * goal_drive
        return p.output_scale_hz_a * np.logaddexp(0.0, p.softplus_slope_b * (drive + p.input_offset_c))

    def phase_fit(self, condition: str) -> dict[str, object]:
        """Fit only the biologically expected global bump-to-heading phase."""
        complex_transfer = self.transfer(condition) @ np.exp(1j * self.epg_angles_rad)
        predicted = np.angle(complex_transfer)
        target = np.deg2rad(self.base.pfl3["preferred_heading_deg"].to_numpy(float))
        valid = np.abs(complex_transfer) > 1e-12
        differences = np.angle(np.exp(1j * (target[valid] - predicted[valid])))
        offset = float(np.angle(np.mean(np.exp(1j * differences))))
        residual = np.abs(np.angle(np.exp(1j * (target[valid] - predicted[valid] - offset))))
        return {
            "phase_offset_deg": float(np.rad2deg(offset)),
            "mean_abs_residual_deg": float(np.rad2deg(residual).mean()),
            "maximum_abs_residual_deg": float(np.rad2deg(residual).max()),
            "valid_pfl3": int(valid.sum()),
            "predicted_preferred_heading_deg": np.rad2deg(predicted),
            "transfer_amplitude": np.abs(complex_transfer),
            "residual_deg": np.rad2deg(residual),
            "valid_mask": valid,
        }
