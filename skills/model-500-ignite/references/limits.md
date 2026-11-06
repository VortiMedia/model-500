# RMX-IGNITE limits and layout

Read this when a clip fails validation or when you plan banks. Sources: `docs/tools/ignite.md`, `mcp/ignite-mcp/NOTES.md`, unit manual `RMX-IGNITE_DRI2033-A_EN_manual.pdf`, app manual `RMX-IGNITE_SampleManager_EN.pdf`.

## Official (from manuals)
- Unit files: WAV or AIFF, 16 or 24 bit, 44.1, 48, 88.2, 96 kHz. A file over 16 s cannot be picked on the unit.
- Total bank length over 16 s may be trimmed. Some supported files still fail.
- Drive file systems: FAT16, FAT32, HFS+, exFAT.
- App: 15 banks, slots A to D, 100 banks in BANK COLLECTION (not exported).
- Gain -18 to +9 dB. BPM 40 to 999.99. Loop on C and D only, and it needs BPM and BEAT.

## App strings (not observed)
- App input 10 ms to 30 min: FLAC, ALAC, WAV, AIFF, MP3, AAC.
- Export is blocked if a bank exceeds 16 s.
- Export root: `DRIVE/AlphaTheta/RMX-IGNITE/RMX-IGNITESETTINGS.json`, plus `samples/NN/`.
- App samples: `model/samples/NN/`.
- On assign, the app converts audio to a 2-channel WAV. The call passes 96000 and 24. Some inputs take a copy path. The condition was not traced.

## Our choices (not official)
- Target: 96 kHz, 24 bit, stereo WAV. This matches factory samples and the conversion call.
- Name: uppercase, like `909 KICK`, max 24 characters. The app's real limit was not found.

## On the unit (the user)
1. Connect the drive to [USB for SAMPLER] or a PRO DJ LINK player.
2. Press [BROWSE/UTILITY]. Select [BANK SELECT] > [USER], then the storage media.
3. Select the bank, then [LOAD].
4. Before removal: select [USB STOP], press and hold the multi encoder, and wait for the pop-up to end.

Fire drops from the IGNITE. Do not use a CDJ for a drop.

## App state
`~/Library/Application Support/com.AlphaTheta.RMX-IGNITE-SampleManager/`: `model/model.json`, `bankcollection/bankcollection.json`, `settings/settings.json`, and `log/` (opaque, do not decode). Read only, through the MCP.

## Next test to close the gaps
Export one bank to a scratch drive in the GUI. Read it with `ignite_read_usb`. Correct the parser in `mcp/ignite-mcp/server.py` against what it shows.
