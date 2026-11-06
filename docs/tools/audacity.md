# Audacity MCP (third-party: xDarkzx/Audacity4-MCP)

Status: installed and registered, but NOT usable with stock Audacity 4.0.2. Live editing is unproven.

## Why it cannot drive the installed app
Audacity 4 has no scripting (mod-script-pipe is gone). This server talks to a TCP bridge on
127.0.0.1:2212 that exists only in a custom fork, xDarkzx/Audacity4-Dev-MCP, branch
feature/mcp-audio-cleanup-pipelines. We checked /Applications/Audacity 4.app: no MCP strings in the
binary, nothing listening on 2212. No prebuilt fork exists. Upstream says only Windows was built end to end.
Building on macOS needs Qt 6.8+, CMake, Ninja, about 20 min. Not done.

## Setup (done)
- Clone: ~/Audacity4-MCP, pinned commit 280c7a3f46c19c8686c53a37f788264630aa4b8c (2026-09-28).
- Venv: ~/Audacity4-MCP/.venv (Python 3.15.0, mcp 1.30.0; server needs mcp<2).
- Registered user scope: claude mcp add --scope user audacity -- ~/Audacity4-MCP/.venv/bin/audacity4-mcp
- Setup changed no Audacity preferences. Nothing touched mod-script-pipe.

## Security review (read all server4/ code; ran only after review)
- No subprocess, os.system, eval/exec, pickle, telemetry, or outbound HTTP in the server.
- Network: only 127.0.0.1:2212, host and port fixed. Token read from
  ~/Library/Application Support/Audacity/Audacity4(Development)/mcp_token (or AUDACITY4_MCP_TOKEN).
- Deletes: only its own temp WAVs (os.remove). Path guard blocks /System /Library /usr /bin /sbin /etc;
  it is not a sandbox. Tools can overwrite any user file via export, so keep overwrite=False.
- transcribe_* tools lazily import faster-whisper (separate pip install) and download models
  from Hugging Face on first use. Not installed. Do not call transcription_set_model unprompted.
- Result: no unsafe code found. Risk is in the fork (C++), which we did not read.

## Tools (159, seen in tools/list; none exercised against Audacity)
Listed by stdio protocol only. Seen to do: with no bridge, project_get_info returns
isError "Connect call failed ('127.0.0.1', 2212)". That is the only call observed.
Groups: project_* (new/open/save/import/export), select_*, edit_* (cut/copy/trim/split/silence/undo),
effect_*, normalize, loudness_normalize, limiter, compressor, noise_reduction, truncate_silence, label_*,
track_*, transport_*, generate_*, add_realtime_effect (VST3), auto_* (one-call pipelines), transcribe_*.

## Known limits
- Needs the fork; bridge accepts one client at a time.
- A native dialog in Audacity blocks the bridge; calls time out after 30 s.
- Early alpha; macOS never built upstream. Never force-quit the fork (corrupts recovery).
- Do not run alongside another session using Audacity.

## Recipe: trim a drop (UNTESTED, needs the fork running)
1. project_new, then project_import_audio(path=/abs/track.wav)
2. select_all, then select_region(start=<drop_s>, end=<drop_s + len>)
   (optional: select_zero_crossing or nearest_zero_crossing to avoid clicks)
3. edit_trim (keeps only the selection)
4. effect_fade_in / effect_fade_out (short), then normalize(peak_level_db=-1)
5. project_export_audio(path=/abs/drop.wav, overwrite=False); verify with ffprobe -show_entries format=duration
Default today: the ffmpeg path in skills/model-500-samples/SKILL.md.

Test: tests/test_audacity_mcp.py (stdio list + clean no-bridge error) passes.
