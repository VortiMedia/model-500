"""The hard allowlist, and fresh answers to "is it running?" and "is it in front?".

The allowlist is a constant on purpose. No flag, argument, or environment variable can
extend it. To add an app, change this file.

Queries go through lsappinfo, not NSWorkspace. NSWorkspace answers from a cache that
only refreshes while a run loop spins, and an MCP server has no run loop. A stale answer
to "is it in front?" could send input to the wrong app.
"""

from __future__ import annotations

import os
import re
import subprocess
from types import MappingProxyType

LSAPPINFO = "/usr/bin/lsappinfo"

# Bundle IDs read from each app's Contents/Info.plist on 2026-11-06.
ALLOWED_APPS = MappingProxyType(
    {
        "com.pioneerdj.rekordboxdj": "rekordbox",
        "com.AlphaTheta.RMX-IGNITE-SampleManager": "RMX-IGNITE Sample Manager",
        "org.audacityteam.audacity4": "Audacity",
    }
)

_ALIASES = MappingProxyType(
    {
        "rekordbox": "com.pioneerdj.rekordboxdj",
        "rmx-ignite": "com.AlphaTheta.RMX-IGNITE-SampleManager",
        "rmx-ignite sample manager": "com.AlphaTheta.RMX-IGNITE-SampleManager",
        "sample manager": "com.AlphaTheta.RMX-IGNITE-SampleManager",
        "audacity": "org.audacityteam.audacity4",
        **{bundle.lower(): bundle for bundle in ALLOWED_APPS},
    }
)


class Refused(Exception):
    """A safety check said no. The message goes back to the caller as it is."""


def resolve_app(name: str) -> str:
    """Return the allowlisted bundle ID for a name, or refuse."""
    bundle = _ALIASES.get(name.strip().lower()) if isinstance(name, str) else None
    if bundle is None:
        allowed = ", ".join(f"{label} ({b})" for b, label in ALLOWED_APPS.items())
        raise Refused(f"app {name!r} is not allowlisted. Allowed apps: {allowed}.")
    return bundle


def _lsappinfo(*args: str) -> str:
    try:
        done = subprocess.run(
            [LSAPPINFO, *args], capture_output=True, text=True, timeout=3, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return done.stdout if done.returncode == 0 else ""


def _field(output: str, pattern: str) -> str | None:
    match = re.search(pattern, output)
    return match.group(1) if match else None


def _bundle_of(output: str) -> str | None:
    return _field(output, r'bundleID="([^"]+)"')


def running_pid(bundle: str) -> int | None:
    """Return the pid for a bundle, or None. lsappinfo can list an exited app, so probe it."""
    output = _lsappinfo("info", "-app", bundle)
    pid = _field(output, r"\bpid = (\d+)")
    if _bundle_of(output) != bundle or pid is None:
        return None
    try:
        os.kill(int(pid), 0)
    except (ProcessLookupError, PermissionError):
        return None
    return int(pid)


def is_frontmost(bundle: str) -> bool:
    """True only when lsappinfo clearly says this bundle is in front. Any doubt is False."""
    output = _lsappinfo("info", "-app", bundle)
    first_line = output.splitlines()[0] if output else ""
    return _bundle_of(output) == bundle and "(in front)" in first_line


def frontmost_label() -> str:
    """Name the frontmost app for error messages. Never use this for a safety decision."""
    asn = _lsappinfo("front").strip()
    return (_bundle_of(_lsappinfo("info", asn)) if asn else None) or "unknown"


def require_frontmost(bundle: str) -> None:
    if not is_frontmost(bundle):
        raise Refused(
            f"{ALLOWED_APPS[bundle]} is not frontmost ({frontmost_label()} is). "
            "No input was sent. Call gui_activate first."
        )
