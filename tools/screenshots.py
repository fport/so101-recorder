"""Renders the screens for the README into docs/, with a made-up arm, account and recording.

    uv run python tools/screenshots.py [--lang tr]

Textual saves SVG; with Google Chrome installed each one is also turned into a PNG (what the README shows).
"""

from __future__ import annotations

import argparse
import asyncio
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from so101_recorder import devices, hub, settings
from so101_recorder.settings import Settings
from so101_recorder.tui import record as record_mod
from so101_recorder.tui.app import RecApp
from so101_recorder.tui.record import RecordScreen

DOCS = Path(__file__).resolve().parent.parent / "docs"
PORTS = ["/dev/cu.usbmodem5AB01794851", "/dev/cu.usbmodem5A7C1232561"]
SIZE = (110, 32)
CHROME = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "google-chrome", "chromium"]


def to_png(svg: Path) -> None:
    chrome = next((c for c in CHROME if Path(c).exists() or shutil.which(c)), None)
    if chrome is None:
        return
    subprocess.run([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=2",
                    f"--screenshot={svg.with_suffix('.png')}", "--window-size=1360,831", svg.as_uri()],
                   check=True, capture_output=True)
    svg.unlink()


def fake_world(tmp: Path) -> Path:
    os.chdir(tmp)  # a project folder with its own calibration/, like so101-xox
    cal = tmp / "calibration"
    cal.mkdir()
    for arm in ("follower", "leader"):
        (cal / f"{arm}.json").write_text("{}")
    s = Settings(follower_port=PORTS[0], leader_port=PORTS[1], calibration_dir="calibration", namespace="fport",
                 dataset="tic-tac-toe-so101-x-round1", task="put the red X in the middle right cell",
                 data_dir="data")
    path = tmp / "settings.json"
    settings.save(s, path)
    devices.list_ports = lambda: PORTS
    hub.hub_datasets = lambda ns, limit=200: []
    hub.hub_episodes = lambda repo: None

    class NoPreview:
        def __init__(self, *a, **k):
            pass

        def start(self):
            return self

        def stop(self, wait=True):
            pass

    devices.Preview = NoPreview
    return path


def synthetic(i: int):
    """A stand-in camera picture: a table with a 3x3 grid seen from above, or a gripper from the wrist."""
    import cv2
    import numpy as np

    img = np.full((480, 640, 3), (60, 64, 70), np.uint8)
    if i == 0:
        cv2.rectangle(img, (120, 60), (520, 420), (215, 220, 225), -1)
        for k in (1, 2):
            cv2.line(img, (120 + k * 133, 60), (120 + k * 133, 420), (40, 40, 40), 6)
            cv2.line(img, (120, 60 + k * 120), (520, 60 + k * 120), (40, 40, 40), 6)
        cv2.line(img, (410, 200), (470, 260), (40, 40, 220), 14)
        cv2.line(img, (470, 200), (410, 260), (40, 40, 220), 14)
    else:
        img[:] = (150, 160, 170)
        cv2.rectangle(img, (40, 300), (280, 480), (30, 30, 30), -1)
        cv2.rectangle(img, (360, 300), (600, 480), (30, 30, 30), -1)
        cv2.circle(img, (320, 200), 70, (40, 120, 255), -1)
    return img


class Idle:
    running = True

    def __init__(self, *a, **k):
        pass

    def start(self):
        pass

    def send(self, word):
        pass


async def main(lang: str) -> None:
    DOCS.mkdir(exist_ok=True)
    suffix = "" if lang == "en" else f"-{lang}"
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        path = fake_world(tmp)
        app = RecApp(settings_path=path, cwd=Path("/Users/you/so101-xox"), lang=lang, check_hub=False)
        async with app.run_test(size=SIZE) as pilot:
            app.set_account(hub.Account(user="fport"))
            await pilot.pause(0.3)
            app.save_screenshot(str(DOCS / f"tui-home{suffix}.svg"))

            await pilot.press("ctrl+s")
            await pilot.pause(0.2)
            app.screen.query_one("TabbedContent").active = "arms"
            await pilot.pause(0.3)
            app.save_screenshot(str(DOCS / f"tui-setup{suffix}.svg"))
            app.screen.query_one("TabbedContent").active = "cameras"
            await pilot.pause(0.3)
            for i in (0, 1):
                app.screen._frame(i, devices.halfblocks(synthetic(i)))
            await pilot.pause(0.2)
            app.save_screenshot(str(DOCS / f"tui-cameras{suffix}.svg"))
            await pilot.press("escape")

            record_mod.Recording = Idle
            from so101_recorder import command

            screen = RecordScreen(command.record_args(app.settings, cwd=app.cwd))
            app.push_screen(screen)
            await pilot.pause(0.2)
            now = time.monotonic()
            for ev in [{"event": "keys", "global_keys": True},
                       {"event": "phase", "phase": "record", "episode": 0, "duration": 40},
                       {"event": "saved", "episode": 0}, {"event": "discarded"},
                       {"event": "phase", "phase": "record", "episode": 1, "duration": 40},
                       {"event": "saved", "episode": 1}]:
                screen.state.apply(ev, now=now - 100)
            screen.state.apply({"event": "phase", "phase": "record", "episode": 2, "duration": 40}, now=now - 23)
            for line in ["INFO lerobot_record.py:462 Keyboard listener started.",
                         "INFO utils.py:147 Recording episode 2"]:
                screen._log(line)
            screen.draw()
            await pilot.pause(0.2)
            app.save_screenshot(str(DOCS / f"tui-record{suffix}.svg"))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--lang", default="en")
    asyncio.run(main(p.parse_args().lang))
    for svg in DOCS.glob("*.svg"):
        to_png(svg)
