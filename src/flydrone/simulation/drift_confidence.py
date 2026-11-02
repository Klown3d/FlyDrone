"""Engineering confidence and fallback layer for PFN/hDeltaB drift correction."""
from __future__ import annotations

from pathlib import Path
import numpy as np
import yaml


def _angle_difference(a:float,b:float)->float:
    return float(np.angle(np.exp(1j*(a-b))))


class DriftConfidenceGovernor:
    """Blend uncertain hDeltaB correction with a slowly decaying trusted value.

    This is an engineering safety layer.  It is neither connectome-derived nor
    presented as a biological computation.
    """

    def __init__(self,config_path:Path):
        c=yaml.safe_load(config_path.read_text(encoding='utf-8'));self.config=c
        self.velocity_age_tau=float(c['velocity_age_time_constant_s']);self.heading_sigma=np.deg2rad(float(c['heading_disagreement_sigma_deg']));self.coherence_sigma=np.deg2rad(float(c['direction_coherence_sigma_deg']))
        self.fall_tau=float(c['confidence_fall_time_constant_s']);self.rise_tau=float(c['confidence_rise_time_constant_s']);self.backup_update_tau=float(c['backup_update_time_constant_s']);self.backup_decay_tau=float(c['backup_decay_time_constant_s'])
        self.trusted_threshold=float(c['trusted_confidence_threshold']);self.maximum_acceleration=float(c['maximum_correction_m_s2']);self.maximum_rate=float(c['maximum_correction_rate_m_s3']);self.reset()
        values=[self.velocity_age_tau,self.heading_sigma,self.coherence_sigma,self.fall_tau,self.rise_tau,self.backup_update_tau,self.backup_decay_tau,self.maximum_acceleration,self.maximum_rate]
        if any(value<=0 for value in values) or not 0<=self.trusted_threshold<=1:raise ValueError('invalid drift confidence configuration')

    def reset(self)->None:
        self.confidence=1.0;self.backup=np.zeros(2);self.output=np.zeros(2)

    def update(self,correction_xy:np.ndarray,measurement_age_s:float,position_available:bool,
               heading_rad:float,inertial_heading_rad:float,decoded_direction_rad:float,
               direct_direction_rad:float,dt_s:float)->tuple[np.ndarray,dict]:
        correction=np.asarray(correction_xy,dtype=float);dt=float(dt_s)
        velocity_confidence=float(np.exp(-max(0.,float(measurement_age_s))/self.velocity_age_tau)) if position_available else float(np.exp(-max(dt,float(measurement_age_s))/self.velocity_age_tau))
        heading_error=abs(_angle_difference(heading_rad,inertial_heading_rad));heading_confidence=float(np.exp(-.5*(heading_error/self.heading_sigma)**2))
        coherence_error=abs(_angle_difference(decoded_direction_rad,direct_direction_rad));coherence_confidence=float(np.exp(-.5*(coherence_error/self.coherence_sigma)**2))
        target=float(np.clip(velocity_confidence*heading_confidence*coherence_confidence,0.,1.));tau=self.rise_tau if target>self.confidence else self.fall_tau
        self.confidence+=(1-np.exp(-dt/tau))*(target-self.confidence);self.confidence=float(np.clip(self.confidence,0.,1.))
        if target>=self.trusted_threshold:
            self.backup+=(1-np.exp(-dt/self.backup_update_tau))*(correction-self.backup)
        else:self.backup*=np.exp(-dt/self.backup_decay_tau)
        requested=self.confidence*correction+(1-self.confidence)*self.backup
        norm=float(np.linalg.norm(requested))
        if norm>self.maximum_acceleration:requested*=self.maximum_acceleration/norm
        delta=requested-self.output;maximum_delta=self.maximum_rate*dt;delta_norm=float(np.linalg.norm(delta))
        if delta_norm>maximum_delta:delta*=maximum_delta/delta_norm
        self.output+=delta
        return self.output.copy(),{'confidence':self.confidence,'raw_confidence':target,'velocity_confidence':velocity_confidence,'heading_confidence':heading_confidence,'coherence_confidence':coherence_confidence,'backup_correction_m_s2':self.backup.copy()}
