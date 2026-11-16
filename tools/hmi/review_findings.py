"""Review findings for the DeLonghi HMI (Gemini redesign @75b78f4 -> this branch).

Single source for docs/hmi-review.md and docs/delongui-hmi-review.html.
`refs` name components per variant ("G" = Gemini build, "C" = this branch); the page
builder turns them into hover IDs such as G14-03 / C14-03.
status: "fixed" = done and verified in this branch, "next" = explicit instruction.
"""

FINDINGS = [
    # ---------------------------------------------------------------- functional bugs
    dict(id="R01", sev="high", status="fixed", screens=["02", "16"],
         title="Long-press then Cancel leaves the wrong profile highlighted (the 'no popup' bug you reported)",
         problem="Holding a profile for 1 s sets pId to that slot before opening the rename keyboard. "
                 "Cancel just returns home, which highlights pId, but trigger 07 was never sent, so the "
                 "firmware keeps running the old profile with no 'Profile switched!' popup. That matches "
                 "your N02-12 report: the new profile stays selected and you have to tap another one and come back.",
         instruction="program.nx: add `int pIdPrev`. home.nx tm0 long-press branch: `pIdPrev = pId` before "
                     "`pId = downSlot.val`. keybdA.nx b251.up (Cancel): `if (loadpageid.val == 1) { pId = pIdPrev }`.",
         evidence="Simulator probe: Gemini build pId after Cancel = 2 (running slot is 1); this branch = 1.",
         refs={"G": ["home.qPf2"], "C": ["home.qPf2"]}),
    dict(id="R02", sev="high", status="fixed", screens=["16"],
         title="Rename + OK saves into the long-pressed slot but never loads it",
         problem="Trigger 08 makes lcdFetchCurrentProfile() write to the slot shown on screen "
                 "(settings.activeProfile only), while runningCfg stays on the old slot. The HMI highlights "
                 "the new slot; later Saves still target the old one.",
         instruction="keybdA.nx b210.up (OK): after `printh 23 02 54 08` add "
                     "`if (loadpageid.val == 1) { printh 23 02 54 07 }` so the firmware switches to the slot it just saved.",
         evidence="nextion.cpp:385-387 vs gaggiuino.ino:431-437 / 495-498.",
         refs={"G": ["keybdA.show"], "C": ["keybdA.show"]}),
    dict(id="R03", sev="high", status="fixed", screens=["13", "10", "08", "07a"],
         title="modeSelect stays at 'steam' (9) after the steam switch goes off on sP, bS, dS and graphPreview",
         problem="These pages compute modeSelect once (or never). If you flip steam off while on one of them, "
                 "the firmware keeps reading modeSelect=9 and starting a brew runs flushActivated() instead of "
                 "the profile. pi, sk, pf and tp only recompute on load.",
         instruction="Run the same modeSelect block as sT.nx tm0 every 50 ms on pi, sk, pf, tp and dS, and add a "
                     "50 ms tm0 timer with that block to sP, bS and graphPreview.",
         evidence="Simulator probe (steam on, open page, steam off): Gemini = 9 on all four pages; this branch = 0.",
         refs={"G": ["sP.b4"], "C": ["sP.b4"]}),
    dict(id="R04", sev="high", status="fixed", screens=["03a", "06", "05a"],
         title="BAR/FLOW toggle desyncs the ON/OFF switch from what will be saved",
         problem="Trigger 06 makes the firmware call uploadPageCfg() and rewrite piState/ppState/paState and "
                 "the curve from EEPROM. The page switches are only copied from those globals on load, so an "
                 "unsaved 'ON' still shows ON while the global is already 0. Leaving the page saves it disabled.",
         instruction="pi/pf/tp: after `printh 23 02 54 06` set `syncTicks.val = 20`. In tm0, count down and at "
                     "ticks 14 and 0 copy the globals back into the switches, then `click refUI,0`.",
         evidence="nextion.cpp:197-260 (uploadPageCfg) and gaggiuino.ino:470-493.",
         refs={"G": ["pi.piType"], "C": ["pi.piType"]}),
    dict(id="R05", sev="high", status="fixed", screens=["09"],
         title="Manual brew: the flow slider snaps back to 0 mid-shot after any popup",
         problem="popupMSG returns by reloading bM, and bM.load does `h0.val = h0.minval`. A 'Scales tared' "
                 "or 'Fill the water tank' toast mid-shot cuts the pump target to 0.",
         instruction="Add `int manFlow` to program.nx. bM.load: `h0.val = manFlow`. Update manFlow on every slider "
                     "or stepper event, and reset it to 0 only on Back and on the CLEAN tab.",
         evidence="Simulator probe: Gemini h0 42 -> 0 after the popup; this branch 42 -> 42.",
         refs={"G": ["bM.h0"], "C": ["bM.h0"]}),
    # ---------------------------------------------------------------- live graph
    dict(id="R06", sev="high", status="fixed", screens=["14"],
         title="Brew graph axis labels don't match the plotted values; anything above 9.7 bar is clipped",
         problem="s0 uses dis=140 and gdh=27. A 9 bar peak is drawn about 0.4 bar too high against the labels, "
                 "and the 136 px plot tops out at 9.7 bar.",
         instruction="s0: dis=125, gdh=25, so every gridline is exactly 2 bar, 2 ml/s or 20 g, with 10.9 bar of headroom. "
                     "tm0 tim=250 with gdw=40 gives exactly 10 s per vertical gridline and ~70 s on screen. "
                     "Redraw the axis labels at y = 176 - 25*k in gen_assets.py.",
         refs={"G": ["brewGraph.s0"], "C": ["brewGraph.s0"]}),
    dict(id="R07", sev="medium", status="fixed", screens=["14"],
         title="The temperature trace is a flat line at the top, and the right axis is red (temperature) but is really weight",
         problem="At 1.4 px/°C a stable 93 °C is just a line hugging the 10 bar gridline. The right-axis numbers "
                 "are red, but the only trace that uses them in practice is weight.",
         instruction="Replace channel 3 with a dim-green target-weight reference line (shotTarget/10, only when "
                     "stop-on-weight is on), and colour the right axis green (grams). Temperature stays in its tile.",
         refs={"G": ["brewGraph.s0", "brewGraph.tGauge"], "C": ["brewGraph.s0", "brewGraph.weight"]}),
    dict(id="R08", sev="medium", status="fixed", screens=["14", "09"],
         title="Shot timer shows MM:SS on the brew graph and seconds on manual brew",
         problem="You asked for the shot timer to always be in seconds (N09-14). The brew graph still used two "
                 "zero-padded numbers with a colon.",
         instruction="brewGraph: one number `n0 = activeBrewTime` (lenth=0) plus a small dim 's' suffix. Remove n1.",
         refs={"G": ["brewGraph.n1", "brewGraph.n0"], "C": ["brewGraph.n0", "brewGraph.time_seconds"]}),
    dict(id="R09", sev="medium", status="fixed", screens=["14", "09"],
         title="Flow is labelled 'g/s', but the firmware sends pump flow in ml/s",
         problem="gaggiuino.ino:380 sends `lcdSetFlow(currentState.smoothedPumpFlow * 10)`, which is pump flow "
                 "(ml/s), not weight flow. The original HMI already said g/s; the redesign copied it.",
         instruction="Label the tiles 'FLOW ml/s' on brewGraph (gen_assets.py) and bM (t0.txt).",
         refs={"G": ["brewGraph.flow", "bM.t0"], "C": ["brewGraph.flow", "bM.t0"]}),
    # ---------------------------------------------------------------- consistency / UX
    dict(id="R10", sev="medium", status="fixed", screens=["12", "13", "09", "11", "03a"],
         title="The selected tab looks exactly like the SAVE button",
         problem="Both use a solid ice-blue fill. In the sT and sP headers 'TEMP' and 'SAVE' sit side by side "
                 "with the same style, so navigation and the main action can't be told apart.",
         instruction="tab*_on: raised neutral surface with a 3 px accent underline and white label "
                     "(cyan underline for CLEAN). tab*_off: flat, borderless pill. Solid accent fill is now reserved for SAVE.",
         refs={"G": ["sT.b0", "sT.b4"], "C": ["sT.b0", "sT.b4"]}),
    dict(id="R11", sev="medium", status="fixed", screens=["05a", "05b"],
         title="Transition: the curve picker is on the HOLD tab, but it shapes the RAMP",
         problem="START/END/SLOPE are on 'RAMP', while the curve that shapes that ramp is on 'HOLD/CRV'. Rows also used "
                 "a full-width layout unlike sk and pf (your N06-15 request).",
         instruction="RAMP tab = exact pf geometry (4 rows of card_204x34 plus the curve column on the right). "
                     "HOLD tab = HOLD (s) and its limit as the same rows, plus an explanatory 'HOLD PHASE' diagram in "
                     "the right column. Add the 'TRANS' label in front of the switch, as on sk and pf. "
                     "Component order is unchanged, so the keybdB clamp ids still match.",
         refs={"G": ["tp.crvBg", "tp.tabHold"], "C": ["tp.crvBg", "tp.tabHold"]}),
    dict(id="R12", sev="low", status="fixed", screens=["07a"],
         title="Preview names phases differently from the tabs",
         problem="The tabs say PI / Soak / Trans / Main, the preview footer says '1 PI / 2 SK / 3 TR / 4 PF', "
                 "and the summary line says 'PF'.",
         instruction="Footer: PI / Soak / Trans / Main. Summary: 'MAIN 18s'.",
         refs={"G": ["graphPreview.bJPf", "graphPreview.tSum"], "C": ["graphPreview.bJPf", "graphPreview.tSum"]}),
    dict(id="R13", sev="low", status="fixed", screens=["03a"],
         title="'More' and 'SWITCH ON TRIG' are vague",
         problem="'More' opens Brew Options. 'SWITCH ON TRIG' reads like a toggle label with no toggle.",
         instruction="Footer b3 'Options' on pi/sk/tp/pf; pi.lblSw 'EXIT TRIGGERS' (matches sk's TRIGGERS tab).",
         refs={"G": ["pi.lblSw", "pi.b3"], "C": ["pi.lblSw", "pi.b3"]}),
    # ---------------------------------------------------------------- maintainability
    dict(id="R14", sev="high", status="fixed", screens=[],
         title="The bitmap generator and test suite lived outside the repo",
         problem="gen_assets.py (all 300 bitmaps), apply_redesign.py, verify_hmi.py and the overview builder were in "
                 "Antigravity's private scratch folder. Nobody else can regenerate a button or re-run the checks.",
         instruction="tools/hmi/: gen_assets.py (writes build/hmi-assets, reproduces the committed pictures bit-for-bit), "
                     "sync_assets.py (copies changed PNGs, appends new ones to app.toml after picture-0099), "
                     "capture_screens.py, verify_hmi.py (now repo-relative, +6 assertions), check_keypad_ids.py, "
                     "build_review_page.py. 9 unused bitmaps were removed.",
         refs={}),
    dict(id="R15", sev="medium", status="fixed", screens=["15"],
         title="Keypad clamps are keyed on raw component ids",
         problem="keybdB.nx clamps typed values with `loadcmpid.val == 14`. Inserting or reordering one component in a "
                 "page.toml silently re-targets the clamp to another field.",
         instruction="Run tools/hmi/check_keypad_ids.py after every page.toml edit. It resolves each (page, id) to a name "
                     "and fails on drift or on an editable field with no clamp. Longer term, compare against "
                     "`tp.tStart.id` instead of literals.",
         refs={}),
    # ---------------------------------------------------------------- next steps
    dict(id="N01", sev="high", status="next", screens=["05b"],
         title="Firmware: the flow-mode hold limit is read from the wrong field",
         problem="nextion.cpp:362 reads tfProfileHoldLimit from \"tp.tLim.val\", but upload (line 128) writes "
                 "\"tp.hLim.val\". The HOLD tab value is ignored in flow mode.",
         instruction="Change nextion.cpp:362 to myNex.readNumber(\"tp.hLim.val\") / 10.f, then run `pio test -e test`.",
         refs={"C": ["tp.hLim"]}),
    dict(id="N02", sev="medium", status="next", screens=["02"],
         title="Firmware: popups within 1.15 s are dropped",
         problem="lcdShowPopup (src/lcd/nextion.cpp:543-550) ignores any message within 1150 ms of the previous one, "
                 "so 'Profile switched!' can disappear behind a tank or tare toast (and uses rollover-unsafe `millis() > timer + 1150`).",
         instruction="Keep the last dropped message in a static buffer and show it when the cooldown expires instead of "
                     "discarding it, and use `millis() - timer > 1150` with `unsigned long timer`.",
         refs={"C": ["home.qPf1"]}),
    dict(id="N03", sev="medium", status="next", screens=["02"],
         title="Home: the tank level (j0) has no widget",
         problem="The firmware writes j0.val on the home page every 150 ms, but there is no j0 there, so each write fails silently.",
         instruction="Either add a 4x116 px vertical progress bar `j0` (bco #1F2937, pco #06B6D4) at x=162,y=80 inside "
                     "the gauge card, or, if the DeLonghi has no tank sensor, guard lcdSetTankWaterLvl() in firmware.",
         refs={"C": ["home.tGauge"]}),
    dict(id="N04", sev="medium", status="next", screens=["12", "03a"],
         title="Steppers need hold-to-repeat",
         problem="Going from 93 to 145 °C steam is 52 taps, or a trip to the keypad.",
         instruction="Per page, add a 120 ms timer `tmRep` and a variable `repBtn`. On a stepper's .down, set repBtn "
                     "and start tmRep after 400 ms; on .up, stop it. tmRep does `click <repBtn button>,1`. "
                     "Clamping and RAM stay unchanged.",
         refs={"C": ["sT.b5", "sT.bSmP"]}),
    dict(id="N05", sev="low", status="next", screens=["02"],
         title="Home: touch targets are smaller than they look",
         problem="The five profile pills are 27 px tall with 3 px gaps (~5 mm on a 2.4\" panel). Fingers often land in "
                 "the gap or on the neighbour.",
         instruction="Make each qPf hit box 30 px (y = 41 + 30*i) and bake the 3 px gap into qpf_* bitmaps "
                     "(draw the pill at y=1..28 inside a 30 px image). The visual stays the same, the touch area grows by 11%.",
         refs={"C": ["home.qPf1", "home.qPf2"]}),
    dict(id="N06", sev="low", status="next", screens=["02"],
         title="Home: the target temperature is red, like an alarm",
         problem="The set point (n5) uses #EF4444 while the live ring is green. Red reads as 'too hot or error'.",
         instruction="n5 pco #F3F4F6 (neutral) and keep the crosshair icon; reserve red for the live temperature tile on brewGraph.",
         refs={"C": ["home.n5"]}),
    dict(id="N07", sev="low", status="next", screens=["07a"],
         title="Preview: tapping a phase band should open its editor",
         problem="The plot already shows PI/SK/TR/MAIN bands, but only the small footer buttons navigate.",
         instruction="Store each band's right edge in d1..d6 while drawing. In plotBox.up, compare tch0 against the edges "
                     "and `page pi|sk|tp|pf`.",
         refs={"C": ["graphPreview.plotBox"]}),
    dict(id="N08", sev="high", status="next", screens=[],
         title="Validate on the real NX3224F024",
         problem="Everything here is verified in nxwright's headless simulator only.",
         instruction="Flash build output nextion-lcd-delongui.tft (SD, FAT32), then check: touch on tp RAMP/HOLD tabs, "
                     "brew graph scroll at 250 ms, graphPreview draw time < 1 s, steam on/off on sP, and a popup mid manual shot.",
         refs={}),
    dict(id="N09", sev="high", status="next", screens=["09", "14"],
         title="Firmware: lcdSetWeight() overflows its stack buffer at >= 100.0 g",
         problem="src/lcd/nextion.cpp:525-532 formats into `char tmp[6]` with `snprintf(tmp, sizeof(tmp), \"%.1f\", ...)` "
                 "and checks `check <= sizeof(tmp)` before `strcat(tmp, \"g\")`. For >= 100.0 g (or <= -10.0 g), "
                 "`check == 5 <= 6`, so `strcat` writes 7 bytes (\"100.0g\\0\") into `tmp[6]` — a 1-byte stack buffer overflow.",
         instruction="Replace with `char tmp[10]; int check = snprintf(tmp, sizeof(tmp), \"%.1fg\", static_cast<double>(val)); "
                     "if (check > 0 && static_cast<unsigned int>(check) < sizeof(tmp)) { myNex.writeStr(\"weight.txt\", tmp); }`.",
         refs={"C": ["bM.weight", "brewGraph.weight"]}),
]
