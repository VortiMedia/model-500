#!/usr/bin/env python3
"""Test ignite-mcp over real stdio JSON-RPC. Run: python3 tests/test_ignite_mcp.py

Files go to IGNITE_TEST_SCRATCH, or to a new temp folder. Set IGNITE_TEST_REAL_USB to a volume path to add a
read-only check of that volume. The tool never writes to it.
"""

import json
import os
import shutil
import struct
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SERVER_DIR = REPO / "mcp/ignite-mcp"
UV = shutil.which("uv") or str(Path.home() / ".local/bin/uv")
# The vendor app is optional. CI runners and most contributors do not have it.
APP = Path("/Applications/RMX-IGNITE Sample Manager.app")
SCRATCH = Path(os.environ.get("IGNITE_TEST_SCRATCH") or tempfile.mkdtemp(prefix="ignite-test-"))
EXPECTED_TOOLS = {
    "ignite_status",
    "ignite_list_library",
    "ignite_validate_sample",
    "ignite_prepare_sample",
    "ignite_read_usb",
    "ignite_gui_steps",
}


def tree_state(root: Path) -> list[tuple[str, int, int]]:
    rows = []
    for path in sorted(root.rglob("*")):
        stat = path.lstat()
        rows.append((str(path.relative_to(root)), stat.st_size, stat.st_mtime_ns))
    return rows


def tone(path: Path, seconds: float, *codec: str) -> Path:
    command = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}"]
    subprocess.run([*command, *codec, str(path)], check=True, stdin=subprocess.DEVNULL)
    return path


def wav_format_tag(path: Path) -> int:
    with path.open("rb") as stream:
        assert stream.read(12)[8:] == b"WAVE"
        while header := stream.read(8):
            tag, size = struct.unpack("<4sI", header)
            if tag == b"fmt ":
                return struct.unpack("<H", stream.read(2))[0]
            stream.seek(size + size % 2, 1)
    raise AssertionError("WAV has no fmt chunk")


