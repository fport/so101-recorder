import json

from so101_recorder import checks, hub
from so101_recorder.hub import Account
from so101_recorder.settings import Settings


def ready(tmp_path) -> Settings:
    cal = tmp_path / "cal"
    cal.mkdir()
    (cal / "follower.json").write_text("{}")
    (cal / "leader.json").write_text("{}")
    return Settings(follower_port="/dev/f", leader_port="/dev/l", calibration_dir=str(cal), task="pick",
                    namespace="me", dataset="d", data_dir=str(tmp_path / "data"))


ME = Account(user="me")


def run(s, tmp_path, account=ME, ports=("/dev/f", "/dev/l"), hub_episodes=None):
    root = s.root(tmp_path)
    return checks.check(s, account, list(ports), hub.local(root), root, hub_episodes)


def test_ready(tmp_path):
    c = run(ready(tmp_path), tmp_path)
    assert c.ok and not c.warnings and not c.arm


def test_sentence_problems_focus_the_slot(tmp_path):
    s = ready(tmp_path)
    s.task, s.dataset = " ", ""
    c = run(s, tmp_path)
    assert len(c.errors) == 2 and c.focus == "task" and not c.arm


def test_arms(tmp_path):
    s = ready(tmp_path)
    s.leader_port = "/dev/f"
    s.leader_id = "nobody"
    c = run(s, tmp_path, ports=["/dev/f"])
    assert c.arm and c.focus == "arm"
    assert len(c.errors) == 2  # same port, missing calibration


def test_unplugged_port(tmp_path):
    c = run(ready(tmp_path), tmp_path, ports=["/dev/f"])
    assert c.arm and any("/dev/l" in e for e in c.errors)


def test_login_needed_only_for_push(tmp_path):
    s = ready(tmp_path)
    assert not run(s, tmp_path, account=Account()).ok
    s.push = False
    assert run(s, tmp_path, account=Account()).ok


def test_existing_dataset(tmp_path):
    s = ready(tmp_path)
    root = s.root(tmp_path)
    (root / "meta").mkdir(parents=True)
    assert not run(s, tmp_path).ok  # a folder that is not a dataset
    info = {"total_episodes": 4, "fps": 15, "features": {"observation.images.top": {"dtype": "video"}}}
    (root / "meta" / "info.json").write_text(json.dumps(info))
    c = run(s, tmp_path)
    assert len(c.errors) == 2  # fps and cameras differ
    s.fps = 15
    s.cameras = s.cameras[:1]
    assert run(s, tmp_path).ok


def test_on_the_hub_but_not_here_is_a_warning(tmp_path):
    c = run(ready(tmp_path), tmp_path, hub_episodes=12)
    assert c.ok and len(c.warnings) == 1 and "12" in c.warnings[0]
