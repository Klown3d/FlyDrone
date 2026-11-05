"""Engineering behavior layer that supplies temporary goals to FlyDrone."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml


MODES = ("point", "manual", "patrol", "explore")


@dataclass(frozen=True)
class BehaviorTarget:
    """One temporary world-frame goal produced outside the neural circuit."""

    mode: str
    target_xy_m: tuple[float, float]
    changed: bool
    target_index: int
    visited_targets: int
    total_targets: int
    completed_targets_total: int = 0
    completed_cycles: int = 0
    abandoned_targets_total: int = 0
    source: str = "engineering_behavior_manager"


class NavigationBehaviorManager:
    """Generate goals without changing the FlyWire-grounded controller.

    This module is an engineering planner. It does not model a named fly
    neuron or claim that exploration and waypoint memory are implemented by
    the reconstructed central-complex circuit.
    """

    def __init__(self, config_path: Path):
        self.config_path = Path(config_path)
        self.config = yaml.safe_load(self.config_path.read_text(encoding="utf-8"))
        if self.config.get("parameter_status") != "engineering_behavior_layer_not_neuronal":
            raise ValueError("Behavior configuration must declare its engineering status")
        self.default_mode = str(self.config["default_mode"])
        if self.default_mode not in MODES:
            raise ValueError(f"Unknown default behavior mode: {self.default_mode}")
        self.patrol = np.asarray(self.config["patrol_waypoints_xy_m"], dtype=float)
        if self.patrol.ndim != 2 or self.patrol.shape[1] != 2 or not len(self.patrol):
            raise ValueError("patrol_waypoints_xy_m must contain 2D points")
        bounds = np.asarray(self.config["exploration_bounds_xy_m"], dtype=float)
        if bounds.shape != (2, 2) or np.any(bounds[:, 0] >= bounds[:, 1]):
            raise ValueError("exploration_bounds_xy_m must be [[xmin,xmax],[ymin,ymax]]")
        spacing = float(self.config["exploration_grid_spacing_m"])
        if spacing <= 0:
            raise ValueError("exploration_grid_spacing_m must be positive")
        xs = np.arange(bounds[0, 0], bounds[0, 1] + spacing * .5, spacing)
        ys = np.arange(bounds[1, 0], bounds[1, 1] + spacing * .5, spacing)
        self.exploration_points = np.asarray([(x, y) for y in ys for x in xs], dtype=float)
        rng = np.random.default_rng(int(self.config["exploration_seed"]))
        self.exploration_order = rng.permutation(len(self.exploration_points))
        self.exploration_selection_policy = str(
            self.config.get("exploration_selection_policy", "seeded_permutation")
        )
        if self.exploration_selection_policy not in {"seeded_permutation", "seeded_nearest_unvisited"}:
            raise ValueError("Unknown exploration_selection_policy")
        self._exploration_tie_rank = np.empty(len(self.exploration_order), dtype=int)
        self._exploration_tie_rank[self.exploration_order] = np.arange(len(self.exploration_order))
        self.mode = self.default_mode
        self.point_target = np.zeros(2)
        self.manual_direction_rad = 0.0
        self.current_index = 0
        self.visited: set[int] = set()
        self.completed_targets_total = 0
        self.completed_cycles = 0
        self.abandoned_targets_total = 0
        self._last_target: tuple[float, float] | None = None

    def reset(self, point_target_xy_m: tuple[float, float], heading_rad: float = 0.0) -> None:
        self.point_target = np.asarray(point_target_xy_m, dtype=float)
        self.manual_direction_rad = float(heading_rad)
        self.current_index = 0
        self.visited = set()
        self.completed_targets_total = 0
        self.completed_cycles = 0
        self.abandoned_targets_total = 0
        self._last_target = None

    def set_mode(self, mode: str, position_xy_m: tuple[float, float],
                 heading_rad: float) -> BehaviorTarget:
        if mode not in MODES:
            raise ValueError(f"Unknown behavior mode: {mode}")
        self.mode = mode
        self.current_index = 0
        self.visited = set()
        self.completed_targets_total = 0
        self.completed_cycles = 0
        self.abandoned_targets_total = 0
        self.manual_direction_rad = float(heading_rad)
        self._last_target = None
        if mode == "explore" and self.exploration_selection_policy == "seeded_nearest_unvisited":
            position = np.asarray(position_xy_m, dtype=float)
            acceptance = float(self.config["exploration_acceptance_radius_m"])
            already_covered = np.flatnonzero(
                np.linalg.norm(self.exploration_points - position, axis=1) <= acceptance
            )
            self.visited.update(int(index) for index in already_covered)
            self.current_index = self._nearest_exploration_index(position)
        return self.update(position_xy_m, heading_rad)

    def _nearest_exploration_index(self, position: np.ndarray) -> int:
        remaining = np.asarray(
            [index for index in range(len(self.exploration_points)) if index not in self.visited],
            dtype=int,
        )
        if not len(remaining):
            raise ValueError("No unvisited exploration point is available")
        distances = np.linalg.norm(self.exploration_points[remaining] - position, axis=1)
        order = np.lexsort((self._exploration_tie_rank[remaining], distances))
        return int(remaining[int(order[0])])

    def set_point(self, target_xy_m: tuple[float, float]) -> None:
        self.point_target = np.asarray(target_xy_m, dtype=float)
        self._last_target = None

    def rotate_manual_direction(self, delta_rad: float) -> None:
        self.manual_direction_rad = float(np.angle(np.exp(1j * (
            self.manual_direction_rad + float(delta_rad)
        ))))
        self._last_target = None

    def skip_current_target(self) -> None:
        """Advance patrol/exploration on explicit operator request."""
        if self.mode not in {"patrol", "explore"}:
            return
        nearest = self.mode == "explore" and self.exploration_selection_policy == "seeded_nearest_unvisited"
        points = (self.patrol if self.mode == "patrol" else
                  (self.exploration_points if nearest else self.exploration_points[self.exploration_order]))
        index = int(self.current_index)
        if index not in self.visited:
            self.completed_targets_total += 1
        self.visited.add(index)
        remaining = [i for i in range(len(points)) if i not in self.visited]
        if remaining:
            self.current_index = (self._nearest_exploration_index(points[index])
                                  if nearest else remaining[0])
        else:
            self.completed_cycles += 1
            self.visited.clear(); self.current_index = 0
        self._last_target = None

    def abandon_current_target(self, position_xy_m: tuple[float, float]) -> None:
        """Advance past an unreachable target without counting completion."""
        if self.mode not in {"patrol", "explore"}:
            return
        position = np.asarray(position_xy_m, dtype=float)
        if position.shape != (2,) or not np.isfinite(position).all():
            raise ValueError("position_xy_m must be one finite 2D point")
        nearest = (self.mode == "explore" and
                   self.exploration_selection_policy == "seeded_nearest_unvisited")
        points = (self.patrol if self.mode == "patrol" else
                  (self.exploration_points if nearest else
                   self.exploration_points[self.exploration_order]))
        index = int(self.current_index)
        self.visited.add(index)
        self.abandoned_targets_total += 1
        remaining = [i for i in range(len(points)) if i not in self.visited]
        if remaining:
            self.current_index = (self._nearest_exploration_index(position)
                                  if nearest else remaining[0])
        else:
            self.completed_cycles += 1
            self.visited.clear()
            self.current_index = 0
        self._last_target = None

    def _advance_if_reached(self, position: np.ndarray, points: np.ndarray,
                            acceptance_m: float) -> None:
        index = int(self.current_index)
        if np.linalg.norm(points[index] - position) <= acceptance_m:
            if index not in self.visited:
                self.completed_targets_total += 1
            self.visited.add(index)
            remaining = [i for i in range(len(points)) if i not in self.visited]
            if remaining:
                self.current_index = remaining[0]
            else:
                self.completed_cycles += 1
                self.visited.clear()
                self.current_index = 0

    def update(self, position_xy_m: tuple[float, float], heading_rad: float) -> BehaviorTarget:
        position = np.asarray(position_xy_m, dtype=float)
        if position.shape != (2,) or not np.isfinite(position).all():
            raise ValueError("position_xy_m must be one finite 2D point")
        if self.mode == "point":
            target = self.point_target.copy(); index = 0; total = 1
        elif self.mode == "manual":
            horizon = float(self.config["manual_goal_horizon_m"])
            target = position + horizon * np.array([
                np.cos(self.manual_direction_rad), np.sin(self.manual_direction_rad)
            ])
            index = 0; total = 1
        elif self.mode == "patrol":
            self._advance_if_reached(position, self.patrol,
                                     float(self.config["patrol_acceptance_radius_m"]))
            index = int(self.current_index); target = self.patrol[index].copy(); total = len(self.patrol)
        else:
            if self.exploration_selection_policy == "seeded_nearest_unvisited":
                points = self.exploration_points
                acceptance = float(self.config["exploration_acceptance_radius_m"])
                index = int(self.current_index)
                if np.linalg.norm(points[index] - position) <= acceptance:
                    if index not in self.visited:
                        self.completed_targets_total += 1
                    self.visited.add(index)
                    if len(self.visited) == len(points):
                        self.completed_cycles += 1
                        self.visited = {index}
                    self.current_index = self._nearest_exploration_index(position)
                index = int(self.current_index); target = points[index].copy(); total = len(points)
            else:
                ordered = self.exploration_points[self.exploration_order]
                self._advance_if_reached(position, ordered,
                                         float(self.config["exploration_acceptance_radius_m"]))
                index = int(self.current_index); target = ordered[index].copy(); total = len(ordered)
        result_target = (float(target[0]), float(target[1]))
        changed = (self._last_target is None if self.mode == "manual" else
                   self._last_target is None or not np.allclose(result_target, self._last_target))
        self._last_target = result_target
        return BehaviorTarget(
            mode=self.mode,
            target_xy_m=result_target,
            changed=changed,
            target_index=index,
            visited_targets=len(self.visited),
            total_targets=total,
            completed_targets_total=self.completed_targets_total,
            completed_cycles=self.completed_cycles,
            abandoned_targets_total=self.abandoned_targets_total,
        )
