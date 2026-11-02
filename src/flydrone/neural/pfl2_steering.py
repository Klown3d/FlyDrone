"""PFL2 magnitude modulation layered over the PFL3 steering direction."""
from pathlib import Path

import numpy as np
import yaml

from flydrone.neural.connectome_pfl2 import ConnectomeWeightedPFL2
from flydrone.neural.steering_interface import command as pfl3_command


class PFL2SteeringController:
    """Preserve PFL3 turn sign while PFL2 scales command magnitude.

    The modulation gain is an engineering parameter. PFL2 activity comes from
    FAFB contacts, but this output mapping is a refutable drone interface.
    """

    def __init__(self, root: Path, config_path: Path):
        self.config_path = config_path
        self.config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        gain = float(self.config["maximum_modulation_gain"])
        if gain < 0:
            raise ValueError("maximum_modulation_gain must be nonnegative")
        self.index_mode = self.config.get("index_mode", "connectome")
        if self.index_mode not in {"connectome", "analytic_error"}:
            raise ValueError(f"unknown PFL2 index mode: {self.index_mode}")
        self.model = ConnectomeWeightedPFL2(root, root / self.config["pfl2_model_config"])

    def modulate(self, base_command: float, heading_rad: float, goal_rad: float, enabled: bool = True):
        activity = self.model.activity(heading_rad, goal_rad)
        if self.index_mode == "connectome":
            index = self.model.anti_goal_index(heading_rad, goal_rad)
        else:
            # Engineering control with the same range and gain, but no connectome.
            index = float((1.0 - np.cos(heading_rad - goal_rad)) / 2.0)
        scale = 1.0 + (float(self.config["maximum_modulation_gain"]) * index if enabled else 0.0)
        result = float(np.clip(base_command * scale,
                               -self.config["maximum_yaw_rate_rad_s"],
                               self.config["maximum_yaw_rate_rad_s"]))
        return result, activity, index, scale

    def command(self, steering_model, heading_rad: float, goal_rad: float,
                orientation_config: dict, *, enabled: bool = True, baseline: bool = False,
                circuit_variant: dict | None = None):
        base, values = pfl3_command(
            steering_model, np.asarray(heading_rad), np.asarray(goal_rad),
            orientation_config, baseline, circuit_variant,
        )
        result, activity, index, scale = self.modulate(float(base), heading_rad, goal_rad, enabled)
        return result, values, activity, index, scale, float(base)
