#!/usr/bin/env python3
"""Build the final deliverables: resolve {{include:raw:<path>}} markers in _src/*.md into ../*.md.

Usage: python3 -I tools/build.py [--check]
 - Paths are relative to the architecture/ folder; escaping the folder is refused.
 - Fails (exit 1) if an include is missing, so a doc can never ship with an unresolved marker.
 - Strips trailing newline of included content so fences close cleanly.
"""
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "_src"
PAT = re.compile(r"\{\{include:raw:([^}]+)\}\}")


def resolve(text: str, doc: str, errors: list) -> str:
    def sub(m):
        rel = m.group(1).strip()
        p = (ROOT / rel).resolve()
        if ROOT not in p.parents or not p.is_file():
            errors.append(f"{doc}: include not found or outside root: {rel}")
            return m.group(0)
        return p.read_text(encoding="utf-8").rstrip("\n")
    return PAT.sub(sub, text)


def main():
    errors, built = [], []
    for f in sorted(SRC.glob("*.md")):
        out = resolve(f.read_text(encoding="utf-8"), f.name, errors)
        if PAT.search(out):
            errors.append(f"{f.name}: unresolved include marker remains")
        if "--check" not in sys.argv:
            (ROOT / f.name).write_text(out if out.endswith("\n") else out + "\n", encoding="utf-8")
        built.append((f.name, len(out.splitlines())))
    for n, l in built:
        print(f"{n:55s} {l:6d} lines")
    if errors:
        print("\nERRORS:"); [print(" -", e) for e in errors]; sys.exit(1)
    print(f"\nOK: {len(built)} documents built")


if __name__ == "__main__":
    main()
