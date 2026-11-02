"""Contact-weighted PFNd/PFNv to hDeltaB allocentric travel-direction model."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import yaml


def wrap(angle: float | np.ndarray) -> float | np.ndarray:
    return np.angle(np.exp(1j * angle))


class ConnectomeTravelDirection:
    """Decode allocentric travel direction from a baseline-subtracted phasor model.

    Cell identities, phases, columns, and PFN→hDeltaB contact weights are tied to
    FAFB 783. The egocentric velocity encoder, signed cosine modulation, and
    global phase anchor are literature-constrained computational abstractions.
    """

    def __init__(self, root: Path, config_path: Path):
        self.config_path = config_path
        self.config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        mapping = pd.read_csv(root / self.config["column_mapping"], dtype={"root_id": str})
        edges = pd.read_csv(root / self.config["edges"], dtype={"pre_pt_root_id": str, "post_pt_root_id": str})
        self.pfn = mapping.loc[mapping["selected_type"].isin(["PFNd", "PFNv"])].reset_index(drop=True)
        self.hdelta = mapping.loc[mapping["selected_type"].eq("hDeltaB")].reset_index(drop=True)
        pfn_index = {root_id: i for i, root_id in enumerate(self.pfn["root_id"])}
        hdelta_index = {root_id: i for i, root_id in enumerate(self.hdelta["root_id"])}
        self.weights = np.zeros((len(self.hdelta), len(self.pfn)), dtype=float)
        selected = edges.loc[
            edges["pre_pt_root_id"].isin(pfn_index)
            & edges["post_pt_root_id"].isin(hdelta_index)
        ]
        for row in selected.itertuples(index=False):
            self.weights[hdelta_index[row.post_pt_root_id], pfn_index[row.pre_pt_root_id]] += row.syn_count
        axes = self.config["preferred_egocentric_axes_deg"]
        self.egocentric_axes_rad = np.deg2rad([
            axes[f"{cell_type}_{side}"]
            for cell_type, side in zip(self.pfn["selected_type"], self.pfn["side"])
        ])
        self.heading_phase_rad = np.deg2rad(self.pfn["inherited_heading_phase_deg"].to_numpy())
        columns = self.hdelta["fb_axon_column"].str.removeprefix("HDB_FB").astype(int).to_numpy()
        # Atlas x grows left-to-right, while the published angular convention is clockwise.
        self.hdelta_angles_rad = -2.0 * np.pi * (columns - 1) / 12.0
        self.phase_anchor_rad = -self._raw_phase(0.0, 0.0)[0]

    def pfn_activity(self, heading_rad: float, egocentric_motion_rad: float, speed: float = 1.0) -> np.ndarray:
        amplitude = np.maximum(0.0, np.cos(egocentric_motion_rad - self.egocentric_axes_rad)) * max(0.0, speed)
        return amplitude * np.cos(heading_rad - self.heading_phase_rad)

    def _raw_phase(self, heading_rad: float, egocentric_motion_rad: float, speed: float = 1.0) -> tuple[float, float, np.ndarray]:
        hdelta_activity = self.weights @ self.pfn_activity(heading_rad, egocentric_motion_rad, speed)
        vector = np.sum(hdelta_activity * np.exp(1j * self.hdelta_angles_rad))
        denominator = float(np.sum(np.abs(hdelta_activity)))
        resultant = 0.0 if denominator == 0.0 else float(abs(vector) / denominator)
        return float(np.angle(vector)), resultant, hdelta_activity

    def decode(self, heading_rad: float, egocentric_motion_rad: float, speed: float = 1.0) -> tuple[float, float, np.ndarray, np.ndarray]:
        phase, resultant, hdelta_activity = self._raw_phase(heading_rad, egocentric_motion_rad, speed)
        return float(wrap(phase + self.phase_anchor_rad)), resultant, self.pfn_activity(heading_rad, egocentric_motion_rad, speed), hdelta_activity
