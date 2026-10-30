"""The Hugging Face side: who is logged in, saving a token, what datasets exist (here and on the Hub)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Account:
    user: str = ""
    orgs: list[str] = field(default_factory=list)
    error: str = ""  # set when a token exists but the Hub did not accept it (or could not be reached)

    @property
    def ok(self) -> bool:
        return bool(self.user)

    @property
    def namespaces(self) -> list[str]:
        return [self.user, *self.orgs] if self.user else []


def account() -> Account:
    from huggingface_hub import get_token, whoami

    if not get_token():
        return Account()
    try:
        info = whoami()
    except Exception as e:  # offline, revoked token, ...
        return Account(error=str(e).splitlines()[0][:200])
    orgs = [o.get("name", "") for o in info.get("orgs", []) if o.get("name")]
    return Account(user=info.get("name", ""), orgs=orgs)


def login(token: str) -> Account:
    """Checks the token with the Hub, then stores it where huggingface_hub (and so lerobot) reads it."""
    from huggingface_hub import login as hf_login
    from huggingface_hub import whoami

    token = token.strip()
    info = whoami(token=token)  # raises on a bad token, before anything is written
    hf_login(token=token, add_to_git_credential=False, skip_if_logged_in=False)
    orgs = [o.get("name", "") for o in info.get("orgs", []) if o.get("name")]
    return Account(user=info.get("name", ""), orgs=orgs)


def logout() -> None:
    from huggingface_hub import logout as hf_logout

    try:
        hf_logout()
    except Exception:
        pass


def hub_datasets(namespace: str, limit: int = 200) -> list[str]:
    """Names (without the namespace) of the datasets under `namespace` on the Hub, newest first."""
    from huggingface_hub import HfApi

    items = HfApi().list_datasets(author=namespace, sort="last_modified", limit=limit)
    return [d.id.split("/", 1)[-1] for d in items]


def hub_episodes(repo_id: str) -> int | None:
    """Episodes in a LeRobot dataset on the Hub, None if it is not there (or not a LeRobot dataset)."""
    from huggingface_hub import hf_hub_download

    try:
        path = hf_hub_download(repo_id, "meta/info.json", repo_type="dataset")
        return int(json.loads(Path(path).read_text()).get("total_episodes", 0))
    except Exception:
        return None


@dataclass
class Local:
    exists: bool  # the folder is there
    valid: bool  # ...and it is a LeRobot dataset (meta/info.json), so it can be resumed
    episodes: int = 0
    fps: int | None = None
    cameras: list[str] = field(default_factory=list)


def local(root: Path) -> Local:
    info_path = root / "meta" / "info.json"
    if not root.exists():
        return Local(False, False)
    try:
        info = json.loads(info_path.read_text())
    except (OSError, json.JSONDecodeError):
        return Local(True, False)
    cams = [k.split(".", 2)[-1] for k, v in info.get("features", {}).items() if v.get("dtype") == "video"]
    return Local(True, True, int(info.get("total_episodes", 0)), fps=info.get("fps"), cameras=cams)


def local_datasets(data_dir: Path) -> list[str]:
    if not data_dir.is_dir():
        return []
    found = [p for p in data_dir.iterdir() if (p / "meta" / "info.json").is_file()]
    return [p.name for p in sorted(found, key=lambda p: p.stat().st_mtime, reverse=True)]


def dataset_url(repo_id: str) -> str:
    return f"https://huggingface.co/datasets/{repo_id}"


def viewer_url(repo_id: str) -> str:
    return f"https://huggingface.co/spaces/lerobot/visualize_dataset?path=/{repo_id}/episode_0"
