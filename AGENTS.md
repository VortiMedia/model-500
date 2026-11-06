# AGENTS.md

model-500 is seven skills and two MCP servers for DJ prep with rekordbox on a Mac. Only Claude Code is tested. On a host with no skill loader, read `skills/model-500/SKILL.md` and follow its routes.

Pick one branch:

- **The user wants DJ work done:** use the `model-500` skill, or the child skill that matches the request. If the skills are absent, install first.
- **The user wants this installed:** go to [Install](#install).
- **The user wants this repo changed:** go to [Change the repo](#change-the-repo).

## Install

Run [Quick start](README.md#quick-start) in order, with these gates:

| Step | Gate |
|---|---|
| Clone | The repo goes at `~/model-500` and the rekordbox MCP at `~/rekordbox-mcp`. The skills use those fixed paths. |
| `scripts/install.sh` prints `REFUSED` | Show the user the path and let them decide. The script overwrites nothing. |
| rekordbox backup | Ask the user to quit rekordbox. Run the backup only after `pgrep -x rekordbox` prints nothing. |
| Database key | Run `setup-key.py` and report its output. If it finds no key, ask the user before `download-key`, because it fetches from the internet. Keep key values out of chat. |
| `state/PROFILE.md` | The user fills in the gear, stick, and folders. Ask for the values. Leave a blank where the user has no answer. |
| mac-gui permissions | The user grants these in System Settings. Name the exact panes from [docs/tools/mac-gui.md](docs/tools/mac-gui.md). |
| Audacity MCP | Optional. Install it only if the user asks. It cannot drive stock Audacity. See [docs/tools/audacity.md](docs/tools/audacity.md). |

Install is done when all of these hold:

- `ls -l ~/.claude/skills | grep -c model-500` prints 7.
- `claude mcp list` shows `ignite`, `mac-gui`, and `rekordbox` as connected.
- `tests/run_all.sh` passes. Report each SKIP line.
- The user knows to start a new chat. New MCPs and skills load only there.

Report what ran and what did not. Send real input through `mac-gui` only while the user watches.

## Change the repo

- `state/` holds private files that git ignores. Only the `*.example.md` files are public. Put names, home-folder paths, track lists, and rig details from a real user there.
- Before each push, run `tests/run_all.sh`. It includes `tests/check_public.py`, which also reads your terms from `state/private-terms.txt`.
- Commit with a GitHub noreply email.
- A new failure goes in `docs/failures.md` and in the `## Do not` list of its skill. See [CONTRIBUTING.md](CONTRIBUTING.md).
- A skill must pass [docs/skill-standards.md](docs/skill-standards.md): short sentences, controlled language, body under 120 lines.
- Status words in the README are *proven*, *tested on fixtures only*, and *not run*. Use the word that matches what ran. A dry run proves only the dry run.
- Pin third-party code. A change to a pinned commit means a new test against a real library.
