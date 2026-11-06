"""Shared helpers for the model-500-library scripts. Import only; do not run."""
import atexit
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import unicodedata

HOME = os.path.expanduser("~")
RB_DIR = f"{HOME}/Library/Pioneer/rekordbox"
AUDIO_EXT = (".mp3", ".m4a", ".aac", ".wav", ".aif", ".aiff", ".flac", ".opus", ".ogg", ".alac")


def nfc(s):
    return unicodedata.normalize("NFC", s or "")


def rekordbox_running():
    return subprocess.run(["pgrep", "-x", "rekordbox"], capture_output=True).returncode == 0


def open_db(rb_dir=RB_DIR, write=False):
    """Open master.db. Read mode copies db, -wal, -shm to a temp dir first, so a
    running rekordbox is never touched. Returns (db, tempdir_or_None)."""
    from pyrekordbox import Rekordbox6Database

    if write:
        if rekordbox_running():
            raise SystemExit("REFUSED: rekordbox is running. Quit it first (pgrep -x rekordbox).")
        return Rekordbox6Database(path=f"{rb_dir}/master.db", db_dir=rb_dir), None
    tmp = tempfile.mkdtemp(prefix="rbcopy-")
    atexit.register(shutil.rmtree, tmp, ignore_errors=True)
    for suffix in ("", "-wal", "-shm"):
        src = f"{rb_dir}/master.db{suffix}"
        if os.path.exists(src):
            shutil.copy2(src, f"{tmp}/master.db{suffix}")
    return Rekordbox6Database(path=f"{tmp}/master.db", db_dir=rb_dir), tmp


def find_content(db, path):
    for p in (path, nfc(path), unicodedata.normalize("NFD", path)):
        found = db.get_content(FolderPath=p).one_or_none()
        if found is not None:
            return found
    return None


def anlz_tags(data):
    """Return [(fourcc, start, end)] for an ANLZ file's tags."""
    if data[:4] != b"PMAI":
        raise ValueError("not an ANLZ file")
    header_len = struct.unpack(">I", data[4:8])[0]
    pos, out = header_len, []
    while pos < len(data):
        tag_len = struct.unpack(">I", data[pos + 8 : pos + 12])[0]
        out.append((data[pos : pos + 4], pos, pos + tag_len))
        pos += tag_len
    return out


def splice_ppth(data, new_path):
    """Return ANLZ bytes with only the PPTH tag replaced and PMAI length fixed."""
    raw = new_path.encode("utf-16-be") + b"\x00\x00"
    tag = b"PPTH" + struct.pack(">III", 16, 16 + len(raw), len(raw)) + raw
    out, done = bytearray(data[: struct.unpack(">I", data[4:8])[0]]), False
    for fourcc, s, e in anlz_tags(data):
        if fourcc == b"PPTH":
            out += tag
            done = True
        else:
            out += data[s:e]
    if not done:
        raise ValueError("no PPTH tag")
    out[8:12] = struct.pack(">I", len(out))
    return bytes(out)


def non_ppth_tags(data):
    return [(f, data[s:e]) for f, s, e in anlz_tags(data) if f != b"PPTH"]


def get_ppth(data):
    for f, s, e in anlz_tags(data):
        if f == b"PPTH":
            n = struct.unpack(">I", data[s + 12 : s + 16])[0]
            return data[s + 16 : s + 16 + n].decode("utf-16-be").rstrip("\x00")
    return None


def die(msg):
    print(msg, file=sys.stderr)
    raise SystemExit(1)
