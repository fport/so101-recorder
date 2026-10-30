"""What has to be right before lerobot-record starts. Each problem is a sentence that says what to do."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .hub import Account, Local
from .i18n import t
from .settings import Settings


@dataclass
class Check:
    errors: list[str] = field(default_factory=list)  # recording cannot start
    warnings: list[str] = field(default_factory=list)  # it can, after a yes
    focus: str = ""  # the sentence slot to put the cursor in for the first error
    arm: bool = False  # something about the arms (ports, calibration) is not right

    @property
    def ok(self) -> bool:
        return not self.errors


def check(s: Settings, account: Account | None, ports: list[str], local: Local, root: Path,
          hub_episodes: int | None = None) -> Check:
    c = Check()

    def error(msg: str, focus: str = "") -> None:
        c.errors.append(msg)
        c.focus = c.focus or focus
        c.arm = c.arm or focus == "arm"

    if not s.task.strip():
        error(t("need task"), "task")
    if not s.dataset.strip():
        error(t("need dataset"), "dataset")
    if s.push:
        if account is not None and not account.ok:
            error(t("need login"))
        elif not s.namespace.strip():
            error(t("need namespace"), "namespace")

    for role, port in (("follower", s.follower_port), ("leader", s.leader_port)):
        if not port:
            error(t("need port", role=role), "arm")
        elif port not in ports:
            error(t("port gone", role=role, port=port), "arm")
    if s.follower_port and s.follower_port == s.leader_port:
        error(t("same port"), "arm")
    for role in ("follower", "leader"):
        path = s.calibration_file(role)
        if not path.is_file():
            error(t("no calibration", role=role, path=short(path)), "arm")

    seen = set()
    for cam in s.cameras:
        if cam.index in seen:
            error(t("same camera", i=cam.index))
        seen.add(cam.index)

    if s.dataset.strip():
        if local.exists and not local.valid:
            error(t("broken dataset", root=short(root)), "dataset")
        elif local.valid:
            if local.fps and local.fps != s.fps:
                error(t("fps mismatch", root=short(root), a=local.fps, b=s.fps))
            names = sorted(c.name for c in s.cameras)
            if local.cameras and sorted(local.cameras) != names:
                error(t("cams mismatch", root=short(root), a=", ".join(sorted(local.cameras)), b=", ".join(names)))
        elif hub_episodes and s.push:
            c.warnings.append(t("on hub", repo=s.repo_id, n=hub_episodes, root=short(root)))
    return c


def short(p: Path) -> str:
    home = str(Path.home())
    s = str(p)
    return "~" + s[len(home):] if s.startswith(home) else s
