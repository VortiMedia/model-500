---
name: model-500-export
description: Get sets from rekordbox onto a USB stick and check the result. Runs export through the GUI, verifies with read_pdb.py, checks OneLibrary, exports My Settings, cleans macOS junk, plans a backup stick, and runs the pre-gig checklist. Use when the user says "get my sets on the USB", "export to my stick", "is the stick ready", "wipe the stick", "start the stick over", "pre-gig check", "make a backup stick". Do not use for playlist edits (model-500-library), RMX-IGNITE banks (model-500-ignite), or set order (model-500-sets).
---

# model-500-export

Own the stick named in the profile and any backup stick. Golden rule: never drag files onto the stick.

## Start
1. Read `~/model-500/state/PROFILE.md` for the stick name, music root, folders, playlists, and working preferences. If it is missing, copy `state/PROFILE.example.md` and ask the user to fill it. Also read `state/failures-private.md` when it exists.
2. Read `~/model-500/state/STATE.md`. Pending items about the export belong here.
3. Run `ls /Volumes`. Run `df -h` on the stick path from the profile. Note its size and file system.
4. Run `defaults read "/Applications/rekordbox 7/rekordbox.app/Contents/Info.plist" CFBundleShortVersionString`. Use 7.2.11 or later. Avoid 7.2.12.
5. Run `pgrep -x rekordbox`. Open is fine for export: the GUI steps need it open.
6. Load `mcp__rekordbox__connect_database` and `mcp__rekordbox__get_playlist_tracks` with ToolSearch. They are deferred.
7. If model-500 did not load first, say in two lines where things stand.

## Tool order
1. MCP `rekordbox`, reads: `connect_database`, `get_playlists`, `get_playlist_tracks`. No MCP tool exports.
2. Script: `python3 -I ~/model-500/skills/model-500-export/scripts/read_pdb.py STICK_PATH`. It writes nothing. Add `--json OUT.json` for a compare. Before a wipe, also run `stick_vs_mac.py` from the same folder.
3. GUI: `mcp__computer-use__*` if present, otherwise `mcp__mac-gui__*`. Use for Reload Tag, Export Playlist, My Settings.
4. The user: approve the export, load the stick on a CDJ-3000X, report what shows.

Save JSON reports outside the audited volume. The scripts reject paths on the stick, including symlink aliases.

## Steps: export
1. Tell the user all GUI-only steps first, in order. Include any rename from model-500-library.
2. Check the playlists: BPM and key on every track, art counts. Route gaps to model-500-library.
3. Add up file sizes with `du -sh`. Compare with free space on the stick.
4. Reload Tag: select tracks in Collection, right-click, `Reload Tags`.
5. Export: select the playlist, right-click, `Export Playlist`, pick the device. Read the device name first.
6. My Settings: find the route with a screenshot of the device panel. Do not use `Import My Settings` or `Delete My Settings`.
7. Run `read_pdb.py`. Compare track and playlist counts with the plan in `state/STATE.md`.
8. Check that `PIONEER/rekordbox/exportLibrary.db` exists. `read_pdb.py` prints its size.
9. Clean junk last. See `references/stick.md`. Ask the user first.
10. Report: "Exported, not tested on a CDJ." Next action: the user loads it on a CDJ-3000X.

GUI recipes are unproven. The user must OK the first real export through mac-gui. Without it, give the exact clicks.

