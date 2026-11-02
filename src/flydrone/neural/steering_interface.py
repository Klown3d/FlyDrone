"""Shared algebraic heading/meta interface for desktop and spatial experiments."""
from typing import Any,Mapping
import numpy as np
from flydrone.neural.epg_delta7 import EPGDelta7Candidate
from flydrone.neural.orientation_closed_loop import wrap


def activity(model: EPGDelta7Candidate, heading: np.ndarray, goal: np.ndarray, config: dict,
             variant: Mapping[str,Any]|None=None) -> tuple:
    """Evaluate the intact circuit or an explicitly labelled computational ablation."""
    variant={} if variant is None else variant
    phase_offset_deg=float(variant.get('phase_offset_deg',config['phase_offset_deg']))
    angles=config['epg_heading_sign']*model.epg_angles_rad+np.deg2rad(phase_offset_deg)
    epg=np.cos(np.asarray(heading)[...,None]-angles)
    epg_to_delta=np.asarray(variant.get('epg_to_delta',model.epg_to_delta))
    delta=epg@epg_to_delta.T if variant.get('delta7_enabled',True) else np.zeros(np.asarray(heading).shape+(len(model.base.delta_ids),))
    fc2=np.cos(np.asarray(goal)[...,None]-model.base.fc2_angles_rad)
    if not variant.get('fc2_enabled',True):fc2=np.zeros_like(fc2)
    p=model.base.parameters
    delta_to_pfl3=np.asarray(variant.get('delta_to_pfl3',model.delta_to_pfl3))
    fc2_weights=np.asarray(variant.get('fc2_weights',model.base.fc2_weights))
    drive=-delta@delta_to_pfl3.T+p.goal_input_gain_d*(fc2@fc2_weights.T)
    rates=p.output_scale_hz_a*np.logaddexp(0,p.softplus_slope_b*(drive+p.input_offset_c))
    signal=rates[...,model.base.right].sum(axis=-1)-rates[...,model.base.left].sum(axis=-1)
    return epg,delta,fc2,rates,signal


def command(model: EPGDelta7Candidate, heading: np.ndarray, goal: np.ndarray, config: dict, baseline: bool=False,
            variant: Mapping[str,Any]|None=None) -> tuple:
    values=activity(model,heading,goal,config,variant)
    raw=-config['proportional_baseline_gain_per_s']*wrap(heading-goal) if baseline else config['readout_gain_rad_per_s_per_hz']*values[-1]
    return np.clip(raw,-config['maximum_yaw_rate_rad_s'],config['maximum_yaw_rate_rad_s']),values
