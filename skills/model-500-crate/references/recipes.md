# Crate recipes

Read this for a conversion, a cover hunt, or an agent pass. Source: old skill `rekordbox-usb/references/failures.md`, items 6, 10, 11, 12, 13.

## Opus to AIFF (F19)
```
ffmpeg -i in -map 0:a:0 -c:a pcm_s16be -map_metadata -1 out.aiff
```
1. Check that the duration is within 0.2 s of the source.
2. Tag with `mutagen.aiff`: ID3 v2.3, APIC cover.
3. Say plainly that this does not raise quality.
4. 32-bit float WAV support is unverified. Test one file first.

## Covers (F23)
1. iTunes: `artworkUrl100`, with `100x100bb` changed to `1200x1200bb`.
2. Bandcamp: `og:image`.
3. Video thumbnail, cropped square: YouTube `maxresdefault` or `hqdefault`. It often shows real sleeve or label art.

Check all covers on one sheet. Do not open images one by one. One sheet holds 40 covers. Tested on 3 generated images.
```
ffmpeg -pattern_type glob -i '*.jpg' -vf "scale=300:300,tile=8x5" -frames:v 1 sheet.jpg
```
Artwork for tracks already in the library needs Reload Tag in the rekordbox GUI. That step belongs to model-500-library.

## Rip tags (F20)
- The Artist tag is often the uploader.
- Under 3 minutes, or words like clip, preview, lo-res: probably a preview.
- Over 15 minutes: probably a mix.
- `audit_folder.py` flags are leads, not facts.

## Rename map (F21)
Keep one JSON file per rename pass: old name, new name, source URL. Keep it next to the backup. The existing map path is in `state/PROFILE.md`.

## Agents (F24)
- Run `resolve_metadata.py` first. Agents get `partial` and `unresolved` items only.
- Unescape `&amp;` in agent output.
- Cheap models need a name verifier.
- Use the Unicode NFC form before you compare names (F10).

## Names still open
`state/PROFILE.md` lists names still open for the user to confirm. Do not change them without an answer.

## the user's quality rule
WAV, AIFF, FLAC, or 320 kbps MP3 for music. YouTube rips only for dialogue drops. This is taste, not a CDJ rule.