## Steps: wipe
"Start over" means: erase everything on the stick, then export again through the GUI.
1. Run `read_pdb.py STICK_PATH`. `No export.pdb` is no stop. It means the stick holds no export.
2. Run `ls -R STICK_PATH`.
3. Run `python3 -I ~/model-500/skills/model-500-export/scripts/stick_vs_mac.py STICK_PATH`. It compares the stick with `~/Music` by name and size.
4. Report the `stick_only`, `size_differs`, and `non_rekordbox` lists. Say a GUI export follows.
5. Get an OK. If any track is stick-only, name it and ask once more.
6. If the profile lists a firmware file to keep at the stick root, copy it off first, to a folder the user picks.
7. Ask the user to erase in Disk Utility: select the stick, Erase, keep the stick name from the profile, format `MS-DOS (FAT)`, scheme `Master Boot Record`.
8. Only if the user asks you to do it: run `diskutil list external`, read the disk ID back, get an OK, then run `diskutil eraseDisk FAT32 "STICK NAME" MBRFormat /dev/diskN`. This command has not run in this suite.
9. Copy the firmware file back if the user wants it. Then run the export steps.

## Pre-gig checklist
Run from `references/stick.md`. Tick only what you checked. Mark each other line "user".

## Backup stick
None exists today. Export again through rekordbox onto a second stick. Do not copy the first stick with Finder.

## Gates
- Before any stick write, ask the user. Exports count.
- Before any wipe: run the wipe steps through step 5.
- A wipe also removes any firmware file at the stick root, such as a mixer `.upd`. Ask the user, and copy it off first.
- If a delete leaves no other copy, name what is lost and ask once more.
- Never rename or move anything in `Contents` or `PIONEER`.

## Do not
- **F45** Did: Sent an audit report to a fixture audio path. Result: The read-only audit overwrote that file. Rule: Keep report paths outside the audited volume and replace reports atomically.
- **F13** Did: Deleted a friend's sets on request, backups included. Result: 162 tracks are gone for good. They were never in the Mac library. Rule: Ask once more when a delete leaves no other copy.
- **F12** Did: Wiped the stick, then needed a GUI export. Result: 162 stick-only tracks had no Mac copy. Rule: Diff stick against Mac and get an OK before any wipe.
- **F11** Did: Moved or renamed files on the stick. Result: `export.pdb` and `exportLibrary.db` hold exact paths, so tracks vanished. Rule: Change playlists in rekordbox and export again.
- **F15** Did: Exported the first set with screenshots and a click helper. Result: Stick showed 11 tracks. No CDJ load ever ran. Rule: Say "not tested on a CDJ". Never write "works".
- **F14** Did: Read an old modified date on `exportLibrary.db` as "not updated". Result: The date does not track writes. The file is encrypted. Rule: Do not judge by date. Do not try to open the file.
- **F16** Did: Planned an export from research notes. Result: CDJ-3000X reads only OneLibrary exports. Rule: Confirm app version and OneLibrary format first.
- **F18** Did: Tried to rename a playlist while rekordbox was open. Result: The user had to rename it before export. Rule: Give GUI-only steps first, in order.
- **F17** Did: Cleaned `._*` early, then created marker files. Result: 3 new `._` files. Rule: Clean last. Recheck after copies.

## Errors
| Error | Cause | Fix |
|---|---|---|
| `No export.pdb` | Nothing exported | Run the export steps. Before a wipe, go on with the wipe steps |
| Files show as missing | NFC vs NFD (F10) | `read_pdb.py` compares as NFC. Do not compare raw names |
| pyrekordbox fails on `export.pdb` | 0.4.3 cannot read it (F36) | Use `read_pdb.py` |

## Example
The user says "get my sets on the USB". Report: "Stick is mounted, no export yet. 3 GUI steps. First: rename the playlist as planned in STATE.md. Do it now?"

## Not proven
- `stick_vs_mac.py` ran on the real stick with no tracks on it. Track matching ran on fixtures only.
- No export has been tested on a CDJ. `read_pdb.py` reads `export.pdb`, so it cannot prove OneLibrary.
- mac-gui export route: the device step and My Settings route are unknown.
- Whether My Settings load on the CDJ-3000X is unverified.

## Context
Follow the working preferences in the profile. Use small returns. Update `state/STATE.md` at the end. Facts: `references/usb-principles.md`, `references/stick.md`.
