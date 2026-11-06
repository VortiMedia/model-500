# Docs

Start with the [README](../README.md) for install and tool status. This page lists the depth.

## Records

- [failures.md](failures.md): the failure log. 42 entries from real sessions, each with one rule. The `## Do not` list in each skill draws from it.
- [sample-mining.md](sample-mining.md): what the first dialogue-mining run did, and where it stopped.

## Rules for writing skills

- [skill-standards.md](skill-standards.md): the checklist each skill must pass. `tests/lint_skills.py` checks part of it.

## Tools

- [tools/rekordbox.md](tools/rekordbox.md): setup, the path patch, and known traps of the third-party MCP.
- [tools/ignite.md](tools/ignite.md): the ignite MCP, RMX-IGNITE limits, and what is not proven. Format notes are in [`mcp/ignite-mcp/NOTES.md`](../mcp/ignite-mcp/NOTES.md).
- [tools/mac-gui.md](tools/mac-gui.md): the mac-gui MCP, its safety rules, permissions, and unproven rekordbox recipes.
- [tools/audacity.md](tools/audacity.md): why the third-party Audacity MCP cannot drive stock Audacity, and its security review.
- [tools/computer-use.md](tools/computer-use.md): background on Anthropic's computer use tool. This suite does not call that API.

## Inside each skill

- `skills/<skill>/SKILL.md`: steps, gates, the `## Do not` list, and a "Not proven" section.
- `skills/<skill>/references/`: detail loaded on demand.
- `skills/<skill>/scripts/`: the scripts. The first lines of each script hold its usage.
- `tests/<skill>/triggers.md`: prompts to try by hand. No script runs them.

## Project

- [CONTRIBUTING.md](../CONTRIBUTING.md), [SECURITY.md](../SECURITY.md), [CHANGELOG.md](../CHANGELOG.md), [LICENSE](../LICENSE).
