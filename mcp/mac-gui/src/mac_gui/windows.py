"""Window lookup and the click hit test, from the window server's own list."""

from __future__ import annotations

from dataclasses import dataclass

import Quartz


@dataclass(frozen=True)
class Window:
    id: int
    pid: int
    owner: str
    title: str
    x: float
    y: float
    width: float
    height: float
    layer: int
    onscreen: bool

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        return (self.x, self.y, self.width, self.height)

    def contains(self, x: float, y: float) -> bool:
        return self.x <= x < self.x + self.width and self.y <= y < self.y + self.height


def _from_info(info: dict) -> Window:
    bounds = info.get("kCGWindowBounds", {})
    return Window(
        id=int(info.get("kCGWindowNumber", 0)),
        pid=int(info.get("kCGWindowOwnerPID", -1)),
        owner=str(info.get("kCGWindowOwnerName", "")),
        title=str(info.get("kCGWindowName", "") or ""),
        x=float(bounds.get("X", 0)),
        y=float(bounds.get("Y", 0)),
        width=float(bounds.get("Width", 0)),
        height=float(bounds.get("Height", 0)),
        layer=int(info.get("kCGWindowLayer", 0)),
        onscreen=bool(info.get("kCGWindowIsOnscreen", False)),
    )


def list_app_windows(pid: int) -> list[Window]:
    """Return the real windows of one process, on-screen first, then largest first."""
    infos = Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionAll, Quartz.kCGNullWindowID)
    found = [
        _from_info(info)
        for info in infos or []
        if info.get("kCGWindowOwnerPID") == pid and float(info.get("kCGWindowAlpha", 1)) > 0
    ]
    found = [w for w in found if w.width >= 50 and w.height >= 50 and w.layer >= 0]
    return sorted(found, key=lambda w: (not w.onscreen, -(w.width * w.height)))


def window_at(x: float, y: float) -> Window | None:
    """Return the top visible window at a screen point. The list comes front to back."""
    infos = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
        Quartz.kCGNullWindowID,
    )
    for info in infos or []:
        if float(info.get("kCGWindowAlpha", 1)) <= 0:
            continue
        window = _from_info(info)
        if window.layer >= 0 and window.contains(x, y):
            return window
    return None
