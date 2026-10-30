"""USB ports and cameras: what is plugged in, and a tiny live preview of each camera for the terminal."""

from __future__ import annotations

import glob
import platform
import threading
import time
from collections.abc import Callable

from rich.style import Style
from rich.text import Text


def list_ports() -> list[str]:
    """Device paths of likely motor-controller boards (/dev/cu.usbmodem… on macOS)."""
    try:
        from serial.tools import list_ports as lp
    except ImportError:
        lp = None
    if lp is not None:
        ports = []
        for p in lp.comports():
            if platform.system() == "Darwin" and p.device.startswith("/dev/tty."):
                continue  # macOS lists every port twice; /dev/cu.* is the one to open
            if p.vid is None and not p.device.startswith(("/dev/ttyACM", "/dev/ttyUSB")):
                continue  # Bluetooth and debug consoles
            ports.append(p.device)
        return sorted(ports)
    patterns = ["/dev/cu.usbmodem*", "/dev/cu.usbserial*", "/dev/ttyACM*", "/dev/ttyUSB*"]
    return sorted(p for pat in patterns for p in glob.glob(pat))


def _capture(index):
    import cv2

    backend = cv2.CAP_AVFOUNDATION if platform.system() == "Darwin" else cv2.CAP_ANY
    return cv2.VideoCapture(index, backend)


def scan_cameras(max_index: int = 6) -> list[int]:
    """OpenCV indices that deliver a frame. Slow (a second or so per index on macOS): call it from a thread."""
    found = []
    for i in range(max_index):
        cap = _capture(i)
        try:
            if cap.isOpened():
                for _ in range(10):  # some cameras need a few reads to wake up
                    ok, _frame = cap.read()
                    if ok:
                        found.append(i)
                        break
                    time.sleep(0.05)
        finally:
            cap.release()
    return found


def halfblocks(frame, width: int = 40) -> Text:
    """A BGR frame as coloured half-block characters: two pixels per cell, `width` cells wide."""
    import cv2

    h, w = frame.shape[:2]
    rows = max(2, round(width * h / w) // 2 * 2)
    small = cv2.resize(frame, (width, rows), interpolation=cv2.INTER_AREA)
    text = Text(no_wrap=True, overflow="crop")
    for y in range(0, rows, 2):
        for x in range(width):
            b1, g1, r1 = small[y, x]
            b2, g2, r2 = small[y + 1, x]
            text.append("▀", Style.parse(f"#{r1:02x}{g1:02x}{b1:02x} on #{r2:02x}{g2:02x}{b2:02x}"))
        if y + 2 < rows:
            text.append("\n")
    return text


class Preview:
    """Reads frames from a few cameras in a thread and hands each one, as Text, to on_frame(index, text).

    Stop it before recording: a camera opened here cannot be opened by lerobot.
    """

    def __init__(self, indices: list[int], on_frame: Callable[[int, Text | None], None], width: int = 40,
                 interval_s: float = 0.2):
        self.indices, self.on_frame, self.width, self.interval_s = indices, on_frame, width, interval_s
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> Preview:
        self._thread.start()
        return self

    def stop(self, wait: bool = True) -> None:
        self._stop.set()
        if wait and self._thread.is_alive():
            self._thread.join(timeout=3)

    def _run(self) -> None:
        caps = {}
        try:
            for i in self.indices:
                if self._stop.is_set():
                    return
                cap = _capture(i)
                caps[i] = cap if cap.isOpened() else None
            while not self._stop.is_set():
                for i, cap in caps.items():
                    if cap is None:
                        self.on_frame(i, None)
                        continue
                    ok, frame = cap.read()
                    self.on_frame(i, halfblocks(frame, self.width) if ok else None)
                self._stop.wait(self.interval_s)
        finally:
            for cap in caps.values():
                if cap is not None:
                    cap.release()
