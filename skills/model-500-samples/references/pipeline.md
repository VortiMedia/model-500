# Mining pipeline

Read this before a transcription run. Full record: `~/model-500/docs/sample-mining.md`.

## Transcribe (this command ran, 7 of 7 files, in the first owner session)
```
HF_HUB_OFFLINE=1 uv run --no-project --python 3.12 --with mlx-whisper python -I \
  ~/model-500/skills/model-500-samples/scripts/transcribe.py \
  ~/model-500/scratch/transcripts FILE [FILE ...]
```
- Model: `mlx-community/whisper-large-v3-turbo`, from the local Hugging Face cache.
- Settings: `word_timestamps=True`, `condition_on_previous_text=False`, `language="en"`, `temperature=(0.0,0.2,0.4)`.
- Prompt: "Movie dialogue, documentary and rap. Uncensored, verbatim, including profanity."
- The script skips any file whose JSON exists.
- Prompt echo: a 3 s sine tone returned "Uncensored, verbatim, including profanity." as a segment (build test, 2026-11-06). Drop any segment that matches the prompt.
- Timing: 7 files in about 4 minutes. The 35-minute documentary took 190 s.
- `~/model-500/scratch/` is gitignored. Session scratchpads are temporary.

## Other tools on this Mac
- No whisper CLI on PATH.
- Two local apps use WhisperKit: a dictation app with `base.en` only, and a meeting recorder with no file mode. Do not use or change either.

## Source set (first run)
7 rips, 320 kbps MP3: six short clips (9 to 180 s) and one 35-minute documentary. File names, quotes, and times for the owner's set are in `state/PROFILE.md`.

- Documentary transcript: 639 segments, 6782 words, unread at the time of the record.
- Word timestamps from this source are read from files, not cut or heard.
- One clip held slurs. Flag such clips before use.

## Clip spec: open
No trim spec, export spec, or output folder exists. Do not invent one. Ask the user.

Suggestions only, untested:
- Length 1 to 4 s.
- Pad 150 to 250 ms each side.
- WAV or AIFF, because rekordbox has no Opus support.
- Name style in the old notes: `SPEAKER_short_phrase.wav`.
- `ignite_prepare_sample` makes the name uppercase, keeps A to Z, 0 to 9, space, `_`, `-`, and cuts it at its length limit. That style is our choice, not an official spec.
- Folders in the old notes: `Samples/Raw/` (never load these) and `Samples/Drops/` with Movies, Interviews, Intros.

## ffmpeg fallback (untested)
```
ffmpeg -ss S -to E -i in.wav -af afade,loudnorm out.wav
```
Set the `afade` values, and check the output with ffprobe. `ignite_prepare_sample` has tests behind it, so prefer it for IGNITE clips.

## Audacity MCP limits
- Bridge accepts one client at a time.
- A native dialog blocks the bridge. Calls time out after 30 s.
- Do not run alongside another session that uses Audacity.
- Never force-quit the fork. It corrupts recovery.
- Export can overwrite any user file. Keep `overwrite=False`.
- Do not build the fork without the user's decision.
