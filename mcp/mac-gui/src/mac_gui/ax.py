"""Accessibility reads, element search, menu walking, and the one AXPress call site.

Everything except press() and set_frontmost() is read-only. Reading a menu through
Accessibility does not open it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ApplicationServices import (
    AXUIElementCopyActionNames,
    AXUIElementCopyAttributeValue,
    AXUIElementCreateApplication,
    AXUIElementPerformAction,
    AXUIElementSetAttributeValue,
    AXUIElementSetMessagingTimeout,
    AXValueGetValue,
    kAXValueCGPointType,
    kAXValueCGSizeType,
)

from .apps import Refused

AX_TIMEOUT_SECONDS = 2.0
SUCCESS = 0
MAX_TEXT = 60
MAX_CHILDREN_SHOWN = 40
SEARCH_NODE_LIMIT = 5000
SEARCH_DEPTH_LIMIT = 30

# These items reach outside the allowlisted app, or end the app or the session.
BLOCKED_MENUS = {"apple", "services"}
BLOCKED_ITEM = re.compile(
    r"^(quit|exit|force quit|log out|shut down|restart|sleep|lock screen)\b", re.IGNORECASE
)


def app_element(pid: int):
    element = AXUIElementCreateApplication(pid)
    AXUIElementSetMessagingTimeout(element, AX_TIMEOUT_SECONDS)
    return element


def attr(element, name: str):
    error, value = AXUIElementCopyAttributeValue(element, name, None)
    return value if error == SUCCESS else None


def children(element) -> list:
    return list(attr(element, "AXChildren") or [])


def _point_or_size(element, name: str, kind) -> tuple[float, float] | None:
    value = attr(element, name)
    if value is None:
        return None
    ok, out = AXValueGetValue(value, kind, None)
    if not ok:
        return None
    return (out.x, out.y) if kind == kAXValueCGPointType else (out.width, out.height)


def _text(value) -> str:
    if not isinstance(value, str):
        return ""
    value = " ".join(value.split())
    return value[:MAX_TEXT] + "..." if len(value) > MAX_TEXT else value


def _label(element) -> tuple[str, str, str]:
    return (
        _text(attr(element, "AXTitle")),
        _text(attr(element, "AXDescription")),
        _text(attr(element, "AXValue")),
    )


def _line(element, geometry: bool) -> tuple[str, str]:
    """Return (text, role) for one node. An unnamed container returns empty text."""
    role = str(attr(element, "AXRole") or "AXUnknown")
    title, description, value = _label(element)
    parts = [role]
    if title:
        parts.append(f'"{title}"')
    if description and description != title:
        parts.append(f'desc="{description}"')
    if value and value not in (title, description):
        parts.append(f'value="{value}"')
    named = len(parts) > 1
    if geometry:
        position = _point_or_size(element, "AXPosition", kAXValueCGPointType)
        size = _point_or_size(element, "AXSize", kAXValueCGSizeType)
        if position and size:
            parts.append(f"@{position[0]:.0f},{position[1]:.0f} {size[0]:.0f}x{size[1]:.0f}")
    if attr(element, "AXEnabled") is False:
        parts.append("disabled")
    leaf_role = role not in {"AXGroup", "AXUnknown", "AXSplitGroup", "AXScrollArea", "AXLayoutArea", "AXMenu"}
    return (" ".join(parts) if (named or leaf_role) else ""), role


def read_tree(
    pid: int,
    scope: str = "windows",
    max_depth: int = 8,
    max_nodes: int = 150,
    contains: str | None = None,
    geometry: bool = False,
) -> dict:
    """Return a trimmed tree as indented lines. Unnamed containers collapse into their children."""
    root = app_element(pid)
    lines: list[str] = []
    state = {"truncated": 0}
    needle = contains.casefold() if contains else None

    def walk(element, depth: int, indent: int) -> None:
        if len(lines) >= max_nodes:
            state["truncated"] += 1
            return
        text, _role = _line(element, geometry)
        if text and (needle is None or needle in text.casefold()):
            lines.append("  " * indent + text)
            indent += 1
        if depth >= max_depth:
            return
        kids = children(element)
        for kid in kids[:MAX_CHILDREN_SHOWN]:
            walk(kid, depth + 1, indent)
        if len(kids) > MAX_CHILDREN_SHOWN:
            state["truncated"] += len(kids) - MAX_CHILDREN_SHOWN
            if needle is None and len(lines) < max_nodes:
                lines.append("  " * indent + f"... {len(kids) - MAX_CHILDREN_SHOWN} more children")

    if scope in ("windows", "all"):
        for window in _windows(root):
            walk(window, 0, 0)
    if scope in ("menubar", "all"):
        for item in _menu_bar_items(root):
            walk(item, 0, 0)
    return {"lines": lines, "nodes": len(lines), "truncated": state["truncated"]}


def _windows(root) -> list:
    """Return the app's windows. Some apps leave AXWindows empty but still report a focused window."""
    listed = list(attr(root, "AXWindows") or [])
    if listed:
        return listed
    focused = attr(root, "AXFocusedWindow")
    main = attr(root, "AXMainWindow")
    if focused is not None and main is not None and focused == main:
        return [focused]
    return [w for w in (focused, main) if w is not None]


