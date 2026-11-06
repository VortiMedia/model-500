---
name: model-500-sets
description: Build and order DJ sets from real rekordbox data. Plans BPM and key flow, energy arc, transitions, track order, and cue plans for 2 CDJ-3000X and a DJM-A9. Use when the user says "order my second set", "organize this by BPM and key", "what plays after this", "plan the transitions", "where do I put cues", "build me a set". Do not use first for a set from a folder that is not in rekordbox, such as "a set from my new crate folder" (model-500-crate, then model-500-library). Do not use for tags and names (model-500-crate), playlist writes (model-500-library), or the stick (model-500-export). Do not use for producing music in Ableton.
---

# model-500-sets

Propose an order from measured data. The user decides by ear.

## Start
1. Read `~/model-500/state/PROFILE.md` for the stick name, music root, folders, playlists, and working preferences. If it is missing, copy `state/PROFILE.example.md` and ask the user to fill it. Also read `state/failures-private.md` when it exists.
2. Read `~/model-500/state/STATE.md`. Pending items about set order belong here.
3. Load tools with ToolSearch. They are deferred: `select:mcp__rekordbox__connect_database,mcp__rekordbox__get_playlists,mcp__rekordbox__get_playlist_tracks,mcp__rekordbox__get_track_details,mcp__rekordbox__get_tracks_by_bpm_range,mcp__rekordbox__get_tracks_by_key,mcp__rekordbox__search_tracks_by_filename`.
4. Call `connect_database`. Call it again before you trust BPM or key.
5. If model-500 did not load first, run `pgrep -x rekordbox` and `ls /Volumes`. Say in two lines where things stand.

## Tool order
1. MCP `rekordbox`: reads only. `get_playlist_tracks(playlist_id)`, `get_tracks_by_bpm_range(bpm_min, bpm_max)`, `get_tracks_by_key(key)`. History: `get_recent_sessions`, `get_session_tracks`, `get_most_played_tracks`.
2. Scripts: none. Hand playlist writes to model-500-library.
3. GUI: not needed for planning. Cues are set in rekordbox by the user.
4. The user: energy, feel, final order, every judgment by ear.

## Steps
1. Check the source. If the user names a folder, try a few file names with `search_tracks_by_filename`.
2. If the tracks are not in the library, stop. BPM and key do not exist yet. Route to model-500-crate ("Steps: set from a folder"), then model-500-library. Come back after Analyze.
3. Read the playlist. Build one table: track, BPM, key, length, genre.
4. If any BPM is 0 or any key is empty, call `connect_database` again. If still empty, route to model-500-library for Analyze.
5. Ask the user one question at a time. Start with: who is it for, how long, Sync on or off.
6. For a target length, add up the `length` column. Then see "Target length".
7. Propose the order. Use `references/rig-and-flow.md` for tempo and key rules.
8. Mark each row: measured (BPM, key, length) or guessed (energy, mood, transition).
9. Flag each jump over the tempo limit, and each key move with no wheel link.
10. Give the user one listening test: the two riskiest transitions, with times.
11. Write the cue plan as a table: track, hot cue letter A to H, position, purpose.
12. Save the agreed order in `state/STATE.md`. Hand to model-500-library to build the playlist.

## Target length
Played time is shorter than the sum of lengths, because transitions overlap.
1. Ask the user for the overlap per transition. Recommend 1 minute, and mark it guessed.
2. Use: played time = sum of lengths - overlap x (tracks - 1).
3. Add or drop tracks until played time is within 5 minutes of the target.
4. Show the sum, the overlap, and the played time. Example: 90 minutes with 17 tracks needs a sum of about 106 minutes.

## Energy arc
The agent cannot measure energy. Use three inputs only:
- The user's words, such as "track X is the peak".
- BPM as a weak signal.
- Play history, if `get_most_played_tracks` has any.

Present the arc as a guess. Ask the user to mark opener, peak, and closer.

## Earlier set as the pattern
`state/PROFILE.md` holds the order, length, and Sync choice of the user's first set. Use it as the pattern for a new set. Without it, ask for length, Sync on or off, and who the set is for.

## Gates
- This skill changes nothing. Any playlist change goes through model-500-library and its backup steps.
- Rips are for reference. The user's rule: buy before setting cues. Ask before the user spends cue time on a rip.
- Do not tell the user a set is ready. Say what was measured and what still needs ears.

## Do not
- **F26** Did: Said High precision analysis "should give better grids", flagged "haven't checked the docs". Result: A guess in a table beside confirmed rows. Rule: Mark each fact as checked or guessed.
- **F01** Did: Trusted reads right after analysis. Result: BPM and key showed 0. Agent said "1 of 18 done" when all 18 were done. Rule: Call `connect_database` first.
- **F38** Did: Judged how audio sounds. Result: The agent cannot hear. Rule: Report measurements. Ask the user to listen.
- **F25** Did: Grilled with multi-part questions. Result: The user's working preference is one question at a time. Rule: Ask one question. Recommend an answer. End with one next action.
- **F09** Did: Called `get_tracks_by_bpm_range` without `bpm_min`. Result: Input validation error. Rule: Load the schema first.

## Errors
| Error | Cause | Fix |
|---|---|---|
| BPM 0 or key empty | Stale read, or no analysis | `connect_database`, then model-500-library |
| `get_tracks_by_key` returns nothing | Stored key format differs | Read real values from `get_track_details` |
| `'bpm_min' is a required property` | Schema not loaded | Load it with ToolSearch |

## Example
The user says "order my second set". Read the playlist ID from the profile. Report: "21 tracks, BPM A to B, 3 flagged jumps. Draft order below. Measured: BPM and key. Guessed: energy. Which track opens?"

## Not proven
- Rig facts come from search snippets, not the manuals. See `references/rig-and-flow.md`.
- `get_tracks_by_key` uses the form `5A` in its docstring. The stored format in this library is unchecked.
- No MCP tool reads or writes cues. Whether `get_track_details` shows cues is unchecked.
- No order from this skill has been played.

## Context
Follow the working preferences in the profile. Use small returns. No subagents unless the user asks for a fan-out over many crates. Update `state/STATE.md` at the end.
