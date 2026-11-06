# Stick housekeeping and pre-gig check

Read this before junk cleanup, a wipe, or a gig. Facts on formats and OneLibrary: `usb-principles.md`.

## Junk cleanup (F17)
Do this last. Ask the user first. It writes to the stick.
1. Delete `._*` and `.Spotlight-V100`.
2. Add `.metadata_never_index` and `.fseventsd/no_log`.
3. Run `mdutil -i off STICK_PATH`. STICK_PATH is the volume path in `state/PROFILE.md`.
4. Run `read_pdb.py`. It counts `._` files. Expect 0.
5. Recheck after any export or Finder copy. Both bring the files back.

Never remove anything else by hand. Keep any firmware file the profile names, such as a mixer `.upd`, at the root until the device is updated.

## Wipe (F12, F13)
The steps are in SKILL.md, "Steps: wipe". `stick_vs_mac.py` does the diff and compares as NFC, so it also works with no `export.pdb`.

History: 162 tracks owned by a friend existed only on one stick. They are gone for good.

## Date and encryption (F14)
- `exportLibrary.db` is encrypted. Do not hunt for keys.
- Its modified date stays at Aug 2025 after exports, while its size changes. Do not judge by date.
- Only a CDJ load test proves the stick loads.

## Pre-gig checklist
Mark each line checked, or "The user" if only the user can do it.
- [ ] rekordbox and CDJ firmware updated
- [ ] Main stick exported (OneLibrary)
- [ ] Backup stick exported again
- [ ] Stick tested on a CDJ-3000X: do the playlists show?
- [ ] Drops loaded on the IGNITE (model-500-ignite)
- [ ] Both sticks in the bag
- [ ] Everything on the stick is bought, not ripped, if the volume is loud

## Today vs target
See the table at the end of `usb-principles.md`. Offer the target layout as a choice. Never do it unasked.
