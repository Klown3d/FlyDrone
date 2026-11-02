"""Engineering drift compensator driven by the PFN/hDeltaB direction readout."""
from __future__ import annotations

from pathlib import Path
import numpy as np
import yaml

from flydrone.neural.travel_direction_model import ConnectomeTravelDirection, wrap
from flydrone.neural.connectome_nulls import degree_preserving_rewire,block_degree_preserving_rewire


def direct_velocity_correction(heading_rad:float,velocity_world_xy:np.ndarray,
                               desired_direction_rad:float,gain_per_s:float,
                               minimum_speed_m_s:float)->dict:
    """Matched non-neural drift readout from the observed velocity vector."""
    velocity=np.asarray(velocity_world_xy,dtype=float);speed=float(np.linalg.norm(velocity))
    if speed<minimum_speed_m_s:
        return {'decoded_direction_rad':float(heading_rad),'lateral_drift_m_s':0.,'correction_world_m_s2':np.zeros(2)}
    direction=float(np.arctan2(velocity[1],velocity[0]));lateral_drift=speed*np.sin(float(wrap(direction-desired_direction_rad)));desired_lateral=np.array([-np.sin(desired_direction_rad),np.cos(desired_direction_rad)])
    return {'decoded_direction_rad':direction,'lateral_drift_m_s':float(lateral_drift),'correction_world_m_s2':-float(gain_per_s)*lateral_drift*desired_lateral}


class TravelDirectionDriftController:
    """Turn decoded travel direction into a world-frame lateral acceleration.

    The direction is neural-model output. Speed magnitude and the proportional
    acceleration rule are explicit engineering layers, not fly physiology.
    """

    def __init__(self, root: Path, config_path: Path, phase_shuffle_seed: int | None = None,
                 weight_rewire_seed: int | None = None,
                 block_weight_rewire_seed: int | None = None):
        if sum(value is not None for value in
               (phase_shuffle_seed, weight_rewire_seed, block_weight_rewire_seed)) > 1:
            raise ValueError("Choose only one connectome null")
        self.config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        self.model = ConnectomeTravelDirection(root, root / self.config["model_config"])
        self.null_metadata = {"mode": "intact", "seed": None, "accepted_swaps": 0,
                              "global_phase_recalibrated": False}
        if phase_shuffle_seed is not None:
            rng = np.random.default_rng(phase_shuffle_seed)
            for _, indices in self.model.pfn.groupby(["selected_type", "side"]).groups.items():
                selected = np.asarray(list(indices), dtype=int)
                shuffled = self.model.heading_phase_rad[selected].copy()
                rng.shuffle(shuffled)
                self.model.heading_phase_rad[selected] = shuffled
            self.null_metadata.update(mode="phase_shuffle", seed=int(phase_shuffle_seed))
        if weight_rewire_seed is not None:
            rewired, accepted = degree_preserving_rewire(
                self.model.weights, np.random.default_rng(weight_rewire_seed))
            self.model.weights = rewired
            self.null_metadata.update(mode="degree_preserving_weight_rewire",
                                      seed=int(weight_rewire_seed), accepted_swaps=int(accepted))
        if block_weight_rewire_seed is not None:
            groups = (self.model.pfn["selected_type"].astype(str) + "_"
                      + self.model.pfn["side"].astype(str)).to_numpy()
            rewired, accepted = block_degree_preserving_rewire(
                self.model.weights, groups, np.random.default_rng(block_weight_rewire_seed))
            self.model.weights = rewired
            self.null_metadata.update(mode="type_side_block_degree_preserving_weight_rewire",
                                      seed=int(block_weight_rewire_seed), accepted_swaps=int(accepted),
                                      preserved_presynaptic_blocks=sorted(np.unique(groups).tolist()))
        if any(value is not None for value in
               (phase_shuffle_seed, weight_rewire_seed, block_weight_rewire_seed)):
            # Permit the same single global angular calibration as the intact model.
            # This prevents a null from failing solely because of a constant rotation.
            self.model.phase_anchor_rad = -self.model._raw_phase(0.0, 0.0)[0]
            self.null_metadata["global_phase_recalibrated"] = True
        self.gain = float(self.config["correction_gain_per_s"])
        self.minimum_speed = float(self.config["minimum_speed_m_s"])

    def command(self, heading_rad: float, velocity_world_xy: np.ndarray,
                desired_direction_rad: float,egocentric_motion_override_rad:float|None=None,
                speed_override_m_s:float|None=None) -> dict:
        velocity = np.asarray(velocity_world_xy, dtype=float)
        speed = float(np.linalg.norm(velocity)) if speed_override_m_s is None else max(0.,float(speed_override_m_s))
        if speed < self.minimum_speed:
            return {"decoded_direction_rad": float(heading_rad), "resultant": 0.0,
                    "lateral_drift_m_s": 0.0, "correction_world_m_s2": np.zeros(2),
                    "egocentric_motion_rad": 0.0,
                    "pfn_activity": np.zeros(len(self.model.pfn)),
                    "hdelta_activity": np.zeros(len(self.model.hdelta))}
        observed_direction = float(np.arctan2(velocity[1], velocity[0]))
        egocentric_motion = float(wrap(observed_direction - heading_rad)) if egocentric_motion_override_rad is None else float(wrap(egocentric_motion_override_rad))
        decoded, resultant, pfn_activity, hdelta_activity = self.model.decode(heading_rad, egocentric_motion, speed)
        lateral_drift = speed * np.sin(float(wrap(decoded - desired_direction_rad)))
        desired_lateral = np.array([-np.sin(desired_direction_rad), np.cos(desired_direction_rad)])
        correction = -self.gain * lateral_drift * desired_lateral
        return {"decoded_direction_rad": decoded, "resultant": resultant,
                "lateral_drift_m_s": float(lateral_drift),
                "correction_world_m_s2": correction,
                "egocentric_motion_rad": egocentric_motion,
                "pfn_activity": pfn_activity, "hdelta_activity": hdelta_activity}
