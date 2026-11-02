"""Experimental PFL3 model weighted by FlyWire 783 synapse counts."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import yaml

from flydrone.neural.pfl3 import PFL3Parameters


# Nine-column alternative reported in Mussells Pires et al. (2024), after
# applying the paper's overall minus sign.
FC2_GOAL_DEG_9 = np.array([0.0, -45.0, -90.0, -135.0, -180.0, 135.0, 90.0, 45.0, 0.0])


@dataclass(frozen=True)
class StreamAudit:
    neuron_count: int
    contact_count: int
    minimum_pfl3_input: int
    maximum_pfl3_input: int


def weighted_circular_mean_deg(angles_deg: np.ndarray, weights: np.ndarray) -> tuple[float, float]:
    vector = np.sum(weights * np.exp(1j * np.deg2rad(angles_deg))) / np.sum(weights)
    return float(np.rad2deg(np.angle(vector))), float(np.abs(vector))


def row_normalize(weights: np.ndarray) -> np.ndarray:
    totals = weights.sum(axis=1, keepdims=True)
    if np.any(totals <= 0):
        raise ValueError("Every PFL3 neuron must receive at least one contact in each active input stream")
    return weights / totals


class ConnectomeWeightedPFL3:
    """Feedforward Δ7/FC2→PFL3 model using real pairwise contact counts.

    Tuning assignments and row normalization remain explicit hypotheses. This
    class therefore must not be described as a fully reconstructed fly circuit.
    """

    def __init__(self, root: Path, config_path: Path, fc2_subtypes: Iterable[str] | None = None):
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        self.config = config
        self.parameters = PFL3Parameters(**config["parameters"])
        self.pfl3 = pd.read_csv(root / config["pfl3_mapping"], dtype={"root_id": str}).reset_index(drop=True)
        self.features = pd.read_csv(root / config["morphology_features"], dtype={"root_id": str})
        self.nodes = pd.read_csv(root / config["nodes"], dtype={"root_id": str})
        edges = pd.read_csv(root / config["edges"], dtype={"pre_pt_root_id": str, "post_pt_root_id": str})
        types = dict(zip(self.nodes["root_id"], self.nodes["selected_type"]))
        edges["pre_type"] = edges["pre_pt_root_id"].map(types)
        edges["post_type"] = edges["post_pt_root_id"].map(types)
        self.pfl3_index = {root_id: i for i, root_id in enumerate(self.pfl3["root_id"])}
        self.left = self.pfl3["lal_projection_side"].eq("left").to_numpy()
        self.right = self.pfl3["lal_projection_side"].eq("right").to_numpy()

        delta_edges = edges.loc[edges["pre_type"].eq("Delta7") & edges["post_type"].eq("PFL3")]
        delta_ids = sorted(delta_edges["pre_pt_root_id"].unique(), key=int)
        delta_index = {root_id: i for i, root_id in enumerate(delta_ids)}
        pfl3_heading = dict(zip(self.pfl3["root_id"], self.pfl3["preferred_heading_deg"]))
        delta_angles = []
        delta_concentration = []
        for root_id in delta_ids:
            group = delta_edges.loc[delta_edges["pre_pt_root_id"].eq(root_id)]
            angle, concentration = weighted_circular_mean_deg(
                group["post_pt_root_id"].map(pfl3_heading).to_numpy(float), group["syn_count"].to_numpy(float)
            )
            delta_angles.append(angle)
            delta_concentration.append(concentration)
        delta_weights = np.zeros((24, len(delta_ids)), dtype=float)
        for row in delta_edges.itertuples(index=False):
            delta_weights[self.pfl3_index[row.post_pt_root_id], delta_index[row.pre_pt_root_id]] += row.syn_count
        self.delta_ids = delta_ids
        self.delta_angles_rad = np.deg2rad(delta_angles)
        self.delta_concentration = np.asarray(delta_concentration)
        self.delta_weights_raw = delta_weights
        self.delta_weights = row_normalize(delta_weights)

        selected_subtypes = tuple(fc2_subtypes or config["primary_fc2_subtypes"])
        allowed = {"FC2A", "FC2B", "FC2C"}
        if not selected_subtypes or not set(selected_subtypes).issubset(allowed):
            raise ValueError(f"Invalid FC2 subtype selection: {selected_subtypes}")
        excluded = set(config.get("excluded_root_ids", []))
        fc2_features = self.features.loc[
            self.features["selected_type"].isin(selected_subtypes) & ~self.features["root_id"].isin(excluded)
        ].copy()
        fc2_features["column_number"] = fc2_features["geometric_column"].str.removeprefix("FB").astype(int)
        fc2_features["goal_deg"] = fc2_features["column_number"].map(
            {i: value for i, value in enumerate(FC2_GOAL_DEG_9, 1)}
        )
        self.fc2_ids = sorted(fc2_features["root_id"].tolist(), key=int)
        fc2_index = {root_id: i for i, root_id in enumerate(self.fc2_ids)}
        fc2_angles = dict(zip(fc2_features["root_id"], fc2_features["goal_deg"]))
        fc2_edges = edges.loc[
            edges["pre_type"].isin(selected_subtypes)
            & edges["post_type"].eq("PFL3")
            & edges["pre_pt_root_id"].isin(self.fc2_ids)
        ]
        fc2_weights = np.zeros((24, len(self.fc2_ids)), dtype=float)
        for row in fc2_edges.itertuples(index=False):
            fc2_weights[self.pfl3_index[row.post_pt_root_id], fc2_index[row.pre_pt_root_id]] += row.syn_count
        self.fc2_subtypes = selected_subtypes
        self.fc2_angles_rad = np.deg2rad([fc2_angles[root_id] for root_id in self.fc2_ids])
        self.fc2_weights_raw = fc2_weights
        self.fc2_weights = row_normalize(fc2_weights)
        self.delta_audit = StreamAudit(len(delta_ids), int(delta_weights.sum()), int(delta_weights.sum(1).min()), int(delta_weights.sum(1).max()))
        self.fc2_audit = StreamAudit(len(self.fc2_ids), int(fc2_weights.sum()), int(fc2_weights.sum(1).min()), int(fc2_weights.sum(1).max()))

    def rates(
        self,
        heading_rad: float,
        goal_rad: float,
        *,
        delta7_enabled: bool = True,
        fc2_enabled: bool = True,
        delta_weights: np.ndarray | None = None,
        fc2_weights: np.ndarray | None = None,
    ) -> np.ndarray:
        heading = np.cos(heading_rad - self.delta_angles_rad)
        goal = np.cos(goal_rad - self.fc2_angles_rad)
        heading_drive = (self.delta_weights if delta_weights is None else delta_weights) @ heading if delta7_enabled else 0.0
        goal_drive = (self.fc2_weights if fc2_weights is None else fc2_weights) @ goal if fc2_enabled else 0.0
        p = self.parameters
        drive = heading_drive + p.goal_input_gain_d * goal_drive
        return p.output_scale_hz_a * np.logaddexp(0.0, p.softplus_slope_b * (drive + p.input_offset_c))

    def readout(self, rates_hz: np.ndarray) -> float:
        return float(rates_hz[self.right].sum() - rates_hz[self.left].sum())

    @staticmethod
    def shuffled_rows(weights: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        """Permute presynaptic assignments independently while preserving each row's values."""
        return np.vstack([rng.permutation(row) for row in weights])
