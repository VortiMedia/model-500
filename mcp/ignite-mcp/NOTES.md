# ignite-mcp notes

Studied app 1.0.0.0336 on 2026-11-06. Vendor binaries, disassembly, and excerpts of them stay out of this repo. Format facts below are in our own words. Each one is marked observed, from the manual, or inferred.

## App
- JUCE native universal binary (x86_64, arm64). Bundle id `com.AlphaTheta.RMX-IGNITE-SampleManager`.
- No URL scheme, no CLI flags found, no document types in Info.plist. `sdef` could not run (needs full Xcode).
- The window's File and Help menus are drawn by JUCE. System Events saw only the Apple menu.

## State the app creates (seen after one launch)
- `~/Library/Application Support/com.AlphaTheta.RMX-IGNITE-SampleManager/`
  - `model/model.json`: plain JSON, `favorite` plus 15 banks with 4 slots each. All empty so far.
  - `bankcollection/bankcollection.json`: plain JSON, `{"bankcollection": []}`.
  - `settings/settings.json`: plain JSON.
  - `log/`: opaque binary usage logs. Not plain text. We did not try to decode them.

## Native backup and export (observed, 2026-11-07)
- Export root: `<drive>/AlphaTheta/RMX-IGNITE/RMX-IGNITESETTINGS.json`. Audio is in `01/`, `02/`, and so on directly under that root.
- JSON `bank_number` starts at zero. USB folder numbers start at one.
- App backup samples are flat: `model/samples/<file_name>`. There is no bank folder here.
- A read-only check found all 14 files in the native export. No private audio or app data is included in the tests.
- Native exports used classic PCM WAV format tag 1, 96 kHz, 24-bit stereo. Preparation writes that header without changing the PCM frames.
- No file prepared by this tool has been tested on the unit. An extended header was not proven to cause playback failure.

## Inferred from the app's resource text, not observed
- On assign, the app converts audio to a 2-channel WAV. The call passes 96000 and 24.
  Some inputs take a copy path instead. The condition was not traced.

## Official limits
- Unit manual: WAV or AIFF, 16 or 24 bit, 44.1, 48, 88.2, 96 kHz. A file over 16 s cannot be picked on the unit.
  Total bank length over 16 s may be trimmed. FAT16, FAT32, HFS+, exFAT. Some supported files still fail.
- App manual: 15 banks, slots A to D, 100 banks in BANK COLLECTION (not exported), gain -18 to +9 dB,
  BPM 40 to 999.99, Loop on C and D only and needs BPM and BEAT.
- Inferred from app text: input 10 ms to 30 min, export blocked if a bank exceeds 16 s.
- Sources: `RMX-IGNITE_DRI2033-A_EN_manual.pdf`, `RMX-IGNITE_SampleManager_EN.pdf` on downloads.support.alphatheta.com.

## Own choices, not official
- Target spec 96 kHz, 24 bit, stereo WAV: matches factory samples and the app's conversion call.
- Name style: uppercase, like `909 KICK`, max 24 characters. The app's name limit was not found.

## Why there is no write tool
Bank edits and export stay in Sample Manager. The native backup and export establish read paths, not a supported write API.
The original GUI test did not fill a bank, and no file prepared by this tool has played on the unit.
