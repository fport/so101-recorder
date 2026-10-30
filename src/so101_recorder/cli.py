"""so101-rec: the recorder UI. `so101-rec --print` shows the lerobot-record command for the saved settings."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="so101-rec", description="Record SO-101 datasets with lerobot-record.")
    p.add_argument("--print", action="store_true", help="print the lerobot-record command and exit")
    p.add_argument("--lang", choices=["en", "tr"], help="interface language (default: the system's)")
    p.add_argument("--settings", type=Path, help="settings file (default: ~/.config/so101-recorder/settings.json)")
    p.add_argument("--version", action="version", version=f"so101-recorder {__version__}")
    args = p.parse_args(argv)

    if args.print:
        from . import command, hub, settings

        s = settings.load(args.settings)
        resume = hub.local(s.root()).valid
        print(command.shell(command.record_args(s, resume=resume)))
        return

    from .tui.app import RecApp

    RecApp(settings_path=args.settings, lang=args.lang).run()
    sys.exit(0)
