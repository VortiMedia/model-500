# Failure log

Real failures from DJ sessions of the first owner, 2026-10-18 to 2026-11-06. One entry per distinct failure.
Skill tags: crate | library | samples | ignite | sets | export | all.
Severity: Critical = data lost or at risk of loss. High = wrong result or real work wasted. Low = cost or friction. The build agent assigned these on 2026-11-06. The owner has not reviewed them.
Session ids, names, and private quotes are removed from this public copy. A fuller private copy may sit in `state/failures-private.md`.

## Library and database
**F01** [library, High] Stale reads  
Did: Trusted MCP reads right after rekordbox analyzed tracks. Result: BPM and key showed 0 or empty. Agent said "1 of 18 done" when all 18 were done.  
Rule: Call connect_database again before trusting any read, and after every change.
**F02** [library, High] Write while rekordbox open  
Did: Planned deletes while rekordbox ran. Result: Writes blocked or risked corruption. Factory clean-up waited two turns for the user to quit the app.  
Rule: Check rekordbox is closed before any write. Read a copy while it is open.
**F03** [library, Critical] Backup missed the WAL  
Did: Relied on the MCP auto-backup. Result: It copies master.db only. Recent changes sit in master.db-wal.  
Rule: Copy the whole rekordbox folder before any write. Verify the copy.
**F04** [library, High] MCP path bug  
Did: Followed the README flag --database-path. Result: The flag does nothing. Upstream path detection returned the wrong folder, so new playlists skipped masterPlaylists6.xml.  
Rule: Check the local path patch survives any git pull of rekordbox-mcp.
**F05** [library, High] Blank tags after import  
Did: import_tracks with auto_tag on tagged AIFF files. Result: Artist and Title came out empty.  
Rule: After import, run set_metadata.py, then read the fields back.
**F06** [library, Critical] ANLZ files rewritten  
Did: update_content_path(save=True) to fix moved paths. Result: pyrekordbox rewrote ANLZ files: PVDI tag lost, PCOB, PCO2, PSSI changed.  
Rule: Use safe_move.py. Never call update_content_path with save=True.
**F07** [library, Critical] remove_broken_tracks too broad  
Did: Passed track IDs to remove_broken_tracks. Result: It soft-deletes any ID, broken or not. The audio file stays on disk.  
Rule: Run find_broken_tracks first. Pass only IDs it returned.
**F08** [library, High] Factory content in Collection  
Did: Left 32 factory samples and demos (Merge FX, Groove Circuit, OSC Sampler) and 2 Spotify stubs. Result: Collection showed 52 tracks, 32 of them junk. The user asked for the sample tracks to be removed.  
Rule: Audit a fresh Collection for factory samples and stubs. Offer removal with a backup.
**F09** [library, Low] Tool schema guessed  
Did: Called get_tracks_by_bpm_range without bpm_min. Result: Input validation error: 'bpm_min' is a required property.  
Rule: Load the MCP tool schema before the first call to any deferred tool.
**F10** [library, Low] Unicode false alarm  
Did: Compared file names between stick and Mac as raw strings. Result: 2 tracks looked missing. The cause was NFC vs NFD.  
Rule: Normalize both sides to NFC before comparing names.

