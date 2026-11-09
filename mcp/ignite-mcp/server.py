"""MCP server for AlphaTheta RMX-IGNITE Sample Manager.

Read-only except ignite_prepare_sample, which writes one new WAV to a staging folder.
See NOTES.md for what is proven and what is only inferred.
"""

from __future__ import annotations

import json
import os
import plistlib
import re
import shutil
import struct
import subprocess
import wave
from pathlib import Path
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

APP_PATH = Path("/Applications/RMX-IGNITE Sample Manager.app")
APP_PROCESS = "RMX-IGNITE Sample Manager"
SUPPORT_DIR = Path.home() / "Library/Application Support/com.AlphaTheta.RMX-IGNITE-SampleManager"
DEFAULT_STAGING = Path.home() / "Music/Samples/Drops"
USB_ROOT = "AlphaTheta/RMX-IGNITE"
USB_SETTINGS = "RMX-IGNITESETTINGS.json"

UNIT_EXTENSIONS = {".wav", ".aif", ".aiff"}
UNIT_CODECS = {"pcm_s16le", "pcm_s24le", "pcm_s16be", "pcm_s24be"}
UNIT_DEPTHS = {16, 24}
UNIT_RATES = {44100, 48000, 88200, 96000}
UNIT_MAX_SECONDS = 16.0
BANK_MAX_SECONDS = 16.0
APP_EXTENSIONS = {".wav", ".aif", ".aiff", ".mp3", ".mp4", ".m4a", ".aac", ".flac", ".fla"}
APP_MIN_SECONDS = 0.010
APP_MAX_SECONDS = 1800.0
UNIT_FILESYSTEMS = {"msdos", "exfat", "hfs"}
PREPARE_RATE = 96000
PREPARE_DEPTH = 24
NAME_MAX = 24
USB_SCAN_LIMIT = 2000
LAYOUT_NOTE = (
    "USB layout was checked against a native Sample Manager 1.0.0.0336 export. "
    "Bank folders are one-based; hardware playback is not verified."
)
UNIT_CAVEAT = "The unit manual says some files in supported formats can still fail to play."

GUI_STEPS: dict[str, list[str]] = {
    "assign": [
        "Open RMX-IGNITE Sample Manager.",
        "In BANKS, click the target bank row (1 to 15).",
        "Drag the prepared WAV from Finder or SAMPLE BROWSE onto slot A, B, C, or D in BANK EDIT.",
        "In SLOT EDIT, set Start, End, and GAIN (-18 to +9 dB).",
        "For Loop, use slot C or D, and enter BPM (40.00 to 999.99) and BEAT first.",
        "Check that the BANK EDIT Total is 16 seconds or less.",
    ],
    "export": [
        "Make sure each bank to export is in BANKS. BANK COLLECTION banks do not export.",
        "Click EXPORT, or use the in-window File menu > Export.",
        "In the Export dialog, select the drive by name. Read the name before you continue.",
        "Click OK. Do not remove the drive until the process ends.",
    ],
    "import": [
        "This overwrites ALL existing BANK and SLOT data. Do File > Backup first.",
        "Use the in-window File menu > Import and select the drive.",
    ],
    "backup": [
        "Use the in-window File menu > Backup, enter a file name, and click Save.",
        "The ZIP is for this app only. The unit cannot load it.",
    ],
    "restore": [
        "This overwrites ALL existing BANK, SLOT, and BANK COLLECTION data.",
        "Use the in-window File menu > Restore, select the ZIP, and click Open.",
    ],
    "unit_load": [
        "Connect the USB drive to the [USB for SAMPLER] port or a PRO DJ LINK player.",
        "Press [BROWSE/UTILITY]. Select [BANK SELECT] > [USER], then the storage media.",
        "Select the bank, then select [LOAD].",
        "Before removal: select [USB STOP], press and hold the multi encoder, and wait for the pop-up to end.",
    ],
}

mcp = FastMCP("ignite")


def _run(args: list[str], timeout: float = 60.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL
    )


def _app_running() -> bool:
    return _run(["pgrep", "-x", APP_PROCESS], timeout=10).returncode == 0


def _app_version() -> str | None:
    try:
        with (APP_PATH / "Contents/Info.plist").open("rb") as handle:
            return plistlib.load(handle).get("CFBundleShortVersionString")
    except OSError:
        return None


