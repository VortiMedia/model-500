# rekordbox MCP (third-party: davehenke/rekordbox-mcp)

The MCP lives outside this repo, at `~/rekordbox-mcp`. Its Python environment also runs the repo scripts that need pyrekordbox. Both paths are fixed in the skills.

**Back up first.** Quit rekordbox and copy the whole `~/Library/Pioneer/rekordbox` folder. The MCP's own auto-backup misses `master.db-wal` (F03).

## Setup

```sh
git clone https://github.com/davehenke/rekordbox-mcp ~/rekordbox-mcp
git -C ~/rekordbox-mcp checkout d8dce67
git -C ~/rekordbox-mcp apply ~/model-500/mcp/rekordbox-mcp-path.patch
uv sync --directory ~/rekordbox-mcp --frozen
claude mcp add --scope user rekordbox -- uv --directory ~/rekordbox-mcp run --frozen rekordbox-mcp
```

Commit `d8dce67` is the one this suite ran against.

rekordbox encrypts its database, and pyrekordbox needs a key to open it. Upstream's `setup-key.py` and the [pyrekordbox docs](https://github.com/dylanljones/pyrekordbox) cover that step. This repo has no script for it.

## Why the patch

Upstream `_detect_database_path` returns the parent folder. `masterPlaylists6.xml` is then not found, so new playlists skip the XML (F04). The patch returns `~/Library/Pioneer/rekordbox` when it holds `master.db`. A `git pull` can conflict with the patch, so read `git -C ~/rekordbox-mcp status --short` after each one.

## Traps

| Trap | Failure | Rule |
|---|---|---|
| `--database-path` in the upstream README does nothing | F04 | Use the patch |
| Reads go stale after analysis, with BPM 0 | F01 | Call `connect_database` again before a read |
| Writes while rekordbox is open | F02 | Check that rekordbox is closed |
| `import_tracks` leaves Artist and Title empty on tagged AIFF | F05 | Run `set_metadata.py`, then read back |
| `remove_broken_tracks` soft-deletes any ID you pass | F07 | Pass only IDs from `find_broken_tracks` |
| pyrekordbox `update_content_path(save=True)` rewrites ANLZ files | F06 | Use `safe_move.py` |
