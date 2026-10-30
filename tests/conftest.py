import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).parent


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("SO101_RECORDER_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("SO101_REC_GLOBAL_KEYS", "0")
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")


def fake_command(args):
    return [sys.executable, "-u", str(HERE / "fake_rig.py"), *args]


def fake_args(root, *, episodes=2, episode_s=0.4, reset_s=0.2, extra=()):
    return [
        "--robot.type=so101_follower", "--robot.port=/dev/fake-follower", "--robot.id=follower",
        "--teleop.type=so101_leader", "--teleop.port=/dev/fake-leader", "--teleop.id=leader",
        "--dataset.repo_id=local/fake", f"--dataset.root={root}", "--dataset.single_task=do the thing",
        f"--dataset.num_episodes={episodes}", f"--dataset.episode_time_s={episode_s}",
        f"--dataset.reset_time_s={reset_s}", "--dataset.fps=30", "--dataset.push_to_hub=false",
        "--dataset.no_stamp=true", "--display_data=false", "--play_sounds=false", *extra,
    ]


os.environ.setdefault("PYTHONUNBUFFERED", "1")
