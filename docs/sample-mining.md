# Sample mining (dialogue drops for DJ sets)

Source: read-only review of the first mining session (transcript copied 2026-11-06), its
scratchpad, and the source folder. Nothing was re-run. Gaps are marked NOT DONE.
Rips and dialogue clips are for reference and for live use the DJ has rights to. Buy or license
what you play out.

## Status (read first)
- The session stopped after step 3 (transcription). The user interrupted the next turn.
- NOT DONE: line mining, ranking, trimming, export, naming, rekordbox import, any feedback loop.
- No trim spec, export spec, or output folder exists. Do not invent one. Ask the user.
- No user feedback beyond the original request. Nothing liked or rejected is on record.

## Request (intent)
Mine all files in a source folder with local voice transcription for strong lines usable in
a DJ set. Quote examples from the owner are in `state/PROFILE.md`. Use a dynamic workflow,
reuse the local transcription models already on the Mac, prioritize efficiency.

## Source type
- A source folder with 7 rips, 320 kbps MP3, 0.09 GiB, title-based names, tags and art
  embedded. Also a playlist file, a track list, a readme, and a hidden folder of rip logs.
- Durations in seconds: 37, 58, 36, 125, 180, 9, and one 35-minute documentary at 2075.
  Titles and quotes sit in `state/PROFILE.md`.

## Process, as run
1. Survey: `find`, `du`, `ffprobe -show_entries format=duration` per file. Ran.
2. Tool scout: no whisper CLI on PATH. Found two local apps that use WhisperKit (a dictation app with only a `base.en` model, and a meeting recorder with no file mode), `uv`, and a cached
   `mlx-community/whisper-large-v3-turbo` plus uv-cached `mlx_whisper`. Chose mlx-whisper.
3. Transcribe (worked, exit 0, 7/7). Script: scratchpad `transcribe.py`
   (a temporary session scratchpad).
   Output: `transcripts/<slug>.json` (segments, word timestamps, probabilities,
   no_speech, logprob) and `<slug>.txt` (`[mm:ss.ss-mm:ss.ss] text`), plus `index.json`.
4. Read the short transcripts; head of the long one. Ran.
5. Planned next (NOT DONE): workflow fan-out over transcripts to score and pick lines.

## Exact command that worked
```
HF_HUB_OFFLINE=1 uv run --no-project --python 3.12 --with mlx-whisper python -I \
  transcribe.py OUT_DIR SOURCE_DIR/*.mp3
```
Settings in the script: model `mlx-community/whisper-large-v3-turbo`, `word_timestamps=True`,
`condition_on_previous_text=False`, `language="en"`, `temperature=(0.0,0.2,0.4)`,
`initial_prompt="Movie dialogue, documentary and rap. Uncensored, verbatim, including profanity."`.
Skips files whose JSON exists. Slug = lowercase title, non-alnum to `-`, 40 chars.
Timing: 7 files in about 4 minutes; the 35-minute doc took 190 s, the others 2 to 17 s each.

## Tools and MCPs used
- Used: Bash, Read, Write, Skill `workflow-authoring` (loaded, no workflow launched), ffprobe,
  uv, mlx-whisper. ffmpeg is installed. No MCP was used.

## Transcript quality (read from files)
- Short drops came out clean, profanity intact. Examples at word level exist in the JSON.
  The owner's best line was found at two points in one clip; times are in `state/PROFILE.md`.
- One clip includes slurs; flag before any use.
- Wall Street greed clip gave 1 segment (9 s). Doc transcript: 639 segments, 6782 words, unread.
- Some segments are empty stubs. Filter on `no_speech` and empty text.

## Folder layout and naming (what exists)
- Inputs: the source folder's `*.mp3` files. Transcripts: session scratchpad `transcripts/` (temp, not durable).
- NOT DONE: clip output folder. Proposed in this repo, unconfirmed by the user:
  keep clips under the music root in `state/PROFILE.md`, never write into
  `~/Music` or the USB from an agent without the user saying so.

## Failures (Did / Result / Rule)
- Did: searched for a CLI to transcribe. Result: none on PATH; WhisperKit cache had only
  `base.en`; the meeting recorder has no file mode. Rule: use mlx-whisper via uv; check the HF cache first.
- Did: one Bash call that cat'd all short transcripts and headed the long one. Result: exit 1,
  then the user interrupted the turn (reason not given). Rule: read long transcripts in slices.

## Rules for the next run
- Pick lines from word timestamps, not segment bounds. Pad 150 to 250 ms each side (suggestion,
  untested). Export WAV or AIFF, since rekordbox has no Opus support.
- Dialogue drops are fine live. Posted mixes (SoundCloud, Mixcloud, IG, YouTube) can get
  flagged for copyrighted film or TV audio. Keep a live-only tag in file names or a playlist.
- Do not touch the rekordbox database or the USB while rekordbox is open; hand paths to the user.
- Report the quote, source file, in/out times, and a one-line why. Short list, best first.

## Next action
Ask the user to confirm: output folder, clip format, live-only versus posted use. Then run the
mining pass over the existing JSON. Keep that session as the owner until the user hands it over.
