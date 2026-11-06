---
name: model-500-crate
description: Research and clean music files before they enter rekordbox. Identifies tracks, fixes tags and names, finds covers, audits download folders, flags rips and previews, converts Opus, builds the buy list. Use when the user says "find covers", "find album covers for the new downloads", "who made this track", "audit my downloads", "clean up this rip folder", "what should I buy", "go through my new crate folder", "build a set from this folder". Do not use for rekordbox database edits, playlists, or moves of imported tracks (model-500-library), for set order once tracks are in rekordbox (model-500-sets), or for dialogue drops (model-500-samples).
---

# model-500-crate

Work on files, names, and tags before import. Hand finished files to model-500-library.

## Start
1. Read `~/model-500/state/PROFILE.md` for the stick name, music root, folders, playlists, and working preferences. If it is missing, copy `state/PROFILE.example.md` and ask the user to fill it. Also read `state/failures-private.md` when it exists.
2. Read `~/model-500/state/STATE.md`. Pending items about names, folders, and the buy list belong here.
3. If model-500 did not load first, run `pgrep -x rekordbox` and `ls /Volumes`. Say in two lines where things stand.
4. Load `WebSearch` and `WebFetch` with ToolSearch when needed. They are deferred. Load the rekordbox tools only to check for duplicates.

## Tool order
1. Scripts in `~/model-500/skills/model-500-crate/scripts/`. All take `--help`. Covers and audits need no MCP.
2. MCP `rekordbox`, reads only, and only to check for duplicates: `connect_database`, `search_tracks_by_filename`.
3. GUI: not needed. Reload Tag belongs to model-500-library.
4. The user: confirm doubtful names, decide what to buy.

| Script | Does | Writes |
|---|---|---|
| `audit_folder.py DIR` | Codec, bitrate, likely previews, likely mixes, duplicates | Nothing, or `--json` output |
| `resolve_metadata.py PATH --out X.json --covers-dir DIR` | yt-dlp, then iTunes: names and covers | JSON and covers in a scratch folder |

Run both with `~/rekordbox-mcp/.venv/bin/python`. Put output in the session scratchpad.

## Steps: covers only
1. Pick the folder. Use the one the user named. Otherwise run `ls -td ~/Downloads/*/ | head -5`, recommend the newest, and ask.
2. Run `resolve_metadata.py FOLDER --out SCRATCH/covers.json --covers-dir SCRATCH/covers`. Without a YouTube ID in the name, it searches iTunes by file name.
3. Make one contact sheet. See `references/recipes.md`.
4. For items with no `cover`, use WebSearch: Bandcamp, then the video thumbnail.
5. Report found and missing counts. Covers stay in the scratch folder. Ask the user before you embed any cover.

## Steps: set from a folder
BPM and key exist only after import and Analyze.
1. Run `audit_folder.py`. Report counts first.
2. Ask the user to drop previews and mixes, and to pick a shortlist. Recommend a shortlist over a full import.
3. Hand the shortlist to model-500-library for import and Analyze.
4. Hand to model-500-sets for the order and target length.

## Steps: new folder
1. Run `audit_folder.py`. Report counts first: tracks, previews, mixes, lossy under 192 kbps.
2. Show the user the doubtful names. Wait for the answer.
3. Run `resolve_metadata.py`. `resolved` came from iTunes. `partial` came from a video title or a guess.
4. Use WebSearch only for `partial` and `unresolved` items.
5. Write the rename map with source URLs. Do this before any rename.
6. Name files `Artist - Title (Mix).ext`. No IDs or catalog numbers in names. Catalog number goes in Comments and `TXXX:CATALOGNUMBER`. Replace characters FAT cannot hold.
7. Check covers on one contact sheet. See `references/recipes.md`.
8. Hand off to model-500-library for import.

## Steps: buy list
1. Read `_rename-map.json` in the backup dir from `state/PROFILE.md`.
2. List each rip: artist, title, source URL, store result. Mark each store result as checked or guessed.
3. Say that rips are for reference. Tell the user to buy a track before playing it out and before setting cues.

## Gates
- `~/Downloads` and `~/Music` belong to the user. Ask before any rename, move, or delete there.
- Opus originals stay in their download folder (see profile) until the user confirms.
- A rip with no store copy may be the only copy. Name it and ask before a delete.

## Do not
- **F20** Did: Trusted Artist tags and file lengths from rips. Result: Artist was the uploader. A lecture video sat in a crate. A 439-track folder had 82 likely previews. Rule: Run `audit_folder.py`. Show the user the doubtful names before import.
- **F21** Did: Stripped YouTube IDs from names. Result: A later buy list needs the sources. All 11 tracks of the first set were still rips. Rule: Write a rename map with source URLs before renaming.
- **F19** Did: Imported YouTube Opus rips. Result: rekordbox has no Opus support. Rule: Convert with ffmpeg to AIFF. Say plainly that this does not raise quality.
- **F22** Did: Built the first set from a folder under `~/Downloads`. Result: The user wanted the files moved out of Downloads into the music root. Rule: Keep music under the music root from the profile.
- **F24** Did: Ran 6 agents on 38 tracks for metadata. Result: 373k tokens, garbled names, `&amp;` left in. Rule: Run `resolve_metadata.py` first. Agents get leftovers only, with a name verifier.
- **F23** Did: Opened artwork one by one. Result: Slow and token-heavy. Rule: Use one ffmpeg contact sheet. Order: iTunes, Bandcamp, video thumbnail.

## Errors
| Error | Cause | Fix |
|---|---|---|
| `resolve_metadata.py` shows only `unresolved` | No network, or no iTunes match for the name | Check the name, then use WebSearch |
| `audit_folder.py` shows probe errors | Bad file, or ffprobe missing | Show the user the file name |
| ffmpeg `drawtext` fails | Not in this build (F36) | Use `tile` with no text |

## Example
The user says "audit my new crate folder". Run `audit_folder.py` on the folder named in the profile. Report: "439 tracks, 82 likely previews. Top 10 doubtful names below. Keep or skip?"

## Not proven
- iTunes matches rest on word overlap. A match can be the wrong version.
- 32-bit float WAV support in rekordbox is unverified. Test one file first.
- `resolve_metadata.py --help` ran in the build. No network run was repeated there.

## Context
Follow the working preferences in the profile. Use small returns. Use cheap subagents only for real fan-out. Update `state/STATE.md` at the end. Details: `references/recipes.md`. Full log: `~/model-500/docs/failures.md`.
