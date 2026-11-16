#!/usr/bin/env python3
"""Reproduce the review's functional bugs in the headless simulator.

  probe_bugs.py --gemini <delongui dir> --opus <delongui dir> --out probe.json
Prints a table and writes [{name, gemini, opus, expect}] for build_review_page.py.
"""
import argparse
import json
from pathlib import Path

from nxwright.mcp_server.headless import HeadlessSimulation


def tap(sim, x, y, hold=60):
    sim.press(x, y)
    sim.wait(hold)
    sim.release()
    sim.wait(150)


def probe(src: Path) -> dict:
    sim = HeadlessSimulation(src, page="splash")
    out = {}
    try:
        sim.wait(700)
        stuck = []
        for pg in ("sP", "bS", "dS", "graphPreview"):
            sim.send("targetState=1")
            sim.send(f"page {pg}")
            sim.wait(150)
            sim.send("targetState=0")
            sim.wait(150)
            if sim.values(["modeSelect"])["modeSelect"] == 9:
                stuck.append(pg)
        out["steam"] = ",".join(stuck) or "none"

        sim.send('home.qPf1.txt="A"')
        sim.send('home.qPf2.txt="B"')
        sim.send("pId=1")
        sim.send("page home")
        sim.wait(150)
        tap(sim, 76, 88, hold=1100)
        tap(sim, 285, 16)
        out["cancel"] = sim.values(["pId"])["pId"]

        sim.send("ppManualState=1")
        sim.send("page bM")
        sim.wait(150)
        sim.send("bM.h0.val=40")
        sim.send("bM.mlPerSec.val=40")
        tap(sim, 290, 214)
        before = sim.values(["h0.val"])["h0.val"]
        sim.send("page popupMSG")
        sim.wait(150)
        sim.send("page bM")
        sim.wait(150)
        out["manual"] = f"{before / 10:.1f} -> {sim.values(['h0.val'])['h0.val'] / 10:.1f} ml/s"
    finally:
        sim.stop()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gemini", type=Path, required=True)
    ap.add_argument("--opus", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    g, c = probe(a.gemini), probe(a.opus)
    rows = [
        dict(name="Steam on -> open page -> steam off: pages where modeSelect stays 9 (R03)",
             gemini=g["steam"], opus=c["steam"], expect="none"),
        dict(name="Running profile 1, long-press profile 2, Cancel: highlighted pId (R01)",
             gemini=g["cancel"], opus=c["cancel"], expect="1"),
        dict(name="Manual brew flow target before -> after a popup (R05)",
             gemini=g["manual"], opus=c["manual"], expect="4.2 -> 4.2 ml/s"),
    ]
    a.out.write_text(json.dumps(rows, indent=1))
    for r in rows:
        print(f"{r['name']}\n   gemini={r['gemini']}  opus={r['opus']}  expect={r['expect']}")


if __name__ == "__main__":
    main()
