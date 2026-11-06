# Contributing

Failure reports count as much as code. Most rules in this repo exist because something went wrong in a real session.

Never commit a private name, a home-folder path, a personal email, a track list, or an audio file. `tests/check_public.py` catches some of this, not all.

## Run the tests

```sh
tests/run_all.sh
```

You need `uv`, `ffmpeg`, and `python3` on macOS. A test whose tool or vendor app is absent skips or narrows itself. The tests send no real input to any app. `test_mac_gui.py` opens one throwaway window that cannot take focus.

To check for your own private terms, list them in `state/private-terms.txt`, one per line. That file is gitignored.

## Add a failure entry

1. Add it to the right section of `docs/failures.md`, with the next free F number:
   ```
   **F43** [export, High] Short title  
   Did: What the agent did. Result: What happened.  
   Rule: One rule that prevents it.
   ```
2. Pick a severity. Critical means data lost or at risk. High means a wrong result or wasted work. Low means cost or friction.
3. Remove names, paths, and private quotes. Keep the tool names, the numbers, and the exact error text.
4. Add it to the `## Do not` list of the skill it belongs to, in the same form. Critical entries always go in a skill.
5. If a new request caused it, add the request to `tests/<skill>/triggers.md`.
6. Run the tests.

## Add a skill

1. Create `skills/<name>/SKILL.md`. Optional folders are `scripts/` and `references/`. Do not add a README inside the skill.
2. Follow `docs/skill-standards.md`. The description says what the skill does, when to use it, and when not to. The body stays under 120 lines.
3. Add `tests/<name>/triggers.md`: 3 or more prompts that must trigger, 3 or more paraphrases, 3 or more that must not.
4. Add a route to `skills/model-500/SKILL.md`, and add a row to the status table in `README.md`.
5. Run `scripts/install.sh`, then test the skill in a new chat. Say in your pull request what ran for real.

## Status words

The status table in `README.md` uses three words. Use the one that matches what ran. **Proven** means it ran on real data. **Tested on fixtures only** means generated data. **Not run** means neither. A dry run proves only the dry run.
