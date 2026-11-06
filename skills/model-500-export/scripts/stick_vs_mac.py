"""Read-only diff of a stick against the Mac. Run it before any wipe (F12, F13). Writes nothing
to the stick. It works with or without an export.pdb, because it walks the files.

Usage: python3 -I stick_vs_mac.py /Volumes/STICK [--mac-root DIR ...] [--json OUT.json]
--mac-root defaults to ~/Music. Names compare as NFC, ignoring case (F10). A name with another
size counts as "size differs": treat it as stick-only until the user checks it. rekordbox can change
names on export, so stick_only can hold false alarms. This is a name and size check, not an audio
check: other audio with the same name and size would count as matched."""
import argparse
import json
import os
import sys
import unicodedata

AUDIO_EXT = (".mp3", ".m4a", ".aac", ".wav", ".aif", ".aiff", ".flac", ".opus", ".ogg", ".alac")
SYSTEM = {".fseventsd", ".Spotlight-V100", ".Trashes", ".TemporaryItems", ".metadata_never_index", ".DS_Store"}
REKORDBOX_ROOTS = ("PIONEER", "Contents")


def key(name):
    return unicodedata.normalize("NFC", name).casefold()


def is_audio(name):
    return name.lower().endswith(AUDIO_EXT) and not name.startswith("._")


def mac_index(roots):
    index = {}
    for root in roots:
        for folder, _, files in os.walk(os.path.expanduser(root)):
            for f in files:
                if is_audio(f):
                    index.setdefault(key(f), set()).add(os.path.getsize(os.path.join(folder, f)))
    return index


def walk_stick(vol):
    for folder, dirs, files in os.walk(vol):
        dirs[:] = [d for d in dirs if d not in SYSTEM]
        for f in files:
            if f not in SYSTEM and not f.startswith("._"):
                yield os.path.join(folder, f)


def compare(vol, roots):
    index = mac_index(roots)
    out = {"matched": [], "stick_only": [], "size_differs": [], "non_rekordbox": []}
    for path in walk_stick(vol):
        rel = os.path.relpath(path, vol)
        name = os.path.basename(path)
        if is_audio(name):
            sizes = index.get(key(name))
            if sizes is None:
                out["stick_only"].append(rel)
            elif os.path.getsize(path) in sizes:
                out["matched"].append(rel)
            else:
                out["size_differs"].append(rel)
        if rel.split(os.sep)[0] not in REKORDBOX_ROOTS:
            out["non_rekordbox"].append(rel)
    return {k: sorted(v) for k, v in out.items()}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("volume")
    ap.add_argument("--mac-root", action="append", help="repeat for more folders; default ~/Music")
    ap.add_argument("--json", help="also write the lists to this file; not on the stick")
    a = ap.parse_args()
    vol = a.volume.rstrip("/")
    if not os.path.isdir(vol):
        print(f"Not mounted: {vol}", file=sys.stderr)
        return 1
    res = compare(vol, a.mac_root or ["~/Music"])
    print(f"audio on stick: matched={len(res['matched'])} stick_only={len(res['stick_only'])} size_differs={len(res['size_differs'])}")
    for label in ("stick_only", "size_differs", "non_rekordbox"):
        print(f"\n--- {label} ({len(res[label])})")
        for rel in res[label]:
            print(" ", rel)
    print("\nA wipe removes all of the above. Name each stick_only and size_differs file to the user.")
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(res, fh, indent=1, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
