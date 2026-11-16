from pathlib import Path
from PIL import Image, ImageDraw
from nxwright.mcp_server.headless import HeadlessSimulation

REPO = Path(__file__).resolve().parents[2]
SRC_DIR = REPO / "lcd-hmi" / "delongui"
OUT_DIR = REPO / "build" / "hmi-verify"
OUT_DIR.mkdir(parents=True, exist_ok=True)

def curr_page(sim):
    txt = sim.screen(picture=False)["text"]
    first = txt.splitlines()[0]
    # "page <name> (320 x 240)..."
    return first.split()[1]

def tap(sim, x, y, wait_ms=120):
    sim.press(x, y)
    sim.wait(60)
    sim.release()
    sim.wait(wait_ms)

def save_shot(sim, name):
    res = sim.screen(picture=True)
    p = OUT_DIR / f"{name}.png"
    p.write_bytes(res["png"])
    return res["text"], p

def main():
    sim = HeadlessSimulation(SRC_DIR, page="splash")
    try:
        # 1. Splash
        sim.send('splash.build_version.txt="v4.2-dl"')
        sim.send('splash.loadBar.val=64')
        sim.wait(60)
        save_shot(sim, "01_splash")

        # Wait for splash -> home
        sim.wait(600)
        print("After splash wait, page:", curr_page(sim))
        assert curr_page(sim) == "home", f"Splash did not transition to home: {curr_page(sim)}"

        # Verify debug1/debug2 globals exist for firmware telemetry/diagnostics
        sim.send("debug1=42")
        sim.send("debug2=99")
        dbg = sim.values(["debug1", "debug2"])
        assert dbg.get("debug1") == 42 and dbg.get("debug2") == 99, f"debug1/debug2 globals missing: {dbg}"

        # Inject realistic machine & profile state (including 24-char profile name test on qPf5)
        sim.send('home.qPf1.txt="Classic 9 Bar"')
        sim.send('home.qPf2.txt="Blooming Esp"')
        sim.send('home.qPf3.txt="Lever Declining"')
        sim.send('home.qPf4.txt="Turbo 6 Bar"')
        sim.send('home.qPf5.txt="123456789012345678901234"')
        assert sim.values(["qPf5.txt"])["qPf5.txt"] == "123456789012345678901234", "qPf5 truncated below 24 chars"
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
        sim.send('sP.pump_zero.val=2400')
        sim.send('dims=90')
        sim.send('warmupState=0')
        sim.send('targetState=0')
        sim.send('timerState=0')

        # Realistic profile params across PI -> SK -> TP -> PF
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

        # Reload home cleanly
        sim.send('page home')
        sim.wait(150)
        save_shot(sim, "02_home")
        vals_home = sim.values(["b2.txt", "tGauge.txt", "modeSelect"])
        print("Home vals:", vals_home)
        assert "36.0g" in str(vals_home.get("b2.txt", "")), f"Unexpected b2.txt: {vals_home}"

        # Verify repeated short taps on home qPf1..2 do NOT accumulate longPressCount -> keybdA
        for _ in range(5):
            tap(sim, 76, 88, wait_ms=260)  # tap qPf2 (sets pId=2)
        assert curr_page(sim) == "home", f"Repeated short taps falsely triggered rename on {curr_page(sim)}"
        assert sim.values(["longPressCount.val"])["longPressCount.val"] == 0, "longPressCount did not reset on short tap"
        print("Home repeated short-tap longPressCount reset OK!")

        # Verify N02-12: qPf.down does NOT mutate pId or highlight; commit happens atomically on .up
        sim.send("pId=1")
        sim.send("page home")
        sim.wait(120)
        q_pics_before = sim.values(["qPf1.pic", "qPf3.pic"])
        sim.press(76, 118)   # down on qPf3
        sim.wait(60)
        mid = sim.values(["pId", "downSlot.val", "qPf1.pic", "qPf3.pic"])
        assert mid["pId"] == 1 and mid["downSlot.val"] == 3, f"qPf3.down prematurely mutated pId or missed downSlot: {mid}"
        assert mid["qPf1.pic"] == q_pics_before["qPf1.pic"] and mid["qPf3.pic"] == q_pics_before["qPf3.pic"], f"qPf3.down prematurely changed highlight: {mid}"
        sim.release()        # clean .up commits pId=3 + highlight + printh 23 02 54 07
        sim.wait(120)
        after_up = sim.values(["pId", "btnPressed.val", "downSlot.val", "qPf1.pic", "qPf3.pic"])
        assert after_up["pId"] == 3 and after_up["btnPressed.val"] == 0 and after_up["downSlot.val"] == 0, f"qPf3.up failed commit: {after_up}"
        assert after_up["qPf3.pic"] == q_pics_before["qPf1.pic"] and after_up["qPf1.pic"] == q_pics_before["qPf3.pic"], f"qPf3.up failed highlight swap: {after_up}"
        # Long-press qPf2 -> keybdA should bind pId=2 and input="Blooming Esp"
        sim.press(76, 88)
        sim.wait(1100)
        sim.release()
        sim.wait(120)
        assert curr_page(sim) == "keybdA", f"Long-press on qPf2 did not open keybdA: {curr_page(sim)}"
        assert sim.values(["pId", "input.txt"]) == {"pId": 2, "input.txt": "Blooming Esp"}, "Long-press keybdA mismatch"
        tap(sim, 285, 16)    # CANCEL -> home
        assert curr_page(sim) == "home", f"Expected home on keybdA Cancel, got {curr_page(sim)}"
        assert sim.values(["pId"])["pId"] == 3, f"keybdA Cancel must restore the running slot (3): {sim.values(['pId'])}"
        print("Home qPf atomic .up commit & long-press rename OK!")

        # Verify active qPf highlight persists after visiting pi and returning to home
        tap(sim, 76, 88)     # pId=2
        tap(sim, 120, 17)    # BREW -> pi
        assert curr_page(sim) == "pi", f"Expected pi, got {curr_page(sim)}"
        tap(sim, 19, 14)     # Back -> home
        assert curr_page(sim) == "home", f"Expected home on Back, got {curr_page(sim)}"
        hv = sim.values(["qPf2.pic", "qPf1.pic", "qPf2.pco", "qPf1.pco"])
        assert hv["qPf2.pic"] != hv["qPf1.pic"], f"qPf2 pic highlight lost after pi->home: {hv}"
        assert hv["qPf2.pco"] == 63422 and hv["qPf1.pco"] == 40213, f"qPf text colors wrong after pi->home: {hv}"
        print("Home qPf highlight persistence across page round-trip OK!")

        # Verify N02-05, N02-11, N02b-07, N02b-11, N02b-12, N02b-13: Steam Mode Left Panel + bStmEdit 'STEAM @' + n5 hidden + tStmHdr PRESSURE + 2.0bar gating + Dynamic tGauge
        sim.send("targetState=1")
        sim.send("currentTemp=136")
        sim.send("home.pressure.val=12")
        sim.wait(120)
        assert sim.values(["stStatus.txt", "bStmEdit.txt", "tStmHdr.txt"]) == {"stStatus.txt": "HEATING...", "bStmEdit.txt": "STEAM @ 145°C", "tStmHdr.txt": "PRESSURE"}, f"Steam HEATING mismatch: {sim.values(['stStatus.txt','bStmEdit.txt','tStmHdr.txt'])}"
        assert int(sim.values(["tGauge.pic"])["tGauge.pic"]) == (136 * 90 // 145), f"Dynamic steam tGauge pic mismatch: {sim.values(['tGauge.pic'])}"
        scr_steam = sim.screen(picture=False)["text"]
        assert "steamPic" not in scr_steam, "steamPic should be removed from home"
        hidden_steam = [h.strip() for h in scr_steam.split("hidden:")[-1].split(",")] if "hidden:" in scr_steam else []
        assert "stCard" not in hidden_steam and "bStmEdit" not in hidden_steam and "tStmHdr" not in hidden_steam and "b2" in hidden_steam and "n5" in hidden_steam and "t7" in hidden_steam, f"Steam visibility swap wrong: {hidden_steam}"
        save_shot(sim, "02b_home_steam")
        sim.send("currentTemp=145")
        sim.wait(100)
        assert sim.values(["stStatus.txt"])["stStatus.txt"] == "PRESSURIZING", f"Expected PRESSURIZING when temp OK but pressure < 2.0 bar, got {sim.values(['stStatus.txt'])}"
        sim.send("home.pressure.val=20")
        sim.wait(100)
        assert sim.values(["stStatus.txt"])["stStatus.txt"] == "STEAM READY", f"Expected STEAM READY at temp & 2.0 bar, got {sim.values(['stStatus.txt'])}"
        assert int(sim.values(["tGauge.pic"])["tGauge.pic"]) == 90, "Steam setpoint should hit 90% notch"
        tap(sim, 77, 216)    # Bottom-left bStmEdit button -> sT
        assert curr_page(sim) == "sT", f"Expected sT from bStmEdit button, got {curr_page(sim)}"
        tap(sim, 22, 14)     # Back -> home
        sim.send("targetState=0")
        sim.send("currentTemp=93")
        sim.send("home.pressure.val=12")
        sim.wait(100)
        scr_brew = sim.screen(picture=False)["text"]
        hidden_brew = [h.strip() for h in scr_brew.split("hidden:")[-1].split(",")] if "hidden:" in scr_brew else []
        assert "n5" not in hidden_brew and "t7" not in hidden_brew and "tStmHdr" in hidden_brew, f"Brew visibility restore wrong: {hidden_brew}"
        assert int(sim.values(["tGauge.pic"])["tGauge.pic"]) == 90, "Brew setpoint should hit 90% notch"
        print("Home Steam Mode Left Panel, STEAM @, n5/tStmHdr swap, 2.0bar ready gate, & dynamic Brew/Steam ring OK!")

        # Verify N02-03: home.b3 (MANUAL) -> bM, and shared MANUAL | CLEAN tabs
        tap(sim, 198, 17)    # MANUAL nav button -> bM
        assert curr_page(sim) == "bM", f"Expected bM from home.b3, got {curr_page(sim)}"
        assert sim.values(["ppManualState", "flushState"]) == {"ppManualState": 1, "flushState": 0}
        tap(sim, 164, 15)    # CLEAN tab -> cleanFlush
        assert curr_page(sim) == "cleanFlush", f"Expected cleanFlush from bM CLEAN tab, got {curr_page(sim)}"
        assert sim.values(["ppManualState", "flushState"]) == {"ppManualState": 0, "flushState": 1}
        tap(sim, 84, 15)     # MANUAL tab -> bM
        assert curr_page(sim) == "bM", f"Expected bM from cleanFlush MANUAL tab, got {curr_page(sim)}"
        assert sim.values(["ppManualState", "flushState"]) == {"ppManualState": 1, "flushState": 0}
        tap(sim, 22, 15)     # Back -> home
        assert curr_page(sim) == "home"
        print("home.b3 -> bM & MANUAL|CLEAN submenu navigation OK!")

        # Restore pId=1 cleanly for screenshots
        sim.send("pId=1")
        sim.send("page home")
        sim.wait(120)
        save_shot(sim, "02_home")

        # 2. Tap BREW nav button (120, 17) -> pi
        tap(sim, 120, 17)
        assert curr_page(sim) == "pi", f"Expected pi, got {curr_page(sim)}"
        assert "b1" not in sim.screen(picture=False)["text"], "b1 should be removed from pi footer"
        save_shot(sim, "03_pi_on")

        # Test stepper + on piBar (bBrP at x=120..154, y=125..150 -> center 136, 137)
        before_bar = sim.values(["piBar.val"])["piBar.val"]
        tap(sim, 136, 137)
        after_bar = sim.values(["piBar.val"])["piBar.val"]
        assert after_bar == before_bar + 5, f"Stepper + failed: {before_bar} -> {after_bar}"
        print(f"PI bar stepper +: {before_bar} -> {after_bar}")

        # Test pi.piPumped preserves whole-ml integer scale (600 -> "600" in keybdB, +10 step -> 610) & clamps 1200 -> 1000
        sim.send("pi.piPumped.val=600")
        tap(sim, 238, 89)  # tap piPumped well -> keybdB
        assert curr_page(sim) == "keybdB", f"Expected keybdB from piPumped, got {curr_page(sim)}"
        assert sim.values(["input.txt"])["input.txt"] == "600", f"piPumped tenfold mismatch in keybdB: {sim.values(['input.txt'])}"
        # Clear "600" and enter "1200" -> OK must clamp to 1000
        for _ in range(3):
            tap(sim, 276, 71, 60)  # DEL
        tap(sim, 42, 71, 60)   # 1
        tap(sim, 119, 71, 60)  # 2
        tap(sim, 42, 212, 60)  # 0
        tap(sim, 42, 212, 60)  # 0
        tap(sim, 237, 212, 120) # OK
        assert curr_page(sim) == "pi", f"Expected pi after piPumped OK, got {curr_page(sim)}"
        assert sim.values(["piPumped.val"])["piPumped.val"] == 1000, f"piPumped keybdB max clamp failed: {sim.values(['piPumped.val'])}"
        sim.send("pi.piPumped.val=600")
        tap(sim, 292, 89)
        after_pumped = sim.values(["piPumped.val"])["piPumped.val"]
        assert after_pumped == 610, f"Expected piPumped=610 from 600+10, got {after_pumped}"
        print("PI piPumped whole-ml 600 -> '600', keybdB 1200->1000 clamp, & 600+10 -> 610 OK!")
        sim.send("pi.piPumped.val=35")

        # Test keybdB +1/-1 decimal preservation ("2.5" -> "3.5" -> "2.5") and 0 clamp
        tap(sim, 82, 137)  # piBar (currently 25 -> "2.5") -> keybdB
        assert curr_page(sim) == "keybdB", f"Expected keybdB, got {curr_page(sim)}"
        tap(sim, 276, 118, 80)  # +1
        assert sim.values(["input.txt"])["input.txt"] == "3.5", f"keybdB +1 failed: {sim.values(['input.txt'])}"
        tap(sim, 276, 165, 80)  # -1
        assert sim.values(["input.txt"])["input.txt"] == "2.5", f"keybdB -1 failed: {sim.values(['input.txt'])}"
        for _ in range(3):
            tap(sim, 276, 165, 60)  # -1 clamp at 0.5
        assert sim.values(["input.txt"])["input.txt"] == "0.5", f"keybdB -1 clamp failed: {sim.values(['input.txt'])}"
        print("keybdB +1/-1 decimal preservation & 0 clamp OK!")
        tap(sim, 276, 25, 100)  # CANCEL -> pi
        assert curr_page(sim) == "pi", f"Expected pi after Cancel, got {curr_page(sim)}"

        # Test tapping piBar number (x=82, y=137) -> keybdB round-trip & xfloat max clamp (15.5 -> 120)!
        tap(sim, 82, 137)
        assert curr_page(sim) == "keybdB", f"Expected keybdB, got {curr_page(sim)}"
        save_shot(sim, "15_keybdB")
        for _ in range(3):
            tap(sim, 276, 71, 60)  # DEL
        tap(sim, 42, 71, 60)    # 1
        tap(sim, 119, 118, 60)  # 5
        tap(sim, 119, 212, 60)  # .
        tap(sim, 119, 118, 60)  # 5
        tap(sim, 237, 212, 120) # OK
        assert curr_page(sim) == "pi", f"Expected return to pi, got {curr_page(sim)}"
        assert sim.values(["piBar.val"])["piBar.val"] == 120, f"piBar keybdB 15.5->120 clamp failed: {sim.values(['piBar.val'])}"
        tap(sim, 82, 137)
        for _ in range(4):
            tap(sim, 276, 71, 60)  # DEL
        tap(sim, 196, 71, 60)   # 3
        tap(sim, 119, 212, 60)  # .
        tap(sim, 42, 212, 60)   # 0
        tap(sim, 237, 212, 120) # OK
        kb_bar = sim.values(["piBar.val"])["piBar.val"]
        assert kb_bar == 30, f"Expected piBar=30 after keybdB, got {kb_bar}"
        print("keybdB round-trip piBar -> 3.0 & xfloat 15.5->12.0 clamp OK!")
        sim.send("pi.piBar.val=20")

        # Toggle piType to FLOW & screenshot, then back
        tap(sim, 154, 44)
        save_shot(sim, "03b_pi_flow")
        tap(sim, 154, 44)

        # Toggle btPiState OFF & verify piPAbv switches to dimmed switch asset
        pi_abv_on_pics = sim.values(["piPAbv.pic", "piPAbv.pic2"])
        tap(sim, 68, 44)
        pi_abv_off_pics = sim.values(["piPAbv.pic", "piPAbv.pic2"])
        assert pi_abv_off_pics["piPAbv.pic"] != pi_abv_on_pics["piPAbv.pic"], f"piPAbv did not dim when disabled: {pi_abv_off_pics}"
        assert pi_abv_off_pics["piPAbv.pic2"] != pi_abv_on_pics["piPAbv.pic2"], f"piPAbv pic2 did not dim when disabled: {pi_abv_off_pics}"
        save_shot(sim, "03c_pi_off")
        tap(sim, 68, 44)

        # 3. Tap 2 Soak (143, 14) -> sk
        tap(sim, 143, 14)
        assert curr_page(sim) == "sk", f"Expected sk, got {curr_page(sim)}"
        assert "b1" not in sim.screen(picture=False)["text"], "b1 should be removed from sk footer"
        save_shot(sim, "04_sk_hold")
        tap(sim, 265, 44)  # TRIGGERS tab
        save_shot(sim, "04b_sk_trig")
        # Verify sk tab persists across keybdB round-trip
        tap(sim, 226, 82)  # skWAbv -> keybdB
        assert curr_page(sim) == "keybdB", f"Expected keybdB from skWAbv, got {curr_page(sim)}"
        tap(sim, 276, 25)  # CANCEL -> sk
        assert curr_page(sim) == "sk", f"Expected sk after Cancel, got {curr_page(sim)}"
        assert sim.values(["viewMode.val"])["viewMode.val"] == 1, "sk TRIGGERS tab did not persist across keybdB"
        tap(sim, 164, 44)  # Reset back to HOLD & RAMP tab
        print("sk tab persistence across keybdB OK!")

        # 4. Tap 3 Trans (213, 14) -> tp
        tap(sim, 213, 14)
        assert curr_page(sim) == "tp", f"Expected tp, got {curr_page(sim)}"
        assert "b1" not in sim.screen(picture=False)["text"], "b1 should be removed from tp footer"
        save_shot(sim, "05_tp_ramp")
        vis_ramp = sim.screen(picture=False)["text"]
        assert "pfEaseInOut" in vis_ramp and "holdDiag" not in vis_ramp.split("hidden:")[0], "tp RAMP tab must show the curve picker next to the ramp values"
        tap(sim, 289, 44)  # HOLD tab
        save_shot(sim, "05b_tp_hold")
        assert sim.values(["viewMode.val"])["viewMode.val"] == 1, "tp HOLD tab did not activate"
        # Verify tp tab persists across keybdB round-trip
        tap(sim, 144, 76)  # tHold -> keybdB
        assert curr_page(sim) == "keybdB", f"Expected keybdB from tHold, got {curr_page(sim)}"
        tap(sim, 276, 25)  # CANCEL -> tp
        assert curr_page(sim) == "tp", f"Expected tp after Cancel, got {curr_page(sim)}"
        assert sim.values(["viewMode.val"])["viewMode.val"] == 1, "tp HOLD/CRV tab did not persist across keybdB"
        tap(sim, 237, 44)  # Reset back to RAMP tab
        print("tp tab persistence across keybdB OK!")

        # 5. Tap 4 Main (284, 14) -> pf
        tap(sim, 284, 14)
        assert curr_page(sim) == "pf", f"Expected pf, got {curr_page(sim)}"
        assert "b1" not in sim.screen(picture=False)["text"], "b1 should be removed from pf footer"
        save_shot(sim, "06_pf")

        # 6. Tap Preview (160, 223) -> graphPreview
        tap(sim, 160, 223, 250)
        assert curr_page(sim) == "graphPreview", f"Expected graphPreview, got {curr_page(sim)}"
        save_shot(sim, "07_graphPreview")

        # Test phase jump button 1 PI on graphPreview
        tap(sim, 33, 222)
        assert curr_page(sim) == "pi", f"Expected pi from graphPreview jump, got {curr_page(sim)}"

        # Verify graphPreview skips skRamp when targetValue <= 0 (matching profile_builder.cpp:74-79),
        # includes skRamp when ppState==0 (9 bar fallback), and plots 8.0 ml/s PI flow + f1==-1 fallback
        sim.send("skState=0")
        sim.send("ppState=1")
        sim.send("paState=0")
        sim.send("pf.pStart.val=0")
        sim.send("page graphPreview")
        sim.wait(200)
        v_skip_pf = sim.values(["d3.val", "tSum.txt"])
        assert v_skip_pf["d3.val"] == 0 and "RMP" not in v_skip_pf["tSum.txt"], f"Expected RMP skipped for pf.pStart=0: {v_skip_pf}"

        sim.send("paState=1")
        sim.send("tp.tStart.val=0")
        sim.send("page graphPreview")
        sim.wait(200)
        v_skip_tp = sim.values(["d3.val", "tSum.txt"])
        assert v_skip_tp["d3.val"] == 0 and "RMP" not in v_skip_tp["tSum.txt"], f"Expected RMP skipped for tp.tStart=0: {v_skip_tp}"

        sim.send("pf.pStart.val=90")
        sim.send("tp.tStart.val=35")

        # Verify Astra Round 4 instant-transition RMP endpoint case:
        # ppState=1, paState=0, pfCrv=4, pf.pStart=0, pf.pEnd=90, skState=1, skRamp=6 -> RMP ends at 90 (y=81), no dip to 0 in MAIN
        sim.send("piState=0")
        sim.send("skState=1")
        sim.send("sk.skBar.val=20")
        sim.send("sk.skRamp.val=6")
        sim.send("ppState=1")
        sim.send("paState=0")
        sim.send("pfCrv=4")
        sim.send("pf.pStart.val=0")
        sim.send("pf.pEnd.val=90")
        sim.send("page graphPreview")
        sim.wait(220)
        assert sim.values(["d3.val"])["d3.val"] == 6, f"Expected d3=6 for pfCrv=4, pStart=0, pEnd=90: {sim.values(['d3.val'])}"
        _, instant_png = save_shot(sim, "07c_graphPreview_instant_rmp")
        im_inst = Image.open(instant_png).convert("RGB")
        # In 07c, tTot = 10 + 6 + 18 + 6 = 40; SK=67px (x=27..94), RMP=40px (x=94..134), MAIN starts x=134
        # Check amber pixel (>200 red) near y=81 (9.0 bar) at x=133..140, and NO amber pixel near y=180 (0 bar) in x=133..150
        amber_at_9bar = any(im_inst.getpixel((xx, yy))[0] > 200 and im_inst.getpixel((xx, yy))[2] < 60 for xx in range(133, 141) for yy in range(78, 85))
        amber_at_0bar_main = any(im_inst.getpixel((xx, yy))[0] > 200 and im_inst.getpixel((xx, yy))[2] < 60 for xx in range(134, 155) for yy in range(175, 183))
        assert amber_at_9bar and not amber_at_0bar_main, f"Instant RMP endpoint failed: 9bar={amber_at_9bar}, dip0={amber_at_0bar_main}"
        sim.send("piState=1")
        sim.send("pfCrv=1")
        sim.send("pf.pStart.val=90")
        sim.send("pf.pEnd.val=60")

        sim.send("skState=0")
        sim.send("ppState=0")
        sim.send("pi.piFlow.val=80")
        sim.send("page graphPreview")
        sim.wait(200)
        assert sim.values(["d3.val"])["d3.val"] == 6, f"Expected d3=6 when skState=0, piState=1, ppState=0: {sim.values(['d3.val'])}"
        assert sim.values(["f1.val"])["f1.val"] == -1, f"Expected f1=-1 (unrestricted) when ppState=0: {sim.values(['f1.val'])}"
        save_shot(sim, "07b_graphPreview_unrestricted")
        sim.send("skState=1")
        sim.send("ppState=1")
        sim.send("pi.piFlow.val=40")
        print("graphPreview targetValue<=0 ramp exclusion, instant RMP endpoint, ppState=0 ramp, 8.0 ml/s scale, and f1=-1 fallback OK!")

        # 7. Dose settings dS
        sim.send("page dS")
        sim.wait(150)
        save_shot(sim, "08_dS")

        # 8. Manual brew bM (0.2 ml/s step precision + pure-seconds timer >60s + 6-tile grid)
        sim.send("ppManualState=1")
        sim.send("page bM")
        sim.wait(150)
        tap(sim, 290, 214)  # +0.2 flow step -> 2
        assert sim.values(["h0.val", "mlPerSec.val"]) == {"h0.val": 2, "mlPerSec.val": 2}, "bFlP did not step +2 (0.2 ml/s)"
        tap(sim, 30, 214)   # -0.2 flow step -> 0
        assert sim.values(["h0.val", "mlPerSec.val"]) == {"h0.val": 0, "mlPerSec.val": 0}, "bFlM did not step -2 (0.2 ml/s)"
        sim.send("bM.flow.val=22")
        sim.send("bM.pressure.val=84")
        sim.send('bM.weight.txt="18.2g"')
        assert sim.values(["weight.txt"])["weight.txt"] == "18.2g", f"bM.weight truncated: {sim.values(['weight.txt'])}"
        print("bM.weight full '18.2g' & ±0.2 ml/s steppers OK!")
        sim.send("bM.h0.val=25")
        sim.send("bM.mlPerSec.val=25")
        sim.send("timerState=1")
        sim.send("activeBrewTime=75")
        sim.wait(250)
        assert sim.values(["n0.val"])["n0.val"] == 75, f"bM seconds-only timer >60s failed: {sim.values(['n0.val'])}"
        # Flow target must survive a popup round-trip (popupMSG returns by reloading bM)
        tap(sim, 290, 214)
        tap(sim, 290, 214)
        before = sim.values(["h0.val"])["h0.val"]
        sim.send('popupMSG.t0.txt="Scales tared"')
        sim.send("popupMSG.returnid.val=6")
        sim.send("page popupMSG")
        sim.wait(200)
        sim.send("page bM")
        sim.wait(150)
        assert sim.values(["h0.val"])["h0.val"] == before, f"bM flow target reset after popup reload: {before} -> {sim.values(['h0.val'])}"
        print("bM flow target persists across popup reload OK!")
        sim.send("activeBrewTime=14")
        sim.wait(250)
        assert sim.values(["n0.val"])["n0.val"] == 14, f"bM timer mismatch: {sim.values(['n0.val'])}"
        save_shot(sim, "09_bM")
        sim.send("timerState=0")
        sim.send("activeBrewTime=0")
        sim.send("ppManualState=0")

        # 9. Brew options bS
        sim.send("page bS")
        sim.wait(150)
        save_shot(sim, "10_bS")

        # 10. Clean/Flush
        sim.send("page cleanFlush")
        sim.wait(150)
        save_shot(sim, "11_cleanFlush")
        sim.send("flushState=0")

        # 11. Temp settings sT (plus keybdB min-clamp tests: mDiv 0->1, setPoint 20->50)
        sim.send("page sT")
        sim.wait(150)
        tap(sim, 82, 212)  # sT.mDiv well -> keybdB
        assert curr_page(sim) == "keybdB", f"Expected keybdB from sT.mDiv, got {curr_page(sim)}"
        for _ in range(2):
            tap(sim, 276, 71, 60)  # DEL
        tap(sim, 42, 212, 60)   # 0
        tap(sim, 237, 212, 120) # OK
        assert curr_page(sim) == "sT", f"Expected sT after mDiv OK, got {curr_page(sim)}"
        assert sim.values(["mDiv.val"])["mDiv.val"] == 1, f"sT.mDiv keybdB 0->1 min clamp failed: {sim.values(['mDiv.val'])}"
        tap(sim, 82, 80)   # sT.setPoint well -> keybdB
        assert curr_page(sim) == "keybdB", f"Expected keybdB from sT.setPoint, got {curr_page(sim)}"
        for _ in range(3):
            tap(sim, 276, 71, 60)  # DEL
        tap(sim, 119, 71, 60)  # 2
        tap(sim, 42, 212, 60)  # 0
        tap(sim, 237, 212, 120) # OK
        assert sim.values(["setPoint.val"])["setPoint.val"] == 50, f"sT.setPoint keybdB 20->50 min clamp failed: {sim.values(['setPoint.val'])}"
        print("sT keybdB min clamps (mDiv 0->1, setPoint 20->50) OK!")
        sim.send("sT.mDiv.val=5")
        sim.send("sT.setPoint.val=93")
        sim.wait(80)
        save_shot(sim, "12_sT")

        # 12. System settings sP (verify pump_zero 10000x scale & 2100..3100 clamping)
        sim.send("sP.pump_zero.val=2225")
        sim.send("page sP")
        sim.wait(150)
        tap(sim, 135, 145)  # +25 -> 2250
        assert sim.values(["pump_zero.val"])["pump_zero.val"] == 2250, f"pump_zero +25 failed: {sim.values(['pump_zero.val'])}"
        tap(sim, 29, 145)   # -25 -> 2225
        assert sim.values(["pump_zero.val"])["pump_zero.val"] == 2225, f"pump_zero -25 failed: {sim.values(['pump_zero.val'])}"
        sim.send("sP.pump_zero.val=2100")
        tap(sim, 29, 145)
        assert sim.values(["pump_zero.val"])["pump_zero.val"] == 2100, "pump_zero min clamp 2100 failed"
        sim.send("sP.pump_zero.val=3100")
        tap(sim, 135, 145)
        assert sim.values(["pump_zero.val"])["pump_zero.val"] == 3100, "pump_zero max clamp 3100 failed"
        print("sP.pump_zero 2100..3100 step 25 OK!")
        # modeSelect must follow the steam switch on every page, not only on load
        for pg in ("sP", "bS", "dS", "graphPreview"):
            sim.send("targetState=1")
            sim.send(f"page {pg}")
            sim.wait(150)
            sim.send("targetState=0")
            sim.wait(150)
            assert sim.values(["modeSelect"])["modeSelect"] != 9, f"{pg}: modeSelect stuck at steam (9) after steam switch off"
        print("modeSelect tracks steam switch on sP/bS/dS/graphPreview OK!")
        sim.send("sP.pump_zero.val=2400")
        sim.wait(80)
        save_shot(sim, "13_sP")

        # 13. Live brewGraph simulation with curved telemetry (~65 samples)
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
        telemetry = []
        for idx in range(len(keyframes) - 1):
            a, b = keyframes[idx], keyframes[idx + 1]
            steps = 5
            for s in range(steps):
                u = s / steps
                telemetry.append((
                    round(a[0] + (b[0] - a[0]) * u),
                    round(a[1] + (b[1] - a[1]) * u),
                    f"{a[2] + (b[2] - a[2]) * u:.1f}g",
                    round(a[3] + (b[3] - a[3]) * u),
                    round(a[4] + (b[4] - a[4]) * u),
                ))
        telemetry.append((keyframes[-1][0], keyframes[-1][1], f"{keyframes[-1][2]:.1f}g", keyframes[-1][3], keyframes[-1][4]))
        for p, f, w, t, sec in telemetry:
            sim.send(f"brewGraph.pressure.val={p}")
            sim.send(f"brewGraph.flow.val={f}")
            sim.send(f'brewGraph.weight.txt="{w}"')
            sim.send(f"currentTemp={t}")
            sim.send("brewGraph.dE.val=4")
            sim.send(f"activeBrewTime={sec}")
            sim.wait(225)
        save_shot(sim, "14_brewGraph")
        assert sim.values(["n0.val"])["n0.val"] == sim.values(["activeBrewTime"])["activeBrewTime"], "brewGraph timer must show whole seconds"
        sim.send("timerState=0")

        # 14. KeybdA (verify 24-char rename capacity, then Classic 9 Bar screenshot)
        sim.send('home.qPf5.txt="12345678901234567890123"')
        sim.send("keybdA.loadpageid.val=1")
        sim.send("keybdA.loadcmpid.val=home.qPf5.id")
        sim.send("page keybdA")
        sim.wait(120)
        assert sim.values(["inputlenth.val"])["inputlenth.val"] == 24, f"keybdA inputlenth != 24: {sim.values(['inputlenth.val'])}"
        tap(sim, 17, 89, 80)  # tap 'q' -> 24th char
        assert sim.values(["input.txt"])["input.txt"] == "12345678901234567890123q", f"keybdA 24-char append failed: {sim.values(['input.txt'])}"
        print("keybdA 24-char profile rename capacity OK!")

        sim.send('home.qPf1.txt="Classic 9 Bar"')
        sim.send("keybdA.loadpageid.val=1")
        sim.send("keybdA.loadcmpid.val=home.qPf1.id")
        sim.send("page keybdA")
        sim.wait(150)
        save_shot(sim, "16_keybdA")

        # 15. PopupMSG
        sim.send('popupMSG.t0.txt="Profile Saved Successfully"')
        sim.send("popupMSG.returnid.val=1")
        sim.send("page popupMSG")
        sim.wait(150)
        save_shot(sim, "17_popupMSG")

        # Build compact 4x5 contact sheet for visual review & council
        ordered = [
            "01_splash", "02_home", "03_pi_on", "03b_pi_flow",
            "03c_pi_off", "04_sk_hold", "04b_sk_trig", "05_tp_ramp",
            "05b_tp_hold", "06_pf", "07_graphPreview", "14_brewGraph",
            "08_dS", "09_bM", "10_bS", "11_cleanFlush",
            "12_sT", "13_sP", "15_keybdB", "16_keybdA",
        ]
        cols, rows = 4, 5
        pw, ph, pad = 320, 240, 12
        sheet = Image.new("RGB", (cols * pw + (cols + 1) * pad, rows * (ph + 20) + (rows + 1) * pad), (10, 12, 16))
        dr = ImageDraw.Draw(sheet)
        for idx, nm in enumerate(ordered):
            r, c = divmod(idx, cols)
            x0 = pad + c * (pw + pad)
            y0 = pad + r * (ph + 20 + pad)
            im = Image.open(OUT_DIR / f"{nm}.png").convert("RGB")
            sheet.paste(im, (x0, y0 + 18))
            dr.text((x0 + 4, y0 + 2), nm, fill=(200, 210, 225))
        sheet_path = OUT_DIR / "all_pages_sheet.png"
        sheet.save(sheet_path)
        print("ALL VERIFICATION ASSERTIONS PASSED! Saved contact sheet:", sheet_path)
    finally:
        sim.stop()

if __name__ == "__main__":
    main()
