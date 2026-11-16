import base64
import io
import json
import re
from pathlib import Path
from PIL import Image
from nxwright.mcp_server.headless import HeadlessSimulation

ORIG_DIR = Path("/home/axe/.t3/userdata/providers/antigravity/ac0a3dfd6dddb20962cecff6ee5fe65e19d3923be20e52c5ab52ff877f7e4c32/antigravity-acp/brain/58beaab0-81bd-450c-9797-114f5ec38335/scratch/ext-nextion-lcd-delongui")
NEW_DIR = Path("/home/axe/misc/gaggiuino/lcd-hmi/delongui")
OUT_JSON = Path("/home/axe/.t3/userdata/providers/antigravity/ac0a3dfd6dddb20962cecff6ee5fe65e19d3923be20e52c5ab52ff877f7e4c32/antigravity-acp/brain/58beaab0-81bd-450c-9797-114f5ec38335/scratch/overview_data.json")
OUT_HTML = Path("/home/axe/misc/gaggiuino/docs/delongui-visual-overview.html")

COMP_LINE_RE = re.compile(
    r'^(\S+)\s+(\S+)\s+(\d+),(\d+)\s+(\d+)x(\d+)(?:\s+(.*))?$'
)


def parse_toml_ids(project_dir: Path, page_name: str) -> dict[str, int]:
    toml_path = project_dir / "pages" / f"{page_name}.page.toml"
    if not toml_path.exists():
        return {}
    ids = {}
    cur_name = None
    for line in toml_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if s.startswith("[[components]]"):
            cur_name = None
        elif s.startswith("name = "):
            cur_name = s.split("=", 1)[1].strip().strip('"')
        elif s.startswith("id = ") and cur_name:
            try:
                ids[cur_name] = int(s.split("=", 1)[1].strip())
            except ValueError:
                pass
    return ids


