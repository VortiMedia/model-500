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

## Inferred from the app's resource text, not observed
- Export root: `<drive>/AlphaTheta/RMX-IGNITE/RMX-IGNITESETTINGS.json`, plus `samples/<NN>/`.
- App samples: `model/samples/<NN>/`.
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
No populated `model.json` or real export was seen, and the unit cannot be tested from here.
The test GUI session could not get a filled bank: a click sent to the app's process had no effect, and taking
focus was not an option while the owner used the machine. A real export to a scratch drive is the next step.
