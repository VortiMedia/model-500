"""Transcribe audio files with word timestamps through mlx-whisper. Skips files already done.

Copied from the first working run. The settings are unchanged. Only the
command-line parsing is new, and the import is late so that --help needs no model.

Usage:
  HF_HUB_OFFLINE=1 uv run --no-project --python 3.12 --with mlx-whisper python -I \\
    transcribe.py OUT_DIR FILE [FILE ...]
Output per file: OUT_DIR/SLUG.json (segments, word times, no_speech, logprob) and
OUT_DIR/SLUG.txt ([mm:ss.ss-mm:ss.ss] text). Also OUT_DIR/index.json.
Empty segments can occur. Filter on no_speech and empty text before you trust a line."""
import argparse
import json
import pathlib
import re
import time

MODEL = "mlx-community/whisper-large-v3-turbo"
PROMPT = "Movie dialogue, documentary and rap. Uncensored, verbatim, including profanity."


def stamp(s):
    return f"{int(s // 60):02d}:{s % 60:05.2f}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out_dir")
    ap.add_argument("files", nargs="+")
    a = ap.parse_args()

    import mlx_whisper

    out = pathlib.Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    index = []
    for i, src in enumerate(a.files, 1):
        src = pathlib.Path(src)
        slug = re.sub(r"[^a-z0-9]+", "-", src.stem.lower()).strip("-")[:40]
        jpath = out / f"{slug}.json"
        tpath = out / f"{slug}.txt"
        index.append({"slug": slug, "source": str(src)})
        if jpath.exists():
            print(f"skip {slug}", flush=True)
            continue
        t0 = time.time()
        r = mlx_whisper.transcribe(
            str(src),
            path_or_hf_repo=MODEL,
            word_timestamps=True,
            condition_on_previous_text=False,
            initial_prompt=PROMPT,
            language="en",
            temperature=(0.0, 0.2, 0.4),
        )
        segs = [
            {
                "start": s["start"],
                "end": s["end"],
                "text": s["text"].strip(),
                "no_speech": round(s.get("no_speech_prob", 0), 3),
                "logprob": round(s.get("avg_logprob", 0), 3),
                "words": [
                    {"w": w["word"], "s": round(w["start"], 2), "e": round(w["end"], 2), "p": round(w["probability"], 2)}
                    for w in s.get("words", [])
                ],
            }
            for s in r["segments"]
        ]
        jpath.write_text(json.dumps({"source": str(src), "segments": segs}, indent=0))
        tpath.write_text("\n".join(f"[{stamp(s['start'])}-{stamp(s['end'])}] {s['text']}" for s in segs) + "\n")
        print(f"done {i}/{len(a.files)} {slug} segs={len(segs)} took={time.time() - t0:.0f}s", flush=True)

    (out / "index.json").write_text(json.dumps(index, indent=1))
    print("ALL DONE", flush=True)


if __name__ == "__main__":
    main()
