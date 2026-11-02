"""Published steady-state PFL3 population model with mapped FAFB neurons."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


@dataclass(frozen=True)
class PFL3Parameters:
    goal_input_gain_d: float
    output_scale_hz_a: float
    softplus_slope_b: float
    input_offset_c: float


class PFL3ReferenceModel:
    """The 24-cell algebraic model reported by Mussells Pires et al. (2024)."""

    def __init__(self, mapping: pd.DataFrame, parameters: PFL3Parameters):
        required = {"root_id", "lal_projection_side", "preferred_goal_deg", "preferred_heading_deg"}
        if not required.issubset(mapping.columns):
            raise ValueError(f"Mapping lacks columns: {sorted(required - set(mapping.columns))}")
        if len(mapping) != 24 or mapping["root_id"].nunique() != 24:
            raise ValueError("The reference model requires exactly 24 unique PFL3 neurons")
        counts = mapping["lal_projection_side"].value_counts().to_dict()
        if counts != {"left": 12, "right": 12}:
            raise ValueError(f"Expected 12 neurons per LAL projection side, found {counts}")
        self.mapping = mapping.reset_index(drop=True).copy()
        self.parameters = parameters
        self.heading_rad = np.deg2rad(self.mapping["preferred_heading_deg"].to_numpy(float))
        self.goal_rad = np.deg2rad(self.mapping["preferred_goal_deg"].to_numpy(float))
        self.left = self.mapping["lal_projection_side"].eq("left").to_numpy()
        self.right = self.mapping["lal_projection_side"].eq("right").to_numpy()

    @classmethod
    def from_config(cls, root: Path, config_path: Path) -> "PFL3ReferenceModel":
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        if config["model_family"] != "rate_based_steady_state":
            raise ValueError("Unsupported model family")
        mapping = pd.read_csv(root / config["mapping"], dtype={"root_id": str})
        return cls(mapping, PFL3Parameters(**config["parameters"]))

    def rates(self, heading_rad: float, goal_rad: float) -> np.ndarray:
        """Return the published model's PFL3 firing rates in hertz."""
        p = self.parameters
        drive = np.cos(heading_rad - self.heading_rad) + p.goal_input_gain_d * np.cos(goal_rad - self.goal_rad)
        return p.output_scale_hz_a * np.logaddexp(0.0, p.softplus_slope_b * (drive + p.input_offset_c))

    def readout(self, rates_hz: np.ndarray) -> dict[str, float]:
        """Compute the reported population-level R-L neural signal."""
        values = np.asarray(rates_hz, dtype=float)
        if values.shape != (24,):
            raise ValueError("Expected one rate for each of 24 PFL3 neurons")
        left = float(values[self.left].sum())
        right = float(values[self.right].sum())
        return {"left_total_hz": left, "right_total_hz": right, "right_minus_left_hz": right - left}

    def evaluate(self, heading_rad: float, goal_rad: float) -> tuple[np.ndarray, dict[str, float]]:
        rates = self.rates(heading_rad, goal_rad)
        return rates, self.readout(rates)
