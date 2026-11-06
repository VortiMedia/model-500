"""Build CGEvents, and send them through one guarded choke point.

Building an event sends nothing, so dry_run can build real events and read them back.
_post() holds the only CGEventPost and CGEventPostToPid calls in the package, and send()
runs the guard before every event.

Keyboard events go to the target pid only, so a focus change cannot put them in another
app. Mouse and scroll events route by screen position, so they use the HID tap, with a
hit test in the guard. None of this has run against a real app yet.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

import Quartz

from .apps import Refused

MAX_TEXT_LENGTH = 1000

_KEYCODES = {
    "a": 0, "s": 1, "d": 2, "f": 3, "h": 4, "g": 5, "z": 6, "x": 7, "c": 8, "v": 9, "b": 11,
    "q": 12, "w": 13, "e": 14, "r": 15, "y": 16, "t": 17, "1": 18, "2": 19, "3": 20, "4": 21,
    "6": 22, "5": 23, "=": 24, "9": 25, "7": 26, "-": 27, "8": 28, "0": 29, "]": 30, "o": 31,
    "u": 32, "[": 33, "i": 34, "p": 35, "l": 37, "j": 38, "'": 39, "k": 40, ";": 41, "\\": 42,
    ",": 43, "/": 44, "n": 45, "m": 46, ".": 47, "`": 50,
    "return": 36, "enter": 36, "tab": 48, "space": 49, "delete": 51, "backspace": 51,
    "escape": 53, "esc": 53, "forwarddelete": 117, "home": 115, "end": 119, "pageup": 116,
    "pagedown": 121, "left": 123, "right": 124, "down": 125, "up": 126,
    "f1": 122, "f2": 120, "f3": 99, "f4": 118, "f5": 96, "f6": 97, "f7": 98, "f8": 100,
    "f9": 101, "f10": 109, "f11": 103, "f12": 111, "f13": 105, "f14": 107, "f15": 113,
}

_MODIFIERS = {
    "cmd": Quartz.kCGEventFlagMaskCommand,
    "command": Quartz.kCGEventFlagMaskCommand,
    "super": Quartz.kCGEventFlagMaskCommand,
    "meta": Quartz.kCGEventFlagMaskCommand,
    "shift": Quartz.kCGEventFlagMaskShift,
    "ctrl": Quartz.kCGEventFlagMaskControl,
    "control": Quartz.kCGEventFlagMaskControl,
    "alt": Quartz.kCGEventFlagMaskAlternate,
    "opt": Quartz.kCGEventFlagMaskAlternate,
    "option": Quartz.kCGEventFlagMaskAlternate,
}

_CANON = {"command": "cmd", "super": "cmd", "meta": "cmd", "control": "ctrl", "opt": "alt", "option": "alt"}

# System chords. Each one leaves the target app, or ends an app or the session.
_BLOCKED_CHORDS = {
    (frozenset(mods), key)
    for mods, key in [
        (("cmd",), "tab"), (("cmd", "shift"), "tab"), (("cmd",), "`"),
        (("cmd",), "space"), (("ctrl",), "space"), (("cmd", "shift"), "space"),
        (("cmd", "ctrl"), "space"), (("cmd", "alt"), "space"),
        (("cmd",), "q"), (("cmd", "alt"), "q"), (("cmd", "shift"), "q"),
        (("cmd", "ctrl"), "q"), (("cmd", "alt", "shift"), "q"),
        (("cmd", "alt"), "escape"), (("cmd", "alt"), "esc"),
        (("cmd", "alt"), "h"),
        (("cmd", "shift"), "3"), (("cmd", "shift"), "4"), (("cmd", "shift"), "5"),
        (("ctrl",), "up"), (("ctrl",), "down"), (("ctrl",), "left"), (("ctrl",), "right"),
    ]
}


@dataclass
class Step:
    event: object
    route: str  # "pid" or "hid"
    label: str
    release: bool = False
    delay: float = 0.0


class Aborted(Refused):
    """The guard failed part way through a sequence."""

    def __init__(self, posted: int, reason: str):
        super().__init__(f"stopped after {posted} events: {reason}")
        self.posted = posted


def _source():
    return Quartz.CGEventSourceCreate(Quartz.kCGEventSourceStatePrivate)


def parse_chord(chord: str) -> tuple[int, int, str]:
    """Return (keycode, flags, canonical name) for a chord such as 'cmd+shift+s'. Refuse the rest."""
    parts = [part.strip().lower() for part in chord.split("+")]
    if chord.strip().endswith("+") and len(chord.strip()) > 1:
        raise Refused(f"key {chord!r} is not valid: write the plus key as 'shift+='.")
    *mods, key = parts
    unknown = [mod for mod in mods if mod not in _MODIFIERS]
    if unknown or key not in _KEYCODES:
        raise Refused(f"key {chord!r} is not supported. Unknown part: {unknown or key!r}.")
    canon = frozenset(_CANON.get(mod, mod) for mod in mods)
    if len(canon) == 4 or (canon, key) in _BLOCKED_CHORDS:
        raise Refused(f"key {chord!r} is blocked: it reaches outside the allowlisted app.")
    flags = 0
    for mod in mods:
        flags |= _MODIFIERS[mod]
    return _KEYCODES[key], flags, "+".join([*sorted(canon), key])


def build_key(chord: str, repeat: int = 1) -> list[Step]:
    if not 1 <= repeat <= 100:
        raise Refused("repeat must be from 1 to 100.")
    code, flags, name = parse_chord(chord)
    steps = []
    for _ in range(repeat):
        for down in (True, False):
            event = Quartz.CGEventCreateKeyboardEvent(_source(), code, down)
            Quartz.CGEventSetFlags(event, flags)
            steps.append(Step(event, "pid", f"key {name} {'down' if down else 'up'}", not down, 0.01))
    return steps


def _unicode_event(char: str, down: bool):
    event = Quartz.CGEventCreateKeyboardEvent(_source(), 0, down)
    Quartz.CGEventSetFlags(event, 0)
    Quartz.CGEventKeyboardSetUnicodeString(event, len(char.encode("utf-16-le")) // 2, char)
    return event


def build_type(text: str) -> list[Step]:
    if not text:
        raise Refused("text is empty.")
    if len(text) > MAX_TEXT_LENGTH:
        raise Refused(f"text is {len(text)} characters. The limit is {MAX_TEXT_LENGTH}.")
    steps = []
    for char in text:
        if char in "\r\n\t":
            code = _KEYCODES["tab"] if char == "\t" else _KEYCODES["return"]
            pair = [(Quartz.CGEventCreateKeyboardEvent(_source(), code, d), d) for d in (True, False)]
            for event, _ in pair:
                Quartz.CGEventSetFlags(event, 0)
        elif ord(char) < 32 or ord(char) == 127:
            raise Refused(f"control character {ord(char)} cannot be typed.")
        else:
            pair = [(_unicode_event(char, d), d) for d in (True, False)]
        for event, down in pair:
            steps.append(Step(event, "pid", f"type {char!r} {'down' if down else 'up'}", not down, 0.005))
    return steps


def read_back_typed(steps: list[Step]) -> str:
    """Rebuild the text from built events. dry_run and tests use this to check the events."""
    out = []
    for step in steps:
        if not step.release:
            length, chars = Quartz.CGEventKeyboardGetUnicodeString(step.event, 8, None, None)
            out.append(chars[:length] if length else "?")
    return "".join(out)


_BUTTONS = {
    "left": (Quartz.kCGEventLeftMouseDown, Quartz.kCGEventLeftMouseUp, Quartz.kCGMouseButtonLeft),
    "right": (Quartz.kCGEventRightMouseDown, Quartz.kCGEventRightMouseUp, Quartz.kCGMouseButtonRight),
    "middle": (Quartz.kCGEventOtherMouseDown, Quartz.kCGEventOtherMouseUp, Quartz.kCGMouseButtonCenter),
}


def _flags(modifiers: list[str] | None) -> int:
    flags = 0
    for mod in modifiers or []:
        if mod.lower() not in _MODIFIERS:
            raise Refused(f"modifier {mod!r} is not supported.")
        flags |= _MODIFIERS[mod.lower()]
    return flags


def build_click(
    x: float, y: float, button: str = "left", clicks: int = 1, modifiers: list[str] | None = None
) -> list[Step]:
    if button not in _BUTTONS:
        raise Refused(f"button {button!r} is not supported. Use left, right, or middle.")
    if not 1 <= clicks <= 3:
        raise Refused("clicks must be 1, 2, or 3.")
    down_type, up_type, code = _BUTTONS[button]
    point, flags = (x, y), _flags(modifiers)
    move = Quartz.CGEventCreateMouseEvent(_source(), Quartz.kCGEventMouseMoved, point, code)
    Quartz.CGEventSetFlags(move, flags)
    steps = [Step(move, "hid", f"move to {x:.0f},{y:.0f}", delay=0.03)]
    for count in range(1, clicks + 1):
        for kind, name, release in ((down_type, "down", False), (up_type, "up", True)):
            event = Quartz.CGEventCreateMouseEvent(_source(), kind, point, code)
            Quartz.CGEventSetIntegerValueField(event, Quartz.kCGMouseEventClickState, count)
            Quartz.CGEventSetFlags(event, flags)
            steps.append(Step(event, "hid", f"{button} {name} #{count} at {x:.0f},{y:.0f}", release, 0.03))
    return steps


def build_scroll(x: float, y: float, direction: str, amount: int) -> list[Step]:
    deltas = {"up": (1, 0), "down": (-1, 0), "left": (0, 1), "right": (0, -1)}
    if direction not in deltas:
        raise Refused(f"direction {direction!r} is not supported. Use up, down, left, or right.")
    if not 1 <= amount <= 50:
        raise Refused("amount must be from 1 to 50.")
    move = Quartz.CGEventCreateMouseEvent(
        _source(), Quartz.kCGEventMouseMoved, (x, y), Quartz.kCGMouseButtonLeft
    )
    wheel_y, wheel_x = deltas[direction]
    wheel = Quartz.CGEventCreateScrollWheelEvent(
        _source(), Quartz.kCGScrollEventUnitLine, 2, wheel_y * amount, wheel_x * amount
    )
    Quartz.CGEventSetLocation(wheel, (x, y))
    return [
        Step(move, "hid", f"move to {x:.0f},{y:.0f}", delay=0.03),
        Step(wheel, "hid", f"scroll {direction} {amount} at {x:.0f},{y:.0f}"),
    ]


def _post(step: Step, pid: int) -> None:
    """The only place in this package that sends an input event."""
    if step.route == "pid":
        Quartz.CGEventPostToPid(pid, step.event)
    else:
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, step.event)


def send(steps: list[Step], pid: int, guard: Callable[[], None]) -> int:
    """Run the guard before every event. A failed guard stops the run and sends only a release."""
    posted = 0
    for step in steps:
        try:
            guard()
        except Refused as refusal:
            # A release only lets go of a key or button this run already pressed.
            if step.release:
                _post(step, pid)
                posted += 1
            raise Aborted(posted, str(refusal)) from refusal
        _post(step, pid)
        posted += 1
        if step.delay:
            time.sleep(step.delay)
    return posted