def _volume_info(path: Path) -> dict[str, Any]:
    result = _run(["diskutil", "info", "-plist", str(path)], timeout=20)
    if result.returncode != 0:
        return {}
    try:
        info = plistlib.loads(result.stdout.encode())
    except plistlib.InvalidFileException:
        return {}
    fs_type = info.get("FilesystemType")
    return {
        "filesystem": info.get("FilesystemName") or fs_type,
        "filesystem_type": fs_type,
        "filesystem_supported_by_unit": fs_type in UNIT_FILESYSTEMS if fs_type else None,
        "external": info.get("Internal") is False,
        "disk_image": info.get("BusProtocol") == "Disk Image",
        "bus": info.get("BusProtocol"),
        "free_bytes": info.get("FreeSpace") or info.get("APFSContainerFree"),
    }


def _attached_volumes() -> list[dict[str, Any]]:
    volumes = []
    for entry in sorted(Path("/Volumes").iterdir()):
        if entry.is_symlink() or not entry.is_dir():
            continue
        info = _volume_info(entry)
        if info.get("external") and not info.get("disk_image"):
            volumes.append(
                {
                    "path": str(entry),
                    **info,
                    "has_ignite_export": (entry / USB_ROOT).is_dir(),
                }
            )
    return volumes


def _probe(path: Path) -> dict[str, Any] | None:
    result = _run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)]
    )
    if result.returncode != 0:
        return None
    data = json.loads(result.stdout)
    audio = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), None)
    if audio is None:
        return None
    duration = audio.get("duration") or data.get("format", {}).get("duration")
    depth = int(audio.get("bits_per_raw_sample") or audio.get("bits_per_sample") or 0)
    return {
        "codec": audio.get("codec_name"),
        "container": data.get("format", {}).get("format_name"),
        "sample_rate": int(audio.get("sample_rate") or 0),
        "bit_depth": depth,
        "channels": int(audio.get("channels") or 0),
        "seconds": round(float(duration), 6) if duration else None,
    }


def _validate(path: Path, bank_used_seconds: float) -> dict[str, Any]:
    if not path.is_file():
        return {"pass": False, "reason": f"File not found: {path}", "failures": ["file not found"]}
    props = _probe(path)
    if props is None:
        return {"pass": False, "reason": "ffprobe found no audio stream.", "failures": ["no audio stream"]}

    ext = path.suffix.lower()
    seconds = props["seconds"] or 0.0
    unit: list[str] = []
    if ext not in UNIT_EXTENSIONS:
        unit.append(f"Extension {ext or '(none)'} is not .wav, .aif, or .aiff.")
    if props["codec"] not in UNIT_CODECS:
        unit.append(f"Codec {props['codec']} is not 16 or 24 bit integer PCM.")
    if props["bit_depth"] not in UNIT_DEPTHS:
        unit.append(f"Bit depth {props['bit_depth']} is not 16 or 24.")
    if props["sample_rate"] not in UNIT_RATES:
        unit.append(f"Sample rate {props['sample_rate']} is not 44100, 48000, 88200, or 96000.")
    if seconds > UNIT_MAX_SECONDS:
        unit.append(f"Length {seconds:.3f} s is over the {UNIT_MAX_SECONDS:.0f} s limit.")
    if seconds <= 0:
        unit.append("Length is zero or unknown.")
    if bank_used_seconds + seconds > BANK_MAX_SECONDS:
        unit.append(
            f"Bank total {bank_used_seconds + seconds:.3f} s is over the {BANK_MAX_SECONDS:.0f} s bank limit."
        )

    app: list[str] = []
    if ext not in APP_EXTENSIONS:
        app.append(f"Extension {ext or '(none)'} is not in the app's file filter.")
    if seconds < APP_MIN_SECONDS:
        app.append("Shorter than the app's 10 ms minimum.")
    if seconds > APP_MAX_SECONDS:
        app.append("Longer than the app's 30 minute maximum.")

    passed = not unit
    if passed:
        reason = "Pass: format, depth, rate, and length are inside the unit limits."
    else:
        reason = "Fail: " + " ".join(unit)
    return {
        "pass": passed,
        "reason": reason,
        "failures": unit,
        "properties": props,
        "unit_direct": {"pass": not unit, "failures": unit},
        "sample_manager_input": {"pass": not app, "failures": app},
        "bank_total_seconds": round(bank_used_seconds + seconds, 6),
        "bank_remaining_seconds": round(BANK_MAX_SECONDS - bank_used_seconds - seconds, 6),
        "caveat": UNIT_CAVEAT,
    }


