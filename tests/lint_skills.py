#!/usr/bin/env python3
"""Lint agent skills against docs/skill-standards.md. Stdlib only.

Usage: python3 tests/lint_skills.py [PATH ...]
PATH is a skills/ folder, a skill folder, or a SKILL.md file.
With no PATH, lint every skills/*/SKILL.md in this repo.
Exit code 1 if any error. Warnings do not fail.
"""
import re
import sys
from pathlib import Path

MAX_DESC = 1024
MAX_LINES = 120
MAX_WORDS = 25
KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
BANNED = ["comprehensive", "robust", "seamless", "leverage", "ensure that",
          "in order to", "it is important", "delve", "powerful", "various"]
TRIGGER = re.compile(r"\buse (when|for|before|after|this)\b|\btriggers? (on|when)\b|\"[^\"]+\"", re.I)
PRONOUN = re.compile(r"\b(he|him|his|himself|she|her|hers|herself)\b", re.I)


def split_frontmatter(lines):
    """Return (dict, body_start_index) or (None, 0)."""
    if not lines or lines[0].strip() != "---":
        return None, 0
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return parse_yaml(lines[1:i]), i + 1
    return None, 0


def parse_yaml(block):
    """Minimal parser: top-level 'key: value', folded or literal blocks."""
    data, key = {}, None
    for raw in block:
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", raw)
        if m and not raw.startswith((" ", "\t")):
            key, val = m.group(1), m.group(2).strip()
            if val in (">", "|", ">-", "|-"):
                val = ""
            if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
                val = val[1:-1]
            data[key] = val
        elif key and raw.strip():
            data[key] = (data[key] + " " + raw.strip()).strip()
    return data


def prose_lines(lines, start):
    """Yield (lineno, text) for prose: skip code fences, tables, headings."""
    fence = False
    for n in range(start, len(lines)):
        t = lines[n].rstrip("\n")
        if t.strip().startswith("```"):
            fence = not fence
            continue
        if fence or t.lstrip().startswith(("|", "#")) or not t.strip():
            continue
        yield n + 1, t


def lint_skill(md: Path):
    errs, warns = [], []
    folder = md.parent
    text = md.read_text(encoding="utf-8")
    lines = text.splitlines()

    if len(lines) > MAX_LINES:
        errs.append(f"SKILL.md has {len(lines)} lines (max {MAX_LINES})")
    for f in folder.iterdir():
        if f.name.lower().startswith("readme"):
            errs.append(f"{f.name} found in skill folder")

    fm, body = split_frontmatter(lines)
    if fm is None:
        errs.append("missing or unclosed frontmatter")
        body = 0
    else:
        name, desc = fm.get("name", ""), fm.get("description", "")
        if not name:
            errs.append("frontmatter: name missing")
        else:
            if not KEBAB.match(name):
                errs.append(f"name '{name}' is not kebab-case")
            if name != folder.name:
                errs.append(f"name '{name}' does not match folder '{folder.name}'")
            if "claude" in name or "anthropic" in name:
                errs.append("name contains reserved word")
        if not desc:
            errs.append("frontmatter: description missing")
        else:
            if len(desc) > MAX_DESC:
                errs.append(f"description is {len(desc)} chars (max {MAX_DESC})")
            if not TRIGGER.search(desc):
                errs.append("description has no trigger phrase ('Use when ...' or quoted phrases)")
        fm_text = "\n".join(lines[: body])
        if "<" in fm_text or ">" in fm_text.replace(": >", ":").replace(": >-", ":"):
            errs.append("angle bracket in frontmatter")

    for n, t in prose_lines(lines, body):
        low = t.lower()
        for w in BANNED:
            if re.search(r"\b" + re.escape(w) + r"\b", low):
                errs.append(f"line {n}: filler '{w}'")
        for sent in re.split(r"(?<=[.!?])\s+", t):
            if re.search(r"\b(the user|the dj)\b", sent.lower()) and PRONOUN.search(sent):
                errs.append(f"line {n}: gendered pronoun near the user")
    # filler and pronouns also apply to the description
    if fm and fm.get("description"):
        d = fm["description"].lower()
        for w in BANNED:
            if re.search(r"\b" + re.escape(w) + r"\b", d):
                errs.append(f"description: filler '{w}'")

    # sentence length, prose only
    for n, t in prose_lines(lines, body):
        clean = re.sub(r"`[^`]*`", "X", t)
        clean = re.sub(r"^\s*(?:[-*]|\d+\.)\s+", "", clean)
        clean = re.sub(r"\b(e\.g|i\.e|etc|vs)\.", r"\1", clean)
        for sent in re.split(r"(?<=[.!?])\s+", clean):
            c = len(sent.split())
            if c > MAX_WORDS:
                warns.append(f"line {n}: sentence has {c} words (max {MAX_WORDS}): {sent[:50]}...")
    return errs, warns


def targets(args):
    root = Path(__file__).resolve().parent.parent / "skills"
    out = []
    for a in args or [str(root)]:
        p = Path(a).expanduser()
        if p.is_file():
            out.append(p)
        elif (p / "SKILL.md").is_file():
            out.append(p / "SKILL.md")
        elif p.is_dir():
            out += sorted(p.glob("*/SKILL.md"))
            for d in sorted(x for x in p.iterdir() if x.is_dir()):
                if not (d / "SKILL.md").exists() and not d.name.startswith("."):
                    print(f"ERROR {d}: folder has no SKILL.md")
    return out


def main(argv):
    files = targets(argv)
    if not files:
        print("No SKILL.md files found.")
        return 0
    bad = 0
    for md in files:
        errs, warns = lint_skill(md)
        status = "FAIL" if errs else "ok"
        print(f"{status}  {md.parent}  ({len(errs)} errors, {len(warns)} warnings)")
        for e in errs:
            print(f"  ERROR {e}")
        for w in warns:
            print(f"  warn  {w}")
        bad += bool(errs)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
