"""The screens, driven with Textual's pilot. No hardware, no Hub, no cameras."""

import pytest
from conftest import fake_command
from textual.widgets import Button, Input

from so101_recorder import devices, settings
from so101_recorder.settings import Settings
from so101_recorder.tui import record as record_mod
from so101_recorder.tui.app import RecApp
from so101_recorder.tui.home import CommandScreen, HomeScreen
from so101_recorder.tui.record import RecordScreen
from so101_recorder.tui.setup import SetupScreen

SIZE = (110, 34)


@pytest.fixture
def ready(tmp_path, monkeypatch):
    cal = tmp_path / "cal"
    cal.mkdir()
    (cal / "follower.json").write_text("{}")
    (cal / "leader.json").write_text("{}")
    s = Settings(follower_port="/dev/fake-follower", leader_port="/dev/fake-leader", calibration_dir=str(cal),
                 push=False, display=False, sounds=False, cameras=[], episodes=2, episode_s=0.4, reset_s=0.2,
                 data_dir=str(tmp_path / "data"))
    path = tmp_path / "settings.json"
    settings.save(s, path)
    monkeypatch.setattr(devices, "list_ports", lambda: ["/dev/fake-follower", "/dev/fake-leader"])

    class NoPreview:
        def __init__(self, *a, **k):
            pass

        def start(self):
            return self

        def stop(self, wait=True):
            pass

    monkeypatch.setattr(devices, "Preview", NoPreview)
    return path


def app_for(path, tmp_path):
    return RecApp(settings_path=path, cwd=tmp_path, lang="en", check_hub=False)


async def test_sentence_fills_settings_and_asks_for_what_is_missing(ready, tmp_path):
    app = app_for(ready, tmp_path)
    async with app.run_test(size=SIZE) as pilot:
        assert isinstance(app.screen, HomeScreen)
        assert app.focused.id == "task"
        await pilot.press(*"pick the cube")
        await pilot.press("enter")  # → the next empty slot
        assert app.focused.id == "dataset"
        await pilot.press("enter")  # record: the dataset has no name yet
        assert isinstance(app.screen, HomeScreen)
        assert "Name the dataset" in str(app.screen.query_one("#problems").render())
        await pilot.press(*"cubes")
        assert app.settings.task == "pick the cube" and app.settings.dataset == "cubes"
        assert settings.load(ready).dataset == "cubes"  # saved as you type


async def test_missing_calibration_marks_the_arm(ready, tmp_path):
    s = settings.load(ready)
    s.leader_id = "nobody"
    settings.save(s, ready)
    app = app_for(ready, tmp_path)
    async with app.run_test(size=SIZE):
        arm = app.screen.query_one("#arm", Button)
        assert arm.has_class("-todo")


async def test_command_screen(ready, tmp_path):
    app = app_for(ready, tmp_path)
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("ctrl+l")
        assert isinstance(app.screen, CommandScreen)
        assert app.screen.text.startswith("lerobot-record")
        await pilot.press("escape")
        assert isinstance(app.screen, HomeScreen)


async def test_records_with_the_fake_rig(ready, tmp_path, monkeypatch):
    original = record_mod.RecordScreen.__init__

    def with_fake_rig(self, args, **kw):
        original(self, args, command=fake_command(args), **kw)

    monkeypatch.setattr(record_mod.RecordScreen, "__init__", with_fake_rig)
    app = app_for(ready, tmp_path)
    async with app.run_test(size=SIZE) as pilot:
        app.screen.query_one("#task", Input).value = "pick the cube"
        app.screen.query_one("#dataset", Input).value = "cubes"
        await pilot.pause()
        app.screen.action_record()
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, RecordScreen)
        for _ in range(600):
            await pilot.pause(0.1)
            if screen.state.phase in ("done", "failed", "stopped"):
                break
        assert screen.state.phase == "done", screen.state.error
        assert len(screen.state.saved) == 2
        await pilot.press("enter")
        assert isinstance(app.screen, HomeScreen)
        assert "adds to 2 episodes" in str(app.screen.query_one("#summary").render())


async def test_setup_switches_and_ids(ready, tmp_path):
    app = app_for(ready, tmp_path)
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("ctrl+s")
        assert isinstance(app.screen, SetupScreen)
        app.screen.query_one("TabbedContent").active = "options"
        await pilot.pause()
        app.screen.query_one("#opt-push").toggle()
        app.screen.query_one("#opt-episode_s", Input).value = "25"
        await pilot.pause()
        assert app.settings.push is True and app.settings.episode_s == 25
        app.screen.query_one("TabbedContent").active = "arms"
        app.screen.query_one("#leader-id", Input).value = "blue"
        await pilot.pause()
        assert "leader: no" in str(app.screen.query_one("#cal-status").render())
        await pilot.press("escape")
        assert isinstance(app.screen, HomeScreen)
        assert settings.load(ready).leader_id == "blue"


async def test_turkish(ready, tmp_path):
    app = app_for(ready, tmp_path)
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("ctrl+t")
        await pilot.pause()
        assert "Kaydet" in str(app.screen.query_one(".word").render())
        assert settings.load(ready).lang == "tr"
