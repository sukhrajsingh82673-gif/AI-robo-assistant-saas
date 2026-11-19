#!/usr/bin/env python3
"""Render every ```mermaid block in the given markdown files with mmdc; exit 1 if any fails."""
import re, subprocess, sys, tempfile, pathlib
bad = total = 0
for f in sys.argv[1:]:
    txt = pathlib.Path(f).read_text()
    for i, m in enumerate(re.finditer(r"```mermaid\n(.*?)```", txt, re.S), 1):
        total += 1
        with tempfile.TemporaryDirectory() as d:
            src = pathlib.Path(d, "x.mmd"); src.write_text(m.group(1))
            r = subprocess.run(["mmdc", "-i", str(src), "-o", str(pathlib.Path(d, "x.svg")), "-q"], capture_output=True, text=True, timeout=120)
            ok = r.returncode == 0 and pathlib.Path(d, "x.svg").exists()
            print(("OK   " if ok else "FAIL ") + f"{pathlib.Path(f).name} diagram #{i}")
            if not ok: bad += 1; print(r.stderr[-600:])
print(f"{total - bad}/{total} diagrams rendered"); sys.exit(1 if bad else 0)