def _clean_name(raw: str) -> str:
    cleaned = re.sub(r"[^A-Z0-9 _-]+", " ", raw.upper())
    return re.sub(r"\s+", " ", cleaned).strip()[:NAME_MAX].strip()


def _refusal(output_dir: Path) -> str | None:
    resolved = output_dir.expanduser().resolve()
    home = Path.home()
    blocked = {
        "/Volumes": Path("/Volumes").resolve(),
        "the app support folder": SUPPORT_DIR,
        "~/Library/Pioneer": home / "Library/Pioneer",
        "the Pioneer support folder": home / "Library/Application Support/Pioneer",
        "the app bundle": APP_PATH,
    }
    for label, root in blocked.items():
        if resolved == root or resolved.is_relative_to(root):
            return f"Refused: output cannot be under {label}. Use a staging folder."
    return None


def _peak_db(path: Path, filters: list[str]) -> float | None:
    chain = ",".join([*filters, "volumedetect"])
    result = _run(["ffmpeg", "-hide_banner", "-nostdin", "-i", str(path), "-af", chain, "-f", "null", "-"], 300)
    match = re.search(r"max_volume:\s*(-?[\d.]+|-inf) dB", result.stderr)
    if not match or match.group(1) == "-inf":
        return None
    return float(match.group(1))


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _wav_format_tag(path: Path) -> int | None:
    """Return the fmt chunk format tag of a RIFF/WAVE file, or None."""
    try:
        with path.open("rb") as stream:
            head = stream.read(12)
            if head[:4] != b"RIFF" or head[8:] != b"WAVE":
                return None
            while len(header := stream.read(8)) == 8:
                tag, size = struct.unpack("<4sI", header)
                if tag == b"fmt ":
                    data = stream.read(2)
                    return struct.unpack("<H", data)[0] if len(data) == 2 else None
                stream.seek(size + size % 2, 1)
    except OSError:
        return None
    return None


def _summarize_banks(model: dict[str, Any], samples_dir: Path, *, bank_folders: bool = False) -> dict[str, Any]:
    banks = []
    bank_rows = model.get("bank") if isinstance(model.get("bank"), list) else []
    for bank in bank_rows:
        if not isinstance(bank, dict):
            continue
        slots = []
        total = 0.0
        for slot in bank.get("slot") or []:
            if not isinstance(slot, dict) or not slot.get("file_name"):
                continue
            seconds = float(slot.get("time_length") or 0.0)
            total += seconds
            index = int(slot.get("slot_number") or 0)
            folder = samples_dir / f"{int(bank.get('bank_number') or 0) + 1:02d}" if bank_folders else samples_dir
            sample = folder / str(slot.get("file_name"))
            slots.append(
                {
                    "slot": "ABCD"[index] if 0 <= index < 4 else str(index),
                    "name": slot.get("slot_name") or slot.get("display_file_name"),
                    "file_name": slot.get("file_name"),
                    "seconds": seconds,
                    "gain_db": slot.get("gain"),
                    "bpm": slot.get("bpm"),
                    "is_loop": bool(slot.get("is_loop")),
                    "sample_found": sample.is_file(),
                    "wav_format_tag": _wav_format_tag(sample),
                    "appledouble_found": (folder / f"._{sample.name}").exists(),
                }
            )
        if slots or bank.get("bank_name"):
            banks.append(
                {
                    "bank": int(bank.get("bank_number") or 0) + 1,
                    "name": bank.get("bank_name"),
                    "total_seconds": round(total, 6),
                    "over_16_seconds": total > BANK_MAX_SECONDS,
                    "slots": slots,
                }
            )
    return {
        "bank_count": len(bank_rows),
        "favorite_bank": int(model.get("favorite") or 0) + 1,
        "used_banks": banks,
    }


@mcp.tool()
def ignite_status() -> dict[str, Any]:
    """Report install state, version, running state, library path, and attached USB volumes. Read-only."""
    model = SUPPORT_DIR / "model/model.json"
    return {
        "installed": APP_PATH.is_dir(),
        "app_path": str(APP_PATH),
        "version": _app_version(),
        "running": _app_running(),
        "library_path": str(SUPPORT_DIR),
        "library_exists": model.is_file(),
        "ffmpeg": shutil.which("ffmpeg"),
        "ffprobe": shutil.which("ffprobe"),
        "usb_volumes": _attached_volumes(),
    }


