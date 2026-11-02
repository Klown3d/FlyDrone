"""Engineering speed governor for temporary sensor uncertainty."""
from pathlib import Path
import numpy as np
import yaml


class SensorConfidenceGovernor:
    def __init__(self,config_path:Path):
        self.config=yaml.safe_load(config_path.read_text(encoding='utf-8'));self.minimum=float(self.config['minimum_speed_fraction']);self.tau=float(self.config['recovery_time_constant_s']);self.reset()
        if not 0<=self.minimum<=1 or self.tau<=0:raise ValueError('invalid sensor confidence governor configuration')

    def reset(self)->None:self.fraction=1.0

    def update(self,heading_confidence:float,velocity_available:bool,dt_s:float)->float:
        confidence=float(np.clip(heading_confidence,0,1));target=self.minimum+(1-self.minimum)*confidence
        if not velocity_available:target=min(target,self.minimum)
        alpha=1-np.exp(-float(dt_s)/self.tau);self.fraction+=alpha*(target-self.fraction)
        return float(np.clip(self.fraction,self.minimum,1.0))
