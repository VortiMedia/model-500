# Changelog

## Unreleased

### Added
- `AGENTS.md` with install gates and checks, and `CLAUDE.md`, which imports it.
- README: a paste-in install prompt, backup and key steps, install checks, and a full links section.
- `docs/tools/audacity.md`: exact setup commands.

### Changed
- Quick start runs `uv sync --frozen` before it registers each MCP, and registers `ignite` with `--frozen`.

### Fixed
- IGNITE reads use flat app sample paths and one-based USB bank folders directly under the export root.
- Prepared WAV files use classic PCM headers without changing the converted PCM frames. Regression tests cover both native layouts and the header.
- IGNITE bank reads report each slot's WAV format tag and any `._` AppleDouble file beside it. Native exports use tag 1.
- USB audit scripts refuse JSON report paths on the audited volume, including symlink and case aliases.
- Reports outside the volume are replaced atomically, preserving audited audio even when the old report is a hard link.

## 0.1.0 (2026-11-06)

First public version.

### Added
- Seven skills: `model-500` (router), `crate`, `library`, `sets`, `export`, `samples`, `ignite`.
- `ignite` MCP server: reads the Sample Manager library and a USB export, checks and prepares samples. It has no bank-write tool.
- `mac-gui` MCP server: drives rekordbox, RMX-IGNITE Sample Manager, and Audacity 4 through macOS input and Accessibility calls. Allowlist of three apps.
- Scripts for folder audits, metadata lookup, safe file moves, track fields, stick checks, and transcription.
- `docs/failures.md`: 42 real failures, each with one rule. The rules feed the `## Do not` list in each skill.
- Tests: skill lint, public-release check, script tests, MCP tests.

### Not proven in this version
- No stick from this suite has loaded on a CDJ-3000X.
- No drop has played on an RMX-IGNITE. The IGNITE USB layout is inferred.
- mac-gui has never sent real input.
- The Audacity MCP has not driven Audacity. It needs a custom fork.
