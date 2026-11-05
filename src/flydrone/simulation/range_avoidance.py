"""Short-lived local hit map and engineering range-based avoidance goals."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml

from flydrone.simulation.range_sensor import RangeScan
from flydrone.simulation.range_safety_barrier import BarrierCommand, InflatedPointBarrier


def wrap(angle: float | np.ndarray) -> float | np.ndarray:
    return np.angle(np.exp(1j * angle))


def surface_segments_from_scan(scan: RangeScan, position_xy_m: np.ndarray,
                               heading_rad: float, maximum_endpoint_gap_m: float,
                               maximum_range_jump_m: float,
                               maximum_angular_gap_rad: float) -> np.ndarray:
    """Join only adjacent, geometrically compatible ray hits into surfaces.

    The construction uses sensor endpoints only.  It intentionally cannot see
    simulator obstacle centers, radii, or labels.
    """
    position = np.asarray(position_xy_m, dtype=float)
    angles = np.asarray(scan.relative_angles_rad, dtype=float)
    ranges = np.asarray(scan.ranges_m, dtype=float)
    hit = np.asarray(scan.hit_mask, dtype=bool)
    if position.shape != (2,) or not np.isfinite(position).all():
        raise ValueError("Surface-map position must be one finite 2D point")
    if not (len(angles) == len(ranges) == len(hit)):
        raise ValueError("Range scan arrays must have equal length")
    if maximum_endpoint_gap_m <= 0 or maximum_range_jump_m <= 0 or maximum_angular_gap_rad <= 0:
        raise ValueError("Surface continuity thresholds must be positive")
    world = heading_rad + angles
    endpoints = position + ranges[:, None] * np.column_stack((np.cos(world), np.sin(world)))
    pairs = [(index, index + 1) for index in range(max(0, len(angles) - 1))]
    if len(angles) > 2:
        circular_gap = abs(float(wrap(angles[0] - angles[-1])))
        if circular_gap <= maximum_angular_gap_rad:
            pairs.append((len(angles) - 1, 0))
    segments = []
    for first, second in pairs:
        angular_gap = abs(float(wrap(angles[second] - angles[first])))
        if (hit[first] and hit[second] and angular_gap <= maximum_angular_gap_rad and
                abs(float(ranges[first] - ranges[second])) <= maximum_range_jump_m and
                float(np.linalg.norm(endpoints[first] - endpoints[second])) <= maximum_endpoint_gap_m):
            segments.append(np.stack((endpoints[first], endpoints[second])))
    return (np.asarray(segments, dtype=float) if segments else
            np.empty((0, 2, 2), dtype=float))


def hit_points_from_scan(scan: RangeScan, position_xy_m: np.ndarray,
                         heading_rad: float) -> np.ndarray:
    """Return current world-frame endpoints for hit rays only."""
    position = np.asarray(position_xy_m, dtype=float)
    hit = np.asarray(scan.hit_mask, dtype=bool)
    angles = float(heading_rad) + np.asarray(scan.relative_angles_rad, dtype=float)[hit]
    ranges = np.asarray(scan.ranges_m, dtype=float)[hit]
    if not len(ranges):
        return np.empty((0, 2), dtype=float)
    return position + ranges[:, None] * np.column_stack((np.cos(angles), np.sin(angles)))


@dataclass(frozen=True)
class AvoidanceTarget:
    target_xy_m: tuple[float, float]
    active: bool
    selected_relative_angle_rad: float
    minimum_sensed_range_m: float
    mapped_points: int
    speed_fraction: float
    source: str = "engineering_range_avoidance"
    safety_correction_xy_m_s2: tuple[float, float] = (0.0, 0.0)
    strategy: str = "direct"
    barrier_active: bool = False
    predicted_clearance_m: float = float("inf")
    barrier_speed_fraction: float = 1.0
    mission_target_blocked: bool = False
    mapped_surfaces: int = 0


class LocalHitMap:
    """Remember quantized ray-hit locations for a bounded amount of time."""

    def __init__(self, memory_s: float, resolution_m: float):
        if memory_s <= 0 or resolution_m <= 0:
            raise ValueError("Local-map memory and resolution must be positive")
        self.memory_s = float(memory_s)
        self.resolution_m = float(resolution_m)
        self._cells: dict[tuple[int, int], tuple[np.ndarray, float]] = {}

    def reset(self) -> None:
        self._cells.clear()

    def update(self, scan: RangeScan, position_xy_m: np.ndarray,
               heading_rad: float, dt_s: float) -> np.ndarray:
        if dt_s <= 0:
            raise ValueError("dt_s must be positive")
        aged = {key: (point, age + dt_s) for key, (point, age) in self._cells.items()
                if age + dt_s <= self.memory_s}
        position = np.asarray(position_xy_m, dtype=float)
        for relative, distance, hit in zip(scan.relative_angles_rad, scan.ranges_m, scan.hit_mask):
            if not hit:
                continue
            angle = float(heading_rad + relative)
            point = position + float(distance) * np.array([np.cos(angle), np.sin(angle)])
            key = tuple(np.rint(point / self.resolution_m).astype(int))
            aged[key] = (point, 0.0)
        self._cells = aged
        if not aged:
            return np.empty((0, 2), dtype=float)
        return np.asarray([item[0] for item in aged.values()], dtype=float)

    def points(self) -> np.ndarray:
        if not self._cells:
            return np.empty((0, 2), dtype=float)
        return np.asarray([item[0] for item in self._cells.values()], dtype=float)

    def visible_recent_points(self, scan: RangeScan, position_xy_m: np.ndarray,
                              heading_rad: float, maximum_age_s: float,
                              visibility_tolerance_m: float,
                              maximum_angular_gap_rad: float) -> np.ndarray:
        """Keep recent points not contradicted by the current range scan."""
        if maximum_age_s <= 0 or visibility_tolerance_m < 0 or maximum_angular_gap_rad <= 0:
            raise ValueError("Selective-memory thresholds are invalid")
        position = np.asarray(position_xy_m, dtype=float)
        angles = np.asarray(scan.relative_angles_rad, dtype=float)
        ranges = np.asarray(scan.ranges_m, dtype=float)
        hit = np.asarray(scan.hit_mask, dtype=bool)
        selected = []
        for point, age in self._cells.values():
            if age > maximum_age_s:
                continue
            offset = point - position
            distance = float(np.linalg.norm(offset))
            if distance <= 1e-9:
                selected.append(point)
                continue
            relative = float(wrap(np.arctan2(offset[1], offset[0]) - heading_rad))
            differences = np.abs(wrap(angles - relative))
            nearest = int(np.argmin(differences))
            if differences[nearest] > maximum_angular_gap_rad:
                continue
            # A nearer current return can occlude the remembered surface.  An
            # absent or materially farther return contradicts the old point.
            if hit[nearest] and ranges[nearest] <= distance + visibility_tolerance_m:
                selected.append(point)
        return (np.asarray(selected, dtype=float) if selected else
                np.empty((0, 2), dtype=float))


class RangeAvoidancePlanner:
    """Choose a short local goal while preserving the mission goal separately."""

    def __init__(self, config_path: Path, barrier_config_path: Path | None = None):
        self.config_path = Path(config_path)
        self.config = yaml.safe_load(self.config_path.read_text(encoding="utf-8"))
        if self.config.get("parameter_status") != "engineering_local_range_avoidance_not_neural":
            raise ValueError("Avoidance configuration must declare its engineering status")
        positive = ("activation_distance_m", "safety_buffer_m", "local_goal_horizon_m",
                    "minimum_goal_horizon_m", "corridor_half_width_deg", "map_memory_s",
                    "map_resolution_m", "mapped_point_clearance_m", "waypoint_acceptance_m",
                    "release_clearance_m", "minimum_candidate_clearance_m",
                    "release_progress_m", "contour_tangent_weight",
                    "blocked_speed_fraction_threshold", "blocked_waypoint_replan_s",
                    "direct_clear_release_hold_s")
        if any(float(self.config[name]) <= 0 for name in positive):
            raise ValueError("Avoidance distances and memory must be positive")
        self.local_map = LocalHitMap(float(self.config["map_memory_s"]),
                                     float(self.config["map_resolution_m"]))
        self.safety_barrier = (None if barrier_config_path is None else
                               InflatedPointBarrier(Path(barrier_config_path)))
        self.activations = 0
        self.active_updates = 0
        self.updates = 0
        self._was_active = False
        self._preferred_sign = 0.0
        self._active_waypoint: np.ndarray | None = None
        self._hit_goal_distance: float | None = None
        self._mission_target: np.ndarray | None = None
        self.contour_waypoints = 0
        self.contour_releases = 0
        self.blocked_waypoint_replans = 0
        self._blocked_waypoint_s = 0.0
        self._direct_clear_s = 0.0
        self._mission_best_distance: float | None = None
        self._mission_no_progress_s = 0.0
        self._current_surfaces = np.empty((0, 2, 2), dtype=float)
        self._current_hit_points = np.empty((0, 2), dtype=float)
        self._selective_safety_points = np.empty((0, 2), dtype=float)
        rejection_start = float(self.config["emergency_rejection_start_m"])
        rejection_full = float(self.config["emergency_rejection_full_m"])
        rejection_max = float(self.config["emergency_rejection_max_acceleration_m_s2"])
        if not 0 < rejection_full < rejection_start or rejection_max <= 0:
            raise ValueError("Invalid emergency rejection configuration")
        if rejection_start > float(self.config["stop_distance_m"]) + 1e-9:
            raise ValueError("Emergency rejection must start no farther than the stop distance")

    def reset(self) -> None:
        self.local_map.reset()
        self.activations = 0
        self.active_updates = 0
        self.updates = 0
        self._was_active = False
        self._preferred_sign = 0.0
        self._active_waypoint = None
        self._hit_goal_distance = None
        self._mission_target = None
        self.contour_waypoints = 0
        self.contour_releases = 0
        self.blocked_waypoint_replans = 0
        self._blocked_waypoint_s = 0.0
        self._direct_clear_s = 0.0
        self._mission_best_distance = None
        self._mission_no_progress_s = 0.0
        self._current_surfaces = np.empty((0, 2, 2), dtype=float)
        self._current_hit_points = np.empty((0, 2), dtype=float)
        self._selective_safety_points = np.empty((0, 2), dtype=float)

    @property
    def final_command_filter_enabled(self) -> bool:
        return bool(self.safety_barrier is not None and
                    self.safety_barrier.config.get("final_command_filter_enabled", False))

    def final_command_safety(self, position_xy_m: tuple[float, float],
                             velocity_xy_m_s: tuple[float, float],
                             nominal_acceleration_xy_m_s2: tuple[float, float]) -> BarrierCommand:
        """Check the fully composed engineering acceleration against sensed geometry."""
        if not self.final_command_filter_enabled:
            return BarrierCommand((0.0, 0.0), 1.0, float("inf"), False)
        if self.safety_barrier.config.get("current_scan_geometry_only", False):
            points = self._current_hit_points
        elif "selective_memory_max_age_s" in self.safety_barrier.config:
            points = self._selective_safety_points
        else:
            points = self.local_map.points()
        return self.safety_barrier.command_for_acceleration(
            position_xy_m, velocity_xy_m_s, nominal_acceleration_xy_m_s2,
            points, self._current_surfaces,
        )

    def _mapped_clearance(self, position: np.ndarray, angles_world: np.ndarray,
                          mapped: np.ndarray, maximum: float) -> np.ndarray:
        result = np.full(len(angles_world), maximum, dtype=float)
        if not len(mapped):
            return result
        offsets = mapped - position
        for index, angle in enumerate(angles_world):
            direction = np.array([np.cos(angle), np.sin(angle)])
            projection = offsets @ direction
            perpendicular = np.abs(offsets[:, 0] * direction[1] - offsets[:, 1] * direction[0])
            candidates = projection[(projection > 0) &
                                    (perpendicular <= float(self.config["mapped_point_clearance_m"]))]
            if len(candidates):
                result[index] = float(np.min(candidates))
        return result

    def _contour_desired_world(self, obstacle_world_rad: float, side_sign: float) -> float:
        """Blend tangent travel with an engineering outward standoff bias."""
        obstacle_direction = np.array([np.cos(obstacle_world_rad), np.sin(obstacle_world_rad)])
        tangent_angle = float(obstacle_world_rad + side_sign * np.pi / 2)
        tangent = np.array([np.cos(tangent_angle), np.sin(tangent_angle)])
        outward = -obstacle_direction
        desired = tangent + float(self.config.get("contour_outward_bias", 0.0)) * outward
        return float(np.arctan2(desired[1], desired[0]))

    def _emergency_correction(self, scan: RangeScan, heading_rad: float,
                              velocity_xy_m_s: np.ndarray | None = None) -> np.ndarray:
        """Return a bounded engineering rejection acceleration from close ray hits."""
        ranges = np.asarray(scan.ranges_m, dtype=float)
        hit = np.asarray(scan.hit_mask, dtype=bool)
        start = float(self.config["emergency_rejection_start_m"])
        full = float(self.config["emergency_rejection_full_m"])
        threat = hit & (ranges < start)
        if not np.any(threat):
            return np.zeros(2)
        weights = np.clip((start - ranges[threat]) / (start - full), 0.0, 1.0)
        world_angles = float(heading_rad) + np.asarray(scan.relative_angles_rad)[threat]
        away = -np.sum(weights[:, None] *
                       np.column_stack((np.cos(world_angles), np.sin(world_angles))), axis=0)
        norm = float(np.linalg.norm(away))
        if norm <= 1e-9:
            nearest = int(np.argmin(ranges))
            angle = float(heading_rad + scan.relative_angles_rad[nearest])
            away = -np.array([np.cos(angle), np.sin(angle)])
            norm = 1.0
        away_unit = away / norm
        base_max = float(self.config["emergency_rejection_max_acceleration_m_s2"])
        magnitude = base_max * float(np.max(weights))
        if velocity_xy_m_s is not None:
            velocity = np.asarray(velocity_xy_m_s, dtype=float)
            if velocity.shape != (2,) or not np.isfinite(velocity).all():
                raise ValueError("Avoidance velocity must be one finite 2D vector")
            closing_speed = max(0.0, float(velocity @ -away_unit))
            magnitude += float(self.config.get("emergency_closing_speed_gain_per_s", 0.0)) * closing_speed
        hard_max = float(self.config.get("emergency_rejection_hard_max_acceleration_m_s2", base_max))
        return away_unit * min(hard_max, magnitude)

    def update(self, scan: RangeScan, position_xy_m: tuple[float, float],
               heading_rad: float, mission_target_xy_m: tuple[float, float],
               dt_s: float, velocity_xy_m_s: tuple[float, float] | None = None) -> AvoidanceTarget:
        position = np.asarray(position_xy_m, dtype=float)
        mission = np.asarray(mission_target_xy_m, dtype=float)
        if position.shape != (2,) or mission.shape != (2,) or not np.isfinite(position).all() or not np.isfinite(mission).all():
            raise ValueError("Avoidance pose and target must be finite 2D points")
        if self._mission_target is not None and not np.allclose(mission, self._mission_target,
                                                                atol=1e-6, rtol=0.0):
            self._active_waypoint = None
            self._hit_goal_distance = None
            self._preferred_sign = 0.0
            self._was_active = False
            self._blocked_waypoint_s = 0.0
            self._direct_clear_s = 0.0
            self._mission_best_distance = None
            self._mission_no_progress_s = 0.0
        self._mission_target = mission.copy()
        mapped = self.local_map.update(scan, position, float(heading_rad), float(dt_s))
        surfaces = np.empty((0, 2, 2), dtype=float)
        if "surface_max_endpoint_gap_m" in self.config:
            surfaces = surface_segments_from_scan(
                scan, position, float(heading_rad),
                float(self.config["surface_max_endpoint_gap_m"]),
                float(self.config["surface_max_range_jump_m"]),
                np.deg2rad(float(self.config["surface_max_angular_gap_deg"])),
            )
        self._current_surfaces = surfaces
        self._current_hit_points = hit_points_from_scan(scan, position, float(heading_rad))
        if self.safety_barrier is not None and "selective_memory_max_age_s" in self.safety_barrier.config:
            self._selective_safety_points = self.local_map.visible_recent_points(
                scan, position, float(heading_rad),
                float(self.safety_barrier.config["selective_memory_max_age_s"]),
                float(self.safety_barrier.config["selective_memory_visibility_tolerance_m"]),
                np.deg2rad(float(self.safety_barrier.config["selective_memory_max_angular_gap_deg"])),
            )
        else:
            self._selective_safety_points = np.empty((0, 2), dtype=float)
        angles = np.asarray(scan.relative_angles_rad, dtype=float)
        ranges = np.asarray(scan.ranges_m, dtype=float)
        half_width = np.deg2rad(float(self.config["corridor_half_width_deg"]))
        corridor = np.asarray([float(np.min(ranges[np.abs(wrap(angles-angle)) <= half_width]))
                               if np.any(np.abs(wrap(angles-angle)) <= half_width) else float(ranges[i])
                               for i, angle in enumerate(angles)])
        world_angles = float(heading_rad) + angles
        mapped_clearance = self._mapped_clearance(position, world_angles, mapped,
                                                   float(np.max(ranges)))
        clearance = np.minimum(corridor, mapped_clearance)
        goal_vector = mission - position
        goal_distance = float(np.linalg.norm(goal_vector))
        goal_bearing = float(np.arctan2(goal_vector[1], goal_vector[0]))
        goal_relative = float(wrap(goal_bearing - float(heading_rad)))
        direct_index = int(np.argmin(np.abs(wrap(angles - goal_relative))))
        blocked_timeout = float(self.config.get("blocked_mission_timeout_s", 0.0))
        blocked_progress = float(self.config.get("blocked_mission_progress_m", 0.25))
        avoidance_context = bool(self._active_waypoint is not None or
                                 clearance[direct_index] < float(self.config["activation_distance_m"]))
        if blocked_timeout > 0 and avoidance_context:
            if (self._mission_best_distance is None or
                    goal_distance <= self._mission_best_distance - blocked_progress):
                self._mission_best_distance = goal_distance
                self._mission_no_progress_s = 0.0
            else:
                self._mission_no_progress_s += float(dt_s)
        else:
            self._mission_best_distance = goal_distance
            self._mission_no_progress_s = 0.0
        mission_target_blocked = bool(blocked_timeout > 0 and
                                      self._mission_no_progress_s >= blocked_timeout)
        minimum = float(np.min(ranges))
        emergency_correction = self._emergency_correction(
            scan, float(heading_rad),
            None if velocity_xy_m_s is None else np.asarray(velocity_xy_m_s, dtype=float),
        )
        barrier_command = (BarrierCommand((0.0, 0.0), 1.0, float("inf"), False)
                           if self.safety_barrier is None else
                           self.safety_barrier.command(
                               tuple(position),
                               (0.0, 0.0) if velocity_xy_m_s is None else velocity_xy_m_s,
                               mapped,
                               surfaces,
                           ))
        safety_correction = (np.asarray(barrier_command.correction_xy_m_s2, dtype=float)
                             if barrier_command.active else emergency_correction)
        stop = float(self.config["stop_distance_m"])
        slow = float(self.config["slowdown_start_distance_m"])
        if not 0 < stop < slow:
            raise ValueError("Avoidance stop distance must be below slowdown distance")
        minimum_candidate_clearance = float(self.config["minimum_candidate_clearance_m"])
        if minimum_candidate_clearance + 1e-9 < stop + float(self.config["minimum_goal_horizon_m"]):
            raise ValueError("Candidate clearance must cover stopping distance and minimum horizon")
        direct_speed_fraction = float(np.clip((clearance[direct_index] - stop) / (slow - stop), 0., 1.))
        self.updates += 1
        activation_clearance = float(self.config["activation_distance_m"])
        release_clearance = float(self.config["release_clearance_m"])
        if release_clearance < activation_clearance:
            raise ValueError("Avoidance release clearance must not be below activation clearance")

        # Keep the detour fixed in world coordinates. Recomputing it around the
        # current pose creates a moving target and can trap the vehicle in an orbit.
        if self._active_waypoint is not None:
            waypoint_vector = self._active_waypoint - position
            waypoint_distance = float(np.linalg.norm(waypoint_vector))
            progressed = (self._hit_goal_distance is None or
                          goal_distance <= self._hit_goal_distance -
                          float(self.config["release_progress_m"]))
            obstacle_evidence = bool(np.any(scan.hit_mask) or len(mapped))
            direct_clear = clearance[direct_index] >= release_clearance
            self._direct_clear_s = (self._direct_clear_s + float(dt_s)
                                    if direct_clear else 0.0)
            if (direct_clear and
                    (progressed or not obstacle_evidence or
                     self._direct_clear_s >= float(self.config["direct_clear_release_hold_s"]))):
                self._active_waypoint = None
                self._hit_goal_distance = None
                self.contour_releases += 1
                self._blocked_waypoint_s = 0.0
                self._direct_clear_s = 0.0
            elif waypoint_distance > float(self.config["waypoint_acceptance_m"]):
                waypoint_bearing = float(np.arctan2(waypoint_vector[1], waypoint_vector[0]))
                waypoint_relative = float(wrap(waypoint_bearing - float(heading_rad)))
                waypoint_index = int(np.argmin(np.abs(wrap(angles - waypoint_relative))))
                selected_speed = float(np.clip((clearance[waypoint_index] - stop) /
                                                (slow - stop), 0., 1.))
                speed_fraction = min(float(self.config["maximum_active_speed_fraction"]),
                                     selected_speed, barrier_command.speed_fraction)
                if speed_fraction <= float(self.config["blocked_speed_fraction_threshold"]):
                    self._blocked_waypoint_s += float(dt_s)
                else:
                    self._blocked_waypoint_s = 0.0
                if self._blocked_waypoint_s >= float(self.config["blocked_waypoint_replan_s"]):
                    self._active_waypoint = None
                    self._blocked_waypoint_s = 0.0
                    self.blocked_waypoint_replans += 1
                else:
                    self.active_updates += 1
                    self._was_active = True
                    return AvoidanceTarget((float(self._active_waypoint[0]),
                                            float(self._active_waypoint[1])), True,
                                           waypoint_relative, minimum, len(mapped), speed_fraction,
                                           safety_correction_xy_m_s2=(float(safety_correction[0]),
                                                                      float(safety_correction[1])),
                                           strategy="contour_follow",
                                           barrier_active=barrier_command.active,
                                           predicted_clearance_m=barrier_command.predicted_clearance_m,
                                           barrier_speed_fraction=barrier_command.speed_fraction,
                                           mission_target_blocked=mission_target_blocked,
                                           mapped_surfaces=len(surfaces))
            else:
                self._active_waypoint = None
                self._blocked_waypoint_s = 0.0

        if clearance[direct_index] >= activation_clearance:
            self._was_active = False
            self._preferred_sign = 0.0
            self._hit_goal_distance = None
            self._blocked_waypoint_s = 0.0
            self._direct_clear_s = 0.0
            return AvoidanceTarget((float(mission[0]), float(mission[1])), False,
                                   goal_relative, minimum, len(mapped),
                                   min(direct_speed_fraction, barrier_command.speed_fraction),
                                   safety_correction_xy_m_s2=(float(safety_correction[0]),
                                                              float(safety_correction[1])),
                                   barrier_active=barrier_command.active,
                                   predicted_clearance_m=barrier_command.predicted_clearance_m,
                                   barrier_speed_fraction=barrier_command.speed_fraction,
                                   mission_target_blocked=mission_target_blocked,
                                   mapped_surfaces=len(surfaces))
        normalized_clearance = np.clip(clearance / activation_clearance, 0.0, 1.0)
        continuing_contour = bool(self._was_active and self._preferred_sign)
        if continuing_contour:
            hit = np.asarray(scan.hit_mask, dtype=bool)
            if np.any(hit):
                hit_indices = np.flatnonzero(hit)
                obstacle_index = int(hit_indices[np.argmin(ranges[hit])])
                obstacle_world = float(world_angles[obstacle_index])
            elif len(mapped):
                nearest_point = mapped[int(np.argmin(np.linalg.norm(mapped - position, axis=1)))]
                offset = nearest_point - position
                obstacle_world = float(np.arctan2(offset[1], offset[0]))
            else:
                obstacle_world = goal_bearing
            desired_world = self._contour_desired_world(obstacle_world, self._preferred_sign)
            tangent_relative = float(wrap(desired_world - float(heading_rad)))
            scores = (float(self.config["contour_tangent_weight"]) *
                      np.cos(wrap(angles - tangent_relative)) +
                      float(self.config["clearance_weight"]) * normalized_clearance -
                      float(self.config["turn_penalty_weight"]) *
                      np.abs(wrap(angles - tangent_relative)) / np.pi)
        else:
            scores = (float(self.config["goal_alignment_weight"]) *
                      np.cos(wrap(angles - goal_relative)) +
                      float(self.config["clearance_weight"]) * normalized_clearance -
                      float(self.config["turn_penalty_weight"]) * np.abs(angles) / np.pi)
        if self._preferred_sign and not continuing_contour:
            scores += float(self.config["side_hysteresis_bonus"]) * (np.sign(angles) == self._preferred_sign)
        safe = clearance >= minimum_candidate_clearance
        selected = int(np.argmax(np.where(safe, scores, -np.inf))) if safe.any() else int(np.argmax(clearance))
        if not self._preferred_sign and abs(float(angles[selected])) > 1e-6:
            self._preferred_sign = float(np.sign(angles[selected]))
            self._hit_goal_distance = goal_distance
        usable = max(float(self.config["minimum_goal_horizon_m"]),
                     float(clearance[selected] - max(stop, float(self.config["safety_buffer_m"]))))
        horizon = min(float(self.config["local_goal_horizon_m"]), usable)
        angle_world = float(world_angles[selected])
        local = position + horizon * np.array([np.cos(angle_world), np.sin(angle_world)])
        self._active_waypoint = local.copy()
        self.contour_waypoints += 1
        if not self._was_active:
            self.activations += 1
        self.active_updates += 1
        self._was_active = True
        selected_speed = float(np.clip((clearance[selected] - stop) / (slow - stop), 0., 1.))
        speed_fraction = min(float(self.config["maximum_active_speed_fraction"]), selected_speed)
        speed_fraction = min(speed_fraction, barrier_command.speed_fraction)
        return AvoidanceTarget((float(local[0]), float(local[1])), True,
                               float(angles[selected]), minimum, len(mapped), speed_fraction,
                               safety_correction_xy_m_s2=(float(safety_correction[0]),
                                                          float(safety_correction[1])),
                               strategy="contour_follow",
                               barrier_active=barrier_command.active,
                               predicted_clearance_m=barrier_command.predicted_clearance_m,
                               barrier_speed_fraction=barrier_command.speed_fraction,
                               mission_target_blocked=mission_target_blocked,
                               mapped_surfaces=len(surfaces))

