"""Exercise actual Panda event dispatch, including deferred slider notifications.

Run from the repository with PYTHONPATH=src. Uses a visible native window.
An external timeout should supervise this test: a blocked event queue cannot
reliably execute its own timeout callback.
"""
from pathlib import Path
import argparse
import time
import numpy as np

from flydrone.data.acquire import save_json
from flydrone.visualization.gate_replay_3d import GateReplay3D
from flydrone.visualization.gate_replay_data import GATES


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cycles", type=int, default=1)
    args = parser.parse_args()
    if args.cycles < 1:
        parser.error("cycles must be positive")
    root = Path(__file__).resolve().parents[1]
    app = GateReplay3D(root)
    gates = list(GATES) * args.cycles
    checks = []
    stage = "start"
    gate_index = 0
    frames = 0
    deadline = 0.
    started = time.monotonic()

    def exercise(task):
        nonlocal stage, gate_index, frames, deadline
        frames += 1
        if stage == "start":
            app.open_gate(gates[gate_index])
            app.change_speed("4x")
            app.toggle()
            stage = "flight"
        elif stage == "flight" and not app.playing:
            assert np.isclose(app.elapsed, app.duration)
            checks.append({"gate": gates[gate_index], "completed_time_s": app.elapsed})
            if gate_index == 0:
                exported = app.export_current_view(
                    root / "results/desktop/gate-replay-3d/live-export-smoke"
                )
                assert (exported / "metadata.json").is_file()
                assert (exported / "neural-activity.csv").is_file()
            app.switch_activity()
            app.filter("PFL3")
            selected_before = app.selected_neuron_rid
            app.select_neuron(1)
            assert app.selected_neuron_rid != selected_before
            assert app._population_group(app.classes[app.selected_neuron_rid]) == "PFL3"
            group, start, stop = app.geometry[app.selected_neuron_rid]
            assert np.all(app._brain_color_buffers[group][start:stop] == 255)
            assert "FlyWire root" in app.neuron_label.getText()
            app.rotate(15)
            app.zoom(.9)
            app.cycle_camera()
            app.orbit_world(30)
            app.zoom_world(.8)
            assert all(np.isfinite(tuple(app.camera.getPos())))
            # Let DirectGUI dispatch the real queued event. Do not call the
            # callback manually: that missed the original infinite feedback bug.
            app.slider["value"] = 5.
            deadline = time.monotonic() + .5
            stage = "seek"
        elif stage == "seek" and time.monotonic() >= deadline:
            assert np.isclose(app.elapsed, 5., atol=1e-5)
            app.filter("Todas")
            app.reset_camera()
            app.next_case()
            app.previous_case()
            app.reset_replay()
            gate_index += 1
            if gate_index < len(gates):
                stage = "start"
            else:
                report = {"passed": True, "checks": checks, "event_loop_frames": frames,
                          "wall_seconds": time.monotonic()-started,
                          "geometry": app.geometry_report,
                          "cycles": args.cycles,
                          "scope": "complete paired replays at 4x; export; queued seeks; filters; neuron selection; case changes; camera controls"}
                save_json(root / "results/desktop/gate-replay-3d/live-stability.json", report)
                print(report, flush=True)
                app.userExit()
        return task.cont

    app.taskMgr.add(exercise, "live-regression", sort=100)
    app.run()


if __name__ == "__main__":
    main()
