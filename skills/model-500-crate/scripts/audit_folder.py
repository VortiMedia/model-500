"""Read-only audit of one or more audio folders: codec, bitrate, likely previews,
likely mixes, junk words, empty tags, near-duplicates. Writes nothing unless --json.

Usage (python3 -I is fine; needs ffprobe on PATH):
  audit_folder.py DIR [DIR ...] [--json OUT.json] [--short 180] [--long 900]
Rips lie: artist tags are often the uploader. Treat the flags as leads, not facts."""
import argparse
import concurrent.futures as cf
import html
import json
import os
import re
import subprocess
import sys
import unicodedata
from collections import Counter, defaultdict

EXT = (".m4a", ".mp3", ".opus", ".ogg", ".wav", ".aif", ".aiff", ".flac")
JUNK = re.compile(r"premiere|out now|preview|&amp;|free d|forthcoming|\bclip\b|taken from|official|\bhq\b|snippet|teaser|lo-?res", re.I)


def probe(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
         "stream=codec_name,bit_rate,sample_rate,bits_per_sample:format=duration,bit_rate,size:format_tags", "-of", "json", path],
        capture_output=True, text=True)
    try:
        d = json.loads(r.stdout)
        s, f = d["streams"][0], d["format"]
        tags = {k.lower(): v for k, v in f.get("tags", {}).items()}
        return {"path": path, "file": os.path.basename(path), "codec": s.get("codec_name"),
                "kbps": int(s.get("bit_rate") or f.get("bit_rate") or 0) // 1000, "hz": int(s.get("sample_rate") or 0),
                "dur": float(f.get("duration") or 0), "size": int(f.get("size") or 0),
                "artist": tags.get("artist", ""), "title": tags.get("title", ""), "genre": tags.get("genre", "")}
    except Exception as e:
        return {"path": path, "file": os.path.basename(path), "error": f"{e} {r.stderr[:80]}"}


def norm(s):
    s = unicodedata.normalize("NFKD", html.unescape(s or "")).lower()
    s = re.sub(r"\[[^\]]*\]|\.(m4a|mp3|opus|wav|aiff?|flac)$", " ", s)
    s = re.sub(r"\b(premiere|out now|preview|original mix|free download|official|hq|clip|taken from)\b", " ", s)
    return re.sub(r"[^a-z0-9]+", "", s)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--json")
    ap.add_argument("--short", type=int, default=180, help="seconds; below = likely preview")
    ap.add_argument("--long", type=int, default=900, help="seconds; above = likely mix")
    ap.add_argument("--top", type=int, default=10, help="rows to list per flag")
    a = ap.parse_args()
    items = []
    for d in a.dirs:
        d = os.path.expanduser(d)
        for root, _, files in os.walk(d):
            for f in sorted(files):
                if f.lower().endswith(EXT) and not f.startswith("."):
                    items.append((d, os.path.join(root, f)))
    with cf.ThreadPoolExecutor(8) as ex:
        rows = list(ex.map(lambda x: {**probe(x[1]), "folder": x[0]}, items))
    for r in rows:
        t = r.get("title") or r["file"]
        r["key"] = norm(t)
        r["junk"] = bool(JUNK.search(t + " " + r["file"]))
    if a.json:
        json.dump(rows, open(a.json, "w"), indent=1)
    for d in a.dirs:
        d = os.path.expanduser(d)
        g = [r for r in rows if r["folder"] == d and "error" not in r]
        errs = [r["file"] for r in rows if r["folder"] == d and "error" in r]
        print(f"\n=== {d}: {len(g)} tracks, {sum(r['size'] for r in g)/1e9:.2f} GB, {sum(r['dur'] for r in g)/3600:.1f} h, probe errors {len(errs)} {errs[:3]}")
        print(" codec:kbps:", Counter(f"{r['codec']}:{round(r['kbps']/32)*32}" for r in g).most_common(8))
        short = sorted((r for r in g if r["dur"] < a.short), key=lambda r: r["dur"])
        long_ = sorted((r for r in g if r["dur"] > a.long), key=lambda r: -r["dur"])
        lossy_low = [r for r in g if r["codec"] in ("mp3", "aac", "opus", "vorbis") and 0 < r["kbps"] < 192]
        print(f" under {a.short}s (likely previews): {len(short)}; over {a.long}s (likely mixes): {len(long_)}")
        print(f" lossy under 192 kbps: {len(lossy_low)}; junk words: {sum(r['junk'] for r in g)}; empty artist: {sum(not r['artist'] for r in g)}; no ' - ' in title: {sum(' - ' not in (r['title'] or r['file']) for r in g)}")
        print(" shortest:", [(r["file"][:40], int(r["dur"])) for r in short[: a.top]])
        print(" longest:", [(r["file"][:40], int(r["dur"] // 60)) for r in long_[: a.top]])
    groups = defaultdict(list)
    for r in rows:
        if "error" not in r and r["key"]:
            groups[r["key"]].append(r)
    dups = {k: v for k, v in groups.items() if len(v) > 1}
    print(f"\n=== near-duplicates by cleaned title: {len(dups)} groups")
    for v in list(dups.values())[: a.top * 2]:
        print("  " + " | ".join(f"{r['file'][:40]}:{r['codec']}:{r['kbps']}k:{int(r['dur'])}s" for r in v))
    return 0


if __name__ == "__main__":
    sys.exit(main())
