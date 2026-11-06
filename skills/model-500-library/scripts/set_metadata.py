"""Set artist, title, album, label, year, comment on rekordbox tracks, then read back.
Dry run by default. Needed because import_tracks (auto_tag) can leave Artist and
Title empty on tagged AIFF files, and the MCP has no edit tool.

Usage (run with ~/rekordbox-mcp/.venv/bin/python):
  set_metadata.py meta.json [--go]
meta.json: [{"path": "/abs/file.aiff" | "id": 123, "artist": "...", "title": "...",
             "album": "...", "label": "...", "year": 2024, "comment": "CAT001"}, ...]
Only keys you give are changed. --go refuses when rekordbox is running.
Back up first (whole ~/Library/Pioneer/rekordbox folder, see model-500-library SKILL.md)."""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _rbcommon import RB_DIR, die, find_content, open_db, rekordbox_running


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("meta_json")
    ap.add_argument("--go", action="store_true")
    ap.add_argument("--rb-dir", default=RB_DIR)
    a = ap.parse_args()
    items = json.load(open(a.meta_json))
    if a.go and rekordbox_running():
        die("REFUSED: rekordbox is running. Quit it first (pgrep -x rekordbox).")
    db, _ = open_db(a.rb_dir, write=a.go)
    getters = {"artist": (db.get_artist, db.add_artist, "ArtistID"), "album": (db.get_album, db.add_album, "AlbumID"),
               "label": (db.get_label, db.add_label, "LabelID")}
    plan = []
    for it in items:
        c = db.get_content(ID=it["id"]) if "id" in it else find_content(db, it.get("path", ""))
        if c is not None and hasattr(c, "one"):
            c = c.one()
        if c is None:
            print("PROBLEM: no track for", it.get("path") or it.get("id"))
            continue
        plan.append((c, it))
    print(f"{'GO' if a.go else 'DRY RUN'}: {len(plan)} of {len(items)} tracks matched")
    for c, it in plan:
        now = f"{c.ArtistName} | {c.Title} | {c.AlbumName}"
        new = " | ".join(str(it.get(k, "(keep)")) for k in ("artist", "title", "album"))
        print(f"  [{c.ID}] {now}  ->  {new}")
    if not a.go:
        print("Nothing changed. Re-run with --go after the user OKs it.")
        return 0
    for c, it in plan:
        if "title" in it:
            c.Title = it["title"]
        for key, (get, add, col) in getters.items():
            if it.get(key):
                found = get(Name=it[key]).one_or_none()
                setattr(c, col, (found if found is not None else add(it[key])).ID)
        if str(it.get("year", "")).isdigit():
            c.ReleaseYear = int(it["year"])
        if "comment" in it:
            c.Commnt = it["comment"] or ""
    db.commit()
    db.close()
    db2, _ = open_db(a.rb_dir, write=True)
    bad = 0
    for c, it in plan:
        r = db2.get_content(ID=c.ID)
        r = r.one() if hasattr(r, "one") else r
        got = {"artist": r.ArtistName, "title": r.Title, "album": r.AlbumName, "comment": r.Commnt}
        wrong = [k for k in got if k in it and (got[k] or "") != (it[k] or "")]
        bad += bool(wrong)
        print(("BAD " + str(wrong) if wrong else "OK  ") + f" [{r.ID}] {got['artist']} | {got['title']}")
    print("readback done, bad =", bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
