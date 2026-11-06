# ignite MCP

MCP server for RMX-IGNITE Sample Manager 1.0.0.0336. The app ships no MCP, CLI, or URL scheme.
**New MCPs load only in a new chat.** Registered at user scope as `ignite`.

Test: `python3 tests/test_ignite_mcp.py` (real stdio JSON-RPC, generated tones). Details: `mcp/ignite-mcp/NOTES.md`.

## Tools

| Tool | What it does | What the test proves |
|---|---|---|
| `ignite_status` | Install, version, running, library path, USB volumes | Reads the real app and its version |
| `ignite_list_library` | Banks and slots from `model.json` | Real empty library, plus a synthetic filled fixture |
| `ignite_validate_sample` | Format, depth, rate, length, bank budget; pass or fail with reason | Real ffprobe on each pass and fail case |
| `ignite_prepare_sample` | Trim, peak normalize, 96 kHz 24 bit stereo WAV | Real ffmpeg output, length and peak measured, input unchanged |
| `ignite_read_usb` | Read-only scan of a volume or folder | No tree change on a fixture; real FAT volume read |
| `ignite_gui_steps` | Exact steps for GUI-only work | Steps return for each action |

`ignite_prepare_sample` writes to `~/Music/Samples/Drops` by default. It refuses `/Volumes`, the app support
folder, the Pioneer folders, and the app bundle. It will not overwrite unless told to. `dry_run` writes nothing.

## GUI only

No write tool exists. These stay in the app, driven by the mac-gui MCP:

- Assign a sample to a slot; set start, end, gain, BPM, BEAT, Loop.
- Export to USB, Import, Backup, Restore. Import and Restore overwrite all current data.

Bank loading on the unit is done by the user: [BROWSE/UTILITY] > [BANK SELECT] > [USER].

## Limits

- Unit: WAV or AIFF, 16 or 24 bit, 44.1, 48, 88.2, 96 kHz. One file 16 s or less. FAT16, FAT32, HFS+, exFAT.
- Bank: 4 slots (A to D), 15 banks, 16 s total. Loop only on C and D, and it needs BPM and BEAT.
- App input: FLAC, ALAC, WAV, AIFF, MP3, AAC; 10 ms to 30 min.
- A pass is not a promise: the unit manual says some supported files still fail.

## Not proven

- No hardware test. No file from this tool has played on an RMX-IGNITE.
- No real export or filled library has been inspected. USB paths are inferred from the app's resource text.
  So filled-bank results in `ignite_list_library` and `ignite_read_usb` rest on synthetic fixtures.
- The 96 kHz 24 bit target and the name style are our choices. They are not official specs.
- Next step: export one bank to a scratch drive in the GUI, then correct the parser against it.
