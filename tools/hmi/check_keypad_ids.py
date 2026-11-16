#!/usr/bin/env python3
"""Guard keybdB's per-field clamp table against component-id drift.

keybdB.nx clamps typed values with `if (loadpageid.val == P) { if (loadcmpid.val == C)`.
Nextion component ids are the 1-based position of a component in its page.toml, so
inserting or reordering components silently re-targets those clamps. This script
resolves every (page index, component id) pair to a component name and fails if a
pair no longer points at a key=2 numeric field, or if a key=2 numeric field on an
editing page has no clamp. Run it after any page.toml edit (scripts/hmi.sh check
does not catch this).
"""
import re
import sys
import tomllib
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2] / "lcd-hmi" / "delongui"
NUMERIC = {"number", "xfloat"}
NO_CLAMP_OK = {("bM", "mlPerSec")}


def main() -> int:
    app = tomllib.loads((PROJECT / "app.toml").read_text())
    pages = app["pages"]
    comps = {}
    for p in pages:
        data = tomllib.loads((PROJECT / "pages" / f"{p}.page.toml").read_text())
        comps[p] = data.get("component", [])

    nx = (PROJECT / "pages" / "keybdB.nx").read_text()
    clamps = {}
    page_idx = None
    for line in nx.splitlines():
        m = re.search(r"loadpageid\.val == (\d+)\)", line)
        if m:
            page_idx = int(m.group(1))
        m = re.search(r"loadcmpid\.val == (\d+)\)", line)
        if m and page_idx is not None:
            clamps.setdefault(page_idx, []).append(int(m.group(1)))

    errors = 0
    for pidx, ids in sorted(clamps.items()):
        page = pages[pidx]
        for cid in ids:
            c = comps[page][cid - 1] if 0 < cid <= len(comps[page]) else None
            ok = c is not None and c.get("type") in NUMERIC and c.get("key") == 2
            label = f"{c['name']} ({c['type']})" if c else "<none>"
            print(f"{'ok ' if ok else 'BAD'} p{pidx} {page:<12} id {cid:>3} -> {label}")
            errors += not ok
        clamped = {comps[page][cid - 1]["name"] for cid in ids if 0 < cid <= len(comps[page])}
        for c in comps[page]:
            if c.get("type") in NUMERIC and c.get("key") == 2 and c["name"] not in clamped \
                    and (page, c["name"]) not in NO_CLAMP_OK:
                print(f"BAD p{pidx} {page:<12} {c['name']} is keypad-editable but has no clamp")
                errors += 1
    print("keypad clamp table OK" if not errors else f"{errors} keypad clamp problem(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
