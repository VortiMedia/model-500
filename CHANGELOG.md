# Changelog

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
