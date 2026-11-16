#!/usr/bin/env python3
"""Render every DeLonghi HMI screen/state headlessly and dump images + hit boxes.

Usage (run with nxwright's Python, it provides HeadlessSimulation):
    capture_screens.py --variant orig    --src <extracted original>  --tag O --out orig.json
    capture_screens.py --variant redesign --src lcd-hmi/delongui     --tag C --out opus.json

`orig` drives the pre-redesign layout (no sub-tabs, timer gauge on bM);
`redesign` drives any layout derived from the nxwright redesign (Gemini or later).
Each screen gets reading-order "easy IDs" (<tag><key>-NN) for review feedback.
"""
import argparse
import base64
import io
import json
import re
from pathlib import Path

from PIL import Image
from nxwright.mcp_server.headless import HeadlessSimulation

COMP_LINE_RE = re.compile(r"^(\S+)\s+(\S+)\s+(\d+),(\d+)\s+(\d+)x(\d+)(?:\s+(.*))?$")

SCREENS = [
    ("01", "splash", "Splash"),
    ("02", "home", "Home"),
    ("02b", "home", "Home (steam mode)"),
    ("03a", "pi", "Pre-infusion (pressure)"),
    ("03b", "pi", "Pre-infusion (flow)"),
    ("03c", "pi", "Pre-infusion (disabled)"),
    ("04a", "sk", "Soak (hold & ramp)"),
    ("04b", "sk", "Soak (triggers)"),
    ("05a", "tp", "Transition (ramp)"),
    ("05b", "tp", "Transition (hold)"),
    ("06", "pf", "Main profile"),
    ("07a", "graphPreview", "Profile preview"),
    ("07b", "graphPreview", "Profile preview (9-bar fallback)"),
    ("08", "dS", "Dose & stop-on-weight"),
    ("09", "bM", "Manual brew"),
    ("10", "bS", "Brew options"),
    ("11", "cleanFlush", "Clean / flush"),
    ("12", "sT", "Temperature settings"),
    ("13", "sP", "System settings"),
    ("14", "brewGraph", "Live brew graph (31 s shot)"),
    ("15", "keybdB", "Numeric keypad"),
    ("16", "keybdA", "Profile rename keyboard"),
    ("17", "popupMSG", "Popup"),
]

# (t seconds, pressure bar, pump flow ml/s, shot weight g) — a typical 36 g shot
SHOT = [
    (0, 0.0, 0.0, 0.0), (2, 1.5, 4.0, 0.0), (6, 2.0, 1.5, 0.0), (10, 2.0, 0.8, 0.5),
    (12, 4.5, 2.5, 1.5), (15, 9.0, 2.0, 4.0), (20, 8.5, 1.8, 12.0), (25, 7.2, 2.0, 22.0),
    (30, 6.2, 2.3, 33.0), (31, 6.0, 2.3, 34.8),
]


def parse_toml_ids(project_dir: Path, page: str) -> dict:
    path = project_dir / "pages" / f"{page}.page.toml"
    ids, idx = {}, 0
    if not path.exists():
        return ids
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if s.startswith("[[component"):
            idx += 1
        elif s.startswith("name = ") and idx:
            ids[s.split("=", 1)[1].strip().strip('"')] = idx
    return ids


