"""Stateful heading estimator using the frozen phase-resolved compass model."""
from pathlib import Path

import numpy as np
import yaml

from flydrone.neural.phase_compass_dynamics import advance, readout
from flydrone.neural.phase_resolved_compass import normalize_columns
from flydrone.neural.phase_velocity_validation import circularize


class PhaseCompassEstimator:
    """Maintain a 16-phase activity bump from heading cues and angular velocity.

    Transfer matrices come from FAFB/FlyWire contacts.  The active v4 model
    derives its velocity operator from lateral PB-to-EB PEN_a transfers; its
    dynamical gains and optional symmetry regularization remain explicit
    engineering choices recorded by configuration and report hashes.
    """

    def __init__(self, root: Path, config_path: Path, initial_heading_rad: float):
        self.config_path = config_path
        self.config = yaml.safe_load((root / config_path).read_text(encoding="utf-8"))
        data = np.load(root / self.config["transfers"])
        self.phases = np.deg2rad(data["phases_deg"])
        transform = circularize if self.config.get("matrix_condition") == "circularized" else lambda value: value
        norm = lambda name: normalize_columns(transform(data[name]))
        self.inhibition = norm("delta7")
        excitation_components=self.config.get("excitation_components",[
            "peg","pen_b_left","pen_b_right","pen_a_left","pen_a_right"])
        self.excitation=sum(norm(name) for name in excitation_components)/len(excitation_components)
        identity = np.eye(len(self.phases))
        velocity_operators={
            "published_one_wedge":(np.roll(identity,1,axis=0)-np.roll(identity,-1,axis=0))/2,
            "pen_a_difference":norm("pen_a_right")-norm("pen_a_left"),
            "pen_b_difference":norm("pen_b_right")-norm("pen_b_left"),
            "pen_combined_difference":(norm("pen_a_right")+norm("pen_b_right")-norm("pen_a_left")-norm("pen_b_left"))/2,
        }
        self.velocity_operator=velocity_operators[self.config.get("velocity_operator","published_one_wedge")]
        report = yaml.safe_load((root / self.config["output"] / "report.json").read_text(encoding="utf-8"))
        self.parameters = {**report["selected_parameters"], **self.config.get("parameter_overrides", {})}
        self.state = np.zeros((1, len(self.phases)), dtype=float)
        self.anchor_heading_rad = float(initial_heading_rad)
        self.anchor_phase_rad = 0.0
        cue = self._cue(initial_heading_rad)
        self.state = self._advance(
            round(self.config["cue_duration_s"] / self.config["dt_s"]), 0.0, cue
        )
        phase, _, _ = readout(self.state, self.phases)
        self.anchor_phase_rad = float(phase[0])

    def _cue(self, heading_rad: float) -> np.ndarray:
        c = self.config
        return c["cue_gain"] * np.exp(
            c["cue_concentration"] * (np.cos(heading_rad - self.phases) - 1)
        )[None, :]

    def _advance(self, steps: int, yaw_rate_rad_s: float, external: np.ndarray) -> np.ndarray:
        p = self.parameters
        return advance(
            self.state, steps, self.config, self.excitation, self.inhibition,
            self.velocity_operator, p["excitation_gain"], p["inhibition_gain"],
            p["bias"], p["velocity_gain"] * p["angular_sign"] * yaw_rate_rad_s,
            external,
        )

    def update(
        self, heading_cue_rad: float | None, yaw_rate_rad_s: float, dt_s: float
    ) -> tuple[float, float, float]:
        """Advance the network and return phase, resultant and bump contrast."""
        model_dt = float(self.config["dt_s"])
        steps = round(dt_s / model_dt)
        if steps < 1 or not np.isclose(steps * model_dt, dt_s):
            raise ValueError("dt_s must be a positive multiple of the compass dt_s")
        external = np.zeros_like(self.state) if heading_cue_rad is None else self._cue(heading_cue_rad)
        self.state = self._advance(steps, yaw_rate_rad_s, external)
        phase, resultant, contrast = readout(self.state, self.phases)
        internal_phase = float(phase[0])
        if heading_cue_rad is not None:
            # A ring-attractor phase has no anatomical world-zero.  Calibrate
            # that offset whenever an external heading cue is available, then
            # decode only relative phase motion during cue loss.
            self.anchor_heading_rad = float(heading_cue_rad)
            self.anchor_phase_rad = internal_phase
        decoded = np.angle(np.exp(1j * (
            self.anchor_heading_rad + internal_phase - self.anchor_phase_rad
        )))
        return float(decoded), float(resultant[0]), float(contrast[0])


class HybridCompassEstimator:
    """Fuse the FlyWire compass with inertial integration during cue loss.

    The neural state always continues evolving.  The inertial estimate limits
    large phase-update errors; its contribution is an explicit engineering
    layer rather than a claimed connectome circuit.
    """
    def __init__(self,root:Path,config_path:Path,initial_heading_rad:float):
        config=yaml.safe_load((root/config_path).read_text(encoding="utf-8"))
        self.neural=PhaseCompassEstimator(root,Path(config["neural_compass_config"]),initial_heading_rad)
        self.maximum_neural_weight=float(config["maximum_neural_weight_during_dropout"])
        self.disagreement_scale=np.deg2rad(float(config["disagreement_scale_deg"]))
        self.gyro_heading=float(initial_heading_rad);self.last_neural_heading=float(initial_heading_rad)
        self.last_gyro_heading=float(initial_heading_rad);self.last_neural_weight=1.0;self.last_disagreement_rad=0.0

    def update(self,heading_cue_rad:float|None,yaw_rate_rad_s:float,dt_s:float)->tuple[float,float,float]:
        neural_heading,resultant,contrast=self.neural.update(heading_cue_rad,yaw_rate_rad_s,dt_s)
        if heading_cue_rad is not None:
            self.gyro_heading=float(heading_cue_rad);weight=1.0;fused=float(heading_cue_rad);disagreement=0.0;confidence=1.0
        else:
            self.gyro_heading=float(np.angle(np.exp(1j*(self.gyro_heading+yaw_rate_rad_s*dt_s))))
            disagreement=float(np.angle(np.exp(1j*(neural_heading-self.gyro_heading))))
            agreement=float(np.exp(-(abs(disagreement)/self.disagreement_scale)**2))
            weight=float(np.clip(self.maximum_neural_weight*resultant*agreement,0,self.maximum_neural_weight))
            vector=(1-weight)*np.exp(1j*self.gyro_heading)+weight*np.exp(1j*neural_heading);fused=float(np.angle(vector))
            confidence=float(np.clip(agreement,0,1))
        self.last_neural_heading=float(neural_heading);self.last_gyro_heading=self.gyro_heading;self.last_neural_weight=weight;self.last_disagreement_rad=disagreement
        return fused,confidence,float(contrast)
