"""Everything the recorder remembers between runs, in one JSON file.

Lives in ~/.config/so101-recorder/settings.json (or $SO101_RECORDER_HOME). The Hugging Face token is not here:
it stays where huggingface_hub keeps it (~/.cache/huggingface/token), so lerobot and the hf CLI see the same login.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from lerobot.utils.constants import HF_LEROBOT_CALIBRATION


def home() -> Path:
    env = os.environ.get("SO101_RECORDER_HOME")
    if env:
        return Path(env).expanduser()
    return Path(os.environ.get("XDG_CONFIG_HOME", "~/.config")).expanduser() / "so101-recorder"


@dataclass
class Camera:
    name: str
    index: int | str  # OpenCV index, or a device path on Linux
    width: int = 640
    height: int = 480
    fps: int = 30


def _default_cameras() -> list[Camera]:
    return [Camera("top", 0), Camera("wrist", 1)]


@dataclass
class Settings:
    # the arms
    follower_port: str = ""
    follower_id: str = "follower"
    leader_port: str = ""
    leader_id: str = "leader"
    calibration_dir: str = ""  # "" = LeRobot's own place (~/.cache/huggingface/lerobot/calibration)
    cameras: list[Camera] = field(default_factory=_default_cameras)
    # the sentence
    episodes: int = 5
    task: str = ""
    namespace: str = ""  # Hugging Face user or org
    dataset: str = ""
    # how
    episode_s: float = 40
    reset_s: float = 90
    fps: int = 30
    data_dir: str = "data"  # datasets go to <data_dir>/<dataset>; relative to where so101-rec starts
    push: bool = True
    private: bool = True
    display: bool = True  # the Rerun viewer
    sounds: bool = True  # lerobot says "Recording episode 3" out loud
    streaming: bool = True  # encode video while recording: saving an episode is instant
    encoder_threads: int = 2
    global_keys: bool = True  # → ← Esc work while another window (Rerun) has focus
    lang: str = ""
    recent_tasks: list[str] = field(default_factory=list)

    @property
    def repo_id(self) -> str:
        return f"{self.namespace or 'local'}/{self.dataset}"

    def root(self, cwd: Path | None = None) -> Path:
        base = Path(self.data_dir).expanduser()
        if not base.is_absolute():
            base = (cwd or Path.cwd()) / base
        return base / self.dataset

    def calibration_file(self, role: str) -> Path:
        """Where LeRobot will look for the follower's or the leader's calibration."""
        arm_id = self.follower_id if role == "follower" else self.leader_id
        if self.calibration_dir:
            return Path(self.calibration_dir).expanduser() / f"{arm_id}.json"
        kind = "robots/so_follower" if role == "follower" else "teleoperators/so_leader"
        return HF_LEROBOT_CALIBRATION / kind / f"{arm_id}.json"

    def remember_task(self, task: str) -> None:
        task = task.strip()
        if not task:
            return
        self.recent_tasks = [task] + [t for t in self.recent_tasks if t != task][:19]


def load(path: Path | None = None) -> Settings:
    path = path or home() / "settings.json"
    s = Settings()
    if not path.is_file():
        if Path("calibration", f"{s.follower_id}.json").is_file():
            s.calibration_dir = "calibration"  # a project with its own calibration folder (like so101-xox)
        return s
    try:
        raw = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return s
    known = {f.name for f in fields(Settings)}
    for k, v in raw.items():
        if k == "cameras" and isinstance(v, list):
            s.cameras = [Camera(**c) for c in v if isinstance(c, dict) and "name" in c and "index" in c]
        elif k in known:
            setattr(s, k, v)
    return s


def save(s: Settings, path: Path | None = None) -> None:
    path = path or home() / "settings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(asdict(s), indent=2, ensure_ascii=False) + "\n")
    tmp.replace(path)
