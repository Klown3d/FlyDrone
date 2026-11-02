"""Low-overhead screen recorder used for the FlyDrone project demo."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from PIL import Image, ImageGrab


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=float, default=105.0)
    parser.add_argument("--fps", type=float, default=4.0)
    parser.add_argument("--width", type=int, default=960)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    interval = 1.0 / args.fps
    frames: list[Image.Image] = []
    started = time.perf_counter()
    deadline = started + args.duration
    next_frame = started

    while time.perf_counter() < deadline:
        frame = ImageGrab.grab(all_screens=False).convert("RGB")
        # Exclude the taskbar and keep the recording compact.
        frame = frame.crop((0, 0, frame.width, min(frame.height, 816)))
        height = round(frame.height * args.width / frame.width)
        frames.append(frame.resize((args.width, height), Image.Resampling.LANCZOS))
        next_frame += interval
        time.sleep(max(0.0, next_frame - time.perf_counter()))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    frame_duration_ms = round(1000 / args.fps)
    frames[0].save(
        args.output,
        save_all=True,
        append_images=frames[1:],
        duration=frame_duration_ms,
        loop=0,
        quality=58,
        method=4,
    )


if __name__ == "__main__":
    main()