@mcp.tool()
def ignite_list_library(support_dir: str | None = None, include_factory: bool = False) -> dict[str, Any]:
    """List banks and slots from the app's model.json, plus its BANK COLLECTION. Read-only.

    support_dir overrides the app support folder, for scratch copies.
    include_factory also lists the factory WAV files inside the app bundle.
    """
    root = Path(support_dir).expanduser() if support_dir else SUPPORT_DIR
    model = _load_json(root / "model/model.json")
    if model is None:
        return {
            "ok": False,
            "library_path": str(root),
            "reason": "model/model.json is missing or unreadable. The app creates it on first launch.",
        }
    collection = _load_json(root / "bankcollection/bankcollection.json") or {}
    rows = collection.get("bankcollection")
    result: dict[str, Any] = {
        "ok": True,
        "library_path": str(root),
        **_summarize_banks(model, root / "model/samples"),
        "bank_collection_count": len(rows) if isinstance(rows, list) else 0,
        "note": "App sample paths were checked against a native backup. Hardware playback is not verified.",
    }
    if include_factory:
        factory = APP_PATH / "Contents/Resources/FactorySamples"
        result["factory_samples"] = sorted(
            str(p.relative_to(factory)) for p in factory.glob("*/*.wav")
        )
    return result


@mcp.tool()
def ignite_validate_sample(path: str, bank_used_seconds: float = 0.0) -> dict[str, Any]:
    """Check one audio file against official RMX-IGNITE limits and return pass or fail with the reason.

    pass means the unit can load it directly and it fits the 16 s bank budget.
    bank_used_seconds is the length already used by the other slots in the target bank.
    sample_manager_input separately reports whether the desktop app can take the file.
    """
    return _validate(Path(path).expanduser(), max(0.0, bank_used_seconds))


