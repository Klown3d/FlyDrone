"""Native Panda3D desktop prototype with complete downloaded FlyWire skeletons."""
from pathlib import Path
import argparse
import json
import time
import os
import subprocess
import sys
import numpy as np
import pandas as pd
import yaml
from panda3d.core import (loadPrcFileData, LineSegs, BitMask32, Geom, GeomNode,
                         GeomVertexData, GeomVertexFormat, GeomLines, PerspectiveLens, ClockObject, Quat)
from direct.showbase.ShowBase import ShowBase
from direct.gui.OnscreenText import OnscreenText
from direct.gui.DirectGui import DirectButton,DirectFrame
from flydrone.visualization.pfl3_viewer import read_skeleton
from flydrone.neural.epg_delta7 import EPGDelta7Candidate
from flydrone.neural.phase_compass_estimator import PhaseCompassEstimator
from flydrone.neural.pfl2_steering import PFL2SteeringController
from flydrone.neural.pfl2_advance import PFL2AdvanceController
from flydrone.neural.travel_direction_drift import TravelDirectionDriftController
from flydrone.simulation.hover import HoverState, update
from flydrone.simulation.navigation import NavigationState, advance, goal_bearing, held_goal_bearing, update_arrival
from flydrone.simulation.quadrotor import (QuadrotorState,acceleration_attitude_controller,euler_to_quaternion,
                                           quaternion_to_rotation,step as quadrotor_step,yaw_from_quaternion)
from flydrone.simulation.obstacles import CircleObstacle,ObstaclePlanner,point_clearance
from flydrone.simulation.travel_velocity_sensor import PositionVelocityEstimator
from flydrone.simulation.landmark_heading_sensor import LandmarkHeadingSensor
from flydrone.simulation.behavior_manager import MODES, NavigationBehaviorManager
from flydrone.neural.steering_interface import command
from flydrone.data.acquire import save_json, file_hash, utc_now


BEHAVIOR_LABELS = {"point": "punto", "manual": "dirección", "patrol": "patrulla", "explore": "exploración"}


def signed_activity_color(value: float, scale: float) -> tuple:
    """Original FlyDrone palette: green near zero, red positive, blue negative."""
    v=float(value/scale)
    return (max(.15,min(1,v)),.25+.6*max(0,1-abs(v)),max(.2,min(1,-v)),1)


def rate_activity_color(value_hz: float, display_max_hz: float) -> tuple:
    """Map nonnegative firing rates from dark green through yellow to red."""
    v = float(np.clip(value_hz / display_max_hz, 0.0, 1.0))
    low = np.array((.06, .18, .12))
    middle = np.array((1.0, .85, .10))
    high = np.array((1.0, .12, .04))
    rgb = low + (middle - low) * (2 * v) if v <= .5 else middle + (high - middle) * (2 * v - 1)
    return (*rgb.tolist(), 1.0)


