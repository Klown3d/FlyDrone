"""Native 3D comparison of preserved steering-gate flights and neuronal activity."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import inspect
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from direct.gui.DirectGui import DirectButton, DirectOptionMenu, DirectSlider
from direct.gui.OnscreenText import OnscreenText
from direct.showbase.ShowBase import ShowBase
from panda3d.core import (BitMask32, ClockObject, Filename, Geom, GeomLines,
                          GeomNode, GeomVertexArrayFormat, GeomVertexData,
                          GeomVertexFormat, InternalName, PerspectiveLens,
                          TextNode, loadPrcFileData)

from flydrone.data.acquire import file_hash, save_json, utc_now
from flydrone.neural.epg_delta7 import EPGDelta7Candidate
from flydrone.neural.pfl2_steering import PFL2SteeringController
from flydrone.neural.travel_direction_drift import TravelDirectionDriftController
from flydrone.visualization.desktop import FlyDroneDesktop, rate_activity_color, signed_activity_color
from flydrone.visualization.gate_replay_data import GATES, GateArchive
from flydrone.visualization.pfl3_viewer import read_skeleton


class GateReplay3D(ShowBase):
    """Replay exact saved positions and inputs; reconstruct only algebraic activity."""

    lines = FlyDroneDesktop.lines
    rotate = FlyDroneDesktop.rotate
    zoom = FlyDroneDesktop.zoom

    def __init__(self, root: Path, offscreen: bool = False):
        loadPrcFileData(
            "",
            "window-title FlyDrone | ensayos 3D\n"
            "win-size 1440 900\n"
            "audio-library-name null\n"
            "sync-video true\n"
            "clock-mode normal\n"
            "client-sleep 0.05\n"
            "yield-timeslice true",
        )
        super().__init__(windowType="offscreen" if offscreen else None)
        self.setSleep(0.05)
        self.root = root
        self.disableMouse()
        self.setBackgroundColor(.025, .04, .075)
        self.playing = False
        self.elapsed = 0.0
        self.speed = 1.0
        self.selected = 0
        self.camera_mode = "general"
        self.camera_angle = 0.0
        self.camera_zoom = 1.0
        self.case_index = 0
        self.setting_slider = False
        # Bound visual updates without changing the saved scientific traces.
        self.visual_update_interval_s = 1.0 / 10.0
        self.interactive_vertex_stride = 1
        self.visual_wall_accumulator_s = 0.0
        self.playback_accumulator_s = 0.0
        self._last_neural_colors: dict[str, tuple[float, float, float, float]] = {}
        self.orientation = yaml.safe_load((root / "configs/orientation_candidate_v1.yaml").read_text())
        self.model = EPGDelta7Candidate(root, root / self.orientation["candidate_config"])
        self.pfl2_controller = PFL2SteeringController(root, root / "configs/pfl2_steering.yaml")
        self.drift_controller = TravelDirectionDriftController(root, root / "configs/travel_direction_drift.yaml")
        self.geometry, self.classes = {}, {}
        self.scene = self.render.attachNewNode("paired saved flights")
        self.scene.hide(BitMask32.bit(1))
        self.brain = self.render.attachNewNode("complete FlyWire morphologies")
        self.brain.hide(BitMask32.bit(0))
        self.cam.node().setCameraMask(BitMask32.bit(0))
        self.camNode.getDisplayRegion(0).setDimensions(0, .56, .25, .77)
        self.camLens.setAspectRatio(1440 * .56 / (900 * .52))
        lens = PerspectiveLens()
        lens.setAspectRatio(1440 * .44 / (900 * .52))
        lens.setNearFar(.1, 3000)
        lens.setFov(45)
        self.braincam = self.makeCamera(self.win, displayRegion=(.56, 1, .25, .77), lens=lens)
        self.braincam.reparentTo(self.render)
        self.braincam.node().setCameraMask(BitMask32.bit(1))
        self.load_neurons()
        self.world_case = self.scene.attachNewNode("case")
        self._build_ui()
        self.open_gate("EPG-Delta7")
        self.accept("space", self.toggle)
        self.accept("r", self.reset_replay)
        self.accept("arrow_left", self.seek, [-1.0])
        self.accept("arrow_right", self.seek, [1.0])
        self.accept("wheel_up", self.zoom, [.9])
        self.accept("wheel_down", self.zoom, [1.1])
        self.accept("escape", self.userExit)
        self.accept("c", self.cycle_camera)
        self.accept("a", self.orbit_world, [-15.])
        self.accept("d", self.orbit_world, [15.])
        self.accept("w", self.zoom_world, [.85])
        self.accept("s", self.zoom_world, [1.15])
        self.accept("home", self.reset_camera)
        self.accept("n", self.select_neuron, [-1])
        self.accept("m", self.select_neuron, [1])
        self.accept("e", self.export_current_view)
        self.taskMgr.add(self.tick, "preserved_gate_replay")

    @staticmethod
    def _population_group(kind: str) -> str:
        """Collapse annotation subtypes only for rendering/filter grouping."""
        if kind.startswith("FC2"):
            return "FC2"
        if kind.startswith("PFN"):
            return "PFN"
        return kind

    def load_neurons(self) -> None:
        """Load every skeleton into a few batched line meshes.

        The original viewer created one scene-graph node and draw operation per
        neuron.  This preserves every downloaded vertex and edge, but groups the
        geometry by annotated population and uses per-vertex colors.  Every
        downloaded vertex and edge remains visible. No display subsampling is
        needed: the observed hang was a deferred slider-event feedback loop.
        """
        loaded = []
        seen: set[str] = set()
        frames = [self.pfl2_controller.model.nodes,
                  self.drift_controller.model.pfn,
                  self.drift_controller.model.hdelta]
        for frame in frames:
            for row in frame.itertuples():
                rid = str(row.root_id)
                if rid in seen:
                    continue
                points, edges = read_skeleton(
                    self.root / f"data/raw/flywire_skeletons_783/{rid}.bin"
                )
                loaded.append((rid, str(row.selected_type), points, edges))
                seen.add(rid)

        origin = np.concatenate([points for _, _, points, _ in loaded]).mean(axis=0)
        radius = max(float(np.linalg.norm((points-origin)/1000, axis=1).max())
                     for _, _, points, _ in loaded)
        self.braincam.setPos(0, -radius*3.3, radius*.7)
        self.braincam.lookAt(0, 0, 0)

        position_format = GeomVertexArrayFormat()
        position_format.addColumn(InternalName.getVertex(), 3, Geom.NTFloat32, Geom.CPoint)
        color_format = GeomVertexArrayFormat()
        color_format.addColumn(InternalName.getColor(), 4, Geom.NTUint8, Geom.CColor)
        vertex_format = GeomVertexFormat()
        vertex_format.addArray(position_format)
        vertex_format.addArray(color_format)
        vertex_format = GeomVertexFormat.registerFormat(vertex_format)

        grouped: dict[str, list] = {}
        for item in loaded:
            grouped.setdefault(self._population_group(item[1]), []).append(item)

        self.geometry = {}
        self.classes = {}
        self.brain_groups = {}
        self._brain_color_buffers: dict[str, np.ndarray] = {}
        self._brain_vertex_data: dict[str, GeomVertexData] = {}
        vertices = 0
        displayed_vertices = 0
        edge_count = 0
        neutral = np.asarray((51, 64, 82, 255), dtype=np.uint8)
        for group, neurons in grouped.items():
            group_points = []
            group_edges = []
            vertex_offset = 0
            for rid, kind, points, edges in neurons:
                normalized = np.asarray((points-origin)/1000, dtype=np.float32)
                displayed = normalized[::self.interactive_vertex_stride]
                start = vertex_offset
                stop = start + len(displayed)
                group_points.append(displayed)
                group_edges.append(np.asarray(edges, dtype=np.uint32) + start)
                self.geometry[rid] = (group, start, stop)
                self.classes[rid] = kind
                vertex_offset = stop
                vertices += len(points)
                displayed_vertices += len(displayed)
                edge_count += len(edges)

            positions = np.concatenate(group_points)
            colors = np.tile(neutral, (len(positions), 1))
            data = GeomVertexData(group, vertex_format, Geom.UHDynamic)
            data.setNumRows(len(positions))
            data.modifyArray(0).modifyHandle().setData(positions.tobytes())
            data.modifyArray(0).setUsageHint(Geom.UHStatic)
            data.modifyArray(1).modifyHandle().setData(colors.tobytes())
            data.modifyArray(1).setUsageHint(Geom.UHStream)
            primitive = GeomLines(Geom.UHStatic)
            primitive.setIndexType(Geom.NTUint32)
            primitive.modifyVertices().modifyHandle().setData(np.concatenate(group_edges).tobytes())
            geom = Geom(data)
            geom.addPrimitive(primitive)
            node = GeomNode(f"{group} batched complete skeletons")
            node.addGeom(geom)
            path = self.brain.attachNewNode(node)
            path.setRenderModeThickness(1.25)
            self.brain_groups[group] = path
            self._brain_color_buffers[group] = colors
            self._brain_vertex_data[group] = data

        self.geometry_report = {
            "neurons": len(loaded), "vertices": vertices, "edges": edge_count,
            "sampling": "none; all source vertices and edges displayed",
            "interactive_vertex_stride": self.interactive_vertex_stride,
            "interactive_displayed_vertices": displayed_vertices,
            "interactive_display": "complete skeleton lines, batched by population",
            "render_batches": len(grouped), "dataset": "FAFB",
            "materialization_version": 783,
        }
        self.current_filter = "Todas"
        self.neuron_order = sorted(self.geometry, key=lambda rid: (self.classes[rid], int(rid)))
        self.selected_neuron_rid = self.neuron_order[0]

    def filter(self, kind: str) -> None:
        self.current_filter = kind
        for group, path in self.brain_groups.items():
            if kind == "Todas" or group == kind:
                path.show()
            else:
                path.hide()
        eligible = self._eligible_neurons()
        if self.selected_neuron_rid not in eligible:
            previous = self.selected_neuron_rid
            self.selected_neuron_rid = eligible[0]
            self._last_neural_colors.pop(previous, None)
            self._last_neural_colors.pop(self.selected_neuron_rid, None)
        if hasattr(self, "flights"):
            self.render_at(self.elapsed)

    def _eligible_neurons(self) -> list[str]:
        if self.current_filter == "Todas":
            return self.neuron_order
        return [rid for rid in self.neuron_order
                if self._population_group(self.classes[rid]) == self.current_filter]

    def select_neuron(self, delta: int) -> None:
        eligible = self._eligible_neurons()
        previous = self.selected_neuron_rid
        index = eligible.index(previous) if previous in eligible else 0
        self.selected_neuron_rid = eligible[(index + delta) % len(eligible)]
        self._last_neural_colors.pop(previous, None)
        self._last_neural_colors.pop(self.selected_neuron_rid, None)
        if hasattr(self, "flights"):
            self.render_at(self.elapsed)

    def label(self, text: str, x: float, y: float, scale: float = .035, color=(.82, .91, 1, 1)):
        return OnscreenText(text=text, pos=(x, y), scale=scale, fg=color,
                            align=TextNode.ALeft, mayChange=True)

    def cycle_camera(self) -> None:
        modes = ["general", "seguir A", "seguir B"]
        self.camera_mode = modes[(modes.index(self.camera_mode)+1) % len(modes)]
        self.update_world_camera()

    def orbit_world(self, degrees: float) -> None:
        self.camera_angle = (self.camera_angle + degrees) % 360
        self.update_world_camera()

    def zoom_world(self, factor: float) -> None:
        self.camera_zoom = float(np.clip(self.camera_zoom * factor, .2, 3.))
        self.update_world_camera()

    def reset_camera(self) -> None:
        self.camera_mode = "general"
        self.camera_angle = 0.
        self.camera_zoom = 1.
        self.update_world_camera()

    def update_world_camera(self) -> None:
        if not hasattr(self, "world_center"):
            return
        center = np.array([*self.world_center, 1.])
        distance = self.world_extent
        if self.camera_mode != "general" and hasattr(self, "drones"):
            index = 0 if self.camera_mode == "seguir A" else 1
            center = np.array(tuple(self.drones[index].getPos()), dtype=float)
            distance = 5.
        angle = np.deg2rad(self.camera_angle)
        x, y = .65*np.cos(angle)+1.05*np.sin(angle), .65*np.sin(angle)-1.05*np.cos(angle)
        offset = np.array([x, y, .85]) * distance * self.camera_zoom
        self.camera.setPos(*(center + offset))
        self.camera.lookAt(*center)
        self.camera_label.setText(f"Camara: {self.camera_mode} | C cambiar | A/D girar | W/S zoom | Inicio restaurar")

    def _build_ui(self) -> None:
        button_style = {"frameColor": (.12, .20, .29, 1), "text_fg": (.85, .95, 1, 1),
                        "relief": 1, "pad": (.28, .16)}
        self.label("FlyDrone | comparacion de ensayos en 3D", -1.48, .93, .052)
        self.label("SIMULADO | FlyWire 783 | estabilizacion y sensores: ingenieria", -1.48, .85, .031)
        self.case_label = self.label("", -1.48, .72, .032)
        self.camera_label = self.label("", -1.48, -.38, .023)
        self.gate_stats = self.label("", .25, .84, .027)
        self.status = self.label("", -1.48, -.48, .031)
        self.neural_label = self.label("", .25, -.48, .029)
        self.neuron_label = self.label("", .25, -.27, .024)
        self.legend = self.label("VERDE: intacto     NARANJA: comparacion     AMARILLO: meta", -1.48, -.58, .026)
        self.label("286 morfologias completas | todos los vertices y aristas", .25, .72, .023)
        self.label("EPG/Delta7/FC2/PFL: reconstruida desde entradas guardadas\nPFN/hDeltaB: actividad registrada | sin propagacion por ramas",
                   .25, -.62, .025)
        self.label("Trazas pareadas guardadas | actividad global por neurona, sin propagacion por ramas.",
                   -1.48, -.94, .026)
        self.gate_menu = DirectOptionMenu(items=list(GATES), initialitem=0,
                                          scale=.035, pos=(-1.48, 0, .63), command=self.open_gate)
        self.null_menu = DirectOptionMenu(items=["Cargando"], scale=.028, pos=(-.83, 0, .63))
        self.play_button = DirectButton(text="Reproducir", scale=.038, pos=(-1.25, 0, -.80), command=self.toggle, **button_style)
        DirectButton(text="Reiniciar", scale=.035, pos=(-.83, 0, -.80), command=self.reset_replay, **button_style)
        DirectButton(text="Caso anterior", scale=.031, pos=(-.40, 0, -.80), command=self.previous_case, **button_style)
        DirectButton(text="Caso siguiente", scale=.031, pos=(.07, 0, -.80), command=self.next_case, **button_style)
        DirectButton(text="Actividad A / B", scale=.032, pos=(.58, 0, -.80), command=self.switch_activity, **button_style)
        self.speed_menu = DirectOptionMenu(items=["0.5x", "1x", "2x", "4x"], initialitem=1,
                                           scale=.032, pos=(1.00, 0, -.80), command=self.change_speed)
        self.slider = DirectSlider(range=(0, 35), value=0, pageSize=1, scale=1.33,
                                   frameSize=(-1, 1, -.008, .008),
                                   frameColor=(.17, .26, .35, 1),
                                   thumb_frameSize=(-.012, .012, -.025, .025),
                                   thumb_frameColor=(.1, .85, .70, 1),
                                   pos=(0, 0, -.72), command=self.slider_changed)
        for index, kind in enumerate(["Todas", "EPG", "Delta7", "FC2", "PFL3", "PFL2", "PFN", "hDeltaB"]):
            DirectButton(text=kind, scale=.024, pos=(.32 + index * .16, 0, -.38),
                         command=self.filter, extraArgs=[kind], **button_style)
        DirectButton(text="Rotar -", scale=.025, pos=(.48, 0, -.87), command=self.rotate, extraArgs=[-15], **button_style)
        DirectButton(text="Rotar +", scale=.025, pos=(.85, 0, -.87), command=self.rotate, extraArgs=[15], **button_style)
        DirectButton(text="Neurona -", scale=.022, pos=(1.18, 0, -.87), command=self.select_neuron, extraArgs=[-1], **button_style)
        DirectButton(text="Neurona +", scale=.022, pos=(1.43, 0, -.87), command=self.select_neuron, extraArgs=[1], **button_style)
        DirectButton(text="Exportar vista", scale=.025, pos=(-1.30, 0, -.88),
                     command=self.export_current_view, **button_style)
        self.time_label = self.label("", -1.48, -.67, .029)
        self.export_label = self.label("E exporta PNG, CSV y procedencia", .25, -.94, .021)

    def open_gate(self, label: str) -> None:
        self.archive = GateArchive(self.root, label)
        self.null_menu["items"] = self.archive.nulls
        self.null_menu["command"] = self.open_null
        self.null_menu.set(0, fCommand=0)
        self.open_null(self.archive.nulls[0])

    def open_null(self, name: str) -> None:
        self.other = name
        self.cases = self.archive.paired_cases(name)
        if not self.cases:
            raise ValueError("No preserved paired traces available for this condition")
        self.case_index = 0
        counts = self.archive.episodes.groupby("controller").success.agg(["sum", "size"])
        a, b = counts.loc[self.archive.intact], counts.loc[name]
        self.other_label = ("convencional" if self.archive.is_ood else
                            "oraculo diagnostico" if self.archive.is_oracle else
                            "ablacion" if self.archive.is_ablation else "nulo")
        title = ("Oraculo post-hoc" if self.archive.is_oracle else
                 "Piloto diagnostico" if self.archive.is_ood else
                 "Gate integrado v4" if self.archive.is_ablation else "Gate completo")
        self.gate_stats.setText(f"{title}: A {int(a['sum'])}/{int(a['size'])} | B {int(b['sum'])}/{int(b['size'])}\n{name} | comparacion pareada")
        self.legend.setText(f"VERDE: intacto     NARANJA: {self.other_label}     AMARILLO: meta")
        self.variant = None
        if self.archive.is_ablation:
            self.variant = {"delta7_enabled": False} if name == "delta7_ablated" else None
        elif not self.archive.is_ood and not self.archive.is_oracle:
            seed = int(name.rsplit("_", 1)[1])
            template = self.archive.config["steering_null_condition_template"]
            builder = self.archive.null_builder
            mode = template.get("steering_null_projection", "both")
            keywords = {"projection_mode": mode} if "projection_mode" in inspect.signature(builder).parameters else {}
            if not keywords and mode != "both":
                raise ValueError("Frozen generator does not support the selected projection")
            self.variant = builder(
                self.model, seed, float(self.orientation["epg_heading_sign"]),
                float(self.orientation["phase_offset_deg"]),
                **keywords,
            ).variant
        self.load_case()

    def load_case(self) -> None:
        self.playing = False
        case = self.cases[self.case_index]
        self.flights = [self.archive.load(controller, case)
                        for controller in (self.archive.intact, self.other)]
        self.activities = []
        self.disabled_groups = []
        self.reconstruction_errors = []
        for index, flight in enumerate(self.flights):
            frame = flight.frame
            disabled = ({"Delta7"} if flight.controller == "delta7_ablated" else
                        {"PFN", "hDeltaB"} if flight.controller == "no_hdelta" else
                        {"PFL2"} if flight.controller == "no_pfl2" else set())
            self.disabled_groups.append(disabled)
            if self.archive.is_ood and index == 1:
                self.activities.append({})
                continue
            values = self.archive.steering_activity(
                self.model, frame.observed_yaw_rad.to_numpy(), frame.goal_rad.to_numpy(),
                self.orientation, None if index == 0 else self.variant,
            )
            epg, delta, fc2, rates, signal = values
            base = np.clip(self.orientation["readout_gain_rad_per_s_per_hz"] * signal,
                           -self.orientation["maximum_yaw_rate_rad_s"], self.orientation["maximum_yaw_rate_rad_s"])
            predicted = np.clip(base * frame.pfl2_scale.to_numpy(),
                                -self.pfl2_controller.config["maximum_yaw_rate_rad_s"],
                                self.pfl2_controller.config["maximum_yaw_rate_rad_s"])
            error = float(np.max(np.abs(predicted - frame.yaw_command_rad_s.to_numpy())))
            if error > 1e-8:
                raise ValueError(f"Reconstructed steering differs from recorded command: {error}")
            self.reconstruction_errors.append(error)
            pfl2 = np.asarray([self.pfl2_controller.model.activity(h, g)
                               for h, g in zip(frame.observed_yaw_rad, frame.goal_rad)])
            mapping = {}
            for ids, array, rate, group in [
                (self.model.epg_ids, epg, False, "EPG"), (self.model.base.delta_ids, delta, False, "Delta7"),
                (self.model.base.fc2_ids, fc2, False, "FC2"), (self.model.base.pfl3.root_id, rates, True, "PFL3"),
                (self.pfl2_controller.model.pfl2_ids, pfl2, True, "PFL2"),
                (self.drift_controller.model.pfn.root_id, frame.filter(regex=r"^pfn_activity_\d+$").to_numpy(), False, "PFN"),
                (self.drift_controller.model.hdelta.root_id, frame.filter(regex=r"^hdelta_activity_\d+$").to_numpy(), False, "hDeltaB"),
            ]:
                if group in disabled:
                    array = np.zeros_like(array)
                if len(ids) != array.shape[1]:
                    raise ValueError("Activity dimensions differ from preserved neuron ordering")
                for column, rid in enumerate(ids):
                    mapping[str(rid)] = (array[:, column], rate, 40.0 if rate and str(rid) in set(self.model.base.pfl3.root_id.astype(str)) else 1.0)
            self.activities.append(mapping)
        self.duration = min(float(f.frame.time_s.iloc[-1]) for f in self.flights)
        self.slider["range"] = (0, self.duration)
        bearing = np.deg2rad(case[1])
        self.target = np.array([np.cos(bearing), np.sin(bearing)]) * self.archive.config["target_distance_m"]
        self._build_case_world()
        self.reset_replay()

    def _build_case_world(self) -> None:
        self.world_case.removeNode()
        self.world_case = self.scene.attachNewNode("paired saved world")
        points = np.concatenate([f.frame[["x_m", "y_m", "z_m"]].to_numpy() for f in self.flights])
        low = np.minimum(points[:, :2].min(axis=0), self.target)
        high = np.maximum(points[:, :2].max(axis=0), self.target)
        center = (low + high) / 2
        extent = max(7., float(np.max(high - low)) + 3.)
        spacing = max(1., float(np.ceil(extent / 14)))
        grid = []
        for offset in np.arange(-extent / 2, extent / 2 + spacing, spacing):
            grid.extend([((center[0] + offset, center[1] - extent/2, 0), (center[0] + offset, center[1] + extent/2, 0)),
                         ((center[0] - extent/2, center[1] + offset, 0), (center[0] + extent/2, center[1] + offset, 0))])
        self.lines(self.world_case, "floor", grid, (.15, .24, .34, 1), 1)
        self.world_center = center
        self.world_extent = extent
        ring = [(self.target[0] + .3*np.cos(t), self.target[1] + .3*np.sin(t), 2.)
                for t in np.linspace(0, 2*np.pi, 49)]
        self.lines(self.world_case, "goal", list(zip(ring[:-1], ring[1:])), (1., .84, .15, 1), 4)
        self.drones, self.trails, self.vector_nodes = [], [], []
        arrow = [((0, 0, 0), (1.0, 0, 0)),
                 ((1.0, 0, 0), (.78, .12, 0)),
                 ((1.0, 0, 0), (.78, -.12, 0))]
        for index, flight in enumerate(self.flights):
            color = (.12, 1., .63, 1) if index == 0 else (1., .42, .14, 1)
            drone = self.world_case.attachNewNode(flight.controller)
            self.lines(drone, "arms", [((-.4,-.4,0),(.4,.4,0)),((-.4,.4,0),(.4,-.4,0))], color, 5)
            self.lines(drone, "heading", [((0,0,.06),(.75,0,.06)),((.75,0,.06),(.55,.13,.06)),((.75,0,.06),(.55,-.13,.06))], color, 4)
            for x, y in [(-.4,-.4),(-.4,.4),(.4,-.4),(.4,.4)]:
                ring = [(x+.18*np.cos(t),y+.18*np.sin(t),0) for t in np.linspace(0,2*np.pi,25)]
                self.lines(drone, "rotor", list(zip(ring[:-1],ring[1:])), color, 2)
            coords = flight.frame[["x_m", "y_m", "z_m"]].to_numpy()
            # Trajectory is shown in full and labelled as saved replay, without resimulation.
            self.lines(self.world_case, "full saved trajectory", list(zip(coords[:-1], coords[1:])), (*color[:3], .35), 1)
            self.drones.append(drone)
            self.trails.append(None)
            vectors = self.world_case.attachNewNode(f"vectors {flight.controller}")
            heading_vector = vectors.attachNewNode("observed heading vector")
            travel_vector = vectors.attachNewNode("hDeltaB travel vector")
            goal_vector = vectors.attachNewNode("goal direction vector")
            self.lines(heading_vector, "observed heading", arrow, (.10, .85, 1., 1), 4)
            self.lines(travel_vector, "decoded travel", arrow, (1., .22, .78, 1), 4)
            self.lines(goal_vector, "goal direction", arrow, (1., .84, .15, 1), 3)
            self.vector_nodes.append({
                "root": vectors,
                "heading": heading_vector,
                "travel": travel_vector,
                "goal": goal_vector,
            })

    def render_at(self, seconds: float) -> None:
        self.elapsed = float(np.clip(seconds, 0, self.duration))
        rows = []
        for index, (drone, flight) in enumerate(zip(self.drones, self.flights)):
            row = flight.frame.iloc[flight.index_at(self.elapsed)]
            drone.setPos(float(row.x_m), float(row.y_m), float(row.z_m))
            drone.setH(float(np.rad2deg(row.yaw_rad)))
            vectors = self.vector_nodes[index]
            vectors["root"].setPos(float(row.x_m), float(row.y_m), float(row.z_m) + .28)
            vectors["heading"].setH(float(np.rad2deg(row.observed_yaw_rad)))
            goal_direction = np.arctan2(self.target[1] - row.y_m, self.target[0] - row.x_m)
            vectors["goal"].setH(float(np.rad2deg(goal_direction)))
            decoded = float(row.decoded_travel_direction_rad)
            if np.isfinite(decoded):
                vectors["travel"].setH(float(np.rad2deg(decoded)))
                vectors["travel"].show()
            else:
                vectors["travel"].hide()
            rows.append(row)
        self.update_world_camera()
        frame_index = self.flights[self.selected].index_at(self.elapsed)
        dirty_groups: set[str] = set()
        for rid, (group, start, stop) in self.geometry.items():
            item = self.activities[self.selected].get(rid)
            if item is None:
                color = (.2, .25, .32, 1.0)
            else:
                values, rate, scale = item
                color = rate_activity_color(values[frame_index], scale) if rate else signed_activity_color(values[frame_index], scale)
                # A 33-level palette is visually smooth but bounds the number of
                # render states, preventing the long-replay memory/state blow-up.
                color = tuple(round(float(channel) * 32.0) / 32.0 for channel in color[:3]) + (1.0,)
            if rid == self.selected_neuron_rid:
                color = (1.0, 1.0, 1.0, 1.0)
            if self._last_neural_colors.get(rid) != color:
                rgba = np.asarray(tuple(round(channel * 255) for channel in color), dtype=np.uint8)
                self._brain_color_buffers[group][start:stop] = rgba
                self._last_neural_colors[rid] = color
                dirty_groups.add(group)
        for group in dirty_groups:
            self._brain_vertex_data[group].modifyArray(1).modifyHandle().setData(
                self._brain_color_buffers[group].tobytes()
            )
        distances = [float(np.hypot(row.x_m-self.target[0], row.y_m-self.target[1])) for row in rows]
        outcomes = ["llego" if f.episode["success"] else "no llego" for f in self.flights]
        case = self.cases[self.case_index]
        self.case_label.setText(f"Caso guardado {self.case_index+1}/{len(self.cases)} | meta {case[1]:.0f} | heading {case[2]:.0f}\n{case[0]}")
        self.status.setText(f"A intacto: {distances[0]:.2f} m | resultado final: {outcomes[0]}\nB {self.other_label}: {distances[1]:.2f} m | resultado final: {outcomes[1]}\nVectores: cyan heading observado | magenta viaje hDeltaB | amarillo meta")
        row = rows[self.selected]
        source = "A intacto" if self.selected == 0 else f"B {self.other_label}"
        rate_note = "Control convencional: actividad neuronal no definida"
        if self.activities[self.selected]:
            model_rates = np.array([self.activities[self.selected][str(rid)][0][frame_index]
                                    for rid in self.model.base.pfl3.root_id])
            left, right = float(model_rates[self.model.base.left].sum()), float(model_rates[self.model.base.right].sum())
            rate_note = f"PFL3 L {left:.1f} Hz | R {right:.1f} Hz | R-L {right-left:+.1f}"
        rid = self.selected_neuron_rid
        eligible = self._eligible_neurons()
        selected_index = eligible.index(rid) + 1
        selected_activity = self.activities[self.selected].get(rid)
        if selected_activity is None:
            value_note = "actividad no definida en esta condicion"
        else:
            values, rate, _ = selected_activity
            value = float(values[frame_index])
            group = self._population_group(self.classes[rid])
            if group in self.disabled_groups[self.selected]:
                value_note = f"ablacion: {group} desconectada del control"
            else:
                origin = "registrada en traza" if group in {"PFN", "hDeltaB"} else "reconstruida"
                unit = "Hz del modelo" if rate else "unidad del modelo"
                value_note = f"{origin}: {value:+.3f} {unit}"
        self.neuron_label.setText(
            f"Seleccion blanca {selected_index}/{len(eligible)} | {self.classes[rid]} | FlyWire root {rid}\n"
            f"{value_note} | N/M o botones para recorrer"
        )
        heading_error = abs(np.angle(np.exp(1j * (row.observed_yaw_rad - row.yaw_rad))))
        true_speed = float(np.hypot(row.vx_m_s, row.vy_m_s))
        estimated_speed = float(np.hypot(row.estimated_vx_m_s, row.estimated_vy_m_s))
        velocity_error = None
        if true_speed > .05 and estimated_speed > .05:
            velocity_error = abs(np.angle(np.exp(1j * (
                np.arctan2(row.estimated_vy_m_s, row.estimated_vx_m_s)
                - np.arctan2(row.vy_m_s, row.vx_m_s)
            ))))
        velocity_note = "n/d" if velocity_error is None else f"{np.rad2deg(velocity_error):.1f}°"
        self.neural_label.setText(f"Actividad: {source} | yaw {row.yaw_command_rad_s:+.2f} rad/s\n{rate_note}\nSensores: heading {'OFF' if row.heading_dropout else 'ON'} | velocidad {'ON' if row.position_available else 'OFF'}\nError heading {np.rad2deg(heading_error):.1f}° | error direccion velocidad {velocity_note}\nLlegada: {'retenida' if row.arrival_latched else 'en camino'} | motor medio {np.mean([row[f'motor_{i}_n'] for i in range(4)]):.2f} N")
        self.time_label.setText(f"t = {self.elapsed:05.2f} / {self.duration:.2f} s | {'reproduciendo' if self.playing else 'pausado'}")
        self.play_button["text"] = "Pausar" if self.playing else "Reproducir"
        self.setting_slider = True
        if abs(float(self.slider["value"]) - self.elapsed) > 1e-5:
            self.slider["value"] = self.elapsed
        self.setting_slider = False

    def slider_changed(self) -> None:
        if not self.setting_slider and hasattr(self, "flights"):
            value = float(self.slider["value"])
            # DirectGUI delivers change events later, after setting_slider has
            # been cleared. Ignore the event echo from our own display update.
            if abs(value - self.elapsed) > 1e-5:
                self.render_at(value)

    def toggle(self) -> None:
        if self.elapsed >= self.duration:
            self.elapsed = 0.
        self.playing = not self.playing
        self.visual_wall_accumulator_s = 0.0
        self.playback_accumulator_s = 0.0
        self.render_at(self.elapsed)

    def reset_replay(self) -> None:
        self.playing = False
        self.visual_wall_accumulator_s = 0.0
        self.playback_accumulator_s = 0.0
        self.render_at(0.)

    def seek(self, delta: float) -> None:
        self.render_at(self.elapsed + delta)

    def previous_case(self) -> None:
        self.case_index = (self.case_index - 1) % len(self.cases)
        self.load_case()

    def next_case(self) -> None:
        self.case_index = (self.case_index + 1) % len(self.cases)
        self.load_case()

    def switch_activity(self) -> None:
        self.selected = 1 - self.selected
        self.render_at(self.elapsed)

    def change_speed(self, label: str) -> None:
        self.speed = float(label[:-1])

    def export_current_view(self, output: Path | None = None) -> Path:
        """Export the visible preserved state without copying or modifying source traces."""
        if not hasattr(self, "flights"):
            raise RuntimeError("No preserved replay is loaded")
        if output is None:
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
            output = self.root / "results/desktop/gate-replay-exports" / stamp
        output = Path(output)
        output.mkdir(parents=True, exist_ok=True)

        self.graphicsEngine.renderFrame()
        screenshot = output / "view.png"
        if not self.win.saveScreenshot(Filename.fromOsSpecific(str(screenshot))):
            raise RuntimeError(f"Screenshot could not be saved: {screenshot}")

        snapshots = []
        activity_rows = []
        for slot, flight in enumerate(self.flights):
            frame_index = flight.index_at(self.elapsed)
            row = flight.frame.iloc[frame_index].to_dict()
            snapshots.append({
                "slot": "A" if slot == 0 else "B",
                "controller": flight.controller,
                "trace": flight.path.relative_to(self.root).as_posix(),
                **row,
            })
            mapping = self.activities[slot]
            for root_id in self.neuron_order:
                group = self._population_group(self.classes[root_id])
                item = mapping.get(root_id)
                if item is None:
                    value = None
                    unit = "not_defined"
                    source = "not_defined_for_condition"
                else:
                    values, rate, _ = item
                    value = float(values[frame_index])
                    unit = "model_hz" if rate else "model_unit"
                    source = ("disconnected_computational_ablation"
                              if group in self.disabled_groups[slot]
                              else "recorded_trace" if group in {"PFN", "hDeltaB"}
                              else "algebraic_reconstruction_from_saved_inputs")
                activity_rows.append({
                    "slot": "A" if slot == 0 else "B",
                    "controller": flight.controller,
                    "root_id": root_id,
                    "selected_type": self.classes[root_id],
                    "population": group,
                    "value": value,
                    "unit": unit,
                    "source": source,
                })
        pd.DataFrame(snapshots).to_csv(output / "snapshot.csv", index=False)
        pd.DataFrame(activity_rows).to_csv(output / "neural-activity.csv", index=False)
        case = self.cases[self.case_index]
        metadata = {
            "created_at": utc_now(),
            "status": "preserved_replay_view_export_not_resimulation",
            "dataset": "FAFB",
            "materialization_version": 783,
            "gate": self.archive.slug,
            "comparison": self.other,
            "case": [str(case[0]), float(case[1]), float(case[2])],
            "time_s": float(self.elapsed),
            "activity_slot": "A" if self.selected == 0 else "B",
            "selected_neuron": {
                "root_id": self.selected_neuron_rid,
                "selected_type": self.classes[self.selected_neuron_rid],
            },
            "traces": [{
                "controller": flight.controller,
                "path": flight.path.relative_to(self.root).as_posix(),
                "sha256": file_hash(flight.path),
                "final_success": bool(flight.episode["success"]),
            } for flight in self.flights],
            "outputs": ["view.png", "snapshot.csv", "neural-activity.csv", "metadata.json"],
            "activity_provenance": (
                "EPG/Delta7/FC2/PFL3/PFL2 are algebraically reconstructed from saved inputs; "
                "PFN/hDeltaB are recorded in the trace; undefined activity remains undefined."
            ),
        }
        save_json(output / "metadata.json", metadata)
        self.export_label.setText(f"Exportado: {output.relative_to(self.root).as_posix()}")
        return output

    def tick(self, task):
        if self.playing:
            wall_seconds = min(.1, ClockObject.getGlobalClock().getDt())
            self.visual_wall_accumulator_s += wall_seconds
            self.playback_accumulator_s += wall_seconds * self.speed
            if self.visual_wall_accumulator_s < self.visual_update_interval_s:
                return task.cont
            seconds = self.elapsed + self.playback_accumulator_s
            self.visual_wall_accumulator_s = 0.0
            self.playback_accumulator_s = 0.0
            if seconds >= self.duration:
                self.playing = False
            self.render_at(seconds)
        return task.cont


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke-test", action="store_true")
    parser.add_argument("--audit-all", action="store_true", help="Check every preserved comparison condition")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    app = GateReplay3D(root, offscreen=args.smoke_test)
    if args.smoke_test:
        folder = root / "results/desktop/gate-replay-3d"
        folder.mkdir(parents=True, exist_ok=True)
        checks = []
        for gate in GATES:
            app.open_gate(gate)
            for selected in (0, 1):
                app.selected = selected
                app.render_at(15.0)
                app.graphicsEngine.renderFrame()
                app.graphicsEngine.renderFrame()
                screenshot = folder / f"{app.archive.slug}-{'intact' if selected == 0 else 'null'}.png"
                if not app.win.saveScreenshot(Filename.fromOsSpecific(str(screenshot))):
                    raise RuntimeError(f"Screenshot could not be saved: {screenshot}")
                checks.append({"gate": gate, "selected": selected, "case": app.cases[app.case_index],
                               "geometry": app.geometry_report,
                               "maximum_yaw_reconstruction_error_rad_s": max(app.reconstruction_errors),
                               "traces": [f.path.relative_to(root).as_posix() for f in app.flights]})
            if args.audit_all and app.archive.is_ood:
                for _ in app.cases:
                    app.next_case()
                    app.render_at(app.duration)
                    checks.append({"gate": gate, "case": app.cases[app.case_index],
                                   "maximum_yaw_reconstruction_error_rad_s": max(app.reconstruction_errors)})
            elif args.audit_all:
                for name in app.archive.nulls[1:]:
                    app.open_null(name)
                    app.switch_activity()
                    app.seek(app.duration)
                    assert np.isclose(app.elapsed, app.duration)
                    app.reset_replay()
                    app.next_case()
                    app.previous_case()
                    app.slider["value"] = 5.
                    app.slider_changed()
                    assert np.isclose(app.elapsed, 5.)
                    checks.append({"gate": gate, "null": name,
                                   "maximum_yaw_reconstruction_error_rad_s": max(app.reconstruction_errors),
                                   "paired_saved_cases": len(app.cases)})
        export_folder = app.export_current_view(folder / "export-smoke")
        expected_exports = {"view.png", "snapshot.csv", "neural-activity.csv", "metadata.json"}
        if not expected_exports.issubset({path.name for path in export_folder.iterdir()}):
            raise RuntimeError("Replay export is incomplete")
        save_json(folder / "smoke-report.json", {
            "checks": checks,
            "mode": "preserved replay",
            "export": export_folder.relative_to(root).as_posix(),
        })
        app.destroy()
        print(f"Verified {len(checks)} rendered gate/activity combinations.")
    else:
        app.run()


if __name__ == "__main__":
    main()