@mcp.tool()
def ignite_prepare_sample(
    input_path: str,
    name: str,
    output_dir: str = str(DEFAULT_STAGING),
    start_seconds: float = 0.0,
    end_seconds: float | None = None,
    normalize: Literal["peak", "none"] = "peak",
    peak_db: float = -1.0,
    fade_out_ms: float = 5.0,
    overwrite: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Trim, normalize, and convert to a 96 kHz, 24 bit, stereo WAV in a staging folder.

    Writes one new file and never changes the input. Does not touch the app library or any USB drive.
    Importing into a bank is GUI only: the result names the steps. dry_run writes nothing.
    """
    source = Path(input_path).expanduser()
    target_dir = Path(output_dir).expanduser()
    refused = _refusal(target_dir)
    if refused:
        return {"ok": False, "reason": refused, "output_written": False}
    if not source.is_file():
        return {"ok": False, "reason": f"Input not found: {source}", "output_written": False}
    props = _probe(source)
    if props is None or not props["seconds"]:
        return {"ok": False, "reason": "ffprobe found no audio with a known length.", "output_written": False}

    clean = _clean_name(name)
    if not clean:
        return {"ok": False, "reason": "Name has no usable characters.", "output_written": False}
    start = max(0.0, start_seconds)
    end = props["seconds"] if end_seconds is None else min(end_seconds, props["seconds"])
    length = end - start
    if length < APP_MIN_SECONDS:
        return {"ok": False, "reason": f"Selected length {length:.3f} s is under 10 ms.", "output_written": False}
    if length > UNIT_MAX_SECONDS:
        return {
            "ok": False,
            "reason": f"Selected length {length:.3f} s is over 16 s. Set start_seconds and end_seconds.",
            "output_written": False,
        }

    output = target_dir / f"{clean}.wav"
    if output.resolve() == source.resolve():
        return {"ok": False, "reason": "Output would replace the input.", "output_written": False}
    if output.exists() and not overwrite:
        return {"ok": False, "reason": f"Output exists: {output}. Set overwrite to replace it.", "output_written": False}

    plan = {
        "input": str(source),
        "output": str(output),
        "start_seconds": start,
        "end_seconds": end,
        "seconds": round(length, 6),
        "spec": {"container": "wav", "sample_rate": PREPARE_RATE, "bit_depth": PREPARE_DEPTH, "channels": 2},
        "normalize": normalize,
        "peak_db_target": peak_db if normalize == "peak" else None,
    }
    if dry_run:
        return {"ok": True, "dry_run": True, "output_written": False, **plan}

    # Upmix before measuring: mono to stereo drops the level by 3 dB, so the gain must include it.
    filters = [
        f"atrim=start={start}:end={end}",
        "asetpts=PTS-STARTPTS",
        f"aresample={PREPARE_RATE}",
        "aformat=channel_layouts=stereo",
    ]
    gain_db = 0.0
    if normalize == "peak":
        measured = _peak_db(source, filters)
        if measured is None:
            return {"ok": False, "reason": "Input is silent or could not be measured.", "output_written": False}
        gain_db = round(peak_db - measured, 2)
        filters.append(f"volume={gain_db}dB")
    fade = min(fade_out_ms / 1000.0, length / 2)
    if fade > 0:
        filters.append(f"afade=t=out:st={length - fade}:d={fade}")

    target_dir.mkdir(parents=True, exist_ok=True)
    temp = output.with_name(f".{output.stem}.tmp.wav")
    command = [
        "ffmpeg", "-hide_banner", "-nostdin", "-y", "-i", str(source), "-vn", "-map_metadata", "-1",
        "-af", ",".join(filters), "-ac", "2", "-ar", str(PREPARE_RATE), "-c:a", "pcm_s24le",
        "-fflags", "+bitexact", str(temp),
    ]  # fmt: skip
    result = _run(command, 300)
    if result.returncode != 0:
        temp.unlink(missing_ok=True)
        return {"ok": False, "reason": "ffmpeg failed: " + result.stderr[-400:], "output_written": False}
    # FFmpeg can write WAVE_FORMAT_EXTENSIBLE. Keep the PCM frames, but use a classic PCM header.
    with wave.open(str(temp), "rb") as reader:
        params = reader.getparams()
        frames = reader.readframes(reader.getnframes())
    with wave.open(str(temp), "wb") as writer:
        writer.setparams(params)
        writer.writeframes(frames)
    check = _validate(temp, 0.0)
    if not check["pass"]:
        temp.unlink(missing_ok=True)
        return {"ok": False, "reason": "Output failed validation: " + check["reason"], "output_written": False}
    temp.replace(output)
    return {
        "ok": True,
        "dry_run": False,
        "output_written": True,
        **plan,
        "gain_applied_db": gain_db,
        "validation": {**check, "properties": _probe(output)},
        "import_is_gui_only": True,
        "next_gui_steps": GUI_STEPS["assign"] + GUI_STEPS["export"],
    }


@mcp.tool()
def ignite_read_usb(volume_path: str, max_files: int = 500) -> dict[str, Any]:
    """Inspect a volume or folder without writing to it.

    Reports file system support, any Sample Manager export folder, and audio file counts.
    """
    root = Path(volume_path).expanduser()
    if not root.is_dir():
        return {"ok": False, "reason": f"Not a folder: {root}"}
    export_root = root / USB_ROOT
    settings_path = export_root / USB_SETTINGS
    settings = _load_json(settings_path) if settings_path.is_file() else None

    limit = max(1, min(max_files, USB_SCAN_LIMIT))
    audio: list[str] = []
    other = 0
    truncated = False
    for current, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d != "PIONEER")
        for filename in sorted(files):
            if filename.startswith("."):
                continue
            if len(audio) + other >= limit:
                truncated = True
                break
            if Path(filename).suffix.lower() in UNIT_EXTENSIONS:
                audio.append(str((Path(current) / filename).relative_to(root)))
            else:
                other += 1
        if truncated:
            break

    result: dict[str, Any] = {
        "ok": True,
        "path": str(root),
        "read_only": True,
        "volume": _volume_info(root) if str(root.resolve()).startswith("/Volumes/") else None,
        "has_ignite_export": export_root.is_dir(),
        "settings_file_found": settings_path.is_file(),
        "settings_parsed": settings is not None,
        "unit_audio_files": len(audio),
        "other_files": other,
        "scan_truncated": truncated,
        "audio_sample": audio[:40],
        "layout_note": LAYOUT_NOTE,
    }
    if settings is not None and "bank" in settings:
        result["export_banks"] = _summarize_banks(settings, export_root, bank_folders=True)
    return result


@mcp.tool()
def ignite_gui_steps(
    action: Literal["assign", "export", "import", "backup", "restore", "unit_load"],
) -> dict[str, Any]:
    """Return the exact manual steps for work this server cannot do. Bank edits and export are GUI only."""
    return {
        "action": action,
        "gui_only": True,
        "driver": "mac-gui MCP" if action != "unit_load" else "the user, at the unit",
        "steps": GUI_STEPS[action],
        "note": "The File menu is drawn inside the app window, not in the macOS menu bar.",
    }


if __name__ == "__main__":
    mcp.run()
