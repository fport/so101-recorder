"""The recording process: lerobot-record itself, with a few hooks so the UI can follow along.

    python -m so101_recorder.runner <lerobot-record arguments>

It parses the arguments with lerobot's own parser and runs lerobot's own record(); the dataset, the Rerun viewer,
the episode/reset loop and the push to the Hub are all lerobot's. The hooks only add:

- events on stdout (episode started, saved, re-recorded, pushed) for the UI,
- control words on stdin (next / redo / stop) next to the global → ← Esc keys,
- a held or doubled key counting once (pynput repeats a held arrow; the UI and pynput can both see one press),
- the "use the calibration file?" prompt answered with ENTER, as you would; a missing calibration stops with a hint,
- a retry when a camera or a servo misses its first reply on connect.
"""

from __future__ import annotations

import builtins
import os
import sys
import threading
import time
import traceback

from .protocol import CONTROLS, encode

DEBOUNCE_S = 0.5
GLOBAL_KEYS = {"right": "next", "left": "redo", "esc": "stop"}  # letters are never global: you type elsewhere


def emit(event: str, **data) -> None:
    sys.stdout.write(encode(event, **data) + "\n")
    sys.stdout.flush()


class NeedsCalibration(RuntimeError):
    pass


# --- keys ---------------------------------------------------------------------------------------------------


class Controls:
    """Applies control words to lerobot's events dict, once per press."""

    def __init__(self, events: dict, debounce_s: float = DEBOUNCE_S, clock=time.monotonic):
        from lerobot.utils.keyboard_input import apply_recording_control

        self.events = events
        self.debounce_s = debounce_s
        self.clock = clock
        self._apply = apply_recording_control
        self._last: dict[str, float] = {}
        self._lock = threading.Lock()

    def press(self, word: str, source: str) -> bool:
        if word not in CONTROLS:
            return False
        with self._lock:
            now = self.clock()
            if now - self._last.get(word, float("-inf")) < self.debounce_s:
                self._last[word] = now  # a held key keeps extending the window
                return False
            self._last[word] = now
            self._apply(CONTROLS[word], self.events)
        emit("control", control=word, source=source)
        return True


class _Listeners:
    def __init__(self, *items):
        self.items = [i for i in items if i is not None]

    def stop(self):
        for i in self.items:
            try:
                i.stop()
            except Exception:
                pass


def _read_stdin(controls: Controls) -> None:
    for line in sys.stdin:
        controls.press(line.strip().lower(), "ui")
    # stdin closed: the UI is gone (quit, crashed, terminal closed). Stop the way Esc does, so lerobot saves
    # what it has and disconnects the arms instead of recording on with nobody watching.
    controls.debounce_s = 0
    controls.press("stop", "ui-closed")


def init_keyboard_listener():
    """Replaces lerobot's: same events dict, fed by the UI over stdin and by global arrows/Esc."""
    events = {"exit_early": False, "rerecord_episode": False, "stop_recording": False}
    controls = Controls(events)
    threading.Thread(target=_read_stdin, args=(controls,), daemon=True).start()

    pynput_listener = None
    if os.environ.get("SO101_REC_GLOBAL_KEYS", "1") != "0":
        from lerobot.utils import keyboard_input as ki

        if ki.pynput_can_capture() and ki.keyboard is not None:

            def on_press(key):
                name = ki._resolve_pynput_key(key)
                if name in GLOBAL_KEYS:
                    controls.press(GLOBAL_KEYS[name], "keyboard")

            pynput_listener = ki.keyboard.Listener(on_press=on_press)
            pynput_listener.start()
            if not ki.pynput_listener_is_trusted(pynput_listener):
                pynput_listener.stop()  # macOS without Accessibility permission: it would never fire
                pynput_listener = None
    emit("keys", global_keys=pynput_listener is not None)
    return _Listeners(pynput_listener), events


# --- prompts and connecting ---------------------------------------------------------------------------------


def _input(prompt: str = "") -> str:
    if "Press ENTER to use provided calibration file" in prompt:
        print(prompt + "<ENTER>", flush=True)
        emit("calibration", used="file")
        return ""
    raise NeedsCalibration(prompt.strip())


