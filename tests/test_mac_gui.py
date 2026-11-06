"""Tests for mcp/mac-gui. They send no real input to any app.

Run: uv run --directory ~/model-500/mcp/mac-gui --frozen python ~/model-500/tests/test_mac_gui.py

- StdioProtocol starts the real server over stdio. Input tools only run with dry_run=True.
- Guards runs the real server code in-process, with the post and press functions replaced by
  recorders, so dry_run=False can be tested without any event leaving the process.
- FixtureReads opens its own throwaway window and only reads it. It never gets focus.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import Quartz
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from mac_gui import apps, audit, ax, capture, events, permissions, server, windows
from mac_gui.apps import Refused

REPO = Path(__file__).resolve().parents[1]
PROJECT = REPO / "mcp" / "mac-gui"
SOURCE = PROJECT / "src" / "mac_gui"
UV = shutil.which("uv") or str(Path.home() / ".local/bin/uv")
REKORDBOX = "com.pioneerdj.rekordboxdj"
INPUT_TOOLS = {"gui_ax_press", "gui_menu", "gui_click", "gui_type", "gui_key", "gui_scroll", "gui_activate"}
ALL_TOOLS = INPUT_TOOLS | {"gui_screenshot", "gui_ax_tree", "gui_status"}
BUNDLE_PATHS = {
    "com.pioneerdj.rekordboxdj": "/Applications/rekordbox 7/rekordbox.app",
    "com.AlphaTheta.RMX-IGNITE-SampleManager": "/Applications/RMX-IGNITE Sample Manager.app",
    "org.audacityteam.audacity4": "/Applications/Audacity 4.app",
}
DISALLOWED = ["Finder", "com.apple.finder", "com.mitchellh.ghostty", "Terminal", "", "rekordbox2",
              "com.pioneerdj.rekordboxdj.evil", "*", "com.apple.systempreferences"]


def input_calls(app: str) -> list[tuple[str, dict]]:
    return [
        ("gui_ax_press", {"app": app, "role": "AXButton", "title": "OK", "dry_run": True}),
        ("gui_menu", {"app": app, "path": ["File", "Import"], "dry_run": True}),
        ("gui_click", {"app": app, "x": 10, "y": 10, "space": "screen", "dry_run": True}),
        ("gui_type", {"app": app, "text": "hello", "dry_run": True}),
        ("gui_key", {"app": app, "keys": "return", "dry_run": True}),
        ("gui_scroll", {"app": app, "x": 10, "y": 10, "direction": "down", "space": "screen", "dry_run": True}),
        ("gui_activate", {"app": app, "dry_run": True}),
    ]


async def with_session(body):
    params = StdioServerParameters(
        command=UV, args=["--directory", str(PROJECT), "run", "--frozen", "mac-gui"]
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            return await body(session, init)


def text_of(result) -> str:
    return "\n".join(c.text for c in result.content if c.type == "text")


def payload(result) -> dict:
    return json.loads(text_of(result))


class StdioProtocol(unittest.TestCase):
    def test_tools_and_schemas(self):
        async def body(session, init):
            tools = (await session.list_tools()).tools
            names = {t.name for t in tools}
            self.assertEqual(names, ALL_TOOLS)
            for tool in tools:
                props = tool.inputSchema.get("properties", {})
                if tool.name in INPUT_TOOLS:
                    self.assertIn("dry_run", props, tool.name)
                for banned in ("force", "override", "bypass", "allow", "bundle_id", "pid", "unsafe"):
                    self.assertNotIn(banned, props, f"{tool.name} has an override-like argument")
            self.assertIn("Permissions at startup", init.instructions)

        asyncio.run(with_session(body))

    def test_status_reports_permissions(self):
        async def body(session, _):
            state = payload(await session.call_tool("gui_status", {}))
            self.assertIsInstance(state["accessibility"], bool)
            self.assertIsInstance(state["screen_recording"], bool)
            self.assertEqual(set(state["apps"]), set(apps.ALLOWED_APPS.values()))
            for line in state["missing"]:
                self.assertIn("System Settings > Privacy & Security >", line)

        asyncio.run(with_session(body))

    def test_disallowed_app_refused_by_every_tool(self):
        async def body(session, _):
            for name in DISALLOWED:
                calls = input_calls(name) + [
                    ("gui_screenshot", {"app": name}),
                    ("gui_ax_tree", {"app": name}),
                ]
                for tool, args in calls:
                    result = payload(await session.call_tool(tool, args))
                    self.assertFalse(result["ok"], f"{tool} {name}")
                    self.assertIn("not allowlisted", result["refused"])
                    self.assertEqual(result["events_posted"], 0)

        asyncio.run(with_session(body))

    def test_dry_run_on_allowlisted_app_posts_nothing_and_logs(self):
        before = audit.LOG_PATH.stat().st_size if audit.LOG_PATH.exists() else 0
        running = apps.running_pid(REKORDBOX) is not None

        async def body(session, _):
            for tool, args in input_calls("rekordbox"):
                result = payload(await session.call_tool(tool, args))
                if not result["ok"]:
                    # With rekordbox open, the sample path may not exist. That is still a clean refusal.
                    self.assertTrue(running, f"{tool}: {result}")
                    self.assertEqual(result["events_posted"], 0)
                    continue
                self.assertTrue(result["dry_run"], tool)
                self.assertEqual(result["events_posted"], 0, tool)
                self.assertTrue(result["would_send"], tool)
                if not running:
                    self.assertIn("rekordbox is not running.", result["would_refuse"], tool)

        asyncio.run(with_session(body))
        with audit.LOG_PATH.open(encoding="utf-8") as handle:
            handle.seek(before)
            entries = [json.loads(line) for line in handle]
        logged = {e["tool"] for e in entries if e["app"] == REKORDBOX and e["dry_run"]}
        self.assertLessEqual(INPUT_TOOLS if not running else set(), logged)
        self.assertFalse([e for e in entries if e["outcome"] in ("attempt", "sent")], "real input was logged")

    def test_blocked_paths_and_chords_refused_even_in_dry_run(self):
        calls = [
            ("gui_menu", {"app": "rekordbox", "path": ["Apple", "Restart…"], "dry_run": True}),
            ("gui_menu", {"app": "rekordbox", "path": ["rekordbox", "Services", "Anything"], "dry_run": True}),
            ("gui_menu", {"app": "rekordbox", "path": ["rekordbox", "Quit rekordbox"], "dry_run": True}),
            ("gui_menu", {"app": "rekordbox", "path": [], "dry_run": True}),
            ("gui_ax_press", {"app": "rekordbox", "role": "AXButton", "title": "Quit", "dry_run": True}),
            ("gui_key", {"app": "rekordbox", "keys": "cmd+q", "dry_run": True}),
            ("gui_key", {"app": "rekordbox", "keys": "cmd+tab", "dry_run": True}),
            ("gui_key", {"app": "rekordbox", "keys": "cmd+shift+space", "dry_run": True}),
            ("gui_key", {"app": "rekordbox", "keys": "ctrl+alt+cmd+shift+f15", "dry_run": True}),
            ("gui_key", {"app": "rekordbox", "keys": "fn", "dry_run": True}),
            ("gui_key", {"app": "rekordbox", "keys": "return", "repeat": 1000, "dry_run": True}),
            ("gui_type", {"app": "rekordbox", "text": "x" * 1001, "dry_run": True}),
            ("gui_type", {"app": "rekordbox", "text": "a\x1bb", "dry_run": True}),
            ("gui_click", {"app": "rekordbox", "x": 1, "y": 1, "space": "screen", "clicks": 9, "dry_run": True}),
        ]

        async def body(session, _):
            for tool, args in calls:
                result = payload(await session.call_tool(tool, args))
                self.assertFalse(result["ok"], f"{tool} {args}")
                self.assertEqual(result["events_posted"], 0)

        asyncio.run(with_session(body))

    def test_reads_on_running_allowlisted_apps(self):
        running = [b for b in apps.ALLOWED_APPS if apps.running_pid(b) is not None]
        if not running:
            self.skipTest("no allowlisted app is running, so real-target reads did not run")

        async def body(session, _):
            for bundle in running:
                tree = text_of(await session.call_tool("gui_ax_tree", {"app": bundle, "scope": "all"}))
                print(f"\n[real target] {bundle} tree: {len(tree)} chars; first line: {tree.splitlines()[0]}")
                shot = await session.call_tool("gui_screenshot", {"app": bundle})
                images = [c for c in shot.content if c.type == "image"]
                if not images:
                    print(f"[real target] {bundle} screenshot refused: {text_of(shot)}")
                    continue
                data = base64.b64decode(images[0].data)
                self.assertEqual(images[0].mimeType, "image/jpeg")
                self.assertLessEqual(max(jpeg_size(data)), capture.MAX_EDGE)
                print(f"[real target] {bundle} screenshot: {jpeg_size(data)}, {len(data)} bytes")

        asyncio.run(with_session(body))


def jpeg_size(data: bytes) -> tuple[int, int]:
    from Foundation import NSData

    source = Quartz.CGImageSourceCreateWithData(NSData.dataWithBytes_length_(data, len(data)), None)
    image = Quartz.CGImageSourceCreateImageAtIndex(source, 0, None)
    return Quartz.CGImageGetWidth(image), Quartz.CGImageGetHeight(image)


class Guards(unittest.TestCase):
    """dry_run=False is safe here: _post and ax.press are recorders, and raw posting raises."""

    def setUp(self):
        self.posted: list[str] = []
        self.pressed: list[object] = []
        self.front = True
        self.top_pid = 4242
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.log = Path(folder.name) / "actions.log"
        server._last_shot.clear()
        self.addCleanup(server._last_shot.clear)

        def forbidden(*_args, **_kwargs):
            raise AssertionError("a real event was about to be posted")

        def top_window(x, y):
            return windows.Window(1, self.top_pid, "Owner", "", 0, 0, 5000, 5000, 0, True)

        element = object()
        patches = [
            mock.patch.object(Quartz, "CGEventPost", forbidden),
            mock.patch.object(Quartz, "CGEventPostToPid", forbidden),
            mock.patch.object(ax, "AXUIElementPerformAction", forbidden),
            mock.patch.object(ax, "AXUIElementSetAttributeValue", forbidden),
            mock.patch.object(events, "_post", lambda step, pid: self.posted.append(step.label)),
            mock.patch.object(ax, "press", lambda e: self.pressed.append(e) or 0),
            mock.patch.object(audit, "LOG_PATH", self.log),
            mock.patch.object(apps, "running_pid", lambda bundle: 4242),
            mock.patch.object(apps, "is_frontmost", lambda bundle: self.front),
            mock.patch.object(apps, "frontmost_label", lambda: "com.other.app"),
            mock.patch.object(permissions, "accessibility_granted", lambda: True),
            mock.patch.object(windows, "window_at", top_window),
            mock.patch.object(ax, "find_elements", lambda pid, role, title: [element]),
            mock.patch.object(ax, "supports_press", lambda e: True),
            mock.patch.object(ax, "is_enabled", lambda e: True),
            mock.patch.object(ax, "describe_element", lambda e: "AXButton"),
            mock.patch.object(ax, "resolve_menu", lambda pid, path: ax.MenuTarget(element, path, True)),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def real_calls(self, app="rekordbox"):
        return [
            (server.gui_ax_press, dict(app=app, role="AXButton", title="OK")),
            (server.gui_menu, dict(app=app, path=["File", "Import"])),
            (server.gui_click, dict(app=app, x=10, y=10, space="screen")),
            (server.gui_type, dict(app=app, text="hello")),
            (server.gui_key, dict(app=app, keys="return")),
            (server.gui_scroll, dict(app=app, x=10, y=10, direction="down", space="screen")),
        ]

    def assert_no_output(self):
        self.assertEqual(self.posted, [])
        self.assertEqual(self.pressed, [])

    def test_disallowed_app_real_mode_sends_nothing(self):
        for fn, kwargs in self.real_calls("com.apple.finder"):
            result = json.loads(fn(**kwargs))
            self.assertFalse(result["ok"])
            self.assertIn("not allowlisted", result["refused"])
        self.assert_no_output()

    def test_not_frontmost_real_mode_sends_nothing(self):
        self.front = False
        for fn, kwargs in self.real_calls():
            result = json.loads(fn(**kwargs))
            self.assertFalse(result["ok"], fn.__name__)
            self.assertIn("not frontmost", result["refused"])
        self.assert_no_output()

    def test_dry_run_sends_nothing_even_when_all_checks_pass(self):
        for fn, kwargs in self.real_calls():
            result = json.loads(fn(**kwargs, dry_run=True))
            self.assertTrue(result["ok"], fn.__name__)
            self.assertEqual(result["would_refuse"], [])
            self.assertEqual(result["events_posted"], 0)
        self.assert_no_output()

    def test_all_checks_pass_reaches_the_recorders(self):
        for fn, kwargs in self.real_calls():
            self.assertTrue(json.loads(fn(**kwargs))["ok"], fn.__name__)
        self.assertEqual(len(self.pressed), 2)
        self.assertGreater(len(self.posted), 0)

    def test_frontmost_lost_during_typing_stops_input(self):
        calls = [0]

        def flips(bundle):
            calls[0] += 1
            return calls[0] <= 4  # one planning check, then 3 event checks pass

        with mock.patch.object(apps, "is_frontmost", flips):
            result = json.loads(server.gui_type("rekordbox", "abcdef"))
        self.assertFalse(result["ok"])
        self.assertIn("stopped after", result["refused"])
        # Down a, up a, down b, then the guard fails on up b. That release goes out, and nothing else.
        self.assertEqual(result["events_posted"], 4)
        self.assertEqual(len(self.posted), 4)
        self.assertIn("up", self.posted[-1])

    def test_frontmost_checked_before_every_event(self):
        calls = [0]

        def counts(bundle):
            calls[0] += 1
            return True

        with mock.patch.object(apps, "is_frontmost", counts):
            server.gui_key("rekordbox", "return", repeat=3)
        self.assertEqual(calls[0], 1 + 6)

    def test_frontmost_lost_before_ax_press_stops_it(self):
        calls = [0]

        def flips(bundle):
            calls[0] += 1
            return calls[0] <= 1

        with mock.patch.object(apps, "is_frontmost", flips):
            result = json.loads(server.gui_menu("rekordbox", ["File", "Import"]))
        self.assertFalse(result["ok"])
        self.assert_no_output()

    def test_click_over_another_app_is_refused(self):
        self.top_pid = 999
        result = json.loads(server.gui_click("rekordbox", 10, 10, space="screen"))
        self.assertFalse(result["ok"])
        self.assertIn("not the target app", result["refused"])
        self.assert_no_output()

    def test_image_space_requires_a_fresh_screenshot(self):
        self.assertIn("needs a gui_screenshot", json.loads(server.gui_click("rekordbox", 5, 5))["refused"])
        bundle = REKORDBOX
        server._last_shot[bundle] = server.Shot(7, (100.0, 100.0, 1000.0, 500.0), 640, 320)
        window = windows.Window(7, 4242, "rb", "", 100, 100, 1000, 500, 0, True)
        with mock.patch.object(windows, "list_app_windows", lambda pid: [window]):
            ok = json.loads(server.gui_click("rekordbox", 320, 160, dry_run=True))
            self.assertEqual(ok["screen_point"], [600.0, 350.0])
            outside = json.loads(server.gui_click("rekordbox", 900, 10, dry_run=True))
            self.assertIn("outside", outside["refused"])
        moved = windows.Window(7, 4242, "rb", "", 150, 100, 1000, 500, 0, True)
        with mock.patch.object(windows, "list_app_windows", lambda pid: [moved]):
            self.assertIn("moved or closed", json.loads(server.gui_click("rekordbox", 5, 5))["refused"])
        self.assert_no_output()

    def test_real_input_writes_a_log_line_first_and_fails_closed(self):
        with mock.patch.object(audit, "LOG_PATH", Path("/dev/null/cannot/write.log")):
            with self.assertRaises(OSError):
                server.gui_key("rekordbox", "return")
        self.assert_no_output()
        server.gui_key("rekordbox", "return")
        outcomes = [json.loads(line)["outcome"] for line in self.log.read_text().splitlines()]
        self.assertEqual(outcomes[-2:], ["attempt", "sent"])


class Allowlist(unittest.TestCase):
    def test_allowlist_matches_info_plist(self):
        self.assertEqual(set(apps.ALLOWED_APPS), set(BUNDLE_PATHS))
        for bundle, path in BUNDLE_PATHS.items():
            if not os.path.isdir(path):  # The vendor apps are optional. CI runners do not have them.
                continue
            with open(f"{path}/Contents/Info.plist", "rb") as handle:
                self.assertEqual(plistlib.load(handle)["CFBundleIdentifier"], bundle)

    def test_allowlist_is_immutable_and_has_no_environment_override(self):
        with self.assertRaises(TypeError):
            apps.ALLOWED_APPS["com.apple.finder"] = "Finder"  # type: ignore[index]
        with mock.patch.dict(os.environ, {"MAC_GUI_ALLOW": "com.apple.finder"}):
            with self.assertRaises(Refused):
                apps.resolve_app("com.apple.finder")

    def test_resolve_app_names(self):
        for name in ("rekordbox", " REKORDBOX ", REKORDBOX):
            self.assertEqual(apps.resolve_app(name), REKORDBOX)
        self.assertEqual(apps.resolve_app("audacity"), "org.audacityteam.audacity4")
        self.assertEqual(apps.resolve_app("Sample Manager"), "com.AlphaTheta.RMX-IGNITE-SampleManager")


class SourceInvariants(unittest.TestCase):
    def source(self) -> dict[str, str]:
        return {p.name: p.read_text() for p in SOURCE.glob("*.py")}

    def call_sites(self, pattern: str) -> list[str]:
        return [name for name, text in self.source().items() for _ in re.findall(pattern, text)]

    def test_one_post_site_for_each_event_route(self):
        self.assertEqual(self.call_sites(r"\.CGEventPost\("), ["events.py"])
        self.assertEqual(self.call_sites(r"\.CGEventPostToPid\("), ["events.py"])
        self.assertEqual(self.call_sites(r"AXUIElementPerformAction\("), ["ax.py"])

    def test_no_tcc_prompts_stale_lookups_or_overrides(self):
        for banned in ("CGRequestScreenCaptureAccess", "AXIsProcessTrustedWithOptions", "NSWorkspace.shared",
                       "os.environ", "getenv", "osascript", "tccutil", "/Library/Pioneer"):
            self.assertEqual(self.call_sites(re.escape(banned)), [], banned)


class EventBuilders(unittest.TestCase):
    """Events are built and read back. None of them are posted."""

    def test_typed_text_round_trips(self):
        steps = events.build_type("Set A é\U0001F600")
        self.assertEqual(events.read_back_typed(steps), "Set A é\U0001F600")
        self.assertEqual({s.route for s in steps}, {"pid"})

    def test_chord_flags_and_keycode(self):
        steps = events.build_key("cmd+shift+s")
        code = Quartz.CGEventGetIntegerValueField(steps[0].event, Quartz.kCGKeyboardEventKeycode)
        self.assertEqual(code, 1)
        flags = Quartz.CGEventGetFlags(steps[0].event)
        self.assertTrue(flags & Quartz.kCGEventFlagMaskCommand and flags & Quartz.kCGEventFlagMaskShift)
        self.assertEqual([s.release for s in steps], [False, True])

    def test_double_click_sequence(self):
        steps = events.build_click(123, 456, "left", 2)
        self.assertEqual(len(steps), 5)
        states = [Quartz.CGEventGetIntegerValueField(s.event, Quartz.kCGMouseEventClickState) for s in steps[1:]]
        self.assertEqual(states, [1, 1, 2, 2])
        location = Quartz.CGEventGetLocation(steps[1].event)
        self.assertEqual((location.x, location.y), (123, 456))
        self.assertEqual(Quartz.CGEventGetType(steps[1].event), Quartz.kCGEventLeftMouseDown)

    def test_scroll_direction_and_location(self):
        steps = events.build_scroll(50, 60, "down", 4)
        wheel = steps[-1].event
        self.assertEqual(Quartz.CGEventGetIntegerValueField(wheel, Quartz.kCGScrollWheelEventDeltaAxis1), -4)
        self.assertEqual(Quartz.CGEventGetLocation(wheel).x, 50)


FIXTURE = """
import AppKit
app = AppKit.NSApplication.sharedApplication()
# Prohibited, not Accessory: an Accessory app took focus from the user when app.run() started.
app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyProhibited)
bar = AppKit.NSMenu.alloc().init()
top = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Fixture", None, "")
sub = AppKit.NSMenu.alloc().initWithTitle_("Fixture")
sub.addItemWithTitle_action_keyEquivalent_("Do Nothing…", None, "")
top.setSubmenu_(sub)
bar.addItem_(top)
top2 = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Second", None, "")
sub2 = AppKit.NSMenu.alloc().initWithTitle_("Second")
sub2.addItemWithTitle_action_keyEquivalent_("Second Item", None, "")
sub2.addItemWithTitle_action_keyEquivalent_("Do Nothing\u2026", None, "")
top2.setSubmenu_(sub2)
bar.addItem_(top2)
app.setMainMenu_(bar)
window = AppKit.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
    ((60, 60), (1400, 900)), AppKit.NSWindowStyleMaskTitled, AppKit.NSBackingStoreBuffered, False)
