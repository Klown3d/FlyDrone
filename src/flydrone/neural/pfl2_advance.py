"""High-level forward-speed modulation from the connectome PFL2 index."""
from pathlib import Path
import numpy as np
import yaml


class PFL2AdvanceController:
    """Map PFL2 antimeta index to a bounded engineering speed fraction."""
    def __init__(self,config_path:Path):
        self.config=yaml.safe_load(config_path.read_text(encoding='utf-8'))
        self.exponent=float(self.config['exponent']);self.minimum=float(self.config['minimum_speed_fraction']);self.maximum=float(self.config['maximum_speed_fraction'])
        if self.exponent<=0 or not 0<=self.minimum<=self.maximum<=1:raise ValueError('invalid PFL2 advance configuration')

    def speed_fraction(self,anti_goal_index:float)->float:
        index=float(np.clip(anti_goal_index,0,1));fraction=(1-index)**self.exponent
        return float(np.clip(fraction,self.minimum,self.maximum))

    def desired_speed(self,distance_m:float,anti_goal_index:float,maximum_speed_m_s:float,distance_gain_per_s:float)->tuple[float,float]:
        fraction=self.speed_fraction(anti_goal_index);cap=min(float(maximum_speed_m_s),float(distance_gain_per_s)*max(0.,float(distance_m)))
        return cap*fraction,fraction

