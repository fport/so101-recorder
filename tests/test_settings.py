import json

from lerobot.utils.constants import HF_LEROBOT_CALIBRATION

from so101_recorder import settings
from so101_recorder.settings import Camera, Settings


def test_roundtrip(tmp_path):
    path = tmp_path / "s.json"
    s = Settings(follower_port="/dev/a", task="pick", cameras=[Camera("top", 2), Camera("side", "/dev/v0")])
    s.remember_task("pick")
    settings.save(s, path)
    back = settings.load(path)
    assert back == s


def test_unknown_and_broken(tmp_path):
    path = tmp_path / "s.json"
    path.write_text(json.dumps({"task": "x", "nope": 1, "cameras": [{"name": "a"}, {"name": "b", "index": 3}]}))
    s = settings.load(path)
    assert s.task == "x" and [c.name for c in s.cameras] == ["b"]
    path.write_text("{not json")
    assert settings.load(path) == Settings()


def test_calibration_file():
    s = Settings()
    assert s.calibration_file("follower") == HF_LEROBOT_CALIBRATION / "robots/so_follower/follower.json"
    assert s.calibration_file("leader") == HF_LEROBOT_CALIBRATION / "teleoperators/so_leader/leader.json"
    s.calibration_dir, s.leader_id = "calibration", "blue"
    assert str(s.calibration_file("leader")) == "calibration/blue.json"


def test_project_calibration_folder_is_picked_up(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "calibration").mkdir()
    (tmp_path / "calibration" / "follower.json").write_text("{}")
    assert settings.load(tmp_path / "missing.json").calibration_dir == "calibration"


def test_root_and_recent_tasks(tmp_path):
    s = Settings(dataset="d", data_dir="data")
    assert s.root(tmp_path) == tmp_path / "data" / "d"
    for task in ["a", "b", "a"]:
        s.remember_task(task)
    assert s.recent_tasks == ["a", "b"]
