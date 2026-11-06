"""Read-only TCC checks. They never open a prompt and never try to get around TCC."""

from __future__ import annotations

import os
import subprocess

import Quartz
from ApplicationServices import AXIsProcessTrusted

ACCESSIBILITY_PATH = "System Settings > Privacy & Security > Accessibility"
SCREEN_RECORDING_PATH = "System Settings > Privacy & Security > Screen & System Audio Recording"


def responsible_app() -> str:
    """Name the outermost .app above this process. macOS asks that app for permission."""
    pid, found = os.getpid(), None
    for _ in range(32):
        try:
            line = subprocess.run(
                ["/bin/ps", "-o", "ppid=,comm=", "-p", str(pid)],
                capture_output=True, text=True, timeout=2, check=False,
            ).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            break
        if not line:
            break
        ppid, _, command = line.partition(" ")
        if ".app/" in command:
            found = command.split(".app/")[0].rsplit("/", 1)[-1]
        if not ppid.isdigit() or int(ppid) <= 1:
            break
        pid = int(ppid)
    return found or "the app that launched this server (could not name it)"


def accessibility_granted() -> bool:
    return bool(AXIsProcessTrusted())


def screen_recording_granted() -> bool:
    return bool(Quartz.CGPreflightScreenCaptureAccess())


def missing_accessibility(app: str | None = None) -> str:
    return (
        f"Accessibility permission is missing. Turn on {app or responsible_app()} in "
        f"{ACCESSIBILITY_PATH}, then restart that app."
    )


def missing_screen_recording(app: str | None = None) -> str:
    return (
        f"Screen Recording permission is missing. Turn on {app or responsible_app()} in "
        f"{SCREEN_RECORDING_PATH}, then restart that app."
    )


def report() -> dict:
    app = responsible_app()
    accessibility, screen = accessibility_granted(), screen_recording_granted()
    missing = []
    if not accessibility:
        missing.append(missing_accessibility(app))
    if not screen:
        missing.append(missing_screen_recording(app))
    return {
        "responsible_app": app,
        "accessibility": accessibility,
        "screen_recording": screen,
        "missing": missing,
    }
