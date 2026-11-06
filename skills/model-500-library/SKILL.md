---
name: model-500-library
description: Work inside the rekordbox library through the rekordbox MCP. Imports tracks, builds playlists, edits track fields, moves files safely, removes factory content, takes full backups, protects ANLZ files, and traces missing tracks. Use when the user says "import these", "rekordbox says my track is missing", "track missing", "broken track", "file not found", "add to the playlist", "rename the playlist", "move the files", "fix the artist name", "back up rekordbox", "delete the factory samples", "reload tags". Do not use for naming files before import (model-500-crate), set order (model-500-sets), or anything on the stick (model-500-export).
---

# model-500-library

Own the Mac library: `~/Library/Pioneer/rekordbox` and music under the music root from the profile.

## Start
1. Read `~/model-500/state/PROFILE.md` for the stick name, music root, folders, playlists, and working preferences. If it is missing, copy `state/PROFILE.example.md` and ask the user to fill it. Also read `state/failures-private.md` when it exists.
2. Read `~/model-500/state/STATE.md`. Pending items about playlists, moves, and factory content belong here.
3. Load tools with ToolSearch. They are deferred: `select:mcp__rekordbox__connect_database,mcp__rekordbox__get_playlists,mcp__rekordbox__search_tracks`.
4. Call `connect_database`. Call it again before you trust a read and after every change.
5. Run `pgrep -x rekordbox`. A process means reads only. `rekordboxAgent` does not block writes.
6. If model-500 did not load first, run `ls /Volumes`. Say in two lines where things stand.

## Tool order
1. MCP `rekordbox`: search, stats, `import_tracks`, `create_playlist`, `add_tracks_to_playlist`, `remove_track_from_playlist`, `delete_playlist`, `find_broken_tracks`, `get_track_file_path`, `remove_broken_tracks`.
2. Scripts in `~/model-500/skills/model-500-library/scripts/`, for what the MCP cannot do. Run with `~/rekordbox-mcp/.venv/bin/python`.
3. GUI: `mcp__computer-use__*` if present, otherwise `mcp__mac-gui__*`. Use for Analyze, Reload Tag, playlist rename, Relocate.
4. The user: quit rekordbox, approve writes, name the exact click if GUI tools fail.

| Script | Does | Writes |
|---|---|---|
| `set_metadata.py meta.json` | Artist, title, album, label, year, comment, then read back | `master.db`, with `--go` only |
| `safe_move.py --map moves.json` | Move file, fix path, splice only PPTH, verify. `--from` and `--to` take one file, not a folder | Files, `master.db`, ANLZ, with `--go --backup-dir` only |
| `make_move_map.py OLD_DIR NEW_DIR --out moves.json` | Build the map for a whole folder | Only `--out` |

`set_metadata.py` and `safe_move.py` dry-run by default. Both refuse `--go` while rekordbox runs. Dry runs read a temp copy of the database, so they work with rekordbox open. `safe_move.py` needs full paths. It does not expand `~`.

## Every write
Do GUI steps first, with rekordbox open. Then:
1. Confirm rekordbox is closed. Ask the user to quit it. Never quit it yourself.
2. Back up the whole folder: `cp -Rp ~/Library/Pioneer/rekordbox ~/rekordbox-backups/NAME`.
3. Verify the copy: `diff -rq ~/Library/Pioneer/rekordbox ~/rekordbox-backups/NAME`. Expect no output.
4. Run the dry run. Show the user the plan. Wait for OK.
5. Run with `--go`, or call the MCP write tool.
6. Call `connect_database`. Read the fields back. Report only after readback.

## Import
1. Follow "Every write".
2. Call `import_tracks` with absolute paths, then `add_tracks_to_playlist` with the returned IDs.
3. Run `set_metadata.py` on all new tracks. `auto_tag` can leave Artist and Title empty.
4. Ask the user to open rekordbox and run Analyze Tracks. Then run Reload Tag for artwork.

## Rename a playlist
No MCP tool and no repo script renames a playlist. Use the GUI with rekordbox open. If the GUI tools fail, give the user the click.

