"""Read-only audit of a rekordbox USB stick: parses PIONEER/rekordbox/export.pdb
and compares it with the audio files under Contents/. Writes nothing to the stick.

Usage: python3 -I read_pdb.py /Volumes/STICK [--json OUT.json]
JSON reports must be outside the audited volume, including resolved symlink targets.
Does not read exportLibrary.db (encrypted). Only a CDJ test proves OneLibrary loads."""
import argparse
import json
import os
import struct
import sys
import tempfile
import unicodedata
from pathlib import Path

nfc = lambda s: unicodedata.normalize("NFC", s or "")


def parse(pdb_path):
    data = open(pdb_path, "rb").read()
    page_size, num_tables = struct.unpack_from("<II", data, 4)

    def read_str(pos):
        b = data[pos]
        if b & 1:
            n = (b >> 1) - 1
            return data[pos + 1 : pos + 1 + n].decode("ascii", "replace")
        length = struct.unpack_from("<H", data, pos + 1)[0]
        raw = data[pos + 4 : pos + length]
        if b == 0x40:
            return raw.decode("ascii", "replace")
        if b == 0x90:
            return raw.decode("utf-16-le", "replace")
        return ""

    def rows(table_type):
        for i in range(num_tables):
            t, _, first, last = struct.unpack_from("<IIII", data, 28 + i * 16)
            if t != table_type:
                continue
            page, seen = first, set()
            while page not in seen:
                seen.add(page)
                base = page * page_size
                next_page = struct.unpack_from("<I", data, base + 12)[0]
                packed = int.from_bytes(data[base + 24 : base + 27], "little")
                n_offsets = packed & 0x1FFF
                if data[base + 27] & 0x40 == 0:
                    for g in range((n_offsets + 15) // 16):
                        gb = base + page_size - g * 0x24
                        present = struct.unpack_from("<H", data, gb - 4)[0]
                        for r in range(16):
                            if present >> r & 1:
                                yield base + 40 + struct.unpack_from("<H", data, gb - (6 + 2 * r))[0]
                if page == last:
                    break
                page = next_page

    tracks = {}
    for pos in rows(0):
        tid = struct.unpack_from("<I", data, pos + 72)[0]
        offs = struct.unpack_from("<21H", data, pos + 94)
        tracks[tid] = {"title": read_str(pos + offs[17]), "path": read_str(pos + offs[20]), "file": read_str(pos + offs[19])}
    nodes = {}
    for pos in rows(7):
        parent, _, sort, nid, folder = struct.unpack_from("<IIIII", data, pos)
        nodes[nid] = {"parent": parent, "sort": sort, "folder": bool(folder), "name": read_str(pos + 20), "entries": []}
    for pos in rows(8):
        idx, tid, pid = struct.unpack_from("<III", data, pos)
        if pid in nodes:
            nodes[pid]["entries"].append((idx, tid))
    return page_size, num_tables, tracks, nodes


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("volume", help="mount point, e.g. /Volumes/STICK")
    ap.add_argument("--json", help="also write parsed tracks and playlists outside the audited volume")
    a = ap.parse_args()
    vol = a.volume.rstrip("/")
    pdb = f"{vol}/PIONEER/rekordbox/export.pdb"
    if not os.path.exists(pdb):
        print(f"No export.pdb at {pdb}. Stick has no exported library.")
        for name in ("PIONEER/rekordbox/exportLibrary.db", "PIONEER/rekordbox"):
            print(f"  {name}: {'present' if os.path.exists(f'{vol}/{name}') else 'absent'}")
        return 1
    report = Path(a.json).absolute() if a.json else None
    if report is not None:
        for destination in (report, report.resolve()):
            if any(p.exists() and p.samefile(vol) for p in (destination, *destination.parents)):
                ap.error("--json must be outside the audited volume; no report was written")
    page_size, n_tables, tracks, nodes = parse(pdb)
    print(f"page_size={page_size} tables={n_tables} tracks={len(tracks)} playlists={len(nodes)}")

    def show(parent, depth=0):
        for nid, n in sorted((x for x in nodes.items() if x[1]["parent"] == parent), key=lambda x: x[1]["sort"]):
            print("  " * depth + f"{n['name']} " + ("[folder]" if n["folder"] else f"({len(n['entries'])} tracks)"))
            show(nid, depth + 1)

    print("\n--- playlist tree")
    show(0)
    disk = set()
    for root, _, files in os.walk(f"{vol}/Contents"):
        for f in files:
            if not f.startswith("._") and f != ".DS_Store":
                disk.add(nfc(os.path.join(root, f)[len(vol):]))
    db_paths = {nfc(t["path"]) for t in tracks.values()}
    in_list = {tid for n in nodes.values() for _, tid in n["entries"]}
    print(f"\nfiles on disk={len(disk)} db paths={len(db_paths)} (compared as NFC)")
    print("in db, missing on disk:", sorted(db_paths - disk))
    print("on disk, not in db:", sorted(disk - db_paths))
    print("in db, in no playlist:", sorted(tracks[t]["path"] for t in tracks if t not in in_list))
    print("playlist entries pointing at no track:", sorted(in_list - set(tracks)))
    junk = [os.path.join(r, f) for r, d, fs in os.walk(vol) for f in fs + d if f.startswith("._")]
    print(f"\nAppleDouble '._' files on stick: {len(junk)}")
    for name in ("exportLibrary.db", "export.pdb"):
        p = f"{vol}/PIONEER/rekordbox/{name}"
        if os.path.exists(p):
            print(f"{name}: size={os.path.getsize(p)}")
    print("NOTE: a CDJ test is still needed to prove the stick loads.")
    if report is not None:
        # Replace the report, rather than truncating an outside hard link to an audited file.
        with tempfile.TemporaryDirectory(prefix=".audit-report-", dir=report.parent) as tmp:
            staged = Path(tmp) / "report.json"
            staged.write_text(json.dumps({"tracks": tracks, "nodes": nodes}, indent=1, default=str), encoding="utf-8")
            staged.replace(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
