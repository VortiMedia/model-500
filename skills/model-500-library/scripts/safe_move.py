"""Move audio files and keep rekordbox in step. Dry run by default.

Per file: back up its ANLZ files, move the file, update DjmdContent paths, splice
ONLY the PPTH tag in each ANLZ file, then check every other tag is byte-identical.
Do not use pyrekordbox update_content_path(save=True): it rewrites other tags.

Usage (run with ~/rekordbox-mcp/.venv/bin/python):
  safe_move.py --from OLD --to NEW [--go --backup-dir DIR]
  safe_move.py --map moves.json [--go --backup-dir DIR]     # [{"from":..., "to":...}]
--go refuses when rekordbox is running. --backup-dir must not exist: the whole
rekordbox folder is copied there first (master.db, -wal, share/PIONEER)."""
import argparse
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _rbcommon import RB_DIR, die, find_content, get_ppth, nfc, non_ppth_tags, open_db, rekordbox_running, splice_ppth


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="src")
    ap.add_argument("--to", dest="dst")
    ap.add_argument("--map")
    ap.add_argument("--go", action="store_true", help="really do it (default is a dry run)")
    ap.add_argument("--backup-dir")
    ap.add_argument("--rb-dir", default=RB_DIR)
    a = ap.parse_args()
    if a.map:
        moves = [(m["from"], m["to"]) for m in json.load(open(a.map))]
    elif a.src and a.dst:
        moves = [(a.src, a.dst)]
    else:
        die("give --from and --to, or --map")
    if a.go and not a.backup_dir:
        die("--go needs --backup-dir (new folder)")
    if a.go and rekordbox_running():
        die("REFUSED: rekordbox is running. Quit it first (pgrep -x rekordbox).")

    db, tmp = open_db(a.rb_dir, write=a.go)
    plan, problems = [], []
    for src, dst in moves:
        c = find_content(db, src)
        if c is None:
            problems.append(f"not in rekordbox: {src}")
            continue
        if not os.path.exists(c.FolderPath):
            problems.append(f"file missing on disk: {c.FolderPath}")
            continue
        if os.path.exists(dst):
            problems.append(f"destination exists: {dst}")
            continue
        anlz = {k: str(v) for k, v in db.get_anlz_paths(c).items() if v}
        plan.append((c, c.FolderPath, dst, anlz))
    if len({nfc(p[2]).lower() for p in plan}) != len(plan):
        problems.append("two moves share a destination")

    print(f"{'GO' if a.go else 'DRY RUN'}: {len(plan)} move(s), {len(problems)} problem(s)")
    for c, old, new, anlz in plan:
        print(f"  [{c.ID}] {old}\n      -> {new}   ANLZ files: {sorted(anlz)}")
    for p in problems:
        print("  PROBLEM:", p)
    if problems:
        die("Fix the problems first. Nothing changed.")
    if not a.go:
        print("Nothing changed. Re-run with --go --backup-dir DIR after the user OKs it.")
        return 0

    if os.path.exists(a.backup_dir):
        die("backup dir exists; pick a new one")
    shutil.copytree(a.rb_dir, a.backup_dir, symlinks=True)
    print("full backup:", a.backup_dir)
    done = []
    try:
        for c, old, new, anlz in plan:
            os.makedirs(os.path.dirname(new), exist_ok=True)
            shutil.move(old, new)
            done.append((c, old, new, anlz))
            before = {k: open(p, "rb").read() for k, p in anlz.items()}
            for k, p in anlz.items():
                open(p, "wb").write(splice_ppth(before[k], new))
            for k, p in anlz.items():
                after = open(p, "rb").read()
                if non_ppth_tags(after) != non_ppth_tags(before[k]):
                    raise RuntimeError(f"non-PPTH tags changed in {p}")
                if get_ppth(after) != new:
                    raise RuntimeError(f"PPTH not updated in {p}")
            c.FolderPath = new
            if c.OrgFolderPath == old:
                c.OrgFolderPath = new
            c.FileNameL = os.path.basename(new)
        db.commit()
    except Exception as e:
        print("FAILED:", e, "- restoring from backup", file=sys.stderr)
        db.session.rollback()
        for c, old, new, anlz in done:
            if os.path.exists(new):
                shutil.move(new, old)
            for k, p in anlz.items():
                rel = os.path.relpath(p, a.rb_dir)
                shutil.copy2(os.path.join(a.backup_dir, rel), p)
        die("Rolled back files and ANLZ. master.db not committed.")
    db.close()
    db2, _ = open_db(a.rb_dir, write=True)
    bad = 0
    for c, old, new, anlz in done:
        r = db2.get_content(ID=c.ID)
        r = r if not hasattr(r, "one") else r.one()
        ok = r.FolderPath == new and os.path.exists(new)
        bad += not ok
        print(("OK  " if ok else "BAD ") + new)
    print("readback done, bad =", bad)
    print("Next: connect_database in the MCP, then open rekordbox and check the tracks play.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
