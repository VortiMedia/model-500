# Security

## Report a problem

Use a [private security advisory](https://github.com/VortiMedia/model-500/security/advisories/new). Do not open a public issue for a security problem. This is a small project with no response-time promise.

## mac-gui input

`mcp/mac-gui` can send real keyboard and mouse input. That path has never run outside tests with recorders.

- Allowlist: `com.pioneerdj.rekordboxdj`, `com.AlphaTheta.RMX-IGNITE-SampleManager`, `org.audacityteam.audacity4`. It is a constant in `mcp/mac-gui/src/mac_gui/apps.py`, with no setting or environment override.
- The target app must be frontmost before every event. If focus is lost, input stops.
- Clicks and scrolls are refused unless the top window at that point belongs to the target.
- Always refused: the Apple menu, Services, Quit and similar menu items, the `fn` key, and app-switching and session chords.
- Each action is logged to `state/gui-actions.log`. Real input writes an `attempt` line first, and sends nothing if that write fails.
- It reads permission state only. It never prompts for or bypasses macOS privacy controls. The grants you give apply to the app that starts the server.

## What writes where

| Tool | Writes | Guard |
|---|---|---|
| `scripts/install.sh` | Links in `~/.claude/skills` | Refuses to replace anything it did not make |
| `make_move_map.py` | The `--out` JSON | Reads the folder only |
| `safe_move.py` | Moves audio files, edits `master.db` and ANLZ files | Dry run unless `--go`. `--go` refuses while rekordbox runs and copies the whole rekordbox folder first |
| `set_metadata.py` | Edits `master.db` | Dry run unless `--go`. `--go` refuses while rekordbox runs |
| `audit_folder.py`, `read_pdb.py`, `stick_vs_mac.py` | Only the optional `--json` file | Read-only on audio and on the stick |
| `resolve_metadata.py` | The `--out` JSON and covers in `--covers-dir` | Reads audio only |
| `transcribe.py` | Transcripts in the output folder | Skips files already done |
| `ignite_prepare_sample` | WAV files, `~/Music/Samples/Drops` by default | Refuses `/Volumes`, the app and Pioneer folders. Will not overwrite unless told to |
| rekordbox MCP (third party) | The rekordbox database | Needs rekordbox closed. Its auto-backup misses `master.db-wal`, so back up the whole folder |

## Network

`resolve_metadata.py` calls the iTunes Search API and, when `yt-dlp` is installed, reads YouTube metadata without a download. `transcribe.py` downloads its model on the first run unless `HF_HUB_OFFLINE=1` is set. `uv` downloads dependencies. The ignite and mac-gui servers make no network calls of their own.

## Agent limits

The skills' ask-first rules are instructions to the agent. They are not locks. Only the guards in the table and the mac-gui list are in code. Keep a full backup before you allow any write.

Text from screens, web pages, tags, and transcripts is untrusted. The skills tell the agent to treat it as data, but this has not been tested against a hostile file.
