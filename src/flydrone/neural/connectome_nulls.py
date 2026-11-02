"""Computational nulls that preserve explicit connectome statistics."""
from __future__ import annotations

import numpy as np


def degree_preserving_rewire(weights: np.ndarray, rng: np.random.Generator,
                             swaps_per_edge: int = 10) -> tuple[np.ndarray, int]:
    """Rewire a weighted bipartite matrix while preserving key marginals.

    Binary row and column degrees are unchanged. Each row retains its exact
    multiset of nonzero weights and therefore its total input weight. Column
    weight sums are not constrained.
    """
    rewired = np.asarray(weights, dtype=float).copy()
    edges = np.argwhere(rewired > 0)
    target = swaps_per_edge * len(edges)
    accepted = 0
    for _ in range(max(1, target * 50)):
        if accepted >= target:
            break
        first, second = rng.integers(0, len(edges), size=2)
        row_a, col_a = edges[first]
        row_b, col_b = edges[second]
        if (first == second or row_a == row_b or col_a == col_b
                or rewired[row_a, col_b] > 0 or rewired[row_b, col_a] > 0):
            continue
        weight_a, weight_b = rewired[row_a, col_a], rewired[row_b, col_b]
        rewired[row_a, col_a] = rewired[row_b, col_b] = 0.0
        rewired[row_a, col_b] = weight_a
        rewired[row_b, col_a] = weight_b
        edges[first] = [row_a, col_b]
        edges[second] = [row_b, col_a]
        accepted += 1
    return rewired, accepted


def block_degree_preserving_rewire(weights: np.ndarray, column_groups: np.ndarray,
                                   rng: np.random.Generator,
                                   swaps_per_edge: int = 10) -> tuple[np.ndarray, int]:
    """Rewire independently inside presynaptic classes.

    In addition to the guarantees of :func:`degree_preserving_rewire`, this
    preserves every postsynaptic neuron's degree and weight multiset separately
    for each presynaptic class.
    """
    weights = np.asarray(weights, dtype=float)
    groups = np.asarray(column_groups)
    if weights.shape[1] != len(groups):
        raise ValueError("One column group is required for every presynaptic neuron")
    rewired = weights.copy()
    accepted = 0
    for group in np.unique(groups):
        selected = np.flatnonzero(groups == group)
        changed, count = degree_preserving_rewire(
            weights[:, selected], rng, swaps_per_edge=swaps_per_edge)
        rewired[:, selected] = changed
        accepted += count
    return rewired, accepted
