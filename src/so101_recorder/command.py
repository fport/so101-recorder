"""Settings -> the exact lerobot-record arguments. The recorder runs these, and shows them so you can too."""

from __future__ import annotations

import shlex
from pathlib import Path

from .settings import Settings


def cameras_arg(s: Settings) -> str:
    def one(c):
        index = c.index if isinstance(c.index, int) else f'"{c.index}"'
        return f"{c.name}: {{type: opencv, index_or_path: {index}, width: {c.width}, height: {c.height}, fps: {c.fps}}}"

    return "{ " + ", ".join(one(c) for c in s.cameras) + "}"


def _num(x: float) -> str:
    return str(int(x)) if float(x).is_integer() else str(x)


def _bool(x: bool) -> str:
    return "true" if x else "false"


def record_args(s: Settings, *, resume: bool = False, cwd: Path | None = None) -> list[str]:
    """Arguments for lerobot-record (without the program name)."""
    args = [
        "--robot.type=so101_follower",
        f"--robot.port={s.follower_port}",
        f"--robot.id={s.follower_id}",
    ]
    if s.calibration_dir:
        args.append(f"--robot.calibration_dir={s.calibration_dir}")
    if s.cameras:
        args.append(f"--robot.cameras={cameras_arg(s)}")
    args += [
        "--teleop.type=so101_leader",
        f"--teleop.port={s.leader_port}",
        f"--teleop.id={s.leader_id}",
    ]
    if s.calibration_dir:
        args.append(f"--teleop.calibration_dir={s.calibration_dir}")
    args += [
        f"--dataset.repo_id={s.repo_id}",
        f"--dataset.root={s.root(cwd)}",
        f"--dataset.single_task={s.task.strip()}",
        f"--dataset.num_episodes={s.episodes}",
        f"--dataset.episode_time_s={_num(s.episode_s)}",
        f"--dataset.reset_time_s={_num(s.reset_s)}",
        f"--dataset.fps={s.fps}",
    ]
    if s.streaming:
        args += ["--dataset.streaming_encoding=true", f"--dataset.encoder_threads={s.encoder_threads}"]
    args += [f"--dataset.push_to_hub={_bool(s.push)}"]
    if s.push:
        args += [f"--dataset.private={_bool(s.private)}"]
    args += [
        "--dataset.no_stamp=true",  # keep the name as typed; lerobot would append a date otherwise
        f"--display_data={_bool(s.display)}",
        f"--play_sounds={_bool(s.sounds)}",
    ]
    if resume:
        args.append("--resume=true")
    return args


def shell(args: list[str]) -> str:
    """lerobot-record with the arguments, one per line, ready to paste into a shell."""
    lines = ["lerobot-record"] + [_quote(a) for a in args]
    return " \\\n  ".join(lines)


def _quote(arg: str) -> str:
    key, sep, value = arg.partition("=")
    if not sep:
        return shlex.quote(arg)
    return f"{key}={shlex.quote(value)}" if shlex.quote(value) != value else arg
