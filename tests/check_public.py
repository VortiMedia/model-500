#!/usr/bin/env python3
"""Fail if a tracked file holds private data. Stdlib only.

Checks every file that git tracks or would add (untracked and not ignored). Outside a git
checkout, such as an unpacked archive, it walks the folder instead and skips the same
private and generated paths:
  1. Each term in state/private-terms.txt (one per line, case-insensitive, '#' starts a comment).
     That file is gitignored. If it is absent, this check prints SKIP and passes.
  2. A home-folder path that starts with a slash, "Users", and a slash.
  3. An email address, unless its local part or domain is a noreply address.

Usage: python3 tests/check_public.py
Exit 1 if anything is found. Output shows file, line, and the kind of match.
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TERMS_FILE = ROOT / "state" / "private-terms.txt"
HOME_PATH = re.compile("/" + "Users" + "/")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")  # A version tag such as tool@v1.2.3 ends in a digit.
SKIP_DIRS = {".git", ".venv", "__pycache__", "scratch"}
SKIP_FILES = {"state/PROFILE.md", "state/STATE.md", "state/failures-private.md",
              "state/private-terms.txt", "state/gui-actions.log"}


def walk_files():
    files = []
    for path in sorted(ROOT.rglob("*")):
        rel = path.relative_to(ROOT)
        if path.is_file() and not SKIP_DIRS & set(rel.parts) and rel.as_posix() not in SKIP_FILES:
            files.append(path)
    return files


def tracked_files():
    if not (ROOT / ".git").exists():
        print("Not a git checkout: walking the folder")
        return walk_files()
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                         capture_output=True, check=True).stdout
    return [ROOT / p for p in out.decode("utf-8", "replace").split("\0") if p]


def load_terms():
    if not TERMS_FILE.is_file():
        return None
    terms = []
    for raw in TERMS_FILE.read_text(encoding="utf-8").splitlines():
        t = raw.strip()
        if t and not t.startswith("#"):
            terms.append(t.lower())
    return terms


def allowed_email(addr):
    local, _, domain = addr.lower().partition("@")
    return "noreply" in local or "noreply" in domain


def scan(path, terms):
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []  # binary or unreadable
    hits = []
    for n, line in enumerate(text.splitlines(), 1):
        low = line.lower()
        for t in terms or []:
            if t in low:
                hits.append((n, f"private term '{t}'"))
        if HOME_PATH.search(line):
            hits.append((n, "home-folder path"))
        for m in EMAIL.finditer(line):
            if not allowed_email(m.group(0)):
                hits.append((n, f"email {m.group(0)}"))
    return hits


def main():
    files = tracked_files()
    terms = load_terms()
    if terms is None:
        print("SKIP private-term check: state/private-terms.txt is absent (path and email checks still run)")
    bad = 0
    for f in files:
        for n, why in scan(f, terms):
            print(f"{f.relative_to(ROOT)}:{n}: {why}")
            bad += 1
    if bad:
        print(f"FAIL check_public: {bad} finding(s)")
        return 1
    print(f"ok check_public: {len(files)} files clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