def connect_with_retry(connect, device, what: str, tries: int = 3, wait_s: float = 1.0):
    """device.connect() with retries. A camera can miss its first frame (TimeoutError) and a servo one packet
    while torque switches on (ConnectionError); lerobot retries neither. Whatever did connect is closed again
    between tries so the next connect() starts clean."""

    def wrapped(*args, **kwargs):
        emit("connecting", device=what)
        for attempt in range(1, tries + 1):
            try:
                result = connect(*args, **kwargs)
                emit("connected", device=what)
                return result
            except (TimeoutError, ConnectionError) as e:
                if attempt == tries:
                    raise
                for cam in getattr(device, "cameras", {}).values():
                    if getattr(cam, "is_connected", False):
                        cam.disconnect()
                bus = getattr(device, "bus", None)
                if bus is not None and bus.is_connected:
                    bus.disconnect(disable_torque=False)
                emit("retry", device=what, attempt=attempt + 1, tries=tries, message=str(e))
                time.sleep(wait_s)

    return wrapped


# --- hooks into lerobot-record ------------------------------------------------------------------------------


def install(lr) -> None:
    """Hook into the lerobot_record module `lr` (passed in so tests can hand a stand-in)."""
    builtins.input = _input
    lr.init_keyboard_listener = init_keyboard_listener

    make_robot, make_teleop = lr.make_robot_from_config, lr.make_teleoperator_from_config

    def make_robot_from_config(cfg):
        robot = make_robot(cfg)
        robot.connect = connect_with_retry(robot.connect, robot, "follower")
        return robot

    def make_teleoperator_from_config(cfg):
        teleop = make_teleop(cfg)
        teleop.connect = connect_with_retry(teleop.connect, teleop, "leader")
        return teleop

    lr.make_robot_from_config = make_robot_from_config
    lr.make_teleoperator_from_config = make_teleoperator_from_config

    record_loop = lr.record_loop

    def phase_loop(*args, **kwargs):
        dataset = kwargs.get("dataset")
        if dataset is not None:
            emit("phase", phase="record", episode=dataset.num_episodes, duration=kwargs.get("control_time_s"))
        else:
            emit("phase", phase="reset", duration=kwargs.get("control_time_s"))
        return record_loop(*args, **kwargs)

    lr.record_loop = phase_loop

    ds = lr.LeRobotDataset
    save_episode, clear_buffer, push = ds.save_episode, ds.clear_episode_buffer, ds.push_to_hub

    def saving(self, *args, **kwargs):
        emit("phase", phase="saving")
        result = save_episode(self, *args, **kwargs)
        emit("saved", episode=self.num_episodes - 1, total=self.num_episodes)
        return result

    def clearing(self, *args, **kwargs):
        emit("discarded")
        return clear_buffer(self, *args, **kwargs)

    def pushing(self, *args, **kwargs):
        emit("phase", phase="pushing")
        result = push(self, *args, **kwargs)
        emit("pushed", repo_id=self.repo_id, url=f"https://huggingface.co/datasets/{self.repo_id}")
        return result

    ds.save_episode, ds.clear_episode_buffer, ds.push_to_hub = saving, clearing, pushing


def hint(e: BaseException) -> str:
    text = f"{type(e).__name__}: {e}"
    if isinstance(e, NeedsCalibration):
        return "This arm has no calibration for its id. Calibrate it first (so101-cal or lerobot-calibrate)."
    if isinstance(e, FileExistsError):
        return "The dataset folder already exists. Pick another name, or turn on resume for it."
    if isinstance(e, TimeoutError) or "camera" in text.lower():
        return ("A camera did not answer. Check the indices in Setup › Cameras; "
                "an iPhone nearby (Continuity Camera) can shift them.")
    if "status packet" in text or "Missing motor" in text or "motor" in text.lower():
        return "A servo did not answer: check the follower's 12 V supply and the cables between the servos."
    if "port" in text.lower() or "serial" in text.lower():
        return "Could not open a USB port. Check the ports in Setup › Arms (unplug and plug back in)."
    if "401" in text or "token" in text.lower():
        return "The Hugging Face Hub refused the upload. Log in again in Setup › Hugging Face."
    return ""


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    emit("start", pid=os.getpid())
    import lerobot.scripts.lerobot_record as lr

    install(lr)
    sys.argv = ["lerobot-record", *argv]
    try:
        lr.main()
    except KeyboardInterrupt:
        emit("finished", ok=False, reason="interrupted")
        return 130
    except BaseException as e:  # noqa: BLE001 - everything goes to the UI, then out
        traceback.print_exc()
        emit("error", kind=type(e).__name__, message=str(e), hint=hint(e))
        emit("finished", ok=False, reason="error")
        return 1
    emit("finished", ok=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