## Export and USB
**F11** [export, Critical] Renamed files inside Contents  
Did: Moved or renamed files on the stick. Result: export.pdb and exportLibrary.db hold exact paths, so tracks vanished from the CDJ library.  
Rule: Never move or rename inside Contents or PIONEER. Change playlists in rekordbox, re-export.
**F12** [export, Critical] Wiped before comparing  
Did: Wiped the stick, then needed a GUI export to refill it. Result: The user did GUI work before the stick was useful. 162 stick-only tracks had no Mac copy.  
Rule: Before any wipe, diff stick against Mac, list stick-only tracks, get an OK.
**F13** [export, Critical] Delete with no copy  
Did: Fully deleted a friend's sets on request, backups included. Result: The 162 tracks are gone for good. They were never in the Mac library.  
Rule: Ask once more when a delete leaves no other copy. Name what is lost.
**F14** [export, High] Staleness judged by date  
Did: Read an old modified date on exportLibrary.db as "not updated". Result: The date does not track writes, because the file changes size while its date stays. The file is encrypted, and an attempt to open it failed.  
Rule: Do not judge by date. Do not try to open the file. Only a CDJ load test proves it.
**F15** [export, High] Export claimed ready, untested  
Did: Exported Set 1 through screenshots and a click helper, no desktop-control tool. Result: Stick showed 11 tracks with BPM, key, waveforms. No CDJ load was ever run.  
Rule: Say "not tested on a CDJ" until the user loads it. Never write "works".
**F16** [export, High] Wrong rekordbox version  
Did: Planned an export from research notes. Result: CDJ-3000X reads only OneLibrary exports. Use rekordbox 7.2.11 or later, avoid 7.2.12. The Mac had 7.2.19.  
Rule: Confirm app version and OneLibrary format before telling the user a stick is ready.
**F17** [export, Low] Mac junk files return  
Did: Cleaned `._*` early, then created marker files. Result: 3 new `._` files appeared. Exports and Finder copies also bring them back.  
Rule: Clean last. Delete `._*` and .Spotlight-V100, run mdutil -i off, recheck after copies.
**F18** [export, High] Rename needed GUI  
Did: Tried to rename a playlist while rekordbox was open. Result: Agent could not write. The user had to rename it before export.  
Rule: Tell the user GUI-only steps first, in order, before the export step.

## Crate, files and tags
**F19** [crate, High] Opus will not play  
Did: Imported YouTube Opus rips. Result: rekordbox has no Opus support. Files unusable.  
Rule: Convert with ffmpeg to AIFF. Say plainly this does not raise quality.
**F20** [crate, High] Rip tags lie  
Did: Trusted Artist tags and file lengths from rips. Result: Artist was the uploader. A lecture video sat in a crate. A 439-track folder had 82 likely previews.  
Rule: Run audit_folder.py. Show the user the doubtful names before importing.
**F21** [crate, High] Lost source URLs  
Did: Stripped YouTube IDs from names. Result: A later buy list needs the sources. All 11 tracks of the first set were still rips.  
Rule: Write a rename map with source URLs before renaming.
**F22** [crate, High] Files left in Downloads  
Did: Built the first set from a folder under ~/Downloads. Result: The user wanted music moved out of Downloads and into the music root.  
Rule: Keep music under the music root in state/PROFILE.md. Update rekordbox paths when moving.
**F23** [crate, Low] Cover art hunt  
Did: Opened artwork one by one. Result: Slow and token-heavy.  
Rule: Check covers on one ffmpeg contact sheet. Order: iTunes, Bandcamp, video thumbnail.
**F24** [crate, Low] Agent cost  
Did: 6 agents on 38 tracks for metadata. Result: 373k tokens. Cheap models also garbled names and left &amp;.  
Rule: Run resolve_metadata.py first. Agents only for leftovers, with a name verifier.

## Sets
**F25** [sets, Low] Too many questions at once  
Did: Grilled with multi-part questions. Result: The owner's working preference is one question at a time with a stated next action. The multi-part questions broke it.  
Rule: Ask one question at a time. Recommend an answer. End with one next action.
**F26** [sets, Low] Unverified claims about analysis settings  
Did: Said High precision analysis "should give better grids", flagged "haven't checked the docs". Result: A guess in a table beside confirmed rows.  
Rule: Mark each fact as checked or guessed. Check docs before advising settings.

