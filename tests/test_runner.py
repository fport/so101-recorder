import pytest

from so101_recorder import runner
from so101_recorder.protocol import decode, encode
from so101_recorder.session import State


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_controls_apply_once_per_press(capsys):
    events = {"exit_early": False, "rerecord_episode": False, "stop_recording": False}
    clock = Clock()
    c = runner.Controls(events, clock=clock)
    assert c.press("next", "ui")
    assert events["exit_early"]
    events["exit_early"] = False
    clock.t = 0.2
    assert not c.press("next", "keyboard")  # the same press seen twice, or a held key
    clock.t = 0.6
    assert not c.press("next", "keyboard")  # still held: the window moves on
    clock.t = 1.2
    assert c.press("next", "ui")
    assert c.press("redo", "ui") and events["rerecord_episode"]
    assert not c.press("jump", "ui")
    assert c.press("stop", "ui") and events["stop_recording"]
    out = [e for e in map(decode, capsys.readouterr().out.splitlines()) if e]  # lerobot prints its own line too
    assert [e["control"] for e in out] == ["next", "next", "redo", "stop"]


def test_calibration_prompt_is_answered_and_a_missing_one_stops():
    assert runner._input("Press ENTER to use provided calibration file associated with the id follower, ...") == ""
    with pytest.raises(runner.NeedsCalibration):
        runner._input("Move follower to the middle of its range of motion and press ENTER....")


def test_connect_retries_then_gives_up(monkeypatch):
    monkeypatch.setattr(runner.time, "sleep", lambda s: None)
    calls = []

    class Dev:
        cameras = {}
        bus = None

    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise TimeoutError("camera")
        return "ok"

    assert runner.connect_with_retry(flaky, Dev(), "follower")() == "ok"

    def broken():
        raise ConnectionError("no status packet")

    with pytest.raises(ConnectionError):
        runner.connect_with_retry(broken, Dev(), "follower", tries=2)()


def test_hints():
    assert "so101-cal" in runner.hint(runner.NeedsCalibration("x"))
    assert "Cameras" in runner.hint(TimeoutError("OpenCVCamera(1) read timed out"))
    assert "12 V" in runner.hint(ConnectionError("[TxRxResult] There is no status packet!"))
    assert "resume" in runner.hint(FileExistsError("data/x"))


def test_protocol_and_state():
    assert decode("INFO something") is None
    assert decode(encode("saved", episode=3)) == {"event": "saved", "episode": 3}
    st = State(planned=3)
    for ev in [{"event": "connecting", "device": "leader"}, {"event": "keys", "global_keys": True},
               {"event": "phase", "phase": "record", "episode": 7, "duration": 40},
               {"event": "phase", "phase": "reset", "duration": 90}, {"event": "discarded"},
               {"event": "phase", "phase": "record", "episode": 7, "duration": 40},
               {"event": "phase", "phase": "saving"}, {"event": "saved", "episode": 7, "total": 8}]:
        st.apply(ev, now=10.0)
    assert st.global_keys and st.redone == 1 and st.saved == [7] and st.current == 2 and st.episode == 7
    assert st.elapsed(now=12.5) == 2.5
    st.apply({"event": "pushed", "url": "https://huggingface.co/datasets/a/b"})
    st.apply({"event": "finished", "ok": True})
    assert st.phase == "done" and st.url.endswith("a/b")
