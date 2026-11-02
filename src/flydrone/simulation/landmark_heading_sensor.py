"""Explicit landmark-bearing abstraction for an external heading cue."""
from pathlib import Path
import numpy as np
import yaml


def wrap(angle): return np.angle(np.exp(1j*np.asarray(angle)))


class LandmarkHeadingSensor:
    """Simulate relative bearing to a known fixed landmark and recover heading."""
    def __init__(self,config_path:Path):
        self.config=yaml.safe_load(config_path.read_text(encoding='utf-8'))
        self.landmark_world_bearing_rad=float(np.deg2rad(self.config['landmark_world_bearing_deg']))
        self.perturbed_noise_rad=float(np.deg2rad(self.config['perturbed_bearing_noise_std_deg']))

    def observe(self,true_heading_rad:float,rng:np.random.Generator,perturbed:bool=False)->tuple[float,float]:
        relative=float(wrap(self.landmark_world_bearing_rad-true_heading_rad))
        if perturbed:relative=float(wrap(relative+rng.normal(0,self.perturbed_noise_rad)))
        estimated=float(wrap(self.landmark_world_bearing_rad-relative))
        return estimated,relative

