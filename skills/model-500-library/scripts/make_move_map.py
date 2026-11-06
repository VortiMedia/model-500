"""Build the --map file for safe_move.py from a whole folder. safe_move.py --from and
--to take one file each, so a folder move needs a map. Reads OLD_DIR and writes only --out.

Usage (python3 -I is fine):
  make_move_map.py OLD_DIR NEW_DIR --out moves.json
Output: [{"from": OLD_DIR/x.aiff, "to": NEW_DIR/x.aiff}, ...]. Audio files only, subfolders
kept. Other files are listed and left out. Check the plan with a safe_move.py dry run."""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _rbcommon import AUDIO_EXT, die


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("old_dir")
    ap.add_argument("new_dir")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    old = os.path.abspath(os.path.expanduser(a.old_dir))
    new = os.path.abspath(os.path.expanduser(a.new_dir))
    if not os.path.isdir(old):
        die(f"not a folder: {old}")
    if new == old or new.startswith(old + os.sep):
        die("NEW_DIR must be outside OLD_DIR")
    moves, skipped = [], []
    for root, dirs, files in os.walk(old):
        dirs.sort()
        for f in sorted(files):
            path = os.path.join(root, f)
            if f.startswith("."):
                continue
            if f.lower().endswith(AUDIO_EXT):
                moves.append({"from": path, "to": os.path.join(new, os.path.relpath(path, old))})
            else:
                skipped.append(path)
    if not moves:
        die(f"no audio files in {old}")
    with open(os.path.expanduser(a.out), "w", encoding="utf-8") as fh:
        json.dump(moves, fh, indent=1, ensure_ascii=False)
    print(f"wrote {a.out}: {len(moves)} move(s). Nothing moved.")
    for path in skipped:
        print("  left out, not audio:", path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
