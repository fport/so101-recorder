"""Runs the recording process and turns its output into state the UI can draw."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from .protocol import decode


@dataclass
class State:
    """What the recording screen shows. Updated only by apply()."""

    planned: int  # episodes asked for in this session
    phase: str = "starting"  # starting, connecting, record, reset, saving, pushing, done, failed, stopped
    phase_started: float = 0.0
    phase_duration: float | None = None
    episode: int | None = None  # dataset index of the episode being recorded
    saved: list[int] = field(default_factory=list)  # dataset indices saved in this session
    redone: int = 0
    connecting: str = ""
    global_keys: bool | None = None
    url: str = ""
    error: str = ""
    hint: str = ""
    last_control: str = ""

    @property
    def current(self) -> int:
        """1-based number of the episode in this session (what "Episode 3 / 5" shows)."""
        return min(len(self.saved) + 1, self.planned)

    def elapsed(self, now: float | None = None) -> float:
        return max(0.0, (now or time.monotonic()) - self.phase_started)

    def apply(self, ev: dict, now: float | None = None) -> None:
        now = now or time.monotonic()
        kind = ev.get("event")
        if kind == "connecting":
            self.phase, self.connecting = "connecting", ev.get("device", "")
        elif kind == "keys":
            self.global_keys = bool(ev.get("global_keys"))
        elif kind == "phase":
            self.phase = ev.get("phase", self.phase)
            self.phase_started = now
            self.phase_duration = ev.get("duration")
            if self.phase == "record":
                self.episode = ev.get("episode")
        elif kind == "saved":
            self.saved.append(ev.get("episode", len(self.saved)))
        elif kind == "discarded":
            self.redone += 1
        elif kind == "control":
            self.last_control = ev.get("control", "")
        elif kind == "pushed":
            self.url = ev.get("url", "")
        elif kind == "error":
            self.error, self.hint = ev.get("message", ""), ev.get("hint", "")
        elif kind == "finished":
            if ev.get("ok"):
                self.phase = "done"
            elif ev.get("reason") == "interrupted":
                self.phase = "stopped"
            else:
                self.phase = "failed"


class Recording:
    """One lerobot-record run in a child process.

    on_event(dict) and on_log(str) are called from a reader thread; the UI moves them to its own thread.
    """

    def __init__(
        self,
        args: list[str],
        *,
        on_event: Callable[[dict], None],
        on_log: Callable[[str], None],
        on_exit: Callable[[int], None],
        global_keys: bool = True,
        command: list[str] | None = None,
    ):
        self.command = command or [sys.executable, "-u", "-m", "so101_recorder.runner", *args]
        self.on_event, self.on_log, self.on_exit = on_event, on_log, on_exit
        self.global_keys = global_keys
        self.proc: subprocess.Popen | None = None

    def start(self) -> None:
        env = dict(os.environ, PYTHONUNBUFFERED="1", SO101_REC_GLOBAL_KEYS="1" if self.global_keys else "0")
        self.proc = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
            start_new_session=True,  # Ctrl+C in the UI is ours; the child is stopped on purpose (stop / abort)
        )
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self) -> None:
        assert self.proc and self.proc.stdout
        buf = b""
        while chunk := self.proc.stdout.read1(4096):
            buf += chunk
            # lerobot rewrites some lines with \r; treat that as a line end too
            *lines, buf = buf.replace(b"\r\n", b"\n").replace(b"\r", b"\n").split(b"\n")
            for raw in lines:
                self._line(raw.decode("utf-8", "replace"))
        if buf:
            self._line(buf.decode("utf-8", "replace"))
        self.on_exit(self.proc.wait())

    def _line(self, line: str) -> None:
        ev = decode(line)
        if ev is not None:
            self.on_event(ev)
        elif line.strip():
            self.on_log(line)

    @property
    def running(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def send(self, word: str) -> None:
        """next, redo or stop. Stop ends the session the way Esc does: the episode in progress is saved."""
        if not self.running or self.proc.stdin is None:
            return
        try:
            self.proc.stdin.write((word + "\n").encode())
            self.proc.stdin.flush()
        except (BrokenPipeError, OSError):
            pass

    def interrupt(self) -> None:
        """Ctrl+C for the child: lerobot's finally still saves what it has and disconnects the arms."""
        if self.running:
            self.proc.send_signal(signal.SIGINT)  # the runner only: the Rerun viewer it spawned stays open

    def kill(self) -> None:
        if self.running:
            self.proc.kill()
