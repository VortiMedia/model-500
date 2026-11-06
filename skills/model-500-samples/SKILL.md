---
name: model-500-samples
description: Mine dialogue drops from movies, clips, and interviews. Takes a source file the user may use, transcribes with mlx-whisper, finds the line, trims, normalizes, exports, and names the clip, with ffmpeg by default. The Audacity MCP needs a fork that is not built. Use when the user says "mine samples from this movie", "find the juicy lines", "cut this quote", "trim this drop", "open this in Audacity", "go through my drops folder". Do not use for loading clips on the unit (model-500-ignite), for music tracks (model-500-crate), or for track order (model-500-sets).
---

# model-500-samples

Turn a source file into a named clip. Hand the clip to model-500-ignite.

## Status
The first mining run stopped after transcription. Line picks, trim, export, and naming have never run. A new source needs no hand-over: proceed. To continue the first run, check the profile for a live owner session and ask the user whether it is still live. If it is, stop. If not, proceed.

## Start
1. Read `~/model-500/state/PROFILE.md` for the stick name, music root, folders, playlists, and working preferences. If it is missing, copy `state/PROFILE.example.md` and ask the user to fill it. Also read `state/failures-private.md` when it exists.
2. Read `~/model-500/state/STATE.md`.
3. If model-500 did not load first, run `pgrep -x rekordbox` and `ls /Volumes`. Say in two lines where things stand.
4. If the user gave no source, ask for the clip path.
5. Get three answers from the user if `state/STATE.md` has none: output folder, clip format, live-only or posted use. Ask one at a time.
6. Use the ffmpeg path. Probe Audacity only if the user asks for it: load `mcp__audacity__project_get_info` with ToolSearch, then call it once. A connect error on 2212 means no fork runs.

## Tool order
1. Scripts and CLI, the default: `transcribe.py`, ffmpeg, ffprobe, yt-dlp. For IGNITE clips, use `mcp__ignite__ignite_prepare_sample`, deferred, to trim and normalize.
2. MCP `audacity`: blocked today (F41). It works only with the fork `Audacity4-Dev-MCP` running.
3. GUI: `mcp__computer-use__*` if present, otherwise `mcp__mac-gui__*`, on Audacity 4. Unproven.
4. The user: choose lines, listen to results, confirm names.

## Steps
1. Source: use a file the user has the right to use. Rips are for reference and for live use the user has rights to. Keep the source URL and the folder the user approves.
2. Probe: `ffprobe -show_entries format=duration FILE`. Find silence: `ffmpeg -i FILE -af silencedetect -f null -`.
3. Transcribe to `~/model-500/scratch/transcripts`. `transcribe.py` creates the folder. The command is in `references/pipeline.md`.
4. Search with `grep -i "QUOTE" *.txt`. Read long files in slices with Read `offset` and `limit`.
5. Take times from the word entries in the JSON, not from segment bounds.
6. Report a short list, best first: quote, source file, in and out times, one line why.
7. Wait for the user to pick. Flag slurs and likely mishears.
8. Trim and normalize. Use one of the ffmpeg paths below.
9. Check with `ffprobe`: duration, codec, sample rate. Ask the user to listen.
10. Name the clip. Hand off to model-500-ignite.

## Trim path: IGNITE clip (tested on generated tones only)
Call `ignite_prepare_sample` with `input_path`, `name`, `output_dir`, `start_seconds`, `end_seconds`, `peak_db=-1`, `dry_run=true`. Read the plan. Run it again with `dry_run=false`. It refuses to overwrite by default. Its default folder, `~/Music/Samples/Drops`, does not exist yet. The tool creates it on a real run, so confirm the folder with the user.

## Trim path: plain clip (tested on a generated tone only)
This trims and adds 10 ms fades. `-n` refuses to overwrite. It does not normalize.
```
ffmpeg -n -ss IN -to OUT -i SOURCE -af "afade=t=in:d=0.01,areverse,afade=t=in:d=0.01,areverse" -ar 48000 -c:a pcm_s24le CLIP.wav
```

## Trim path: Audacity (never run, needs the fork)
`project_new`, `project_import_audio`, `select_region`, `edit_trim`, `effect_fade_in`, `effect_fade_out`, `normalize`, `project_export_audio` with `overwrite=False`. Details: `~/model-500/docs/tools/audacity.md`.

## Gates
- Ask before any write under `~/Music`, or any rename in `~/Downloads`. Never write to the stick.
- Flag any clip that holds slurs or private speech before any use.
- Posted mixes can get flagged for film or TV audio. Mark live-only clips in the name or a playlist. Buy or license what you play out.

## Do not
- **F41** Did: Installed the Audacity MCP. Result: It needs a fork bridge on 2212. Stock Audacity 4.0.2 has none. Rule: Use ffmpeg by default. Call `project_get_info` only if the user asks for Audacity.
- **F27** Did: Ran Whisper over a section of a house-music mix. Result: It output only "I", repeated over music. Rule: Separate vocals first. Never trust text over a music bed.
- **F29** Did: Transcribed 13 minutes of clips, 10 of them silent. Result: Whisper invents text on silence. Rule: Detect silence first. Drop non-speech spans.
- **F30** Did: Started at the user's "around 28 min". Result: The voice was at 25:44 to 26:17 and 26:42 to 27:24. Rule: Search the transcript for the quote.
- **F28** Did: Passed Whisper output through as final. Result: "Seneca" came out as "Xenica". Rule: Flag likely mishears. Ask the user to confirm proper nouns.
- **F31** Did: Said an interrupted cut created no files. Result: The output folder held six WAVs. Rule: After any interrupt, list the output folder before you report.
- **F32** Did: Searched the web for the exact lines. Result: Nothing matched. Rule: Say "not found". Offer Shazam at the timestamp. Do not guess origin.
- **F42** Did: Printed all transcripts in one Bash call. Result: Exit 1, then the user interrupted. Rule: Read long transcripts in slices.

## Errors
| Error | Cause | Fix |
|---|---|---|
| `Connect call failed ('127.0.0.1', 2212)` | No fork bridge | Use the ffmpeg path |
| Audacity call times out after 30 s | Native dialog blocks the bridge | Ask the user to close it |
| `no_speech` high, or empty segment | Silence or music | Drop the segment |
| Segment repeats the prompt text | Whisper echo on non-speech. A 3 s sine tone gave this in the build | Drop the segment |

## Example
The user says "mine samples from this movie". Check for a transcript. Transcribe if none exists. Report: "Top line: 'quote text', 00:26.54 to 00:31.00, clip A. It repeats at 00:35.32. Cut the first one?"

## Not proven
Padding of 150 to 250 ms is a suggestion. Vocal separation has no installed tool, so F27 stays open: flag music beds to the user. `faster-whisper` in the Audacity MCP is not installed. Do not call `transcription_set_model`. Audacity fork not built. No download command has run in this suite.

## Context
Follow the working preferences in the profile. Use small returns. Use cheap subagents only for real fan-out over transcripts. Update `state/STATE.md` at the end. Process record: `references/pipeline.md`.
