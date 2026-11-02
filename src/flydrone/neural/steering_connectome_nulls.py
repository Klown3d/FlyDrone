"""Projection-specific connectome nulls for EPG→Delta7→PFL3 steering."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from flydrone.neural.connectome_nulls import block_degree_preserving_rewire
from flydrone.neural.epg_delta7 import EPGDelta7Candidate, normalize_nonzero_rows


@dataclass(frozen=True)
class SteeringNull:
    """A rewired steering variant plus an audit of the controlled change."""

    variant: dict[str, np.ndarray | float]
    metadata: dict[str, object]


def _global_phase_alignment_deg(
    model: EPGDelta7Candidate,
    epg_to_delta: np.ndarray,
    delta_to_pfl3: np.ndarray,
    heading_sign: float,
) -> tuple[float, float, float]:
    """Align only the null's global phase to the intact composite transfer."""
    basis = np.exp(1j * heading_sign * model.epg_angles_rad)
    intact_transfer = -model.delta_to_pfl3 @ model.epg_to_delta
    null_transfer = -delta_to_pfl3 @ epg_to_delta
    intact_complex = intact_transfer @ basis
    null_complex = null_transfer @ basis
    valid = (np.abs(intact_complex) > 1e-12) & (np.abs(null_complex) > 1e-12)
    if not np.any(valid):
        raise ValueError("Steering null has no valid PFL3 phase response")
    difference = np.angle(intact_complex[valid] / null_complex[valid])
    offset = float(np.angle(np.mean(np.exp(1j * difference))))
    residual = np.abs(np.angle(np.exp(1j * (difference - offset))))
    return (
        float(np.rad2deg(offset)),
        float(np.rad2deg(residual).mean()),
        float(np.rad2deg(residual).max()),
    )


def build_steering_null(
    model: EPGDelta7Candidate,
    seed: int,
    heading_sign: float,
    base_phase_offset_deg: float = 0.0,
    swaps_per_edge: int = 10,
    projection_mode: str = "both",
) -> SteeringNull:
    """Rewire both steering projections within presynaptic side blocks.

    For each projection and side block, binary row/column degrees and every
    postsynaptic row's exact nonzero raw-weight multiset are preserved. Weighted
    column sums and partner identities are intentionally not preserved.
    """
    if projection_mode not in {"both", "epg_to_delta", "delta_to_pfl3"}:
        raise ValueError(f"Unknown steering-null projection mode: {projection_mode}")
    rng = np.random.default_rng(seed)
    epg_groups = model.epg["source_side"].to_numpy(str)
    delta_features = model.base.features.set_index("root_id").loc[model.base.delta_ids]
    delta_groups = delta_features["source_side"].to_numpy(str)

    epg_to_delta_raw = model.epg_to_delta_raw.copy()
    delta_to_pfl3_raw = model.delta_to_pfl3_raw.copy()
    epg_swaps = 0
    delta_swaps = 0
    if projection_mode in {"both", "epg_to_delta"}:
        epg_to_delta_raw, epg_swaps = block_degree_preserving_rewire(
            model.epg_to_delta_raw, epg_groups, rng, swaps_per_edge=swaps_per_edge
        )
    if projection_mode in {"both", "delta_to_pfl3"}:
        delta_to_pfl3_raw, delta_swaps = block_degree_preserving_rewire(
            model.delta_to_pfl3_raw, delta_groups, rng, swaps_per_edge=swaps_per_edge
        )
    if projection_mode in {"both", "epg_to_delta"} and epg_swaps == 0:
        raise RuntimeError("Steering null did not rewire EPG-to-Delta7")
    if projection_mode in {"both", "delta_to_pfl3"} and delta_swaps == 0:
        raise RuntimeError("Steering null did not rewire Delta7-to-PFL3")

    epg_to_delta = normalize_nonzero_rows(epg_to_delta_raw)
    delta_to_pfl3 = normalize_nonzero_rows(delta_to_pfl3_raw)
    phase_delta, mean_residual, maximum_residual = _global_phase_alignment_deg(
        model, epg_to_delta, delta_to_pfl3, heading_sign
    )
    return SteeringNull(
        variant={
            "epg_to_delta": epg_to_delta,
            "delta_to_pfl3": delta_to_pfl3,
            "phase_offset_deg": float(base_phase_offset_deg + phase_delta),
        },
        metadata={
            "mode": f"{projection_mode}_side_block_rewire",
            "projection_mode": projection_mode,
            "seed": int(seed),
            "epg_to_delta_accepted_swaps": int(epg_swaps),
            "delta_to_pfl3_accepted_swaps": int(delta_swaps),
            "global_phase_alignment_deg": phase_delta,
            "mean_pfl3_phase_residual_deg": mean_residual,
            "maximum_pfl3_phase_residual_deg": maximum_residual,
            "preserves": (
                "binary row/column degrees and each postsynaptic row's raw-weight "
                "multiset within presynaptic source-side blocks"
            ),
            "does_not_preserve": "weighted column sums or exact partner identity",
        },
    )