def _normal(text: str) -> str:
    return " ".join(text.replace("…", "...").split()).casefold().removesuffix("...").strip()


def _full_labels(element) -> list[str]:
    labels = []
    for name in ("AXTitle", "AXDescription", "AXValue"):
        value = attr(element, name)
        if isinstance(value, str) and value.strip():
            labels.append(value)
    return labels


def normalize_role(role: str) -> str:
    role = role.strip()
    return role if role.startswith("AX") else "AX" + role[:1].upper() + role[1:]


def find_elements(pid: int, role: str, title: str) -> list:
    """Find window elements whose role matches and whose title, description, or value matches."""
    wanted_role, wanted = normalize_role(role), _normal(title)
    matches: list = []
    seen = [0]

    def walk(element, depth: int) -> None:
        if seen[0] >= SEARCH_NODE_LIMIT or depth > SEARCH_DEPTH_LIMIT:
            return
        seen[0] += 1
        if attr(element, "AXRole") == wanted_role and any(
            _normal(label) == wanted for label in _full_labels(element)
        ):
            matches.append(element)
        for kid in children(element):
            walk(kid, depth + 1)

    for window in _windows(app_element(pid)):
        walk(window, 0)
    return matches


def describe_element(element) -> str:
    return _line(element, True)[0]


def supports_press(element) -> bool:
    error, actions = AXUIElementCopyActionNames(element, None)
    return error == SUCCESS and "AXPress" in (actions or [])


def is_enabled(element) -> bool:
    return attr(element, "AXEnabled") is not False


def require_pressable_label(title: str) -> None:
    if BLOCKED_ITEM.match(title.strip()):
        raise Refused(f"{title!r} is blocked: mac-gui does not quit apps or end the session.")


def _menu_bar_items(root) -> list:
    """Return the app's menu bar items, without the Apple menu at index 0."""
    bar = attr(root, "AXMenuBar")
    return children(bar)[1:] if bar is not None else []


def _pick(elements: list, wanted: str, where: str):
    titled = [(e, attr(e, "AXTitle")) for e in elements]
    titled = [(e, t) for e, t in titled if isinstance(t, str) and t.strip()]
    exact = [e for e, t in titled if t == wanted]
    hits = exact or [e for e, t in titled if _normal(t) == _normal(wanted)]
    if len(hits) == 1:
        return hits[0]
    names = [t for _, t in titled][:30]
    if not hits:
        raise Refused(f"menu item {wanted!r} was not found in {where}. Available: {names}")
    raise Refused(f"menu item {wanted!r} is ambiguous in {where}. Available: {names}")


@dataclass
class MenuTarget:
    element: object
    path: list[str]
    enabled: bool


def check_menu_path(path: list[str]) -> None:
    """Refuse menu paths that leave the allowlisted app. This needs no running app."""
    if not path or not all(isinstance(part, str) and part.strip() for part in path):
        raise Refused("menu path must be a non-empty list of titles, for example ['File', 'Import'].")
    for part in path:
        if _normal(part) in BLOCKED_MENUS:
            raise Refused(f"menu {part!r} is blocked: it reaches outside the allowlisted app.")
    require_pressable_label(path[-1])


def resolve_menu(pid: int, path: list[str]) -> MenuTarget:
    """Walk a menu path through read-only attributes. This opens nothing and presses nothing."""
    check_menu_path(path)
    node = _pick(_menu_bar_items(app_element(pid)), path[0], "the menu bar")
    for depth, part in enumerate(path[1:], start=1):
        menus = [kid for kid in children(node) if attr(kid, "AXRole") == "AXMenu"]
        items = children(menus[0]) if menus else []
        node = _pick(items, part, " > ".join(path[:depth]))
    return MenuTarget(node, list(path), is_enabled(node))


def press(element) -> int:
    """The only AXPress call in this package. The caller must check frontmost right before it."""
    return AXUIElementPerformAction(element, "AXPress")


def set_frontmost(pid: int) -> int:
    return AXUIElementSetAttributeValue(app_element(pid), "AXFrontmost", True)