## Samples and RMX-IGNITE
**F27** [samples, High] Whisper on music beds  
Did: Transcribed a section of a house-music mix with Whisper. Result: It output only "I" repeated over music.  
Rule: Separate vocals first, then transcribe. Never trust text over a music bed.
**F28** [samples, High] Misheard names  
Did: Passed Whisper output through as final. Result: A Roman philosopher's name came out as a near-homophone.  
Rule: Flag likely mishears. Ask the user to confirm proper nouns.
**F29** [samples, High] Silence filled with text  
Did: Transcribed 13 minutes of clips, 10 of them silent. Result: Whisper invents text on silence.  
Rule: Detect silence first. Drop non-speech spans before transcribing.
**F30** [samples, High] Wrong timestamp from memory  
Did: Started at the user's "around 28 min". Result: The voice was at 25:44 to 26:17 and 26:42 to 27:24.  
Rule: Search the transcript for the quote. Do not cut at a remembered time.
**F31** [samples, High] Phantom files after interrupt  
Did: Said the interrupted cut created no files. Result: The output folder held six WAVs. Agent corrected later.  
Rule: After any interrupted job, list the output folder before reporting.
**F32** [samples, Low] Source not found  
Did: Searched web for the exact lines. Result: Nothing matched. The track may be unreleased or DJ-set only.  
Rule: Say "not found". Offer Shazam at the timestamp. Do not guess origin.
**F33** [ignite, High] No MCP exists  
Did: The user installed RMX-IGNITE Sample Manager. No MCP covers it. Result: The agent cannot drive it. Samples must not be dragged onto the stick.  
Rule: Build a local tool or use GUI steps. Never drag samples onto the stick.

## Agent behavior
**F34** [all, Low] Opus on simple audits  
Did: Six-agent audit inherited Opus. Result: The user stopped it as too slow for a simple audit.  
Rule: Set model haiku or sonnet on lookups and audits. Return short summaries.
**F35** [all, Low] Polling with sleep  
Did: Used `sleep N` in Bash to wait. Result: The harness blocked it: "Blocked: sleep 60 followed by...".  
Rule: Wait with Monitor and an until-loop. Never chain sleep.
**F36** [all, Low] Shell and tool gaps on this Mac  
Did: Used pgrep -E, strings -e, ffmpeg drawtext, pyrekordbox on export.pdb. Result: None exist or work here. pyrekordbox 0.4.3 cannot read export.pdb.  
Rule: Use read_pdb.py for export.pdb. Test flags before scripting.
**F37** [all, Low] Music built from generic stock sounds  
Did: Used stock synth drums and presets. Result: The user rejected the sound as basic and stock. Real 909 samples fixed it.  
Rule: Name a real machine first. Build in Live, not offline renders. Out of scope for the model-500 skills: they do not produce music. Kept as a record.
**F38** [all, High] Hearing claims  
Did: Judged how audio sounds. Result: The agent cannot hear. Only the user's ears judge results.  
Rule: Report measurements only. Ask the user to listen.

## Build of model-500 (agent reports, 2026-11-06)
**F39** [ignite, High] Click sent to a background app  
Did: Sent one pid-targeted synthetic click to Sample Manager to fill a bank. Result: No effect. No filled library exists to test the parser.  
Rule: Bank edits need the app in front, or the user. Ask before taking focus.
**F40** [all, High] Test window took focus  
Did: Ran early mac-gui tests with a fixture window. Result: It came to the front for a few seconds each run. The user's keystrokes may have been lost.  
Rule: Never take focus without the user's OK. Dry-run first.
**F41** [samples, High] MCP installed, app cannot use it  
Did: Installed and registered the Audacity MCP. Result: It needs a custom fork bridge on port 2212. Stock Audacity 4.0.2 has none.  
Rule: Use ffmpeg by default. Call project_get_info only if the user asks for Audacity.
**F42** [samples, Low] Long transcript in one call  
Did: One Bash call printed all short transcripts and the head of the long one. Result: Exit 1, then the user interrupted the turn (reason not given).  
Rule: Read long transcripts in slices.

## Method and limits

- Source: a scan of the agent transcripts from the first owner's sessions (user corrections, error results, retractions), then a read of targeted parts of four sessions. Plus an older skill's failure notes and seven memory files.
- One live session was not read beyond its first message. Several entries rest on notes, not the original turn.
- Heuristic filters miss errors without an error flag. Entry counts are not frequencies.
