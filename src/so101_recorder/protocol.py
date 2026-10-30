"""How the runner (lerobot-record) and the UI talk: JSON events on stdout, control words on stdin.

Every other stdout line is lerobot's own output and is shown as-is.
"""

from __future__ import annotations

import json

PREFIX = "@so101-rec "

# control words the UI writes to the runner's stdin, one per line, and the lerobot key each one stands for
CONTROLS = {"next": "right", "redo": "left", "stop": "esc"}


def encode(event: str, **data) -> str:
    return PREFIX + json.dumps({"event": event, **data}, ensure_ascii=False)


def decode(line: str) -> dict | None:
    """The event in a stdout line, or None for an ordinary log line."""
    if not line.startswith(PREFIX):
        return None
    try:
        data = json.loads(line[len(PREFIX):])
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) and "event" in data else None
