#!/usr/bin/env python3
"""Local approximation of the skills.sh / Vercel security audit.

Runs the same *kinds* of checks the published audit flags, so a regression is
caught in CI before publish instead of after. It is a best-effort smoke test,
not a reimplementation of the full ruleset:

  W021 (hidden Unicode)      — deterministic; reliable.
  W007 (credential handling) — heuristic; catches the obvious patterns
                               (a secret value placed in a command flag, or
                               instructions to paste a secret into the chat).
                               Pair with human/LLM review for full coverage.

Usage:
  python3 scripts/skill_audit.py                 # scan skills/**/*.md
  python3 scripts/skill_audit.py path/to/SKILL.md ...
Exit code 0 = clean, 1 = findings.
"""

from __future__ import annotations

import glob
import re
import sys
import unicodedata

# Zero-width, joiners, bidi controls, BOM, and the emoji variation selector.
_INVISIBLE = (
    set(range(0x200B, 0x2010))
    | set(range(0x202A, 0x202F))
    | set(range(0x2066, 0x206A))
    | {0x00AD, 0x2060, 0x2061, 0x2062, 0x2063, 0x2064, 0xFEFF, 0xFE0F}
)

_SECRET_IN_FLAG = re.compile(
    r"--[\w-]*secret[\w-]*\s+<?\s*(secret|value|key|token)", re.I
)
_PASTE_SECRET = re.compile(r"paste\b.{0,40}\bsecret", re.I)
_TO_CHAT = re.compile(r"\b(to you|in the chat|to the agent)\b", re.I)


def audit(path: str) -> list[tuple[str, str, int, str]]:
    text = open(path, encoding="utf-8").read()
    findings: list[tuple[str, str, int, str]] = []

    # W021 — hidden / format characters.
    for i, ch in enumerate(text):
        cp = ord(ch)
        is_fmt = unicodedata.category(ch) in ("Cf", "Cc") and ch not in "\n\t"
        if cp in _INVISIBLE or is_fmt:
            line = text.count("\n", 0, i) + 1
            name = unicodedata.name(ch, "?")
            findings.append(("W021", "MEDIUM", line, f"hidden char U+{cp:04X} ({name})"))

    # W007 — credential handling (heuristic). Negations ("never pass", "no `--`")
    # are how a skill *correctly* documents the prohibition, so they don't count.
    for n, ln in enumerate(text.splitlines(), 1):
        low = ln.lower()
        if _SECRET_IN_FLAG.search(ln) and "never" not in low and "no `--" not in low:
            findings.append(("W007", "HIGH", n, f"secret value in a flag: {ln.strip()[:90]}"))
        if (
            _PASTE_SECRET.search(ln)
            and _TO_CHAT.search(ln)
            and "not" not in low
            and "never" not in low
        ):
            findings.append(("W007", "HIGH", n, f"pastes a secret into chat: {ln.strip()[:90]}"))

    return findings


def main(argv: list[str]) -> int:
    paths = argv or sorted(glob.glob("skills/**/*.md", recursive=True))
    if not paths:
        print("no skill markdown found", file=sys.stderr)
        return 1
    clean = True
    for path in paths:
        found = audit(path)
        if found:
            clean = False
            print(f"\n{path}")
            for code, sev, line, msg in found:
                print(f"  {code} ({sev}) line {line}: {msg}")
        else:
            print(f"{path}: OK")
    print("\n" + ("PASS — no W007/W021-class findings" if clean else "FAIL — findings above"))
    return 0 if clean else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