def parse_screen_components(text: str, page_name: str, toml_ids: dict[str, int], prefix: str):
    lines = text.splitlines()
    comps = []
    hidden = []
    for idx, line in enumerate(lines[1:]):
        if line.startswith("hidden:"):
            hidden = [h.strip() for h in line.split(":", 1)[1].split(",") if h.strip()]
            continue
        m = COMP_LINE_RE.match(line.strip())
        if not m:
            continue
        name, ctype, x, y, w, h, extra = m.groups()
        x, y, w, h = int(x), int(y), int(w), int(h)
        if x >= 320 or y >= 240 or w <= 0 or h <= 0:
            continue
        if ctype == "hotspot" and w <= 4 and h <= 4:
            continue
        comps.append({
            "name": name,
            "type": ctype,
            "x": x,
            "y": y,
            "w": w,
            "h": h,
            "extra": (extra or "").strip(),
            "nxId": toml_ids.get(name),
            "order": idx,
        })
    # Assign human-friendly sequential Easy IDs top-to-bottom, left-to-right (intuitive reading order)
    reading = sorted(comps, key=lambda c: (c["y"] // 8, c["x"], c["order"]))
    for idx, c in enumerate(reading, start=1):
        c["easyId"] = f"{prefix}-{idx:02d}"
    return comps, hidden


def png_to_b64(png_bytes: bytes) -> str:
    im = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    buf = io.BytesIO()
    # Quantize to 256 adaptive colors for sharp, compact lossless PNG (~30-45% smaller)
    q = im.quantize(colors=256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
    q.save(buf, format="PNG", optimize=True)
    raw = buf.getvalue()
    if len(raw) >= len(png_bytes):
        raw = png_bytes
    return "data:image/png;base64," + base64.b64encode(raw).decode("ascii")


def inject_realistic_state(sim: HeadlessSimulation, is_new: bool):
    sim.send('home.qPf1.txt="Classic 9 Bar"')
    sim.send('home.qPf2.txt="Blooming Esp"')
    sim.send('home.qPf3.txt="Lever Declining"')
    sim.send('home.qPf4.txt="Turbo 6 Bar"')
    sim.send('home.qPf5.txt="Filter 2.1"')
    sim.send('pId=1')
    sim.send('currentTemp=93')
    sim.send('home.dE.val=4')
    sim.send('home.pressure.val=12')
    sim.send('systemUpTime=862')
    sim.send('shotState=1')
    sim.send('shotPreset=2')
    sim.send('dS.numDose.val=180')
    sim.send('dS.numDoseForced.val=0')
    sim.send('sT.setPoint.val=93')
    sim.send('sT.steamSetPoint.val=145')
    sim.send('sT.hpwr.val=550')
    sim.send('sT.offSet.val=7')
    sim.send('sT.mDiv.val=5')
    sim.send('sT.bDiv.val=2')
    sim.send('sP.n1.val=60')
    if is_new:
        sim.send('sP.pump_zero.val=2400')
    else:
        # Original firmware HMI used 10x or 10000x depending on build; probe safely
        sim.send('sP.pump_zero.val=2400')
    sim.send('dims=90')
    sim.send('warmupState=0')
    sim.send('targetState=0')
    sim.send('timerState=0')

    sim.send('piState=1')
    sim.send('piFlowState=0')
    sim.send('piRPressure=1')
    sim.send('pi.piTime.val=8')
    sim.send('pi.piBar.val=20')
    sim.send('pi.piFlow.val=40')
    sim.send('pi.piPumped.val=35')
    sim.send('pi.piAbove.val=0')

    sim.send('skState=1')
    sim.send('skCrv=0')
    sim.send('sk.skTime.val=10')
    sim.send('sk.skBar.val=20')
    sim.send('sk.skFlow.val=15')
    sim.send('sk.skRamp.val=6')
    sim.send('sk.skWAbv.val=15')
    sim.send('sk.skAbv.val=25')
    sim.send('sk.skBelow.val=10')

    sim.send('paState=1')
    sim.send('paType=0')
    sim.send('paCrv=2')
    sim.send('tp.tStart.val=35')
    sim.send('tp.tEnd.val=90')
    sim.send('tp.tSlope.val=5')
    sim.send('tp.tLim.val=45')
    sim.send('tp.tHold.val=4')
    sim.send('tp.hLim.val=40')

    sim.send('ppState=1')
    sim.send('ppType=0')
    sim.send('pfCrv=1')
    sim.send('pf.pStart.val=90')
    sim.send('pf.pEnd.val=60')
    sim.send('pf.pSlope.val=18')
    sim.send('pf.pLim.val=35')


def tap(sim: HeadlessSimulation, x: int, y: int, wait_ms: int = 120):
    sim.press(x, y)
    sim.wait(60)
    sim.release()
    sim.wait(wait_ms)


def capture_suite(project_dir: Path, is_new: bool):
    tag = "N" if is_new else "O"
    sim = HeadlessSimulation(project_dir, page="splash")
    results = {}
    try:
        def snap(key: str, page_name: str):
            res = sim.screen(picture=True)
            toml_ids = parse_toml_ids(project_dir, page_name)
            comps, hidden = parse_screen_components(
                res["text"], page_name, toml_ids, f"{tag}{key}"
            )
            results[key] = {
                "page": page_name,
                "img": png_to_b64(res["png"]),
                "components": comps,
                "hidden": hidden,
            }

        # 01 splash
        sim.send('splash.build_version.txt="v4.2-dl"')
        sim.send('splash.loadBar.val=64')
        sim.wait(80)
        snap("01", "splash")
        sim.wait(650)

        inject_realistic_state(sim, is_new)

        # 02 home
        sim.send("page home")
        sim.wait(150)
        snap("02", "home")

        # 02b home (Steam Mode)
        sim.send("targetState=1")
        sim.send("currentTemp=136")
        sim.wait(120)
        snap("02b", "home")
        sim.send("targetState=0")
        sim.send("currentTemp=93")
        sim.wait(100)

        # 03a pi (pressure, ON)
        sim.send("piState=1")
        sim.send("piFlowState=0")
        sim.send("page pi")
        sim.wait(150)
        snap("03a", "pi")

        # 03b pi (flow, ON)
        sim.send("piFlowState=1")
        sim.send("page pi")
        sim.wait(150)
        snap("03b", "pi")

        # 03c pi (OFF)
        sim.send("piState=0")
        sim.send("piFlowState=0")
        sim.send("page pi")
        sim.wait(150)
        snap("03c", "pi")
        sim.send("piState=1")

        # 04a sk (hold & ramp)
        sim.send("page sk")
        sim.wait(150)
        snap("04a", "sk")

        # 04b sk (triggers tab in new; same screen in orig)
        if is_new:
            tap(sim, 265, 44)
        snap("04b", "sk")

        # 05a tp (ramp)
        sim.send("page tp")
        sim.wait(150)
        snap("05a", "tp")

        # 05b tp (hold/crv tab in new; same screen in orig)
        if is_new:
            tap(sim, 277, 44)
        snap("05b", "tp")

        # 06 pf
        sim.send("page pf")
        sim.wait(150)
        snap("06", "pf")

        # 07a graphPreview
        sim.send("page graphPreview")
        sim.wait(220)
        snap("07a", "graphPreview")

        # 07b graphPreview (9-bar unrestricted fallback)
        sim.send("skState=0")
        sim.send("ppState=0")
        sim.send("pi.piFlow.val=80")
        sim.send("page graphPreview")
        sim.wait(220)
        snap("07b", "graphPreview")
        sim.send("skState=1")
        sim.send("ppState=1")
        sim.send("pi.piFlow.val=40")

        # 08 dS
        sim.send("page dS")
        sim.wait(150)
        snap("08", "dS")

        # 09 bM
        sim.send("ppManualState=1")
        sim.send("page bM")
        sim.wait(150)
        sim.send("bM.flow.val=22")
        sim.send("bM.pressure.val=84")
        sim.send('bM.weight.txt="18.2g"')
        if is_new:
            sim.send("bM.h0.val=25")
            sim.send("bM.mlPerSec.val=25")
            sim.send("timerState=1")
            sim.send("activeBrewTime=14")
            sim.wait(250)
            snap("09", "bM")
            sim.send("timerState=0")
            sim.send("activeBrewTime=0")
        else:
            sim.send("bM.n0.val=14")
            sim.send("bM.p0.pic=14")
            sim.wait(80)
            snap("09", "bM")
        sim.send("ppManualState=0")

        # 10 bS
        sim.send("page bS")
        sim.wait(150)
        snap("10", "bS")

        # 11 cleanFlush
        sim.send("page cleanFlush")
        sim.wait(150)
        snap("11", "cleanFlush")
        sim.send("flushState=0")

        # 12 sT
        sim.send("page sT")
        sim.wait(150)
        snap("12", "sT")

        # 13 sP
        sim.send("page sP")
        sim.wait(150)
        snap("13", "sP")

        # 14 brewGraph
        sim.send("timerState=1")
        sim.send("page brewGraph")
        sim.wait(100)
        keyframes = [
            (12, 38, 0.0, 93, 2),
            (20, 42, 0.0, 93, 4),
            (22, 32, 0.2, 93, 6),
            (24, 18, 0.6, 93, 8),
            (38, 28, 1.8, 93, 10),
            (65, 30, 4.2, 93, 12),
            (88, 22, 7.8, 93, 14),
            (90, 21, 12.0, 93, 16),
            (86, 22, 16.5, 93, 18),
            (80, 23, 21.0, 93, 20),
            (74, 24, 25.8, 93, 22),
            (68, 25, 30.4, 93, 24),
            (62, 26, 34.8, 93, 26),
        ]
        for idx in range(len(keyframes) - 1):
            a, b = keyframes[idx], keyframes[idx + 1]
            for s in range(5):
                u = s / 5
                sim.send(f"brewGraph.pressure.val={round(a[0] + (b[0] - a[0]) * u)}")
                sim.send(f"brewGraph.flow.val={round(a[1] + (b[1] - a[1]) * u)}")
                sim.send(f'brewGraph.weight.txt="{a[2] + (b[2] - a[2]) * u:.1f}g"')
                sim.send(f"currentTemp={round(a[3] + (b[3] - a[3]) * u)}")
                sim.send("brewGraph.dE.val=4")
                sim.send(f"activeBrewTime={round(a[4] + (b[4] - a[4]) * u)}")
                sim.wait(225)
        a = keyframes[-1]
        sim.send(f"brewGraph.pressure.val={a[0]}")
        sim.send(f"brewGraph.flow.val={a[1]}")
        sim.send(f'brewGraph.weight.txt="{a[2]:.1f}g"')
        sim.send(f"currentTemp={a[3]}")
        sim.send("brewGraph.dE.val=4")
        sim.send(f"activeBrewTime={a[4]}")
        sim.wait(225)
        snap("14", "brewGraph")
        sim.send("timerState=0")

        # 15 keybdB
        sim.send("page pi")
        sim.wait(100)
        if is_new:
            tap(sim, 82, 137)
        else:
            sim.send('keybdB.input.txt="2.5"')
            sim.send('keybdB.show.txt="2.5"')
            sim.send("page keybdB")
            sim.wait(150)
        snap("15", "keybdB")

        # 16 keybdA
        sim.send('home.qPf1.txt="Classic 9 Bar"')
        sim.send("keybdA.loadpageid.val=1")
        sim.send("keybdA.loadcmpid.val=home.qPf1.id")
        sim.send("page keybdA")
        sim.wait(150)
        snap("16", "keybdA")

        # 17 popupMSG
        sim.send('popupMSG.t0.txt="Profile Saved"')
        sim.send("popupMSG.returnid.val=1")
        sim.send("page popupMSG")
        sim.wait(150)
        snap("17", "popupMSG")
    finally:
        sim.stop()
    return results


SCREENS = [
    ("01", "splash", "Splash Screen", "Boot logo, firmware version & progress bar"),
    ("02", "home", "Home Dashboard", "Quick profiles, temperature gauge, pressure & brew/clean/setup nav"),
    ("02b", "home", "Home Dashboard (Steam Mode)", "New: steam status left card & scaled steam ring; Orig: icon-only toggle"),
    ("03a", "pi", "Pre-Infusion (Pressure)", "Fill toggle, pressure/flow mode, timer, target & pressure restriction"),
    ("03b", "pi", "Pre-Infusion (Flow)", "Flow-controlled pre-infusion target & pressure limit"),
    ("03c", "pi", "Pre-Infusion (Disabled)", "Dimmed disabled visual state for all pre-infusion controls"),
    ("04a", "sk", "Soak — Hold & Ramp", "New: tabbed HOLD & RAMP view; Orig: combined single-page soak"),
    ("04b", "sk", "Soak — Exit Triggers", "New: spacious TRIGGERS tab; Orig: same single-page soak"),
    ("05a", "tp", "Transition — Ramp", "New: RAMP tab (start/end/slope/limit); Orig: single-page transition"),
    ("05b", "tp", "Transition — Hold & Curve", "New: HOLD/CRV tab (hold time, hold limit, curve picker)"),
    ("06", "pf", "Main Profile", "Main extraction pressure/flow slope, restriction & curve selector"),
    ("07a", "graphPreview", "Profile Graph Preview", "Full PI -> SK -> RMP -> HD -> TR -> MAIN curve preview & quick jumps"),
    ("07b", "graphPreview", "Graph Preview (9-Bar Fallback)", "Profiling disabled (9 bar unrestricted) + 8.0 ml/s flow scale"),
    ("08", "dS", "Dose & Stop-on-Weight", "Stop-on-weight toggle, dose weight, custom override & 1:1..1:4 ratio tiles"),
    ("09", "bM", "Manual Brew", "Live telemetry readout, timer gauge & manual pump flow slider"),
    ("10", "bS", "Brew Options", "Return-home after shot, brew temp delta & basket prefill toggles"),
    ("11", "cleanFlush", "Group Head Flush", "Active group-head flush prompt & status indicator"),
    ("12", "sT", "Boiler & Temp Settings", "Brew temp, steam temp, heater power, offset & PID dividers"),
    ("13", "sP", "System Settings", "Warmup mode, sleep timeout, pump zero offset, reset & brightness"),
    ("14", "brewGraph", "Live Brew Graph", "Real-time dual-axis pressure/flow waveform, weight, temp & elapsed timer"),
    ("15", "keybdB", "Numeric Keypad", "Touch numeric entry with +/-1 nudges & per-field bounds clamping"),
    ("16", "keybdA", "Profile Rename Keyboard", "QWERTY / symbols / 24-char profile name editor + Load Default"),
    ("17", "popupMSG", "Status Popup", "Transient status toast returning to caller page"),
]


def main():
    orig_data = capture_suite(ORIG_DIR, is_new=False)
    new_data = capture_suite(NEW_DIR, is_new=True)
    bundle = []
    for key, page_name, title, desc in SCREENS:
        bundle.append({
            "key": key,
            "page": page_name,
            "title": title,
            "desc": desc,
            "orig": orig_data[key],
            "new": new_data[key],
        })
    OUT_JSON.write_text(json.dumps(bundle), encoding="utf-8")
    print(f"Captured {len(bundle)} screen pairs -> {OUT_JSON} ({OUT_JSON.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
