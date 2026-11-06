# Library failures: rest and detail

Read this when a write fails, or when SKILL.md points here. Source: `docs/failures.md` and old skill `rekordbox-usb/references/failures.md`.

## Overflow from the Do not list
- **F09** Did: Called `get_tracks_by_bpm_range` without `bpm_min`. Result: Input validation error: 'bpm_min' is a required property. Rule: Load the MCP tool schema before the first call to any deferred tool.
- **F10** Did: Compared file names between stick and Mac as raw strings. Result: 2 tracks looked missing. The cause was NFC vs NFD. Rule: Normalize both sides to NFC before comparing names.

## ANLZ damage (F06)
- Symptom: after `update_content_path(save=True)`, ANLZ files lost the PVDI tag, and PCOB, PCO2, PSSI changed.
- Cause: pyrekordbox rewrites the whole file.
- Fix: `safe_move.py`. It backs up, splices only PPTH, and checks that every other tag is byte-identical.
- Repair: rebuild from a pre-change copy if damage happened. Backups sit in `~/rekordbox-backups/`.

## Empty tags after import (F05)
- Symptom: `import_tracks` with `auto_tag` left Artist and Title empty on tagged AIFF files.
- Fix: `set_metadata.py` sets Title, ArtistID, AlbumID, LabelID, ReleaseYear, Commnt. Read back.

## MCP path patch (F04)
- Upstream `_detect_database_path` returns the parent folder, so `masterPlaylists6.xml` is not found and new playlists skip the XML.
- Local fix: return `~/Library/Pioneer/rekordbox` when it holds `master.db`. The patch is uncommitted in `~/rekordbox-mcp`.
- `--database-path` in the README is not implemented.
- After any `git pull`, run `git -C ~/rekordbox-mcp status --short` and read the patch.

## Moves (F22)
Keep music under the music root in `state/PROFILE.md`. Moving a file without a path update breaks the rekordbox link. Use `safe_move.py`.

## Factory content (F08)
`state/PROFILE.md` holds the IDs. rekordbox may reseed this content. Check after reopening, and report.

## GUI labels (unproven)
`docs/tools/mac-gui.md` holds the rekordbox recipes for Reload Tag and Analyze. Labels come from locale files, not from a live `gui_ax_tree`. Run `gui_ax_tree(app="rekordbox", scope="menubar")` first and update that file.
