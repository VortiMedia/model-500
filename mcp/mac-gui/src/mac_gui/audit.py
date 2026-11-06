"""Append-only action log at ~/model-500/state/gui-actions.log, one JSON object per line."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

LOG_PATH = Path.home() / "model-500" / "state" / "gui-actions.log"
_MAX_VALUE = 200


def _clip(value):
    return value[:_MAX_VALUE] + "..." if isinstance(value, str) and len(value) > _MAX_VALUE else value


def record(tool: str, app: str, args: dict, dry_run: bool, outcome: str, detail: str = "") -> None:
    """Write one line. An OSError reaches the caller, so real input fails closed without a log."""
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "tool": tool,
        "app": app,
        "dry_run": dry_run,
        "outcome": outcome,
        "args": {key: _clip(value) for key, value in args.items()},
        "detail": _clip(detail),
    }
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