window.setTitle_("mac-gui test fixture")
button = AppKit.NSButton.alloc().initWithFrame_(((20, 20), (160, 32)))
button.setTitle_("Fixture Button")
window.contentView().addSubview_(button)
window.orderBack_(None)
print("ready", flush=True)
app.run()
"""


def front_pid() -> int | None:
    asn = subprocess.run(["/usr/bin/lsappinfo", "front"], capture_output=True, text=True).stdout.strip()
    info = subprocess.run(["/usr/bin/lsappinfo", "info", asn], capture_output=True, text=True).stdout
    match = re.search(r"\bpid = (\d+)", info)
    return int(match.group(1)) if match else None


class FixtureReads(unittest.TestCase):
    """Read paths against a window this test owns. Nothing here presses or clicks."""

    @classmethod
    def setUpClass(cls):
        cls.process = subprocess.Popen(
            [sys.executable, "-c", FIXTURE], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
        )
        cls.process.stdout.readline()
        cls.fixture_was_front = False
        for _ in range(15):
            cls.fixture_was_front |= front_pid() == cls.process.pid
            cls.windows = windows.list_app_windows(cls.process.pid)
            time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.process.terminate()
        cls.process.wait(timeout=5)
        cls.process.stdout.close()

    def test_window_listing_only_returns_this_process(self):
        self.assertTrue(self.windows)
        self.assertEqual({w.pid for w in self.windows}, {self.process.pid})

    @unittest.skipUnless(permissions.screen_recording_granted(), "Screen Recording is not granted")
    def test_capture_is_jpeg_and_downscaled(self):
        data, width, height = capture.capture_window(self.windows[0].id)
        self.assertEqual(data[:2], b"\xff\xd8")
        self.assertEqual((width, height), jpeg_size(data))
        self.assertLessEqual(max(width, height), capture.MAX_EDGE)
        window = self.windows[0]
        self.assertAlmostEqual(width / height, window.width / window.height, delta=0.03)
        small, w2, h2 = capture.capture_window(window.id, max_edge=200)
        self.assertEqual(max(w2, h2), 200)
        print(f"\n[fixture] window {window.width:.0f}x{window.height:.0f} -> {width}x{height}, {len(data)} bytes")

    @unittest.skipUnless(permissions.accessibility_granted(), "Accessibility is not granted")
    def test_ax_tree_finds_window_and_button(self):
        tree = ax.read_tree(self.process.pid, "windows", geometry=True)
        joined = "\n".join(tree["lines"])
        self.assertIn('AXWindow "mac-gui test fixture"', joined)
        self.assertIn('AXButton "Fixture Button"', joined)
        self.assertRegex(joined, r'AXButton "Fixture Button" @-?\d+,-?\d+ \d+x\d+')
        matches = ax.find_elements(self.process.pid, "button", "fixture button")
        self.assertEqual(len(matches), 1)
        self.assertTrue(ax.supports_press(matches[0]))
        limited = ax.read_tree(self.process.pid, "windows", max_nodes=1)
        self.assertEqual(limited["nodes"], 1)
        self.assertGreater(limited["truncated"], 0)

    @unittest.skipUnless(permissions.accessibility_granted(), "Accessibility is not granted")
    def test_menu_walk_is_read_only_and_hides_apple(self):
        tree = "\n".join(ax.read_tree(self.process.pid, "menubar")["lines"])
        self.assertNotIn('"Apple"', tree)
        target = ax.resolve_menu(self.process.pid, ["Second", "Second Item"])
        self.assertEqual(target.path, ["Second", "Second Item"])
        ellipsis = ax.resolve_menu(self.process.pid, ["Second", "do nothing"])
        self.assertEqual(ax.attr(ellipsis.element, "AXTitle"), "Do Nothing…")
        with self.assertRaisesRegex(Refused, "not found"):
            ax.resolve_menu(self.process.pid, ["Second", "Missing"])

    def test_fixture_never_takes_focus(self):
        self.assertFalse(self.fixture_was_front)
        self.assertNotEqual(front_pid(), self.process.pid)

    def test_hit_test_ignores_points_off_every_display(self):
        self.assertIsNone(windows.window_at(-1_000_000, -1_000_000))


if __name__ == "__main__":
    unittest.main(verbosity=2)