class FlyDroneDesktop(ShowBase):
    def __init__(self, root: Path, offscreen: bool=False):
        loadPrcFileData('', 'window-title FlyDrone | navegación simulada\nwin-size 1440 900\naudio-library-name null\nsync-video true')
        super().__init__(windowType='offscreen' if offscreen else None)
        self.root=root;self.disableMouse();self.setBackgroundColor(.025,.04,.075)
        self.c=yaml.safe_load((root/'configs/desktop.yaml').read_text())
        self.navigation=yaml.safe_load((root/self.c.get('navigation_config','configs/navigation.yaml')).read_text())
        self.quad=yaml.safe_load((root/self.c['quadrotor_config']).read_text())
        self.quad_navigation=yaml.safe_load((root/self.c['quadrotor_navigation_config']).read_text())
        self.b=yaml.safe_load((root/self.c['orientation_config']).read_text())
        self.model=EPGDelta7Candidate(root,root/self.b['candidate_config'])
        self.pfl2_controller=PFL2SteeringController(root,root/self.c['pfl2_steering_config'])
        self.pfl2_advance_controller=PFL2AdvanceController(root/self.c['pfl2_advance_config'])
        self.drift_controller=TravelDirectionDriftController(root,root/self.c['travel_direction_drift_config'])
        self.velocity_sensor=PositionVelocityEstimator(root/self.c['travel_velocity_sensor_config'])
        self.landmark_sensor=LandmarkHeadingSensor(root/self.c['landmark_heading_sensor_config'])
        self.behavior_manager=NavigationBehaviorManager(root/self.c['behavior_manager_config'])
        self.scene=self.render.attachNewNode('hover environment');self.scene.hide(BitMask32.bit(1))
        self.brain=self.render.attachNewNode('complete skeleton circuit');self.brain.hide(BitMask32.bit(0))
        self.cam.node().setCameraMask(BitMask32.bit(0));self.camNode.getDisplayRegion(0).setDimensions(0,.6,0,1)
        self.camLens.setAspectRatio(1440*.6/900);self.camera.setPos(9,-14,11);self.camera.lookAt(.5,.5,1.3)
        lens=PerspectiveLens();lens.setAspectRatio(1440*.4/(900*.58));lens.setFov(45);lens.setNearFar(.1,3000)
        self.braincam=self.makeCamera(self.win,displayRegion=(.6,1,.18,.76),lens=lens)
        self.braincam.reparentTo(self.render)
        self.braincam.node().setCameraMask(BitMask32.bit(1));self.braincam.setPos(0,-210,65);self.braincam.lookAt(0,0,0)
        self.geometry={};self.classes={};self.trace=[];self.accumulator=0.;self.paused=True;self.baseline=False;self.flight_mode='plano';self.gust_remaining_s=0.;self.obstacle_enabled=False;self.heading_signal_available=True;self.velocity_signal_available=True;self.drift_enabled=True;self.pfl2_advance_enabled=True
        self.compass_variant='v4_pen_a_regularizada';self.active_phase_compass_config=Path(self.c['phase_compass_config'])
        self.sensor_mode='ideal';self.sensor_rng=np.random.default_rng(self.c['sensor_seed'])
        self.make_environment();self.load_neurons();self.reset()
        self.title=OnscreenText(text='FlyDrone  |  SIMULADO - MODELO PROVISIONAL',pos=(-1.5,.91),scale=.047,align=0,fg=(.8,.94,1,1))
        DirectButton(text='Comparar ensayos 3D',scale=.030,pos=(1.08,0,.93),command=self.open_gate_replay)
        self.metrics=OnscreenText(text='',pos=(-1.48,.76),scale=.043,align=0,fg=(.8,.9,1,1),mayChange=True)
        self.pipeline=OnscreenText(text='',pos=(-1.48,.39),scale=.034,align=0,fg=(.55,1,.82,1),mayChange=True)
        OnscreenText(text=f"{self.geometry_report['neurons']} esqueletos completos - FlyWire 783\nEPG/Delta7/FC2/PFN/hDeltaB: azul - | verde cero | rojo +\nPFL3/PFL2: verde bajo | amarillo medio | rojo alto\nActividad global, no propagación por ramas",pos=(.66,.82),scale=.029,fg=(.8,.9,1,1))
        self.status=OnscreenText(text='Pausado',pos=(0,-.91),scale=.034,fg=(.8,.9,1,1),mayChange=True)
        OnscreenText(text='Vectores: verde rumbo | celeste movimiento | magenta hDeltaB | naranja corrección',pos=(-.44,-.53),scale=.025,fg=(.72,.85,1,1))
        OnscreenText(text='hDeltaB - 12 columnas',pos=(.96,-.17),scale=.027,fg=(1,.45,.9,1))
        self.hdelta_bars=[]
        for i in range(12):
            bar=DirectFrame(frameColor=(.2,.7,.4,1),frameSize=(-.022,.022,0,.001),pos=(.60+i*.065,0,-.36))
            self.hdelta_bars.append(bar)
        buttons=[('Iniciar / pausar',self.toggle),('Reiniciar',self.reset),('Cambiar meta',self.next_goal),('Neuronal / proporcional',self.switch),('Guardar ensayo',self.save)]
        for i,(label,action) in enumerate(buttons):
            DirectButton(text=label,scale=.04,pos=(-1.32+i*.64,0,-.82),command=action)
        DirectButton(text='Sensor ideal / perturbado',scale=.034,pos=(-1.18,0,-.72),command=self.switch_sensor)
        self.behavior_button=DirectButton(text='Modo: punto',scale=.030,pos=(-1.30,0,-.63),command=self.cycle_behavior_mode)
        DirectButton(text='Perturbar dron +0,6 m',scale=.034,pos=(-.53,0,-.72),command=self.disturb)
        DirectButton(text='Planta plana / 6DoF',scale=.034,pos=(.10,0,-.72),command=self.switch_flight_mode)
        DirectButton(text='Ráfaga 0,5 N',scale=.031,pos=(.47,0,-.75),command=self.apply_gust)
        DirectButton(text='Obstáculo seguro',scale=.031,pos=(.84,0,-.75),command=self.toggle_obstacle)
        DirectButton(text='Landmark ON/OFF',scale=.029,pos=(1.18,0,-.69),command=self.toggle_heading_signal)
        DirectButton(text='Deriva hDeltaB ON/OFF',scale=.026,pos=(1.18,0,-.76),command=self.toggle_drift)
        DirectButton(text='Velocidad PFN ON/OFF',scale=.025,pos=(.80,0,-.69),command=self.toggle_velocity_signal)
        DirectButton(text='Brújula v4 / v2',scale=.025,pos=(.42,0,-.69),command=self.toggle_compass_variant)
        DirectButton(text='Avance PFL2 ON/OFF',scale=.024,pos=(.04,0,-.69),command=self.toggle_pfl2_advance)
        for i,label in enumerate(['Todas','EPG','Delta7','FC2','PFL3','PFL2','PFN','hDeltaB']):
            DirectButton(text=label,scale=.027,pos=(.27+i*.17,0,-.61),command=self.filter,extraArgs=[label])
        self.accept('space',self.toggle);self.accept('r',self.reset);self.accept('g',self.next_goal);self.accept('b',self.cycle_behavior_mode);self.accept('s',self.save)
        self.accept('arrow_left',self.rotate,[-12]);self.accept('arrow_right',self.rotate,[12])
        self.accept('wheel_up',self.zoom,[.9]);self.accept('wheel_down',self.zoom,[1.1])
        self.taskMgr.add(self.tick,'fixed_step_simulation')

    def lines(self,parent,name,segments,color,width=2):
        lines=LineSegs(name);lines.setColor(*color);lines.setThickness(width)
        for a,b in segments:lines.moveTo(*a);lines.drawTo(*b)
        return parent.attachNewNode(lines.create())

    def make_environment(self):
        grid=[]
        for i in range(-5,6):grid.extend([((i,-5,0),(i,5,0)),((-5,i,0),(5,i,0))])
        self.lines(self.scene,'floor grid',grid,(.15,.24,.34,1),1)
        self.drone=self.scene.attachNewNode('simplified drone')
        arms=[((-.5,-.5,0),(.5,.5,0)),((-.5,.5,0),(.5,-.5,0))]
        self.lines(self.drone,'arms',arms,(.85,.92,1,1),7)
        for x,y in [(-.5,-.5),(-.5,.5),(.5,-.5),(.5,.5)]:
            circle=[(x+.22*np.cos(t),y+.22*np.sin(t),0) for t in np.linspace(0,2*np.pi,40)]
            self.lines(self.drone,'rotor ring',list(zip(circle[:-1],circle[1:])),(.35,.8,1,1),3)
        self.lines(self.drone,'heading arrow',[((0,0,.06),(.8,0,.06)),((.8,0,.06),(.6,.13,.06)),((.8,0,.06),(.6,-.13,.06))],(.2,1,.7,1),5)
        arrow=[((0,0,0),(1,0,0)),((1,0,0),(.78,.12,0)),((1,0,0),(.78,-.12,0))]
        self.motionnode=self.scene.attachNewNode('measured travel direction');self.lines(self.motionnode,'movement vector',arrow,(.15,.8,1,1),5)
        self.travelnode=self.scene.attachNewNode('hDeltaB decoded travel direction');self.lines(self.travelnode,'neural travel vector',arrow,(1,.25,.85,1),5)
        self.correctionnode=self.scene.attachNewNode('hDeltaB correction');self.lines(self.correctionnode,'neural correction vector',arrow,(1,.55,.1,1),5)
        self.motionnode.hide();self.travelnode.hide();self.correctionnode.hide()
        self.windnode=self.scene.attachNewNode('external wind force')
        self.lines(self.windnode,'wind arrow',[((0,-1.2,0),(0,0,0)),((0,0,0),(-.14,-.25,0)),((0,0,0),(.14,-.25,0))],(1,.45,.1,1),6);self.windnode.hide()
        self.goalnode=self.scene.attachNewNode('goal heading marker')
        ring=[(.3*np.cos(t),.3*np.sin(t),2) for t in np.linspace(0,2*np.pi,40)]
        self.lines(self.goalnode,'spatial goal',list(zip(ring[:-1],ring[1:]))+[((0,0,0),(0,0,2))],(1,.8,.2,1),3)
        self.obstaclenode=self.scene.attachNewNode('circular obstacle');radius=float(self.c['desktop_obstacle_radius_m']);height=2.6
        lower=[(radius*np.cos(t),radius*np.sin(t),0) for t in np.linspace(0,2*np.pi,48)];upper=[(x,y,height) for x,y,_ in lower]
        vertical=[(lower[i],upper[i]) for i in range(0,len(lower)-1,8)]
        self.lines(self.obstaclenode,'obstacle cylinder',list(zip(lower[:-1],lower[1:]))+list(zip(upper[:-1],upper[1:]))+vertical,(1,.28,.12,1),5);self.obstaclenode.hide()
        self.waypointnode=self.scene.attachNewNode('conventional local waypoint');waypoint_ring=[(.16*np.cos(t),.16*np.sin(t),1.4) for t in np.linspace(0,2*np.pi,32)]
        self.lines(self.waypointnode,'local waypoint',list(zip(waypoint_ring[:-1],waypoint_ring[1:]))+[((0,0,0),(0,0,1.4))],(.2,1,1,1),3);self.waypointnode.hide()
        self.landmarknode=self.scene.attachNewNode('known visual landmark');landmark_ring=[(.22*np.cos(t),.22*np.sin(t),2.8) for t in np.linspace(0,2*np.pi,36)]
        self.lines(self.landmarknode,'landmark beacon',list(zip(landmark_ring[:-1],landmark_ring[1:]))+[((0,0,0),(0,0,2.8))],(.2,1,.85,1),4)
        lb=self.landmark_sensor.landmark_world_bearing_rad;ld=float(self.landmark_sensor.config['landmark_distance_m']);self.landmarknode.setPos(ld*np.cos(lb),ld*np.sin(lb),0)

    def load_neurons(self):
        loaded=[]
        seen=set()
        for row in self.pfl2_controller.model.nodes.itertuples():
            points,edges=read_skeleton(self.root/f'data/raw/flywire_skeletons_783/{row.root_id}.bin')
            rid=str(row.root_id);loaded.append((rid,row.selected_type,points,edges));seen.add(rid)
        travel_nodes=pd.concat([self.drift_controller.model.pfn,self.drift_controller.model.hdelta],ignore_index=True)
        for row in travel_nodes.itertuples():
            rid=str(row.root_id)
            if rid in seen:continue
            points,edges=read_skeleton(self.root/f'data/raw/flywire_skeletons_783/{rid}.bin')
            loaded.append((rid,row.selected_type,points,edges));seen.add(rid)
        origin=np.concatenate([p for _,_,p,_ in loaded]).mean(axis=0)
        radius=max(float(np.linalg.norm((p-origin)/1000,axis=1).max()) for _,_,p,_ in loaded)
        self.braincam.setPos(0,-radius*3.3,radius*.7);self.braincam.lookAt(0,0,0)
        vertices=0;edge_count=0
        for rid,kind,points,edges in loaded:
            data=GeomVertexData(rid,GeomVertexFormat.getV3(),Geom.UHStatic)
            data.setNumRows(len(points));data.modifyArray(0).modifyHandle().setData(np.asarray((points-origin)/1000,dtype=np.float32).tobytes())
            primitive=GeomLines(Geom.UHStatic);primitive.setIndexType(Geom.NTUint32)
            primitive.modifyVertices().modifyHandle().setData(np.asarray(edges,dtype=np.uint32).tobytes())
            geom=Geom(data);geom.addPrimitive(primitive);node=GeomNode(rid);node.addGeom(geom)
            path=self.brain.attachNewNode(node);path.setColor(.2,.25,.32,1);path.setRenderModeThickness(1)
            self.geometry[rid]=path;self.classes[rid]=kind;vertices+=len(points);edge_count+=len(edges)
        self.geometry_report={'neurons':len(loaded),'vertices':vertices,'edges':edge_count,'sampling':'none; all downloaded vertices and edges','dataset':'FAFB','materialization_version':783}

    def reset(self):
        self.state=NavigationState(altitude=self.c['initial_altitude_m'],heading=np.deg2rad(self.c['initial_heading_deg']))
        self.gust_remaining_s=0.;self.advance_fraction=0.
        if self.flight_mode=='6dof':
            self.quad_state=QuadrotorState(position_m=np.array([0.,0.,self.c['initial_altitude_m']]),
                                            quaternion_wxyz=euler_to_quaternion(0,0,self.state.heading))
            self.neural_countdown=0.;self.last_yaw_command=0.;self.desired_speed=0.;self.last_motor_command=np.zeros(4)
        self.behavior_manager.reset(tuple(self.navigation['target_xy_m']),self.state.heading)
        self.behavior_target=self.behavior_manager.update((float(self.state.x),float(self.state.y)),self.state.heading)
        self.target=self.behavior_target.target_xy_m;self.goal=float(goal_bearing(self.state,self.target));self.elapsed=0.;self.trace=[];self.accumulator=0.
        self.compass_estimator=PhaseCompassEstimator(self.root,self.active_phase_compass_config,self.state.heading)
        self.compass_heading=self.state.heading;self.compass_resultant=1.;self.compass_contrast=1.
        self.configure_obstacle()
        self.goal_held=False;self.last_reliable_goal=self.goal
        self.sensor_rng=np.random.default_rng(self.c['sensor_seed'])
        self.velocity_sensor.reset()
        if hasattr(self,'trail'):self.trail.removeNode()
        self.trail=self.scene.attachNewNode('recorded trajectory');self.last_trail_update=-1.
        if hasattr(self,'status'):self.status.setText('Pausado')
        if hasattr(self,'behavior_button'):self.behavior_button['text']=f"Modo: {BEHAVIOR_LABELS[self.behavior_manager.mode]}"
        raw=self.observe();self.last_control_observation=self.compass_observe(raw,self.c['dt_s'])
        self.neural_update(self.last_control_observation);self.render_state()

    def observe(self):
        if self.sensor_mode=='ideal':
            dx=dy=dh=0.
        else:
            bias=self.c['sensor_position_bias_m'];sigma=self.c['sensor_position_noise_m']
            dx=float(bias[0]+self.sensor_rng.normal(0,sigma));dy=float(bias[1]+self.sensor_rng.normal(0,sigma))
            dh=0.
        heading,self.landmark_relative_bearing=self.landmark_sensor.observe(self.state.heading,self.sensor_rng,self.sensor_mode!='ideal')
        return NavigationState(x=float(self.state.x+dx),y=float(self.state.y+dy),vx=0.,vy=0.,altitude=float(self.state.altitude),heading=heading)

    def compass_observe(self,raw,dt):
        self.raw_observation=raw
        cue=raw.heading if self.heading_signal_available else None
        self.compass_heading,self.compass_resultant,self.compass_contrast=self.compass_estimator.update(cue,self.state.yaw_rate,dt)
        velocity=self.velocity_sensor.update(np.array([raw.x,raw.y]) if self.velocity_signal_available else None,dt)
        return NavigationState(x=raw.x,y=raw.y,vx=float(velocity[0]),vy=float(velocity[1]),altitude=raw.altitude,heading=self.compass_heading)

    def neural_update(self,observation=None):
        m=self.model;observation=self.observe() if observation is None else observation
        self.observation=observation
        behavior=self.behavior_manager.update((float(observation.x),float(observation.y)),observation.heading)
        self.apply_behavior_target(behavior)
        self.true_goal=float(goal_bearing(self.state,self.target))
        self.local_target=self.target if self.planner is None else tuple(self.planner.local_goal(np.array([observation.x,observation.y]),np.asarray(self.target),observation.heading))
        if np.allclose(self.local_target,self.target):
            self.goal,self.goal_held=held_goal_bearing(self.last_reliable_goal,self.goal_held,observation,self.target,
                                                      self.c['neural_goal_hold_radius_m'],self.c['neural_goal_release_radius_m'])
        else:
            self.goal=float(np.arctan2(self.local_target[1]-observation.y,self.local_target[0]-observation.x));self.goal_held=False
        if not self.goal_held:self.last_reliable_goal=self.goal
        self.drift_state=self.drift_controller.command(observation.heading,np.array([observation.vx,observation.vy]),self.goal)
        yaw,values,pfl2_activity,pfl2_index,pfl2_scale,base_yaw=self.pfl2_controller.command(
            m,observation.heading,self.goal,self.b,enabled=not self.baseline,baseline=self.baseline)
        epg,delta,fc2,rates,signal=values
        self.activity={}
        for ids,values,scale in [(m.epg_ids,epg,1),(m.base.delta_ids,delta,1),(m.base.fc2_ids,fc2,1)]:
            for rid,value in zip(ids,values):
                v=float(value/scale);self.activity[str(rid)]=float(value)
                self.geometry[str(rid)].setColor(*signed_activity_color(value,scale))
        pfl3_display_max_hz=float(self.c.get('pfl3_activity_display_max_hz',40.0))
        for rid,value in zip(m.base.pfl3.root_id,rates):
            self.activity[str(rid)]=float(value)
            self.geometry[str(rid)].setColor(*rate_activity_color(value,pfl3_display_max_hz))
        for rid,value in zip(self.pfl2_controller.model.pfl2_ids,pfl2_activity):
            self.activity[str(rid)]=float(value)
            self.geometry[str(rid)].setColor(*rate_activity_color(value,1.0))
        pfn_activity=self.drift_state['pfn_activity'];hdelta_activity=self.drift_state['hdelta_activity']
        for ids,values in [(self.drift_controller.model.pfn.root_id,pfn_activity),(self.drift_controller.model.hdelta.root_id,hdelta_activity)]:
            scale=max(1e-9,float(np.max(np.abs(values))))
            for rid,value in zip(ids,values):
                self.activity[str(rid)]=float(value);self.geometry[str(rid)].setColor(*signed_activity_color(value,scale))
        column_activity=np.zeros(12)
        for column,value in zip(self.drift_controller.model.hdelta.fb_axon_column,hdelta_activity):
            column_activity[int(str(column).removeprefix('HDB_FB'))-1]+=float(value)
        self.hdelta_column_activity=column_activity
        if hasattr(self,'hdelta_bars'):
            scale=max(1e-9,float(np.max(np.abs(column_activity))))
            for bar,value in zip(self.hdelta_bars,column_activity):
                normalized=float(value/scale);height=.16*normalized
                bar['frameSize']=(-.022,.022,min(0.,height),max(.001,height));bar['frameColor']=signed_activity_color(value,scale)
        pfl3_peak=int(np.argmax(rates))
        self.neural_summary={'epg_peak':int(np.argmax(epg)),'delta_peak':int(np.argmax(np.abs(delta))),
                             'fc2_peak':int(np.argmax(fc2)),'pfl3_peak':pfl3_peak,'pfl3_peak_hz':float(rates[pfl3_peak]),
                             'pfl3_left_hz':float(rates[m.base.left].sum()),
                             'pfl3_right_hz':float(rates[m.base.right].sum()),'signal_hz':float(signal),
                             'pfl2_mean_activity':float(np.mean(pfl2_activity)),'pfl2_index':float(pfl2_index),
                             'pfl2_scale':float(pfl2_scale),'base_yaw_rad_s':float(base_yaw),'yaw_rad_s':float(yaw),
                             'travel_direction_rad':float(self.drift_state['decoded_direction_rad']),
                             'travel_resultant':float(self.drift_state['resultant']),
                             'lateral_drift_m_s':float(self.drift_state['lateral_drift_m_s']),
                             'drift_correction_m_s2':float(np.linalg.norm(self.drift_state['correction_world_m_s2'])),
                             'pfn_peak':int(np.argmax(np.abs(pfn_activity))),'hdelta_peak':int(np.argmax(np.abs(hdelta_activity)))}
        return float(yaw)

    def render_state(self):
        self.drone.setPos(float(self.state.x),float(self.state.y),self.state.altitude)
        self.windnode.setPos(float(self.state.x),float(self.state.y),self.state.altitude+.45)
        if self.flight_mode=='6dof' and self.gust_remaining_s>0:self.windnode.show()
        else:self.windnode.hide()
        if self.flight_mode=='6dof':
            q=self.quad_state.quaternion_wxyz;self.drone.setQuat(Quat(float(q[0]),float(q[1]),float(q[2]),float(q[3])))
        else:self.drone.setHpr(np.rad2deg(self.state.heading),0,0)
        self.goalnode.setPos(*self.target,0)
        if self.obstacle_enabled and self.flight_mode=='6dof':
            self.obstaclenode.show();self.waypointnode.setPos(*self.local_target,0)
            if np.allclose(self.local_target,self.target):self.waypointnode.hide()
            else:self.waypointnode.show()
        else:self.obstaclenode.hide();self.waypointnode.hide()
        speed=float(np.hypot(self.state.vx,self.state.vy));correction=np.asarray(self.drift_state['correction_world_m_s2'])
        if self.flight_mode=='6dof' and speed>.03:
            for node,z,angle,scale in [(self.motionnode,.35,np.arctan2(self.state.vy,self.state.vx),min(1.3,.35+speed)),(self.travelnode,.58,self.drift_state['decoded_direction_rad'],min(1.3,.35+speed))]:
                node.show();node.setPos(self.state.x,self.state.y,self.state.altitude+z);node.setH(np.rad2deg(angle));node.setScale(scale)
        else:self.motionnode.hide();self.travelnode.hide()
        if self.flight_mode=='6dof' and self.drift_enabled and not self.baseline and np.linalg.norm(correction)>.01:
            self.correctionnode.show();self.correctionnode.setPos(self.state.x,self.state.y,self.state.altitude+.82);self.correctionnode.setH(np.rad2deg(np.arctan2(correction[1],correction[0])));self.correctionnode.setScale(min(1.3,.35+float(np.linalg.norm(correction))))
        else:self.correctionnode.hide()
        if self.trace and self.elapsed-self.last_trail_update>=.2:
            for child in self.trail.getChildren():child.removeNode()
            points=[(0.,0.,.03)]+[(r['x_m'],r['y_m'],.03) for r in self.trace[::10]]
            self.lines(self.trail,'trajectory',list(zip(points[:-1],points[1:])),(.7,.45,1,1),2)
            self.last_trail_update=self.elapsed

    def sync_quad_state(self):
        q=self.quad_state;self.state.x=float(q.position_m[0]);self.state.y=float(q.position_m[1]);self.state.altitude=float(q.position_m[2])
        self.state.vx=float(q.velocity_m_s[0]);self.state.vy=float(q.velocity_m_s[1]);self.state.vertical_speed=float(q.velocity_m_s[2])
        self.state.heading=yaw_from_quaternion(q.quaternion_wxyz);self.state.yaw_rate=float(q.body_rate_rad_s[2])

    def step_6dof(self,dt):
        record=False;self.neural_countdown-=dt
        if self.neural_countdown<=0:
            raw=self.observe();observation=self.compass_observe(raw,self.quad_navigation['neural_update_period_s']);self.last_control_observation=observation;self.last_yaw_command=self.neural_update(observation)
            update_arrival(self.state,observation,self.target,self.navigation,self.quad_navigation['neural_update_period_s'])
            distance=float(np.hypot(self.target[0]-observation.x,self.target[1]-observation.y));error=float(np.angle(np.exp(1j*(observation.heading-self.goal))))
            if self.pfl2_advance_enabled and not self.baseline:
                self.desired_speed,self.advance_fraction=self.pfl2_advance_controller.desired_speed(distance,self.neural_summary['pfl2_index'],self.quad_navigation['maximum_forward_speed_m_s'],self.quad_navigation['distance_gain_per_s'])
            else:
                self.advance_fraction=float(max(0.,np.cos(error)));self.desired_speed=min(self.quad_navigation['maximum_forward_speed_m_s'],self.quad_navigation['distance_gain_per_s']*distance)*self.advance_fraction
            if self.state.arrived:self.desired_speed=0.;self.advance_fraction=0.
            self.neural_countdown+=self.quad_navigation['neural_update_period_s'];record=True
        yaw=yaw_from_quaternion(self.quad_state.quaternion_wxyz);forward=np.array([np.cos(yaw),np.sin(yaw)]);lateral=np.array([-np.sin(yaw),np.cos(yaw)])
        forward_speed=float(self.quad_state.velocity_m_s[:2]@forward);lateral_speed=float(self.quad_state.velocity_m_s[:2]@lateral)
        neural_drift=self.drift_enabled and not self.baseline
        lateral_gain=0. if neural_drift else self.quad_navigation['lateral_velocity_kd_per_s']
        drift_correction=np.asarray(self.drift_state['correction_world_m_s2']) if neural_drift else np.zeros(2)
        acceleration_xy=forward*self.quad_navigation['forward_speed_kp_per_s']*(self.desired_speed-forward_speed)-lateral*lateral_gain*lateral_speed+drift_correction
        acceleration_z=self.quad['altitude_kp_per_s2']*(self.quad_navigation['target_altitude_m']-self.quad_state.position_m[2])-self.quad['altitude_kd_per_s']*self.quad_state.velocity_m_s[2]
        self.last_motor_command,_=acceleration_attitude_controller(self.quad_state,np.r_[acceleration_xy,acceleration_z],self.last_yaw_command,self.quad)
        wind=np.asarray(self.c['desktop_gust_force_world_n'],float) if self.gust_remaining_s>0 else np.zeros(3)
        quadrotor_step(self.quad_state,self.last_motor_command,self.quad,dt,external_force_world_n=wind);self.gust_remaining_s=max(0.,self.gust_remaining_s-dt);self.sync_quad_state();self.elapsed+=dt
        if self.obstacle is not None:self.minimum_obstacle_clearance_m=min(self.minimum_obstacle_clearance_m,point_clearance(self.quad_state.position_m[:2],self.obstacle,float(self.c['desktop_vehicle_radius_m'])))
        if record:
            row={'time_s':self.elapsed,'x_m':self.state.x,'y_m':self.state.y,'observed_x_m':float(self.observation.x),'observed_y_m':float(self.observation.y),'observed_heading_rad':float(self.raw_observation.heading),'neural_heading_rad':float(self.compass_heading),'compass_resultant':self.compass_resultant,'compass_contrast':self.compass_contrast,'heading_signal_available':self.heading_signal_available,'velocity_signal_available':self.velocity_signal_available,'target_x_m':self.target[0],'target_y_m':self.target[1],'arrived':bool(self.state.arrived),'altitude_m':self.state.altitude,'heading_rad':self.state.heading,'goal_rad':self.goal,'true_goal_rad':self.true_goal,'command_rad_s':self.last_yaw_command,'desired_speed_m_s':self.desired_speed,'advance_fraction':self.advance_fraction,'pfl2_advance_enabled':self.pfl2_advance_enabled and not self.baseline,'pfl3_right_minus_left_hz':self.neural_summary['signal_hz'],'pfl2_index':self.neural_summary['pfl2_index'],'pfl2_scale':self.neural_summary['pfl2_scale'],'controller':'proportional' if self.baseline else 'neural','sensor_mode':self.sensor_mode,'flight_mode':'6dof'}
            row.update(self.behavior_trace_fields())
            row.update({'local_target_x_m':self.local_target[0],'local_target_y_m':self.local_target[1],'obstacle_clearance_m':None if self.obstacle is None else self.minimum_obstacle_clearance_m,'hdelta_drift_enabled':neural_drift,'decoded_travel_direction_rad':self.drift_state['decoded_direction_rad'],'travel_resultant':self.drift_state['resultant'],'lateral_drift_m_s':self.drift_state['lateral_drift_m_s'],'drift_correction_m_s2':float(np.linalg.norm(drift_correction))});row.update({f'motor_{i}_n':float(v) for i,v in enumerate(self.quad_state.motor_thrust_n)});row.update({f'wind_{axis}_n':float(value) for axis,value in zip('xyz',wind)});row.update({f'activity_{rid}':v for rid,v in self.activity.items()});self.trace.append(row)

    def tick(self,task):
        if not self.paused:
            self.accumulator+=min(ClockObject.getGlobalClock().getDt(),.1)
            dt=self.quad['dt_s'] if self.flight_mode=='6dof' else self.c['dt_s']
            while self.accumulator>=dt:
                if self.flight_mode=='6dof':self.step_6dof(dt)
                else:
                    raw=self.observe();observation=self.compass_observe(raw,dt);self.last_control_observation=observation;yaw_command=self.neural_update(observation)
                    thrust=advance(self.state,yaw_command,self.target,self.c,self.navigation,self.b['yaw_response_tau_s'],dt,observation=observation);self.elapsed+=dt
                    row={'time_s':self.elapsed,'x_m':float(self.state.x),'y_m':float(self.state.y),'observed_x_m':float(observation.x),'observed_y_m':float(observation.y),'observed_heading_rad':float(self.raw_observation.heading),'neural_heading_rad':float(self.compass_heading),'compass_resultant':self.compass_resultant,'compass_contrast':self.compass_contrast,'heading_signal_available':self.heading_signal_available,'target_x_m':self.target[0],'target_y_m':self.target[1],'arrived':bool(self.state.arrived),'altitude_m':self.state.altitude,'heading_rad':self.state.heading,'goal_rad':self.goal,'true_goal_rad':self.true_goal,'command_rad_s':yaw_command,'pfl3_right_minus_left_hz':self.neural_summary['signal_hz'],'pfl2_index':self.neural_summary['pfl2_index'],'pfl2_scale':self.neural_summary['pfl2_scale'],'thrust_n':thrust,'controller':'proportional' if self.baseline else 'neural','sensor_mode':self.sensor_mode,'flight_mode':'plano'}
                    row.update(self.behavior_trace_fields())
                    row.update({f'activity_{rid}':v for rid,v in self.activity.items()});self.trace.append(row)
                self.accumulator-=dt
            self.neural_update(self.last_control_observation);self.render_state()
        error=np.rad2deg(np.angle(np.exp(1j*(self.state.heading-self.goal))))
        distance=float(np.hypot(self.target[0]-self.state.x,self.target[1]-self.state.y))
        sensed_distance=float(np.hypot(self.target[0]-self.observation.x,self.target[1]-self.observation.y));n=self.neural_summary
        attitude=''
        if self.flight_mode=='6dof':
            r=quaternion_to_rotation(self.quad_state.quaternion_wxyz);roll=np.rad2deg(np.arctan2(r[2,1],r[2,2]));pitch=np.rad2deg(np.arcsin(np.clip(-r[2,0],-1,1)));attitude=f"\nRoll {roll:+.1f}° | pitch {pitch:+.1f}° | motores {self.quad_state.motor_thrust_n.mean():.2f} N | ráfaga {self.gust_remaining_s:.1f} s"
            if self.obstacle is not None:attitude+=f" | margen {self.minimum_obstacle_clearance_m:.2f} m"
        compass_error=np.rad2deg(np.angle(np.exp(1j*(self.compass_heading-self.state.heading))))
        signal='ON' if self.heading_signal_available else 'OFF'
        self.metrics.setText(f"{'Proporcional' if self.baseline else 'FlyWire'} | brújula {self.compass_variant} | planta {self.flight_mode}\nTiempo {self.elapsed:.1f} s | altura {self.state.altitude:.2f} m | modo {BEHAVIOR_LABELS[self.behavior_manager.mode]}\nDistancia real {distance:.2f} m | observada {sensed_distance:.2f} m | objetivo {self.behavior_target.target_index+1}/{self.behavior_target.total_targets}\n{'Meta alcanzada' if self.state.arrived else 'En camino'} | sensor {self.sensor_mode} | landmark {signal}\nRumbo neuronal {np.rad2deg(self.compass_heading):.1f}° | error {compass_error:+.1f}° | confianza {self.compass_resultant:.2f}{attitude}")
        goal_note=' (retenida cerca de meta)' if self.goal_held else (' (meta local convencional)' if not np.allclose(self.local_target,self.target) else '')
        self.pipeline.setText(f"ENTRADA  landmark {np.rad2deg(self.landmark_relative_bearing):+.1f}° -> heading {np.rad2deg(self.observation.heading):.1f}° -> meta {np.rad2deg(self.goal):.1f}°{goal_note}\nCIRCUITO EPG[{n['epg_peak']}] -> Delta7[{n['delta_peak']}] + FC2[{n['fc2_peak']}]\nSALIDA   PFL3 L {n['pfl3_left_hz']:.1f} Hz | R {n['pfl3_right_hz']:.1f} Hz | pico PFL3[{n['pfl3_peak']}] {n['pfl3_peak_hz']:.1f} Hz\nPFL2     actividad {n['pfl2_mean_activity']:.2f} | antimeta {n['pfl2_index']:.2f} | giro x{n['pfl2_scale']:.2f} | avance x{self.advance_fraction:.2f} {'ON' if self.pfl2_advance_enabled and not self.baseline else 'analítico'}\nPFN->hDeltaB  dirección {np.rad2deg(n['travel_direction_rad']):+.1f}° | confianza {n['travel_resultant']:.2f} | velocidad {'ON' if self.velocity_signal_available else 'OFF'}\nDERIVA   {n['lateral_drift_m_s']:+.2f} m/s -> corrección {n['drift_correction_m_s2']:.2f} m/s2 | {'ON' if self.drift_enabled else 'OFF'}")
        return task.cont

    def toggle(self):self.paused=not self.paused;self.status.setText('Pausado' if self.paused else 'Simulando | flechas: rotar circuito | rueda: zoom')
    def open_gate_replay(self):
        environment=os.environ.copy();environment['PYTHONPATH']=str(self.root/'src')
        subprocess.Popen([sys.executable,'-m','flydrone.visualization.gate_replay_3d'],
                         cwd=self.root,env=environment,
                         creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        self.status.setText('Comparador 3D abierto: reproduce ensayos preservados')
    def apply_behavior_target(self,behavior):
        previous=getattr(self,'target',None);self.behavior_target=behavior;self.target=behavior.target_xy_m
        changed=behavior.changed and (previous is None or not np.allclose(previous,self.target))
        if changed and hasattr(self,'state'):
            self.state.arrived=False;self.state.arrival_candidate_s=0.;self.state.departure_candidate_s=0.
            self.state.filtered_x=None;self.state.filtered_y=None;self.goal_held=False
            if hasattr(self,'obstaclenode') and self.obstacle_enabled and self.behavior_manager.mode!='manual':
                self.configure_obstacle()
    def behavior_trace_fields(self):
        return {'behavior_mode':self.behavior_target.mode,
                'behavior_target_index':self.behavior_target.target_index,
                'behavior_visited_targets':self.behavior_target.visited_targets,
                'behavior_total_targets':self.behavior_target.total_targets,
                'behavior_target_source':self.behavior_target.source}
    def cycle_behavior_mode(self):
        index=(MODES.index(self.behavior_manager.mode)+1)%len(MODES)
        behavior=self.behavior_manager.set_mode(MODES[index],(float(self.state.x),float(self.state.y)),self.state.heading)
        self.apply_behavior_target(behavior);self.configure_obstacle();self.goal_held=False
        self.behavior_button['text']=f"Modo: {BEHAVIOR_LABELS[self.behavior_manager.mode]}"
        self.neural_update(self.last_control_observation);self.render_state()
        self.status.setText(f"Modo {BEHAVIOR_LABELS[self.behavior_manager.mode]}: metas temporales de ingeniería")
    def next_goal(self):
        if self.behavior_manager.mode=='point':
            angle=np.arctan2(self.target[1],self.target[0])+np.pi/3;radius=np.hypot(*self.navigation['target_xy_m'])
            self.behavior_manager.set_point((float(radius*np.cos(angle)),float(radius*np.sin(angle))))
        elif self.behavior_manager.mode=='manual':
            self.behavior_manager.rotate_manual_direction(np.pi/3)
        else:self.behavior_manager.skip_current_target()
        behavior=self.behavior_manager.update((float(self.state.x),float(self.state.y)),self.state.heading)
        self.apply_behavior_target(behavior);self.configure_obstacle();self.render_state();self.neural_update(self.last_control_observation)
    def switch(self):self.baseline=not self.baseline;self.reset()
    def switch_sensor(self):
        self.sensor_mode='perturbado' if self.sensor_mode=='ideal' else 'ideal';self.reset()
    def toggle_heading_signal(self):
        self.heading_signal_available=not self.heading_signal_available
        self.status.setText('Landmark visible: cue externo disponible' if self.heading_signal_available else 'Landmark oculto: brújula en modo interno')
    def toggle_drift(self):
        self.drift_enabled=not self.drift_enabled
        self.status.setText('Compensación PFN/hDeltaB activa' if self.drift_enabled else 'Compensación PFN/hDeltaB desactivada; amortiguación convencional activa')
    def toggle_velocity_signal(self):
        self.velocity_signal_available=not self.velocity_signal_available
        self.status.setText('Velocidad PFN disponible' if self.velocity_signal_available else 'Velocidad PFN interrumpida: estimación en decaimiento')
    def toggle_compass_variant(self):
        if self.compass_variant=='v4_pen_a_regularizada':
            self.compass_variant='v2_cuña_publicada';self.active_phase_compass_config=Path(self.c['phase_compass_alternate_config'])
        else:
            self.compass_variant='v4_pen_a_regularizada';self.active_phase_compass_config=Path(self.c['phase_compass_config'])
        self.reset();self.status.setText(f'Brújula activa: {self.compass_variant}')
    def toggle_pfl2_advance(self):
        self.pfl2_advance_enabled=not self.pfl2_advance_enabled;self.reset()
        self.status.setText('PFL2 controla el avance' if self.pfl2_advance_enabled else 'Avance angular analítico activo')
    def switch_flight_mode(self):
        self.flight_mode='6dof' if self.flight_mode=='plano' else 'plano';self.reset()
    def configure_obstacle(self):
        self.obstacle=None;self.planner=None;self.minimum_obstacle_clearance_m=float('inf');self.local_target=self.target
        if self.obstacle_enabled and self.flight_mode=='6dof':
            center=np.asarray(self.target)*float(self.c['desktop_obstacle_distance_fraction']);self.obstacle=CircleObstacle(center,float(self.c['desktop_obstacle_radius_m']))
            self.planner=ObstaclePlanner([self.obstacle],float(self.c['desktop_vehicle_radius_m']),float(self.c['desktop_obstacle_safety_margin_m']),float(self.c['desktop_obstacle_waypoint_margin_m']))
            self.obstaclenode.setPos(float(center[0]),float(center[1]),0)
    def toggle_obstacle(self):
        if self.flight_mode!='6dof':self.status.setText('El obstáculo requiere planta 6DoF');return
        self.obstacle_enabled=not self.obstacle_enabled;self.reset();self.status.setText('Obstáculo y evasión convencional activos' if self.obstacle_enabled else 'Obstáculo desactivado')
    def apply_gust(self):
        if self.flight_mode!='6dof':
            self.status.setText('La ráfaga requiere planta 6DoF');return
        self.gust_remaining_s=float(self.c['desktop_gust_duration_s']);self.status.setText(f"Ráfaga física activa durante {self.gust_remaining_s:.1f} s")
    def disturb(self):
        if self.flight_mode=='6dof':self.quad_state.position_m[0]+=.6;self.sync_quad_state()
        else:self.state.x+=.6
        self.state.arrival_candidate_s=0.;self.state.departure_candidate_s=0.;self.neural_update(self.last_control_observation);self.render_state()
        self.status.setText('Perturbación física aplicada: +0,6 m en x')
    def rotate(self,angle):self.brain.setH(self.brain.getH()+angle)
    def zoom(self,factor):self.brain.setScale(max(.2,min(3,self.brain.getSx()/factor)))
    def filter(self,kind):
        for rid,path in self.geometry.items():
            if kind=='Todas' or self.classes[rid]==kind or (kind=='FC2' and self.classes[rid].startswith('FC2')) or (kind=='PFN' and self.classes[rid].startswith('PFN')):path.show()
            else:path.hide()
    def save(self):
        folder=self.root/'results/desktop'/str(time.time_ns());folder.mkdir(parents=True)
        pd.DataFrame(self.trace).to_csv(folder/'trace.csv',index=False)
        claim='6DoF rigid-body engineering plant; neural yaw and optional PFN/hDeltaB drift correction; conventional attitude/altitude/motors' if self.flight_mode=='6dof' else 'simplified vertical/yaw/planar velocity simulation'
        save_json(folder/'metadata.json',{'created_at':utc_now(),'geometry':self.geometry_report,'plant':self.c,'quadrotor':self.quad if self.flight_mode=='6dof' else None,'orientation':self.b,'navigation':self.navigation,'velocity_sensor':self.velocity_sensor.config,'pfl2_advance':self.pfl2_advance_controller.config,'pfl2_advance_enabled':self.pfl2_advance_enabled,'compass_variant':self.compass_variant,'phase_compass_config':self.active_phase_compass_config.as_posix(),'flight_mode':self.flight_mode,'behavior_mode':self.behavior_manager.mode,'behavior_manager':self.behavior_manager.config,'claim':claim+'; temporary goals are supplied by an explicit engineering behavior manager','config_sha256':file_hash(self.root/'configs/desktop.yaml')})
        self.status.setText('Ensayo guardado en results/desktop')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--smoke-test',action='store_true');args=parser.parse_args()
    app=FlyDroneDesktop(Path.cwd(),args.smoke_test)
    if args.smoke_test:
        trials=[]
        for baseline in (False,True):
            app.baseline=baseline;app.sensor_mode='ideal';app.reset();errors=[]
            for _ in range(round(20/app.c['dt_s'])):
                observation=app.observe();yaw=app.neural_update(observation);advance(app.state,yaw,app.target,app.c,app.navigation,app.b['yaw_response_tau_s'],app.c['dt_s'],observation=observation)
                errors.append(float(np.rad2deg(np.angle(np.exp(1j*(app.state.heading-app.goal))))))
            trials.append({'controller':'proportional' if baseline else 'neural','duration_s':20,
                'final_altitude_m':app.state.altitude,'final_error_deg':errors[-1],
                'arrived':bool(app.state.arrived),'distance_m':float(np.hypot(app.target[0]-app.state.x,app.target[1]-app.state.y))})
        app.baseline=False;app.sensor_mode='ideal';app.reset()
        for _ in range(round(30/app.c['dt_s'])):
            observation=app.observe();yaw=app.neural_update(observation);advance(app.state,yaw,app.target,app.c,app.navigation,app.b['yaw_response_tau_s'],app.c['dt_s'],observation=observation)
            if app.state.arrived:break
        arrived_before_disturbance=bool(app.state.arrived);held_goals=[];held_signals=[]
        for angle in np.linspace(0,2*np.pi,17)[:-1]:
            observation=NavigationState(x=app.target[0]+.08*np.cos(angle),y=app.target[1]+.08*np.sin(angle),
                                        altitude=app.state.altitude,heading=app.state.heading)
            app.neural_update(observation);held_goals.append(app.goal);held_signals.append(app.neural_summary['signal_hz'])
        stability={'synthetic_position_jitter_radius_m':.08,
                   'held_goal_span_deg':float(np.ptp(np.unwrap(held_goals))*180/np.pi),
                   'pfl3_signal_span_hz':float(np.ptp(held_signals))}
        app.state.x+=.6;resumed=False
        for _ in range(round(20/app.c['dt_s'])):
            observation=app.observe();yaw=app.neural_update(observation);advance(app.state,yaw,app.target,app.c,app.navigation,app.b['yaw_response_tau_s'],app.c['dt_s'],observation=observation)
            resumed=resumed or not bool(app.state.arrived)
        recovery={'displacement_x_m':.6,'arrived_before_disturbance':arrived_before_disturbance,'resumed_after_disturbance':resumed,
                  'arrived_again':bool(app.state.arrived),'final_distance_m':float(np.hypot(app.target[0]-app.state.x,app.target[1]-app.state.y))}
        behavior_checks=[]
        for mode in MODES:
            command=app.behavior_manager.set_mode(mode,(float(app.state.x),float(app.state.y)),app.state.heading)
            app.apply_behavior_target(command);initial_target=app.target
            yaw=app.neural_update(app.last_control_observation)
            if mode in {'patrol','explore'}:
                synthetic=NavigationState(x=initial_target[0],y=initial_target[1],altitude=app.state.altitude,heading=app.state.heading)
                app.neural_update(synthetic)
            elif mode=='manual':
                synthetic=NavigationState(x=app.state.x+.5,y=app.state.y+.25,altitude=app.state.altitude,heading=app.state.heading)
                app.neural_update(synthetic)
            behavior_checks.append({'mode':mode,'initial_target_xy_m':list(initial_target),'updated_target_xy_m':list(app.target),
                                    'target_changed':not np.allclose(initial_target,app.target),'yaw_command_rad_s':float(yaw),
                                    'source':app.behavior_target.source})
        app.behavior_manager.set_mode('point',(float(app.state.x),float(app.state.y)),app.state.heading);app.reset()
        output=Path('results/desktop');output.mkdir(parents=True,exist_ok=True)
        app.flight_mode='6dof';app.baseline=False;app.sensor_mode='ideal';app.reset();max_tilt=0.;saturated=False;wall_start=time.perf_counter()
        for index in range(round(30/app.quad['dt_s'])):
            if index==round(4/app.quad['dt_s']):app.apply_gust()
            app.step_6dof(app.quad['dt_s']);rotation=quaternion_to_rotation(app.quad_state.quaternion_wxyz)
            max_tilt=max(max_tilt,float(np.rad2deg(np.arccos(np.clip(rotation[2,2],-1,1)))))
            saturated=saturated or bool(np.any(app.last_motor_command>=app.quad['maximum_motor_thrust_n']-1e-9))
            if index==round(5/app.quad['dt_s']):
                app.render_state();app.taskMgr.step();app.win.saveScreenshot(str(output/'desktop-6dof-preview.png'))
        wall_duration=time.perf_counter()-wall_start
        sixdof={'controller':'neural','duration_s':30,'wall_duration_s':wall_duration,'realtime_factor':30/wall_duration,'gust_force_world_n':app.c['desktop_gust_force_world_n'],'gust_duration_s':app.c['desktop_gust_duration_s'],'arrived':bool(app.state.arrived),'distance_m':float(np.hypot(app.target[0]-app.state.x,app.target[1]-app.state.y)),
                'final_altitude_m':app.state.altitude,'final_speed_m_s':float(np.linalg.norm(app.quad_state.velocity_m_s)),'max_tilt_deg':max_tilt,
                'motor_saturated':saturated,'quaternion_norm':float(np.linalg.norm(app.quad_state.quaternion_wxyz))}
        app.obstacle_enabled=True;app.reset();obstacle_collision=False
        for index in range(round(35/app.quad['dt_s'])):
            app.step_6dof(app.quad['dt_s']);obstacle_collision=obstacle_collision or app.minimum_obstacle_clearance_m<0
            if index==round(2/app.quad['dt_s']):
                app.render_state();app.taskMgr.step();app.win.saveScreenshot(str(output/'desktop-obstacle-preview.png'))
        obstacle_trial={'controller':'neural','duration_s':35,'arrived':bool(app.state.arrived),'collision':obstacle_collision,'minimum_clearance_m':app.minimum_obstacle_clearance_m,
                        'distance_m':float(np.hypot(app.target[0]-app.state.x,app.target[1]-app.state.y)),'final_speed_m_s':float(np.linalg.norm(app.quad_state.velocity_m_s)),'planner_activations':app.planner.activations}
        app.obstacle_enabled=False;app.flight_mode='plano';app.baseline=False;app.reset();app.filter('EPG');app.filter('Todas')
        app.toggle()
        for _ in range(4):app.taskMgr.step()
        app.paused=True;app.reset();app.taskMgr.step()
        app.win.saveScreenshot(str(output/'desktop-preview.png'))
        save_json(output/'geometry-report.json',app.geometry_report)
        save_json(output/'navigation-integration-check.json',{'trials':trials,'arrival_activity_stability':stability,'post_arrival_recovery':recovery,'behavior_interface_checks':behavior_checks,'six_dof_trial':sixdof,'obstacle_trial':obstacle_trial,'claim':'Two ideal planar checks plus engineering arrival stability/recovery, four engineering behavior interfaces, selectable 6DoF with PFN/hDeltaB drift correction, gust, and one conventional obstacle-layer application check; not robustness evaluation'})
        if app.geometry_report['neurons']!=286:raise RuntimeError(f"Expected 286 complete skeletons, found {app.geometry_report['neurons']}")
        if not all(t['arrived'] and t['distance_m']<=app.navigation['arrival_radius_m'] and abs(t['final_altitude_m']-app.c['target_altitude_m'])<=.1 for t in trials):
            raise RuntimeError('Spatial desktop integration check failed')
        if not (recovery['arrived_before_disturbance'] and recovery['resumed_after_disturbance'] and recovery['arrived_again'] and recovery['final_distance_m']<=app.navigation['arrival_radius_m']):
            raise RuntimeError('Post-arrival recovery check failed')
        if stability['held_goal_span_deg']>1e-9 or stability['pfl3_signal_span_hz']>1e-9:
            raise RuntimeError('Neural goal changed under near-target position jitter')
        if (not all(np.isfinite(item['yaw_command_rad_s']) and item['source']=='engineering_behavior_manager' for item in behavior_checks)
                or not all(item['target_changed'] for item in behavior_checks if item['mode']!='point')):
            raise RuntimeError('Behavior manager interface check failed')
        if not (sixdof['arrived'] and sixdof['distance_m']<=app.navigation['arrival_radius_m'] and abs(sixdof['final_altitude_m']-app.quad_navigation['target_altitude_m'])<=.1 and sixdof['final_speed_m_s']<=app.quad_navigation['stop_speed_m_s'] and not sixdof['motor_saturated'] and abs(sixdof['quaternion_norm']-1)<1e-9):
            raise RuntimeError('Selectable 6DoF desktop integration check failed')
        if not (obstacle_trial['arrived'] and not obstacle_trial['collision'] and obstacle_trial['distance_m']<=app.navigation['arrival_radius_m'] and obstacle_trial['final_speed_m_s']<=app.quad_navigation['stop_speed_m_s']):
            raise RuntimeError('Desktop obstacle integration check failed')
        app.destroy()
    else:app.run()
