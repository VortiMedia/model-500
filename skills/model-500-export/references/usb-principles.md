# USB principles

Read this for facts on formats, OneLibrary, My Settings, and target layout. Drops steps here are the old notes. model-500-samples and model-500-ignite own that work now.

From a pasted Claude chat, fact-checked 2026-11-06. The check used search snippets; the pages were not opened in full. Items marked unverified stay unverified until someone reads the manual.

## Principles

- **Golden rule: never drag files onto the stick.** Tracks go through rekordbox 7. Samples go through RMX-IGNITE Sample Manager. (Holds. See F11.)
- **Two identical sticks**, main and backup, labeled with the owner's name. Metal USB 3.0, 64-256 GB, SanDisk or Samsung. (Advice, not a spec.)
- **File system:** AlphaTheta lists FAT16, FAT32, exFAT, HFS+. NTFS is not supported. Older Pioneer pages omit exFAT; newer ones win. The "FAT32 4 GB file limit" is a general FAT32 fact; no AlphaTheta size limit found, so unverified for the CDJ.
- **Audio:** official list is WAV, AIFF, FLAC, ALAC, MP3, AAC. Playback to 96 kHz / 24-bit. Opus: unverified, treat as unsupported. 32-bit float WAV: unverified.
- **Quality rule (the owner's):** WAV, AIFF, FLAC, 320 kbps MP3 for music. YouTube rips only for dialogue drops. (Taste, not a CDJ rule.)
- **OneLibrary:** required. The CDJ-3000X reads only OneLibrary (Device Library Plus). Use rekordbox 7.2.11 or later; it writes both formats on export. Whether a stick "shows blank" without it is unverified, but the library will not show. Keep rekordbox and CDJ firmware updated.
- **My Settings:** generated in rekordbox and written to the stick. The player cannot write them back. Loaded from the Utility menu. Unverified for the CDJ-3000X specifically.
- **Samples:** the app is RMX-IGNITE Sample Manager (Mac and Windows). Build up to 15 banks, then press [EXPORT] to the USB. On the unit: [SAMPLE BROWSE] via the [USB for SAMPLER] port. Eject with [USB STOP]. Accepted sample formats: unverified; use WAV.
- **Posted mixes:** movie dialogue is fine live. Posts to SoundCloud, Mixcloud, YouTube can be flagged.

Sources: support.alphatheta.com/en-US/articles/48525420426009; CDJ-3000X manual (downloads.support.alphatheta.com, DRI1956B); alphatheta.com notice on USB devices; support.pioneerdj.com articles 4405915074969, 4406512519193, 52342126216345; forum post 28649676409369 (Opus Quad My Settings).

## Tracks workflow (rekordbox)

1. Consolidate tracks into one folder.
2. Import, analyze.
3. Fix beatgrids. Set hot cues and memory cues.
4. Build playlists.
5. Export playlists to the stick (GUI, with OneLibrary).
6. Export My Settings to the stick.
7. Run `read_pdb.py`. Test on a CDJ-3000X.

## Drops workflow (RMX-IGNITE)

1. Rip, save to `Samples/Raw/` (never load these).
2. Trim to the one line, 1-4 s.
3. Normalize, export WAV.
4. Name clearly: `SPEAKER_short_phrase.wav`.
5. Save to `Samples/Drops/` (Movies, Interviews, Intros).
6. Load in Sample Manager, export to the stick.
7. Fire drops from the IGNITE. Do not burn a CDJ on a drop.

## Pre-gig checklist

- [ ] rekordbox and CDJ firmware updated
- [ ] Main stick exported (OneLibrary)
- [ ] Backup stick re-synced
- [ ] Test stick on a CDJ-3000X: do the playlists show?
- [ ] Drops loaded on the IGNITE
- [ ] Both sticks in the bag
- [ ] Everything on the stick is bought, not ripped, if the volume is loud

## Target vs today (do not rewrite the user's layout)

| Item | Target (pasted) | Today |
|---|---|---|
| Track folder | `Music/Tracks/` | The music root in `state/PROFILE.md` |
| Samples | `Music/Samples/{Drops,Raw}` | Not set up. Factory sampler files sit in `~/Music/rekordbox/Sampler` |
| Stick | two exFAT sticks, 64-256 GB | One stick, 8 GB FAT32, MBR (see profile) |
| Music source | lossless or 320 kbps | mostly rips (mp3, converted Opus as AIFF) |
| Backup stick | yes | none |

FAT32 is on the supported list, so today's stick can work. At 8 GB it fits few lossless tracks (32 tracks of mixed mp3 and AIFF is the near-term plan). Offer the move to the target layout as a choice; never do it unasked.