## Missing track
1. Load `mcp__rekordbox__find_broken_tracks` and `mcp__rekordbox__get_track_file_path` with ToolSearch. Call `connect_database`.
2. Call `find_broken_tracks`. Call `get_track_file_path(track_id)` for the track the user named.
3. Check the stored path, comparing names as NFC (F10). A hit means a false alarm. Report it and stop:
```
python3 -I -c 'import os,sys,unicodedata as u;p=sys.argv[1];n=u.normalize("NFC",os.path.basename(p));print([f for f in os.listdir(os.path.dirname(p)) if u.normalize("NFC",f)==n])' "PATH"
```
4. Look for a moved or renamed file: `find ~/Music ~/Downloads -iname "*WORD*"`. Use one plain word of the title.
5. Report the old path and each hit. Ask the user which file is right.
6. Fix in the GUI with rekordbox open: right-click the track, `Relocate`. For many tracks, use `Auto Relocate`. Labels come from locale files, so read the menu first.
7. Or, with the user's OK, move the file back to the stored path. `safe_move.py` cannot fix this: it stops with `file missing on disk`.
8. Call `connect_database`, then `find_broken_tracks`. Report only after readback.

Never use `remove_broken_tracks` to fix a missing track. It removes the entry and leaves the problem. Use it only if the user says the file is gone for good.

## Gates
- Any move, rename, or delete under `~/Music` needs the user's OK first.
- `remove_broken_tracks` soft-deletes any ID. Pass only IDs from `find_broken_tracks`, or IDs listed in `state/STATE.md`.
- For `~/Music/rekordbox/Sampler` and any other file delete, list the files and sizes, then ask the user.
- If a delete leaves no other copy, name what is lost and ask once more.
- Keep the default My Tags unless the user says otherwise.

## Do not
- **F06** Did: Ran `update_content_path(save=True)` to fix moved paths. Result: pyrekordbox rewrote ANLZ files: PVDI lost, PCOB, PCO2, PSSI changed. Rule: Use `safe_move.py`. Never call that function with `save=True`.
- **F03** Did: Relied on the MCP auto-backup. Result: It copies `master.db` only. Recent changes sit in `master.db-wal`. Rule: Copy the whole folder and verify the copy.
- **F02** Did: Planned deletes while rekordbox ran. Result: Writes blocked or risked corruption. Factory clean-up waited two turns. Rule: Check rekordbox is closed before any write.
- **F07** Did: Passed track IDs to `remove_broken_tracks`. Result: It soft-deletes any ID, broken or not. The audio file stays. Rule: Run `find_broken_tracks` first.
- **F05** Did: Ran `import_tracks` with `auto_tag` on tagged AIFF files. Result: Artist and Title came out empty. Rule: Run `set_metadata.py`, then read back.
- **F01** Did: Trusted reads right after analysis. Result: BPM and key showed 0. Agent said "1 of 18 done" when all 18 were done. Rule: Call `connect_database` again first.
- **F08** Did: Left 32 factory samples and 2 Spotify stubs. Result: The user asked for the sample tracks to be removed. Rule: Audit a fresh Collection. Offer removal with a backup.
- **F04** Did: Followed the README flag `--database-path`. Result: It does nothing, and new playlists skipped `masterPlaylists6.xml`. Rule: After any `git pull`, check the patch in `~/rekordbox-mcp/rekordbox_mcp/database.py`.

F09 and F10: `references/failures.md`.

## Errors
| Error | Cause | Fix |
|---|---|---|
| `REFUSED: rekordbox is running` | App open | Ask the user to quit it |
| `backup dir exists` | Name in use | Pick a new name |
| `not in rekordbox` from `safe_move.py` | A folder path, or `~`, in `--from` | Use full file paths. Use `make_move_map.py` for a folder |
| `file missing on disk` from `safe_move.py` | File is not at the stored path | See Missing track |
| `'bpm_min' is a required property` | Schema not loaded | Load it with ToolSearch |

## Example
The user says "my draft playlist is now set 2". Names and paths come from the profile.
1. With rekordbox open, rename the playlist in the GUI.
2. Ask the user to quit rekordbox.
3. Back up and verify, as in "Every write", to a new folder under `~/rekordbox-backups/`.
4. Run `make_move_map.py "$HOME/Music/DJ/Draft" "$HOME/Music/DJ/Set 2" --out SCRATCH/moves.json`.
5. Run `safe_move.py --map SCRATCH/moves.json`. Show the 21 moves.
6. Ask the user. Wait for OK.
7. Run again with `--go --backup-dir ~/rekordbox-backups/pre-set2-rename`. That folder must be new.
8. Ask the user to reopen rekordbox. Call `connect_database`. Read the playlist and paths back.

## Not proven
`safe_move.py --go` and `set_metadata.py --go` have not run on a real track since they were written. The `safe_move.py` dry run ran on the real 21-file map. `Relocate` has not run. mac-gui labels for rekordbox come from locale files. Row order after `add_tracks_to_playlist` is unchecked.

## Context
Follow the working preferences in the profile. Use small returns. Use cheap subagents only for real fan-out. Update `state/STATE.md` at the end. Causes and fixes: `references/failures.md`.