def parse_components(text: str, toml_ids: dict, prefix: str):
    comps, hidden = [], []
    for order, line in enumerate(text.splitlines()[1:]):
        if line.startswith("hidden:"):
            hidden = [h.strip() for h in line.split(":", 1)[1].split(",") if h.strip()]
            continue
        m = COMP_LINE_RE.match(line.strip())
        if not m:
            continue
        name, ctype, x, y, w, h, extra = m.groups()
        if name.endswith(":"):
            continue
        x, y, w, h = int(x), int(y), int(w), int(h)
        if x >= 320 or y >= 240 or w <= 0 or h <= 0 or (ctype == "hotspot" and w <= 4 and h <= 4):
            continue
        comps.append(dict(name=name, type=ctype, x=x, y=y, w=w, h=h, extra=(extra or "").strip(),
                          nxId=toml_ids.get(name), order=order))
    for i, c in enumerate(sorted(comps, key=lambda c: (c["y"] // 8, c["x"], c["order"])), start=1):
        c["easyId"] = f"{prefix}-{i:02d}"
    return comps, hidden


def png_to_b64(png: bytes) -> str:
    im = Image.open(io.BytesIO(png)).convert("RGB")
    buf = io.BytesIO()
    im.quantize(colors=256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE).save(buf, format="PNG", optimize=True)
    raw = buf.getvalue() if len(buf.getvalue()) < len(png) else png
    return "data:image/png;base64," + base64.b64encode(raw).decode("ascii")


def inject_state(sim):
    for cmd in [
        'home.qPf1.txt="Classic 9 Bar"', 'home.qPf2.txt="Blooming Esp"', 'home.qPf3.txt="Lever Declining"',
        'home.qPf4.txt="Turbo 6 Bar"', 'home.qPf5.txt="Filter 2.1"', "pId=1", "currentTemp=93", "home.dE.val=4",
        "home.pressure.val=12", "systemUpTime=862", "shotState=1", "shotPreset=2", "dS.numDose.val=180",
        "dS.numDoseForced.val=0", "sT.setPoint.val=93", "sT.steamSetPoint.val=145", "sT.hpwr.val=550",
        "sT.offSet.val=7", "sT.mDiv.val=5", "sT.bDiv.val=2", "sP.n1.val=60", "sP.pump_zero.val=2400", "dims=90",
        "warmupState=0", "targetState=0", "timerState=0",
        "piState=1", "piFlowState=0", "piRPressure=1", "pi.piTime.val=8", "pi.piBar.val=20", "pi.piFlow.val=40",
        "pi.piPumped.val=35", "pi.piAbove.val=0",
        "skState=1", "skCrv=0", "sk.skTime.val=10", "sk.skBar.val=20", "sk.skFlow.val=15", "sk.skRamp.val=6",
        "sk.skWAbv.val=15", "sk.skAbv.val=25", "sk.skBelow.val=10",
        "paState=1", "paType=0", "paCrv=2", "tp.tStart.val=35", "tp.tEnd.val=90", "tp.tSlope.val=5",
        "tp.tLim.val=45", "tp.tHold.val=4", "tp.hLim.val=40",
        "ppState=1", "ppType=0", "pfCrv=1", "pf.pStart.val=90", "pf.pEnd.val=60", "pf.pSlope.val=18",
        "pf.pLim.val=35",
    ]:
        sim.send(cmd)


def tap(sim, x, y, wait_ms=120):
    sim.press(x, y)
    sim.wait(60)
    sim.release()
    sim.wait(wait_ms)


def shot_at(t: float):
    for a, b in zip(SHOT, SHOT[1:]):
        if a[0] <= t <= b[0]:
            u = (t - a[0]) / (b[0] - a[0])
            return tuple(a[i] + (b[i] - a[i]) * u for i in range(1, 4))
    return SHOT[-1][1:]


def capture(project_dir: Path, variant: str, tag: str) -> dict:
    redesign = variant == "redesign"
    sim = HeadlessSimulation(project_dir, page="splash")
    out = {}

    def snap(key, page):
        res = sim.screen(picture=True)
        comps, hidden = parse_components(res["text"], parse_toml_ids(project_dir, page), f"{tag}{key}")
        out[key] = dict(page=page, img=png_to_b64(res["png"]), components=comps, hidden=hidden)

    def show(page, wait=150):
        sim.send(f"page {page}")
        sim.wait(wait)

    try:
        sim.send('splash.build_version.txt="v4.2-dl"')
        sim.send("splash.loadBar.val=64")
        sim.wait(80)
        snap("01", "splash")
        sim.wait(650)
        inject_state(sim)

        show("home")
        snap("02", "home")
        sim.send("targetState=1")
        sim.send("currentTemp=136")
        sim.wait(150)
        snap("02b", "home")
        sim.send("targetState=0")
        sim.send("currentTemp=93")
        sim.wait(100)

        show("pi")
        snap("03a", "pi")
        sim.send("piFlowState=1")
        show("pi")
        snap("03b", "pi")
        sim.send("piState=0")
        sim.send("piFlowState=0")
        show("pi")
        snap("03c", "pi")
        sim.send("piState=1")

        show("sk")
        snap("04a", "sk")
        if redesign:
            tap(sim, 265, 44)
        snap("04b", "sk")

        show("tp")
        snap("05a", "tp")
        if redesign:
            tap(sim, 289, 44)
        snap("05b", "tp")

        show("pf")
        snap("06", "pf")

        show("graphPreview", 250)
        snap("07a", "graphPreview")
        sim.send("skState=0")
        sim.send("ppState=0")
        sim.send("pi.piFlow.val=80")
        show("graphPreview", 250)
        snap("07b", "graphPreview")
        sim.send("skState=1")
        sim.send("ppState=1")
        sim.send("pi.piFlow.val=40")

        show("dS")
        snap("08", "dS")

        sim.send("ppManualState=1")
        show("bM")
        sim.send("bM.flow.val=22")
        sim.send("bM.pressure.val=84")
        sim.send('bM.weight.txt="18.2g"')
        if redesign:
            sim.send("bM.h0.val=25")
            sim.send("bM.mlPerSec.val=25")
            sim.send("timerState=1")
            sim.send("activeBrewTime=14")
            sim.wait(250)
        else:
            sim.send("bM.n0.val=14")
            sim.send("bM.p0.pic=14")
            sim.wait(80)
        snap("09", "bM")
        sim.send("timerState=0")
        sim.send("activeBrewTime=0")
        sim.send("ppManualState=0")

        show("bS")
        snap("10", "bS")
        show("cleanFlush")
        snap("11", "cleanFlush")
        sim.send("flushState=0")
        show("sT")
        snap("12", "sT")
        show("sP")
        snap("13", "sP")

        # Real-time 31 s shot: firmware pushes every ~150 ms, we push every 250 ms.
        show("home")
        sim.send("timerState=1")
        show("brewGraph", 50)
        step = 0.25
        t = 0.0
        while t <= SHOT[-1][0] + 1e-6:
            p, f, w = shot_at(t)
            sim.send(f"brewGraph.pressure.val={round(p * 10)}")
            sim.send(f"brewGraph.flow.val={round(f * 10)}")
            sim.send(f'brewGraph.weight.txt="{w:.1f}g"')
            sim.send("currentTemp=93")
            sim.send("brewGraph.dE.val=4")
            sim.send(f"activeBrewTime={int(t)}")
            sim.wait(int(step * 1000))
            t += step
        snap("14", "brewGraph")
        sim.send("timerState=0")

        show("pi", 100)
        if redesign:
            tap(sim, 82, 137)
        else:
            sim.send('keybdB.input.txt="2.5"')
            sim.send('keybdB.show.txt="2.5"')
            show("keybdB")
        snap("15", "keybdB")

        sim.send('home.qPf1.txt="Classic 9 Bar"')
        sim.send("keybdA.loadpageid.val=1")
        sim.send("keybdA.loadcmpid.val=home.qPf1.id")
        show("keybdA")
        snap("16", "keybdA")

        sim.send('popupMSG.t0.txt="Profile Saved"')
        sim.send("popupMSG.returnid.val=1")
        show("popupMSG")
        snap("17", "popupMSG")
    finally:
        sim.stop()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, type=Path)
    ap.add_argument("--variant", choices=["orig", "redesign"], required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--png-dir", type=Path, help="also write plain PNGs here")
    a = ap.parse_args()
    data = capture(a.src, a.variant, a.tag)
    a.out.write_text(json.dumps(data), encoding="utf-8")
    if a.png_dir:
        a.png_dir.mkdir(parents=True, exist_ok=True)
        for key, page, _ in SCREENS:
            b64 = data[key]["img"].split(",", 1)[1]
            (a.png_dir / f"{key}_{page}.png").write_bytes(base64.b64decode(b64))
    print(f"{a.tag}: captured {len(data)} screens -> {a.out}")


if __name__ == "__main__":
    main()
