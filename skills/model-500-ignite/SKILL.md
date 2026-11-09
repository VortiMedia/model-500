---
name: model-500-ignite
description: Load and manage drops on the RMX-IGNITE through the ignite MCP, with mac-gui for steps only the Sample Manager app can do. Checks sample limits, prepares WAV files, reads banks, plans bank layout, and reads the IGNITE export on a drive. Use when the user says "put this drop on the IGNITE", "fill bank 3", "what's on my IGNITE", "will this file work on the IGNITE", "export my banks". Do not use for finding or cutting lines (model-500-samples) or for rekordbox exports (model-500-export).
---

# model-500-ignite

Take finished clips from model-500-samples. Put them in banks in RMX-IGNITE Sample Manager.

## Start
1. Read `~/model-500/state/PROFILE.md` for the stick name, music root, folders, playlists, and working preferences. If it is missing, copy `state/PROFILE.example.md` and ask the user to fill it. Also read `state/failures-private.md` when it exists.
2. Read `~/model-500/state/STATE.md`. Pending items about the IGNITE and mac-gui belong here.
3. Load tools with ToolSearch. They are deferred: `select:mcp__ignite__ignite_status,mcp__ignite__ignite_list_library,mcp__ignite__ignite_validate_sample,mcp__ignite__ignite_prepare_sample,mcp__ignite__ignite_read_usb,mcp__ignite__ignite_gui_steps`.
4. Call `ignite_status`. If the tools do not load, tell the user to open a new chat.
5. If model-500 did not load first, run `pgrep -x rekordbox` and `ls /Volumes`. Say in two lines where things stand.

## Tool order
1. MCP `ignite`: all reads, checks, and sample preparation.
2. Scripts: none. ffprobe only for a second check.
3. GUI: `mcp__computer-use__*` if present, otherwise `mcp__mac-gui__*`. Use for assign, export, backup.
4. The user: at the unit, bank load and hardware test. Also any decision on names or layout.

| Tool | Use |
|---|---|
| `ignite_status` | Install, version, running, library path, USB volumes |
| `ignite_list_library` | Banks and slots |
| `ignite_validate_sample(path, bank_used_seconds)` | Pass or fail with a reason |
| `ignite_prepare_sample(..., dry_run=true)` | Trim, peak normalize, 96 kHz 24 bit stereo WAV |
| `ignite_read_usb(volume_path)` | Read-only scan of a drive |
| `ignite_gui_steps(action)` | Steps for `assign`, `export`, `import`, `backup`, `restore`, `unit_load` |

## Steps
1. Call `ignite_list_library`. Note used seconds in the target bank.
2. Call `ignite_validate_sample` on each clip. Fix any fail with `ignite_prepare_sample`.
3. Plan the layout as a table: bank, slot, clip, seconds. Check the 16 s bank total.
4. Ask the user to OK the plan. Ask before taking focus.
5. Call `ignite_gui_steps(action="assign")`. Run the steps in the GUI, or give them to the user.
6. Call `ignite_list_library` again. Check each expected slot. Investigate missing paths before calling an audio file corrupt. Re-assign any slot whose `wav_format_tag` is not 1.
7. Call `ignite_gui_steps(action="export")`. Tell the user the drive name before you click OK.
8. Call `ignite_read_usb` on that drive. Each slot needs `wav_format_tag` 1 and `appledouble_found` false. Re-assign any other slot in the GUI.
9. Give the user the `unit_load` steps: [BROWSE/UTILITY] > [BANK SELECT] > [USER].
10. Report "not tested on the unit" until the user plays it.

## GUI notes
- The File menu is drawn inside the app window. It is not in the macOS menu bar, so `gui_menu` cannot reach it.
- Use `gui_screenshot`, then `gui_click`. Dry-run first. Read the screen again after each click.
- App allowlist name in mac-gui: `com.AlphaTheta.RMX-IGNITE-SampleManager`.
- Real mac-gui input has never run. The user must watch the first test.

## Limits
- Unit: WAV or AIFF, 16 or 24 bit, 44.1, 48, 88.2, 96 kHz. One file 16 s or less.
- Bank: slots A to D, 15 banks, 16 s total. Loop only on C and D, and it needs BPM and BEAT.
- BANK COLLECTION banks do not export. Details: `references/limits.md`.

## Gates
- Import and Restore overwrite ALL current data. Run Backup first. Ask the user.
- First export goes to a scratch drive, not the music stick. The user decides this.
- Do not edit `model.json` or any file in the app support folder. No write tool exists on purpose.
- Before any sample delete, check for another copy. If none exists, name it and ask once more.

## Do not
- **F43** Did: Used an inferred folder layout. Result: All 14 native export samples appeared missing. Rule: Check flat app samples and one-based USB bank folders separately.
- **F44** Did: Checked the codec only. Result: FFmpeg wrote an extended WAV header. Rule: Prepare classic PCM headers and verify unchanged PCM frames. Hardware playback stays unverified.
- **F46** Did: Wrote WAVs into the app folder by hand, then exported. Result: The stick had tag 65534 files and `._` files, and the scan passed them. Rule: Check `wav_format_tag` and `appledouble_found` after export.
- **F33** Did: Looked for a way to drive Sample Manager. No MCP covered it. Result: Samples must not be dragged onto the stick. Rule: Use the app's Export. Never drag samples onto the stick.
- **F39** Did: Sent one pid-targeted click to the app to fill a bank. Result: No effect. Rule: Bank edits need the app in front, or the user.
- **F40** Did: Early mac-gui tests took focus. Result: the user's keystrokes may have been lost. Rule: Ask the user before taking focus.
- **F15** Did: Exported a first set through screenshots and a click helper. Result: Stick showed 11 tracks, with no CDJ load. Rule: Say "not tested" until the user plays it. This applies to the unit too.
- **F38** Did: Judged how audio sounds. Result: The agent cannot hear. Rule: Report length and peak. Ask the user to listen.

## Errors
| Error | Cause | Fix |
|---|---|---|
| `ignite_*` tools missing | MCP loads only in a new chat | Ask the user to open one |
| `ignite_prepare_sample` refuses the folder | `/Volumes`, app, or Pioneer path | Use a folder the user approved |
| Bank total over 16 s | Clips too long | Export is blocked. Trim or move a clip |

## Example
The user says "put the first drop on bank 1". Validate the clip. Report: "4.5 s, pass. Bank 1 is empty, so 11.5 s stay free. Slot A?" After OK, run the assign steps.

## Not proven
- No hardware test. No file from this tool has played on an RMX-IGNITE.
- Paths were checked against a native backup and export. Automated tests use generated samples with those layouts.
- 96 kHz 24 bit and the name style are our choices. A validation pass is not a promise.

## Context
Follow the working preferences in the profile. Use small returns. Update `state/STATE.md` at the end.
