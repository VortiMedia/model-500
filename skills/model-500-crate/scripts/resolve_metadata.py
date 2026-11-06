"""Resolve artist/title/album/label/year/cover for files cheaply, before any agent.
Order: yt-dlp (YouTube ID in the filename) then the iTunes Search API.
Leaves what it cannot resolve in the output as status "unresolved" for agents.
Downloads iTunes covers (1200x1200) into --covers-dir. Reads audio files only.

Usage (python3 -I is fine; needs yt-dlp for the YouTube step):
  resolve_metadata.py FILE_OR_DIR [...] --out resolved.json --covers-dir DIR
Output items: {path, status: resolved|partial|unresolved, source, artist, title,
album, label, year, cover, source_url, query}. Text is HTML-unescaped.
Names from a video title or a guess are "partial": show them to the user."""
import argparse
import html
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request

EXT = (".m4a", ".mp3", ".opus", ".ogg", ".wav", ".aif", ".aiff", ".flac")
YT_ID = re.compile(r"\[([A-Za-z0-9_-]{11})\]|[ _-]([A-Za-z0-9_-]{11})\.[A-Za-z0-9]+$")


def clean(s):
    s = html.unescape(s or "")
    s = re.sub(r"\[[^\]]*\]", " ", s)
    s = re.sub(r"\((?:[^)]*(?:premiere|out now|preview|free download|official|forthcoming|taken from)[^)]*)\)", " ", s, flags=re.I)
    return re.sub(r"\s+", " ", s).strip(" -_")


def yt_meta(vid):
    try:
        r = subprocess.run(["yt-dlp", "--skip-download", "--no-warnings", "-J", f"https://www.youtube.com/watch?v={vid}"],
                           capture_output=True, text=True, timeout=60)
        d = json.loads(r.stdout)
        return {"title": d.get("track") or d.get("title"), "artist": d.get("artist") or d.get("creator"),
                "album": d.get("album"), "year": d.get("release_year"), "uploader": d.get("uploader"),
                "url": d.get("webpage_url")}
    except Exception:
        return None


def itunes(term):
    url = "https://itunes.apple.com/search?" + urllib.parse.urlencode({"term": term, "entity": "song", "limit": 3})
    try:
        with urllib.request.urlopen(url, timeout=20) as f:
            res = json.load(f).get("results", [])
        return res[0] if res else None
    except Exception:
        return None


def words(s):
    return set(re.findall(r"[a-z0-9]+", s.lower()))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--covers-dir", required=True, help="created if missing; use a scratch folder")
    ap.add_argument("--no-network", action="store_true", help="parse filenames only (for tests)")
    a = ap.parse_args()
    files = []
    for p in a.paths:
        p = os.path.expanduser(p)
        if os.path.isdir(p):
            files += [os.path.join(r, f) for r, _, fs in os.walk(p) for f in sorted(fs) if f.lower().endswith(EXT) and not f.startswith(".")]
        else:
            files.append(p)
    os.makedirs(a.covers_dir, exist_ok=True)
    out = []
    for path in files:
        base = os.path.splitext(os.path.basename(path))[0]
        m = YT_ID.search(os.path.basename(path))
        vid = (m.group(1) or m.group(2)) if m else None
        item = {"path": path, "status": "unresolved", "source": None, "yt_id": vid, "source_url": f"https://www.youtube.com/watch?v={vid}" if vid else None}
        guess = clean(base)
        yt = yt_meta(vid) if (vid and not a.no_network) else None
        term = guess
        if yt:
            item["source"] = "yt-dlp"
            item["uploader"] = yt.get("uploader")
            if yt.get("artist") and yt.get("title"):
                item.update(artist=html.unescape(yt["artist"]), title=html.unescape(yt["title"]), album=yt.get("album"), year=yt.get("year"), status="partial")
            term = f"{yt.get('artist') or ''} {yt.get('title') or guess}".strip()
        item["query"] = term
        hit = None if a.no_network else itunes(term)
        if hit and words(hit["trackName"]) & words(term) and words(hit["artistName"]) & words(term):
            art = hit["artworkUrl100"].replace("100x100bb", "1200x1200bb")
            cover = os.path.join(a.covers_dir, re.sub(r"\W+", "_", base)[:80] + ".jpg")
            try:
                urllib.request.urlretrieve(art, cover)
                item["cover"] = cover
            except Exception:
                pass
            item.update(source="itunes", status="resolved", artist=html.unescape(hit["artistName"]), title=html.unescape(hit["trackName"]),
                        album=html.unescape(hit.get("collectionName", "")), year=(hit.get("releaseDate") or "")[:4])
        out.append(item)
    json.dump(out, open(a.out, "w"), indent=1, ensure_ascii=False)
    from collections import Counter
    print("wrote", a.out, dict(Counter(i["status"] for i in out)))
    print("Unresolved and partial items need an agent or the user. Covers: iTunes only; next try Bandcamp og:image, then the video thumbnail cropped square.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