class Client:
    def __init__(self) -> None:
        self.proc = subprocess.Popen(
            [UV, "run", "--directory", str(SERVER_DIR), "python", "server.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        self.next_id = 0

    def send(self, payload: dict) -> None:
        self.proc.stdin.write(json.dumps({"jsonrpc": "2.0", **payload}) + "\n")
        self.proc.stdin.flush()

    def request(self, method: str, params: dict) -> dict:
        self.next_id += 1
        self.send({"id": self.next_id, "method": method, "params": params})
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError("Server closed stdout")
            message = json.loads(line)
            if message.get("id") == self.next_id:
                if "error" in message:
                    raise RuntimeError(message["error"])
                return message["result"]

    def call(self, tool: str, **arguments) -> dict:
        result = self.request("tools/call", {"name": tool, "arguments": arguments})
        if result.get("isError"):
            raise RuntimeError(result)
        return json.loads(result["content"][0]["text"])

    def close(self) -> None:
        self.proc.stdin.close()
        self.proc.wait(timeout=10)


class IgniteMcpTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        cls.audio = SCRATCH / "audio"
        cls.audio.mkdir(exist_ok=True)
        cls.good = tone(cls.audio / "good.wav", 3, "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le")
        cls.long = tone(cls.audio / "long.wav", 17, "-ar", "48000", "-ac", "2", "-c:a", "pcm_s24le")
        cls.low_rate = tone(cls.audio / "low_rate.wav", 1, "-ar", "22050", "-c:a", "pcm_s16le")
        cls.float32 = tone(cls.audio / "float32.wav", 1, "-ar", "48000", "-c:a", "pcm_f32le")
        cls.mp3 = tone(cls.audio / "drop.mp3", 2, "-ar", "44100")
        cls.aiff = tone(cls.audio / "good.aiff", 1, "-ar", "96000", "-c:a", "pcm_s24be")
        cls.client = Client()
        init = cls.client.request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "ignite-test", "version": "1"},
            },
        )
        cls.server_name = init["serverInfo"]["name"]
        cls.client.send({"method": "notifications/initialized"})

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.close()

    def test_tools_listed(self) -> None:
        self.assertEqual(self.server_name, "ignite")
        tools = self.client.request("tools/list", {})["tools"]
        self.assertEqual({tool["name"] for tool in tools}, EXPECTED_TOOLS)

    def test_status(self) -> None:
        status = self.client.call("ignite_status")
        self.assertEqual(status["installed"], APP.is_dir())
        if APP.is_dir():
            self.assertIsInstance(status["version"], str)
        else:
            self.assertIsNone(status["version"])
        self.assertIsInstance(status["running"], bool)
        self.assertIsInstance(status["usb_volumes"], list)

    def test_validate_pass_and_each_failure(self) -> None:
        self.assertTrue(self.client.call("ignite_validate_sample", path=str(self.good))["pass"])
        self.assertTrue(self.client.call("ignite_validate_sample", path=str(self.aiff))["pass"])
        cases = {
            self.long: "over the 16 s limit",
            self.low_rate: "Sample rate 22050",
            self.float32: "Codec pcm_f32le",
            self.mp3: "Extension .mp3",
        }
        for path, expected in cases.items():
            result = self.client.call("ignite_validate_sample", path=str(path))
            self.assertFalse(result["pass"], path)
            self.assertIn(expected, result["reason"])
        self.assertTrue(
            self.client.call("ignite_validate_sample", path=str(self.mp3))["sample_manager_input"]["pass"]
        )

    def test_validate_bank_budget(self) -> None:
        result = self.client.call("ignite_validate_sample", path=str(self.good), bank_used_seconds=14.0)
        self.assertFalse(result["pass"])
        self.assertIn("bank limit", result["reason"])

    def test_validate_missing_file(self) -> None:
        result = self.client.call("ignite_validate_sample", path=str(SCRATCH / "absent.wav"))
        self.assertFalse(result["pass"])

    def test_prepare_trim_normalize_convert(self) -> None:
        out = SCRATCH / "staging"
        before = self.good.read_bytes()
        result = self.client.call(
            "ignite_prepare_sample",
            input_path=str(self.good),
            name="air horn! #1",
            output_dir=str(out),
            start_seconds=0.5,
            end_seconds=2.5,
            overwrite=True,
        )
        self.assertTrue(result["ok"], result)
        output = Path(result["output"])
        self.assertEqual(output.name, "AIR HORN 1.wav")
        props = result["validation"]["properties"]
        self.assertEqual(
            (props["codec"], props["sample_rate"], props["bit_depth"], props["channels"]),
            ("pcm_s24le", 96000, 24, 2),
        )
        self.assertAlmostEqual(props["seconds"], 2.0, delta=0.01)
        self.assertEqual(wav_format_tag(output), 1)
        self.assertTrue(self.client.call("ignite_validate_sample", path=str(output))["pass"])
        peak = subprocess.run(
            ["ffmpeg", "-hide_banner", "-nostdin", "-i", str(output), "-af", "volumedetect", "-f", "null", "-"],
            capture_output=True,
            text=True,
        ).stderr
        self.assertIn("max_volume: -1.0 dB", peak)
        self.assertEqual(self.good.read_bytes(), before)
        self.assertTrue(result["import_is_gui_only"])

    def test_prepare_peak_target_for_stereo_input(self) -> None:
        result = self.client.call(
            "ignite_prepare_sample",
            input_path=str(self.long),
            name="stereo in",
            output_dir=str(SCRATCH / "staging"),
            end_seconds=2.0,
            peak_db=-3.0,
            overwrite=True,
        )
        self.assertTrue(result["ok"], result)
        self.assertEqual(wav_format_tag(Path(result["output"])), 1)
        peak = subprocess.run(
            ["ffmpeg", "-hide_banner", "-nostdin", "-i", result["output"], "-af", "volumedetect", "-f", "null", "-"],
            capture_output=True,
            text=True,
        ).stderr
        self.assertIn("max_volume: -3.0 dB", peak)

    def test_prepare_classic_header_preserves_pcm(self) -> None:
        source = tone(SCRATCH / "pcm24.wav", 1, "-ar", "96000", "-ac", "2", "-c:a", "pcm_s24le")
        expected = subprocess.check_output(
            ["ffmpeg", "-v", "error", "-i", str(source), "-f", "s24le", "-c:a", "pcm_s24le", "-"]
        )
        result = self.client.call(
            "ignite_prepare_sample", input_path=str(source), name="pcm frames",
            output_dir=str(SCRATCH / "staging"), normalize="none", fade_out_ms=0,
        )
        self.assertTrue(result["ok"], result)
        output = Path(result["output"])
        self.assertEqual(wav_format_tag(output), 1)
        with wave.open(str(output), "rb") as reader:
            self.assertEqual(reader.readframes(reader.getnframes()), expected)

    def test_prepare_refusals_write_nothing(self) -> None:
        out = SCRATCH / "refused"
        long_result = self.client.call(
            "ignite_prepare_sample", input_path=str(self.long), name="long", output_dir=str(out)
        )
        self.assertFalse(long_result["ok"])
        self.assertIn("over 16 s", long_result["reason"])
        self.assertFalse(out.exists())

        dry = self.client.call(
            "ignite_prepare_sample", input_path=str(self.good), name="dry", output_dir=str(out), dry_run=True
        )
        self.assertTrue(dry["ok"])
        self.assertFalse(dry["output_written"])
        self.assertFalse(out.exists())

        # dry_run guards these two calls: even a broken refusal check could not write here.
        for blocked in ("/Volumes/__m500_absent__/x", str(Path.home() / "Library/Pioneer/x")):
            result = self.client.call(
                "ignite_prepare_sample",
                input_path=str(self.good),
                name="blocked",
                output_dir=blocked,
                dry_run=True,
            )
            self.assertFalse(result["ok"], blocked)
            self.assertIn("Refused", result["reason"])

    def test_prepare_will_not_overwrite_by_default(self) -> None:
        out = SCRATCH / "no_overwrite"
        args = dict(input_path=str(self.good), name="once", output_dir=str(out))
        self.assertTrue(self.client.call("ignite_prepare_sample", **args, overwrite=True)["ok"])
        again = self.client.call("ignite_prepare_sample", **args)
        self.assertFalse(again["ok"])
        self.assertIn("exists", again["reason"])

    def make_library(self, root: Path, key: str) -> None:
        empty = {
            "file_size": 0, "bpm": 0, "sample_num": 0, "start_sample": 0, "end_sample": 0, "time_length": 0.0,
            "beat_length": 0.0, "gain": 0.0, "channel_num": 0, "is_loop": 0, "is_dubkick_mode": 0,
            "file_name": "", "display_file_name": "", "original_file_name": "", "slot_name": "",
        }  # fmt: skip
        banks = [
            {
                "bank_number": b,
                "bank_name": "",
                "slot": [{**empty, "slot_number": s} for s in range(4)],
            }
            for b in range(15)
        ]
        banks[2]["bank_name"] = "DROPS"
        banks[2]["slot"][1].update(file_name="HORN.wav", slot_name="HORN", time_length=17.0, gain=-3.0)
        root.mkdir(parents=True, exist_ok=True)
        path = root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"favorite": 2, "bank": banks}))

    def test_library_fixture_and_real_read(self) -> None:
        root = SCRATCH / "support_fixture"
        self.make_library(root, "model/model.json")
        samples = root / "model/samples"
        samples.mkdir(parents=True, exist_ok=True)
        shutil.copy(self.good, samples / "HORN.wav")
        result = self.client.call("ignite_list_library", support_dir=str(root), include_factory=True)
        self.assertTrue(result["ok"])
        self.assertEqual(result["bank_count"], 15)
        self.assertEqual(result["favorite_bank"], 3)
        bank = result["used_banks"][0]
        self.assertEqual((bank["bank"], bank["name"]), (3, "DROPS"))
        self.assertTrue(bank["over_16_seconds"])
        self.assertEqual(bank["slots"][0]["slot"], "B")
        self.assertTrue(bank["slots"][0]["sample_found"])
        if APP.is_dir():
            self.assertTrue(result["factory_samples"])
        else:
            self.assertEqual(result["factory_samples"], [])

        real = self.client.call("ignite_list_library")
        self.assertIn("ok", real)

        absent = self.client.call("ignite_list_library", support_dir=str(SCRATCH / "absent"))
        self.assertFalse(absent["ok"])

    def test_read_usb_fixture_is_read_only(self) -> None:
        root = SCRATCH / "usb_fixture"
        self.make_library(root, "AlphaTheta/RMX-IGNITE/RMX-IGNITESETTINGS.json")
        samples = root / "AlphaTheta/RMX-IGNITE/03"
        samples.mkdir(parents=True, exist_ok=True)
        shutil.copy(self.good, samples / "HORN.wav")
        before = tree_state(root)
        result = self.client.call("ignite_read_usb", volume_path=str(root))
        self.assertEqual(tree_state(root), before)
        self.assertTrue(result["has_ignite_export"])
        self.assertTrue(result["settings_parsed"])
        self.assertEqual(result["unit_audio_files"], 1)
        self.assertEqual(result["export_banks"]["used_banks"][0]["name"], "DROPS")
        self.assertTrue(result["export_banks"]["used_banks"][0]["slots"][0]["sample_found"])

    def test_read_usb_uses_one_based_bank_folders(self) -> None:
        root = SCRATCH / "usb_bank_boundaries"
        key = "AlphaTheta/RMX-IGNITE/RMX-IGNITESETTINGS.json"
        self.make_library(root, key)
        path = root / key
        model = json.loads(path.read_text())
        model["bank"][2]["bank_name"] = ""
        model["bank"][2]["slot"][1].update(file_name="", slot_name="")
        for index in (0, 14):
            model["bank"][index]["bank_name"] = f"BANK {index + 1}"
            model["bank"][index]["slot"][0].update(file_name="HORN.wav", time_length=3.0)
        path.write_text(json.dumps(model))
        samples = root / "AlphaTheta/RMX-IGNITE/01"
        samples.mkdir(parents=True)
        shutil.copy(self.good, samples / "HORN.wav")
        before = tree_state(root)
        result = self.client.call("ignite_read_usb", volume_path=str(root))
        banks = result["export_banks"]["used_banks"]
        self.assertEqual([b["bank"] for b in banks], [1, 15])
        self.assertTrue(banks[0]["slots"][0]["sample_found"])
        self.assertFalse(banks[1]["slots"][0]["sample_found"])
        self.assertEqual(tree_state(root), before)
        samples = root / "AlphaTheta/RMX-IGNITE/15"
        samples.mkdir()
        shutil.copy(self.good, samples / "HORN.wav")
        before = tree_state(root)
        result = self.client.call("ignite_read_usb", volume_path=str(root))
        self.assertTrue(result["export_banks"]["used_banks"][-1]["slots"][0]["sample_found"])
        self.assertEqual(tree_state(root), before)

    def test_read_usb_missing_path(self) -> None:
        self.assertFalse(self.client.call("ignite_read_usb", volume_path=str(SCRATCH / "absent"))["ok"])

    @unittest.skipUnless(os.environ.get("IGNITE_TEST_REAL_USB"), "IGNITE_TEST_REAL_USB is not set")
    def test_read_real_volume(self) -> None:
        volume = Path(os.environ["IGNITE_TEST_REAL_USB"])
        result = self.client.call("ignite_read_usb", volume_path=str(volume), max_files=200)
        self.assertTrue(result["ok"])
        self.assertTrue(result["volume"]["filesystem_type"])

    def test_gui_steps(self) -> None:
        for action in ("assign", "export", "import", "backup", "restore", "unit_load"):
            result = self.client.call("ignite_gui_steps", action=action)
            self.assertTrue(result["gui_only"])
            self.assertTrue(result["steps"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
