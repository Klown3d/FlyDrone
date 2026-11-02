"""Run the FlyDrone test suite in a small GUI, without showing a terminal."""

from __future__ import annotations

import queue
import subprocess
import threading
import tkinter as tk
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    window = tk.Tk()
    window.title("FlyDrone — pruebas automatizadas")
    window.geometry("1000x560")
    window.configure(bg="#071018")

    title = tk.Label(
        window,
        text="FlyDrone · suite de verificación",
        bg="#071018",
        fg="#6ee7ff",
        font=("Segoe UI", 22, "bold"),
        pady=18,
    )
    title.pack(fill="x")

    status = tk.Label(
        window,
        text="Ejecutando pytest sobre el proyecto completo…",
        bg="#071018",
        fg="#d7f9e9",
        font=("Segoe UI", 13),
        pady=8,
    )
    status.pack(fill="x")

    output = tk.Text(
        window,
        bg="#0b1620",
        fg="#c6f6d5",
        insertbackground="#c6f6d5",
        font=("Cascadia Mono", 12),
        borderwidth=0,
        padx=20,
        pady=20,
    )
    output.pack(fill="both", expand=True, padx=24, pady=(0, 24))
    output.insert("end", "Comando interno: python -m pytest -q\n\n")

    messages: queue.Queue[tuple[str, str | int]] = queue.Queue()

    def run_tests() -> None:
        process = subprocess.Popen(
            [str(ROOT / ".venv/Scripts/python.exe"), "-m", "pytest", "-q"],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert process.stdout is not None
        for line in process.stdout:
            messages.put(("line", line))
        messages.put(("done", process.wait()))

    def poll() -> None:
        try:
            while True:
                kind, value = messages.get_nowait()
                if kind == "line":
                    output.insert("end", str(value))
                    output.see("end")
                else:
                    code = int(value)
                    status.configure(
                        text="Verificación completada correctamente" if code == 0 else "La verificación encontró fallos",
                        fg="#68d391" if code == 0 else "#fc8181",
                    )
        except queue.Empty:
            pass
        window.after(100, poll)

    threading.Thread(target=run_tests, daemon=True).start()
    poll()
    window.mainloop()


if __name__ == "__main__":
    main()
