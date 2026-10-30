"""The runner inside the real lerobot record(), with a stand-in rig."""

import threading

from conftest import fake_args, fake_command

from so101_recorder import hub
from so101_recorder.session import Recording, State


def run(args, controls=None, timeout=60):
    events, logs, done = [], [], threading.Event()
    exit_code = []

    def on_event(ev):
        events.append(ev)
        if controls:
            controls(ev, rec)

    def on_exit(code):
        exit_code.append(code)
        done.set()

    rec = Recording(args, on_event=on_event, on_log=logs.append, on_exit=on_exit, global_keys=False,
                    command=fake_command(args))
    rec.start()
    assert done.wait(timeout), "\n".join(logs[-40:])
    return events, logs, exit_code[0]


def test_records_episodes_and_reports_them(tmp_path):
    root = tmp_path / "fake"
    events, logs, code = run(fake_args(root))
    assert code == 0, "\n".join(logs[-40:])
    kinds = [e["event"] for e in events]
    assert kinds[0] == "start"
    assert [e["phase"] for e in events if e["event"] == "phase"] == ["record", "reset", "saving", "record", "saving"]
    assert [e["episode"] for e in events if e["event"] == "saved"] == [0, 1]
    assert kinds[-1] == "finished" and events[-1]["ok"]

    state = State(planned=2)
    for e in events:
        state.apply(e)
    assert state.phase == "done" and state.saved == [0, 1]

    local = hub.local(root)
    assert local.valid and local.episodes == 2


def test_ui_controls_next_redo_stop(tmp_path):
    root = tmp_path / "fake"
    seen = {"record": 0}

    def controls(ev, rec):
        if ev["event"] == "phase" and ev["phase"] == "record":
            seen["record"] += 1
            # 1st episode: redo it; 2nd (the redo): end it early; 3rd: stop the session
            rec.send({1: "redo", 2: "next", 3: "stop"}[seen["record"]])
        elif ev["event"] == "phase" and ev["phase"] == "reset":
            rec.send("next")

    events, logs, code = run(fake_args(root, episodes=3, episode_s=30, reset_s=30), controls)
    assert code == 0, "\n".join(logs[-40:])
    assert sum(e["event"] == "discarded" for e in events) == 1
    assert [e["episode"] for e in events if e["event"] == "saved"] == [0, 1]  # the stopped one is kept, as in lerobot
    assert {e["control"] for e in events if e["event"] == "control"} >= {"redo", "next", "stop"}
    assert hub.local(root).episodes == 2


def test_resume_adds_to_the_dataset(tmp_path):
    root = tmp_path / "fake"
    assert run(fake_args(root, episodes=1))[2] == 0
    events, logs, code = run(fake_args(root, episodes=1, extra=["--resume=true"]))
    assert code == 0, "\n".join(logs[-40:])
    assert [e["episode"] for e in events if e["event"] == "saved"] == [1]
    assert hub.local(root).episodes == 2


def test_existing_folder_without_resume_is_an_error_with_a_hint(tmp_path):
    root = tmp_path / "fake"
    assert run(fake_args(root, episodes=1))[2] == 0
    events, _, code = run(fake_args(root, episodes=1))
    assert code == 1
    err = next(e for e in events if e["event"] == "error")
    assert "resume" in err["hint"]


def test_closing_the_ui_stops_the_recording(tmp_path):
    root = tmp_path / "fake"

    def controls(ev, rec):
        if ev["event"] == "phase" and ev["phase"] == "record":
            rec.proc.stdin.close()  # what happens when the UI process dies

    events, logs, code = run(fake_args(root, episodes=3, episode_s=30, reset_s=30), controls)
    assert code == 0, "\n".join(logs[-40:])
    assert any(e["event"] == "control" and e["source"] == "ui-closed" for e in events)
    assert hub.local(root).episodes == 1
