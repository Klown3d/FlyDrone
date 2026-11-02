"""Conventional geometric safety layer for circular horizontal obstacles."""
from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class CircleObstacle:
    center_xy_m: np.ndarray
    radius_m: float


def point_clearance(position_xy: np.ndarray,obstacle: CircleObstacle,vehicle_radius_m: float=0.) -> float:
    return float(np.linalg.norm(np.asarray(position_xy)-obstacle.center_xy_m)-obstacle.radius_m-vehicle_radius_m)


def segment_clearance(start_xy: np.ndarray,end_xy: np.ndarray,obstacle: CircleObstacle,vehicle_radius_m: float=0.) -> float:
    start=np.asarray(start_xy,float);end=np.asarray(end_xy,float);delta=end-start
    fraction=0. if float(delta@delta)<1e-15 else float(np.clip((obstacle.center_xy_m-start)@delta/(delta@delta),0,1))
    closest=start+fraction*delta
    return point_clearance(closest,obstacle,vehicle_radius_m)


class ObstaclePlanner:
    """Select one deterministic bypass waypoint; no biological interpretation."""
    def __init__(self,obstacles: list[CircleObstacle],vehicle_radius_m: float,safety_margin_m: float,waypoint_margin_m: float,waypoint_acceptance_m: float=.25):
        self.obstacles=obstacles;self.vehicle_radius_m=vehicle_radius_m;self.safety_margin_m=safety_margin_m;self.waypoint_margin_m=waypoint_margin_m
        self.waypoint_acceptance_m=waypoint_acceptance_m;self.active_waypoint=None;self.activations=0

    def _clear(self,start,end,obstacle):
        return segment_clearance(start,end,obstacle,self.vehicle_radius_m)>=self.safety_margin_m

    def local_goal(self,position_xy: np.ndarray,target_xy: np.ndarray,heading_rad: float|None=None) -> np.ndarray:
        position=np.asarray(position_xy,float);target=np.asarray(target_xy,float)
        if self.active_waypoint is not None:
            if all(self._clear(position,target,o) for o in self.obstacles):self.active_waypoint=None
            else:return self.active_waypoint.copy()
        blocking=[o for o in self.obstacles if not self._clear(position,target,o)]
        if not blocking:return target.copy()
        obstacle=min(blocking,key=lambda o:np.linalg.norm(o.center_xy_m-position));direction=target-position;direction/=np.linalg.norm(direction);perpendicular=np.array([-direction[1],direction[0]])
        required=obstacle.radius_m+self.vehicle_radius_m+self.safety_margin_m+self.waypoint_margin_m;candidates=[]
        for sign in (1.,-1.):
            offset=required
            for _ in range(8):
                candidate=obstacle.center_xy_m+sign*offset*perpendicular
                if self._clear(position,candidate,obstacle) and self._clear(candidate,target,obstacle):break
                offset*=1.25
            length=np.linalg.norm(candidate-position)+np.linalg.norm(target-candidate)
            bearing=float(np.arctan2(candidate[1]-position[1],candidate[0]-position[0]))
            turn=0. if heading_rad is None else abs(float(np.arctan2(np.sin(bearing-heading_rad),np.cos(bearing-heading_rad))))
            candidates.append((turn,length,-sign,candidate))
        self.active_waypoint=min(candidates,key=lambda item:(item[0],item[1],item[2]))[3];self.activations+=1
        return self.active_waypoint.copy()
