"""Generate every bitmap used by lcd-hmi/delongui.

Writes into build/hmi-assets/ (git-ignored). Run tools/hmi/sync_assets.py afterwards
to copy changed PNGs into lcd-hmi/delongui/pictures/ (rings/picture-NNNN.png keep
their fixed indices 0..99, which home.nx/bM.nx address numerically).
"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import math
import os

REPO = Path(__file__).resolve().parents[2]
OUT = Path(os.environ.get("HMI_ASSET_OUT", REPO / "build" / "hmi-assets"))
OUT.mkdir(parents=True, exist_ok=True)
RINGS = OUT / "rings"
RINGS.mkdir(exist_ok=True)

# Clean old stale PNGs first so app.toml never carries unused assets
for p in list(OUT.glob("*.png")) + list(RINGS.glob("*.png")):
    p.unlink()

# Design Tokens
BG = "#0D1117"
WELL_BG = "#090D12"
CARD = "#141B24"
CARD_TOP = "#1C2532"
CARD_PILL = "#1A222E"
ELEV = "#1F2937"
ELEV_TOP = "#2A3647"
ELEV2 = "#263244"
BDR = "#2A3441"
BDR_SOFT = "#212B38"
BDR_SUBTLE = "#1E2733"
SHADOW = "#070A0E"
ACC = "#38BDF8"
ACC_TOP = "#67D0FA"
ACC_BOT = "#0284C7"
ACC_MUTED = "#285770"
PRESS = "#F59E0B"
FLOW = "#06B6D4"
WEIGHT = "#10B981"
WEIGHT_TOP = "#34D399"
TEMP = "#EF4444"
TXT = "#F3F4F6"
DIM = "#9CA3AF"
MUTED = "#475569"
DIM_BG = "#10161F"
DIM_BDR = "#19212C"
DIM_SW_BG = "#19212B"
DIM_SW_KNOB = "#526073"

def fnt(sz, bold=True):
    p = "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf" if bold else "/usr/share/fonts/truetype/ubuntu/Ubuntu-M.ttf"
    return ImageFont.truetype(p, sz)

def rr(d, box, rad, fill=None, outline=None, width=1):
    d.rounded_rectangle(box, radius=rad, fill=fill, outline=outline, width=width)

def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

# Reusable modern tactile pill/button/card renderers (2x supersampled)
def make_btn(name, w, h, rad, outer_bg, fill, border=None, state="up", top_sheen=None, shadow_col=SHADOW, left_bar=None, border_w=1):
    S = 2
    im = Image.new("RGB", (w * S, h * S), outer_bg)
    d = ImageDraw.Draw(im)
    kw = {"outline": border, "width": border_w * S} if border else {}
    if state == "up":
        rr(d, [0, 2 * S, w * S - 1, h * S - 1], rad * S, fill=shadow_col)
        rr(d, [0, 0, w * S - 1, (h - 2) * S], rad * S, fill=fill, **kw)
        if top_sheen:
            d.line([(rad + 1) * S, 1 * S, (w - rad - 1) * S, 1 * S], fill=top_sheen, width=S)
    elif state == "flat":
        rr(d, [0, 0, w * S - 1, h * S - 1], rad * S, fill=fill, **kw)
        if top_sheen:
            d.line([(rad + 1) * S, 1 * S, (w - rad - 1) * S, 1 * S], fill=top_sheen, width=S)
    else:  # "dn" pressed travel (shifts down 2px)
        rr(d, [0, 2 * S, w * S - 1, h * S - 1], rad * S, fill=fill, **kw)
    if left_bar:
        y_off = 2 * S if state == "dn" else 0
        y_end = (h - 4) * S
        rr(d, [4 * S, y_off + 5 * S, 7 * S, y_off + y_end - 1 * S], 2 * S, fill=left_bar)
    im.resize((w, h), Image.Resampling.LANCZOS).save(OUT / f"{name}.png")

def make_card(name, w, h, rad=8, outer_bg=BG, fill=CARD, border=None, top_accent=None, sheen=True):
    S = 2
    im = Image.new("RGB", (w * S, h * S), outer_bg)
    d = ImageDraw.Draw(im)
    # Soft 1px drop depth for quiet elevation
    rr(d, [0, 1 * S, w * S - 1, h * S - 1], rad * S, fill=SHADOW)
    kw = {"outline": border, "width": S} if border else {}
    rr(d, [0, 0, w * S - 1, (h - 1) * S], rad * S, fill=fill, **kw)
    if top_accent:
        rr(d, [10 * S, 2 * S, (w - 10) * S, 4 * S], 1 * S, fill=top_accent)
    elif sheen:
        d.line([(rad + 1) * S, 1 * S, (w - rad - 1) * S, 1 * S], fill=CARD_TOP, width=S)
    im.resize((w, h), Image.Resampling.LANCZOS).save(OUT / f"{name}.png")

def make_well(name, w, h, rad=6, outer_bg=CARD, fill=WELL_BG, border=None, border_w=1):
    S = 2
    im = Image.new("RGB", (w * S, h * S), outer_bg)
    d = ImageDraw.Draw(im)
    kw = {"outline": border, "width": border_w * S} if border else {}
    rr(d, [0, 0, w * S - 1, h * S - 1], rad * S, fill=fill, **kw)
    im.resize((w, h), Image.Resampling.LANCZOS).save(OUT / f"{name}.png")

# 1. 100-frame 116x116 270-deg Dynamic Ring Gauge (spike-free, larger radius, 90% target notch)
def gen_rings():
    S = 4
    W = 116 * S
    cx = cy = W // 2
    rad = 50 * S
    th = 10 * S
    for val in range(100):
        im = Image.new("RGB", (W, W), CARD)
        d = ImageDraw.Draw(im)
        box = [cx - rad, cy - rad, cx + rad, cy + rad]
        d.arc(box, start=135, end=405, fill=ELEV, width=th)
        # Subtle inner 90% "AT TARGET" marker notch inside track (no outer spikes)
        targ_ang = math.radians(135 + 270 * (90 / 99.0))
        r_in = rad - (th // 2) + 1 * S
        r_out = rad + (th // 2) - 1 * S
        d.line(
            [cx + r_in * math.cos(targ_ang), cy + r_in * math.sin(targ_ang),
             cx + r_out * math.cos(targ_ang), cy + r_out * math.sin(targ_ang)],
            fill=WEIGHT, width=2 * S,
        )
        if val < 50:
            col = hex_rgb(FLOW)
        elif val < 75:
            col = hex_rgb(ACC)
        elif val < 87:
            col = hex_rgb(PRESS)
        elif val <= 94:
            col = hex_rgb(WEIGHT)
        else:
            col = hex_rgb(TEMP)
        if val > 0:
            end_deg = 135 + int(270 * (val / 99.0))
            d.arc(box, start=135, end=end_deg, fill=col, width=th)
            ang = math.radians(end_deg)
            tx = cx + rad * math.cos(ang)
            ty = cy + rad * math.sin(ang)
            r_cap = th // 2
            d.ellipse([tx - r_cap, ty - r_cap, tx + r_cap, ty + r_cap], fill=col)
            r_dot = 2 * S
            d.ellipse([tx - r_dot, ty - r_dot, tx + r_dot, ty + r_dot], fill=TXT)
        else:
            ang = math.radians(135)
            tx = cx + rad * math.cos(ang)
            ty = cy + rad * math.sin(ang)
            r_cap = th // 2
            d.ellipse([tx - r_cap, ty - r_cap, tx + r_cap, ty + r_cap], fill=MUTED)
        out = im.resize((116, 116), Image.Resampling.LANCZOS)
        out.save(RINGS / f"picture-{val:04d}.png")

# 2. Splash Screen (320x240)
def gen_splash():
    S = 2
    W, H = 320 * S, 240 * S
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    rr(d, [16*S, 16*S, 304*S, 224*S], 14*S, fill=CARD, outline=BDR_SOFT, width=S)
    cx, cy = 160 * S, 78 * S
    d.arc([cx-30*S, cy-30*S, cx+30*S, cy+30*S], start=135, end=405, fill=BDR, width=5*S)
    d.arc([cx-30*S, cy-30*S, cx+30*S, cy+30*S], start=135, end=330, fill=ACC, width=5*S)
    pts = []
    for i in range(25):
        u = i / 24.0
        px = cx - 18*S + u * 36*S
        py = cy + 4*S - math.sin(u * math.pi) * 12*S
        pts.append((px, py))
    d.line(pts, fill=PRESS, width=3*S)
    d.ellipse([cx+12*S, cy-16*S, cx+18*S, cy-10*S], fill=WEIGHT)
    d.text((160*S, 132*S), "GAGGIUINO", font=fnt(24*S, True), fill=TXT, anchor="mm")
    rr(d, [96*S, 150*S, 224*S, 168*S], 9*S, fill=ELEV, outline=ACC, width=S)
    d.text((160*S, 159*S), "DELONGHI 51MM", font=fnt(10*S, True), fill=ACC, anchor="mm")
    # Snug rounded capsule around 6px loadBar (x=58..262, y=182..188)
    rr(d, [55*S, 180*S, 265*S, 190*S], 5*S, fill=WELL_BG, outline=BDR_SOFT, width=S)
    im.resize((320, 240), Image.Resampling.LANCZOS).save(OUT / "bg_splash.png")

# 3. Home Background (idle + pressed for top nav picc/picc2)
def draw_nav_icon(d, kind, cx, cy, col, S):
    w = 2 * S
    if kind == "home":
        d.polygon([(cx, cy-6*S), (cx-7*S, cy), (cx-5*S, cy), (cx-5*S, cy+6*S), (cx+5*S, cy+6*S), (cx+5*S, cy), (cx+7*S, cy)], outline=col, width=w)
    elif kind == "brew":
        for dy, dx in [(-4*S, -2*S), (0, 3*S), (4*S, -1*S)]:
            d.line([cx-7*S, cy+dy, cx+7*S, cy+dy], fill=col, width=w)
            d.ellipse([cx+dx-2*S, cy+dy-2*S, cx+dx+2*S, cy+dy+2*S], fill=col)
    elif kind == "manual":
        # Stylized control dial + droplet arc for Manual / Clean submenu
        d.arc([cx-6*S, cy-6*S, cx+6*S, cy+6*S], start=135, end=405, fill=col, width=w)
        d.line([cx, cy, cx+4*S, cy-4*S], fill=col, width=w)
        d.ellipse([cx-2*S, cy-2*S, cx+2*S, cy+2*S], fill=col)
    elif kind == "setup":
        for dy in (-4*S, 0, 4*S):
            d.line([cx-6*S, cy+dy, cx+6*S, cy+dy], fill=col, width=w)

def gen_home():
    S = 2
    for state in ("up", "dn"):
        W, H = 320 * S, 240 * S
        im = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, W, 35*S], fill=CARD)
        d.line([0, 35*S, W, 35*S], fill=BDR_SOFT, width=S)
        navs = [("HOME", "home", True), ("BREW", "brew", False), ("MANUAL", "manual", False), ("SETUP", "setup", False)]
        for i, (lbl, kind, act) in enumerate(navs):
            x0 = (4 + i * 79) * S
            x1 = x0 + 75 * S
            y0, y1 = 4 * S, 31 * S
            if state == "dn":
                y0 += 2 * S
            if act:
                if state == "up":
                    rr(d, [x0, y0+2*S, x1, y1+2*S], 6*S, fill=SHADOW)
                rr(d, [x0, y0, x1, y1], 6*S, fill=ACC)
                draw_nav_icon(d, kind, x0+15*S, (y0+y1)//2, BG, S)
                d.text((x0+47*S, (y0+y1)//2), lbl, font=fnt(10*S, True), fill=BG, anchor="mm")
            else:
                if state == "up":
                    rr(d, [x0, y0+2*S, x1, y1+2*S], 6*S, fill=SHADOW)
                rr(d, [x0, y0, x1, y1], 6*S, fill=ELEV if state == "up" else ELEV2, outline=BDR, width=S)
                draw_nav_icon(d, kind, x0+13*S, (y0+y1)//2, ACC if state == "dn" else DIM, S)
                d.text((x0+47*S, (y0+y1)//2), lbl, font=fnt(10*S, True), fill=TXT if state == "dn" else DIM, anchor="mm")
        # Left Profile Panel frame (x=4..150, y=40..194)
        rr(d, [4*S, 41*S, 150*S, 195*S], 10*S, fill=SHADOW)
        rr(d, [4*S, 40*S, 150*S, 194*S], 10*S, fill=CARD, outline=BDR_SOFT, width=S)
        # Right Hero Card (x=154..316, y=40..234)
        rr(d, [154*S, 41*S, 316*S, 235*S], 10*S, fill=SHADOW)
        rr(d, [154*S, 40*S, 316*S, 234*S], 10*S, fill=CARD, outline=BDR_SOFT, width=S)
        d.line([160*S, 77*S, 310*S, 77*S], fill=BDR_SOFT, width=S)
        d.line([235*S, 46*S, 235*S, 71*S], fill=BDR_SOFT, width=S)
        d.line([160*S, 198*S, 310*S, 198*S], fill=BDR_SOFT, width=S)
        # Target crosshair icon (left of n5 at x=167, y=58) + "°C" unit (right of n5 at x=219, y=59)
        tx, ty = 167 * S, 58 * S
        d.ellipse([tx-6*S, ty-6*S, tx+6*S, ty+6*S], outline=TEMP, width=2*S)
        d.ellipse([tx-2*S, ty-2*S, tx+2*S, ty+2*S], fill=TEMP)
        d.line([tx-8*S, ty, tx-5*S, ty], fill=TEMP, width=2*S)
        d.line([tx+5*S, ty, tx+8*S, ty], fill=TEMP, width=2*S)
        d.line([tx, ty-8*S, tx, ty-5*S], fill=TEMP, width=2*S)
        d.line([tx, ty+5*S, tx, ty+8*S], fill=TEMP, width=2*S)
        d.text((220*S, 59*S), "°C", font=fnt(10*S, True), fill=DIM, anchor="lm")
        # Pressure gauge icon (left of pressure at x=245, y=58) + "bar" unit (right of pressure at x=298, y=60)
        px, py = 245 * S, 59 * S
        d.arc([px-6*S, py-6*S, px+6*S, py+6*S], start=150, end=390, fill=PRESS, width=2*S)
        d.line([px, py, px+4*S, py-4*S], fill=TXT, width=2*S)
        d.ellipse([px-2*S, py-2*S, px+2*S, py+2*S], fill=PRESS)
        d.text((297*S, 60*S), "bar", font=fnt(9*S, True), fill=DIM, anchor="lm")
        im.resize((320, 240), Image.Resampling.LANCZOS).save(OUT / f"bg_home_{state}.png")

# 4. brewGraph Background (extra breathing room above bottom cards)
def gen_brewgraph():
    S = 2
    for state in ("up", "dn"):
        W, H = 320 * S, 240 * S
        im = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, W, 35*S], fill=CARD)
        d.line([0, 35*S, W, 35*S], fill=BDR_SOFT, width=S)
        by = (4 if state == "dn" else 2) * S
        if state == "up":
            rr(d, [4*S, by+2*S, 44*S, by+30*S], 6*S, fill=SHADOW)
        rr(d, [4*S, by, 44*S, by+28*S], 6*S, fill=ELEV if state == "up" else ELEV2, outline=BDR, width=S)
        cx, cy = 24*S, by+14*S
        d.line([cx+6*S, cy, cx-6*S, cy], fill=TXT, width=2*S)
        d.line([cx-6*S, cy, cx-1*S, cy-5*S], fill=TXT, width=2*S)
        d.line([cx-6*S, cy, cx-1*S, cy+5*S], fill=TXT, width=2*S)
        if state == "up":
            rr(d, [276*S, by+2*S, 316*S, by+30*S], 6*S, fill=SHADOW)
        rr(d, [276*S, by, 316*S, by+28*S], 6*S, fill=ELEV if state == "up" else ELEV2, outline=WEIGHT, width=S)
        # Circular refresh/tare arrow icon (matches original b2 refresh glyph)
        rcx, rcy = 296 * S, by + 14 * S
        rcol = WEIGHT if state == "dn" else TXT
        d.arc([rcx-7*S, rcy-7*S, rcx+7*S, rcy+7*S], start=35, end=315, fill=rcol, width=2*S)
        ax, ay = rcx + 5 * S, rcy - 5 * S
        d.polygon([(ax+2*S, ay+2*S), (ax+2*S, ay-4*S), (ax-4*S, ay+1*S)], fill=rcol)
        # Waveform frame (y=38..178). s0 is y=40..176 with dis=125 and gdh=25, so each
        # 25px gridline is exactly 2 bar / 2 ml/s (left axis) or 20 g (right axis).
        rr(d, [17*S, 38*S, 303*S, 178*S], 4*S, fill=BG, outline=BDR_SOFT, width=S)
        for k in range(1, 6):
            yy = (176 - 25 * k) * S
            d.text((14*S, yy), str(2 * k), font=fnt(9*S, True), fill=DIM, anchor="rm")
            d.text((305*S, yy), str(20 * k), font=fnt(8*S, True), fill=WEIGHT, anchor="lm")
        d.text((14*S, 172*S), "0", font=fnt(9*S, True), fill=MUTED, anchor="rm")
        cards = [
            (4, "PRESS bar", PRESS),
            (83, "FLOW ml/s", FLOW),
            (162, "WEIGHT g", WEIGHT),
            (241, "TEMP °C", TEMP),
        ]
        for x, lbl, col in cards:
            rr(d, [x*S, 187*S, (x+75)*S, 238*S], 8*S, fill=SHADOW)
            rr(d, [x*S, 186*S, (x+75)*S, 237*S], 8*S, fill=CARD, outline=BDR_SOFT, width=S)
            rr(d, [(x+10)*S, 188*S, (x+65)*S, 190*S], 1*S, fill=col)
            d.text(((x+37)*S, 197*S), lbl, font=fnt(9*S, True), fill=col, anchor="mm")
        im.resize((320, 240), Image.Resampling.LANCZOS).save(OUT / f"bg_brewgraph_{state}.png")

# 5. Badges, Toggles, Steppers, Curves, Sliders
def gen_widgets():
    S = 2
    for name, txt_s, col in [("badge_brewing", "BREWING", PRESS), ("badge_done", "READY", WEIGHT)]:
        im = Image.new("RGB", (74*S, 24*S), CARD)
        d = ImageDraw.Draw(im)
        rr(d, [1*S, 1*S, 73*S, 23*S], 11*S, fill=ELEV, outline=col, width=S)
        d.ellipse([7*S, 8*S, 15*S, 16*S], fill=col)
        d.text((44*S, 12*S), txt_s, font=fnt(10*S, True), fill=col, anchor="mm")
        im.resize((74, 24), Image.Resampling.LANCZOS).save(OUT / f"{name}.png")

    # Toggle switches (CARD & BG outer corners + dimmed disabled variants)
    for prefix, outer in [("sw", CARD), ("sw_bg", BG)]:
        for suffix, on in [("off", False), ("on", True)]:
            im = Image.new("RGB", (52*S, 24*S), outer)
            d = ImageDraw.Draw(im)
            rr(d, [1*S, 1*S, 51*S, 23*S], 11*S, fill=WEIGHT if on else ELEV, outline=WEIGHT if on else BDR, width=S)
            if on:
                d.ellipse([30*S, 4*S, 48*S, 20*S], fill=TXT)
                d.text((16*S, 12*S), "ON", font=fnt(9*S, True), fill=BG, anchor="mm")
            else:
                d.ellipse([4*S, 4*S, 22*S, 20*S], fill=DIM)
                d.text((36*S, 12*S), "OFF", font=fnt(9*S, True), fill=DIM, anchor="mm")
            im.resize((52, 24), Image.Resampling.LANCZOS).save(OUT / f"{prefix}_{suffix}.png")

    # Dimmed switches on CARD (for disabled form states preserving ON/OFF visual position)
    for suffix, on in [("off_dim", False), ("on_dim", True)]:
        im = Image.new("RGB", (52*S, 24*S), CARD)
        d = ImageDraw.Draw(im)
        rr(d, [1*S, 1*S, 51*S, 23*S], 11*S, fill=DIM_SW_BG, outline=DIM_BDR, width=S)
        if on:
            d.ellipse([30*S, 4*S, 48*S, 20*S], fill=DIM_SW_KNOB)
            d.text((16*S, 12*S), "ON", font=fnt(9*S, True), fill=MUTED, anchor="mm")
        else:
            d.ellipse([4*S, 4*S, 22*S, 20*S], fill=MUTED)
            d.text((36*S, 12*S), "OFF", font=fnt(9*S, True), fill=MUTED, anchor="mm")
        im.resize((52, 24), Image.Resampling.LANCZOS).save(OUT / f"sw_{suffix}.png")

    # BAR | FLOW segmented toggle (96x24, on BG)
    for name, flow_on in [("mode_bar", False), ("mode_flow", True)]:
        im = Image.new("RGB", (96*S, 24*S), BG)
        d = ImageDraw.Draw(im)
        rr(d, [0, 0, 96*S-1, 24*S-1], 7*S, fill=CARD, outline=BDR_SOFT, width=S)
        if not flow_on:
            rr(d, [2*S, 2*S, 48*S, 21*S], 5*S, fill=PRESS)
            d.text((25*S, 12*S), "BAR", font=fnt(10*S, True), fill=BG, anchor="mm")
            d.text((71*S, 12*S), "FLOW", font=fnt(10*S, True), fill=DIM, anchor="mm")
        else:
            rr(d, [48*S, 2*S, 93*S, 21*S], 5*S, fill=FLOW)
            d.text((25*S, 12*S), "BAR", font=fnt(10*S, True), fill=DIM, anchor="mm")
            d.text((71*S, 12*S), "FLOW", font=fnt(10*S, True), fill=BG, anchor="mm")
        im.resize((96, 24), Image.Resampling.LANCZOS).save(OUT / f"{name}.png")

    # Back button (36x26) on CARD header
    for st in ("up", "dn"):
        im = Image.new("RGB", (36*S, 26*S), CARD)
        d = ImageDraw.Draw(im)
        y0 = (2 if st == "dn" else 0) * S
        if st == "up":
            rr(d, [0, 2*S, 36*S-1, 26*S-1], 6*S, fill=SHADOW)
        rr(d, [0, y0, 36*S-1, y0+24*S], 6*S, fill=ELEV if st == "up" else ELEV2, outline=ACC if st == "dn" else BDR, width=S)
        if st == "up":
            d.line([7*S, 1*S, 29*S, 1*S], fill=ELEV_TOP, width=S)
        cx, cy = 18*S, y0 + 12*S
        d.line([cx+6*S, cy, cx-6*S, cy], fill=TXT, width=2*S)
        d.line([cx-6*S, cy, cx-1*S, cy-5*S], fill=TXT, width=2*S)
        d.line([cx-6*S, cy, cx-1*S, cy+5*S], fill=TXT, width=2*S)
        im.resize((36, 26), Image.Resampling.LANCZOS).save(OUT / f"btn_back_{st}.png")

    # Larger tactile Stepper +/- key-caps (exact-matched sizes!)
    stepper_sizes = [
        ("step", 36, 28, ("up", "dn", "dim")),
        ("step27", 36, 27, ("up", "dn", "dim")),
        ("step34", 34, 27, ("up", "dn", "dim")),
        ("step36", 36, 30, ("up", "dn")),
    ]
    for prefix, sw, sh, states in stepper_sizes:
        for sym, tag in [("-", "m"), ("+", "p")]:
            for st in states:
                im = Image.new("RGB", (sw*S, sh*S), CARD)
                d = ImageDraw.Draw(im)
                if st == "dim":
                    rr(d, [0, 0, sw*S-1, (sh-2)*S], 6*S, fill=DIM_BG, outline=DIM_BDR, width=S)
                    tc = MUTED
                    cy = ((sh - 2) * S) // 2
                elif st == "up":
                    rr(d, [0, 2*S, sw*S-1, sh*S-1], 6*S, fill=SHADOW)
                    rr(d, [0, 0, sw*S-1, (sh-2)*S], 6*S, fill=ELEV, outline=BDR, width=S)
                    d.line([7*S, 1*S, (sw-7)*S, 1*S], fill=ELEV_TOP, width=S)
                    tc = TXT
                    cy = ((sh - 3) * S) // 2
                else:
                    rr(d, [0, 2*S, sw*S-1, sh*S-1], 6*S, fill=ACC, outline=ACC, width=S)
                    tc = BG
                    cy = ((sh + 1) * S) // 2
                cx = (sw * S) // 2
                d.line([cx-5*S, cy, cx+5*S, cy], fill=tc, width=2*S)
                if sym == "+":
                    d.line([cx, cy-5*S, cx, cy+5*S], fill=tc, width=2*S)
                im.resize((sw, sh), Image.Resampling.LANCZOS).save(OUT / f"{prefix}_{tag}_{st}.png")

    # Unified Vertical Curve Icon Pills (96x25 for pf, 96x22 for sk & tp) + dim / dim_on states!
    curves = [
        (0, "In-Out"),
        (1, "Ease-In"),
        (2, "Ease-Out"),
        (3, "Linear"),
        (4, "Instant"),
    ]
    specs = [
        (96, 25, "crv", 7, 25, 61, 10),
        (96, 22, "crv22", 7, 25, 61, 10),
    ]
    for cid, lbl in curves:
        for state_tag in ("off", "on", "dim", "dim_on"):
            for w_px, h_px, prefix, gx0, gx1, tx, fsz in specs:
                im = Image.new("RGB", (w_px*S, h_px*S), CARD)
                d = ImageDraw.Draw(im)
                if state_tag == "on":
                    bgc, bdc, tc, lc, bw = ELEV2, ACC, ACC, ACC, 2
                elif state_tag == "off":
                    bgc, bdc, tc, lc, bw = ELEV, BDR, DIM, TXT, 1
                    rr(d, [0, 2*S, w_px*S-1, h_px*S-1], 6*S, fill=SHADOW)
                elif state_tag == "dim_on":
                    bgc, bdc, tc, lc, bw = DIM_BG, ACC_MUTED, MUTED, MUTED, 1
                else:  # "dim"
                    bgc, bdc, tc, lc, bw = DIM_BG, DIM_BDR, MUTED, MUTED, 1
                bot_y = (h_px - 2) * S if state_tag == "off" else h_px * S - 1
                rr(d, [0, 0, w_px*S-1, bot_y], 6*S, fill=bgc, outline=bdc, width=bw*S)
                pts = []
                gy0, gy1 = (bot_y // S - 4)*S, 4*S
                for i in range(17):
                    u = i / 16.0
                    if cid == 0:
                        f = 0.5 - 0.5 * math.cos(math.pi * u)
                    elif cid == 1:
                        f = pow(u, 1.675)
                    elif cid == 2:
                        f = 1 - pow(1 - u, 1.675)
                    elif cid == 3:
                        f = u
                    else:
                        f = 0.0 if u < 0.25 else 1.0
                    px = gx0*S + u * (gx1 - gx0)*S
                    py = gy0 + f * (gy1 - gy0)
                    pts.append((px, py))
                d.line(pts, fill=lc, width=2*S)
                d.text((tx*S, (bot_y // 2)), lbl, font=fnt(fsz*S, True), fill=tc, anchor="mm")
                im.resize((w_px, h_px), Image.Resampling.LANCZOS).save(OUT / f"{prefix}_{cid}_{state_tag}.png")

    # Sliders: Flow (208x32) & Dim (196x28)
    for tag, W, H, tw, col in [("flow", 208, 32, 26, FLOW), ("dim", 196, 28, 22, ACC)]:
        im = Image.new("RGB", (W*S, H*S), CARD)
        d = ImageDraw.Draw(im)
        cy = (H * S) // 2
        rr(d, [2*S, cy-5*S, (W-2)*S, cy+5*S], 5*S, fill=WELL_BG, outline=BDR_SOFT, width=S)
        im.resize((W, H), Image.Resampling.LANCZOS).save(OUT / f"sld_trk_{tag}.png")

        im = Image.new("RGB", (W*S, H*S), CARD)
        d = ImageDraw.Draw(im)
        rr(d, [2*S, cy-5*S, (W-2)*S, cy+5*S], 5*S, fill=col)
        im.resize((W, H), Image.Resampling.LANCZOS).save(OUT / f"sld_fil_{tag}.png")

        im = Image.new("RGB", (tw*S, H*S), CARD)
        d = ImageDraw.Draw(im)
        rr(d, [0, 3*S, tw*S - 1, (H-1)*S], 6*S, fill=SHADOW)
        rr(d, [0, 1*S, tw*S - 1, (H-3)*S], 6*S, fill=TXT, outline=col, width=2*S)
        d.line([(tw//2)*S, 7*S, (tw//2)*S, (H-9)*S], fill=col, width=2*S)
        im.resize((tw, H), Image.Resampling.LANCZOS).save(OUT / f"sld_thb_{tag}.png")

    # Clean/Flush icon (64x64)
    im = Image.new("RGB", (64*S, 64*S), CARD)
    d = ImageDraw.Draw(im)
    d.arc([8*S, 8*S, 56*S, 56*S], start=0, end=360, fill=ELEV, width=4*S)
    d.polygon([(32*S, 14*S), (20*S, 36*S), (44*S, 36*S)], fill=FLOW)
    d.ellipse([20*S, 26*S, 44*S, 48*S], fill=FLOW)
    d.arc([25*S, 31*S, 39*S, 43*S], start=20, end=120, fill=TXT, width=2*S)
    im.resize((64, 64), Image.Resampling.LANCZOS).save(OUT / "ico_flush.png")

    # Warmup status badge (26x26 for home)
    sz = 26
    im = Image.new("RGB", (sz*S, sz*S), CARD)
    d = ImageDraw.Draw(im)
    rr(d, [1*S, 1*S, (sz-1)*S, (sz-1)*S], 6*S, fill=ELEV, outline=PRESS, width=S)
    c = sz // 2
    d.polygon([(c*S, 6*S), ((c-6)*S, (sz-10)*S), ((c+6)*S, (sz-10)*S)], fill=PRESS)
    d.ellipse([(c-5)*S, (c-1)*S, (c+5)*S, (sz-6)*S], fill=PRESS)
    im.resize((sz, sz), Image.Resampling.LANCZOS).save(OUT / "ico_warmup_26.png")

    # popupMSG clean notice icon (36x36 on CARD)
    im = Image.new("RGB", (36*S, 36*S), CARD)
    d = ImageDraw.Draw(im)
    rr(d, [2*S, 2*S, 34*S, 34*S], 17*S, fill=ELEV, outline=ACC, width=2*S)
    # Crisp "i" badge glyph
    d.ellipse([16*S, 9*S, 20*S, 13*S], fill=ACC)
    rr(d, [16*S, 16*S, 20*S, 27*S], 2*S, fill=TXT)
    im.resize((36, 36), Image.Resampling.LANCZOS).save(OUT / "ico_notice_36.png")

# 6. Modern Rounded Chrome, Borderless Surface Cards, Wells, Pills & Tactile Keyboards
def gen_modern_chrome():
    S = 2
    # Home quick-profile pills (136x27, CARD outer corners; borderless when inactive!)
    make_btn("qpf_off", 136, 27, 6, CARD, CARD_PILL, border=None, state="flat")
    make_btn("qpf_on", 136, 27, 6, CARD, ELEV, border=ACC, state="flat", top_sheen=ELEV_TOP, left_bar=ACC)
    make_btn("qpf_dn", 136, 27, 6, CARD, ELEV2, border=ACC, state="dn")

    # Home Steam Mode Left Panel card (136x145, CARD outer corners) + 146x35 bottom Steam Temp pill (BG outer corners)
    im = Image.new("RGB", (136*S, 145*S), CARD)
    d = ImageDraw.Draw(im)
    rr(d, [0, 0, 136*S-1, 145*S-1], 8*S, fill=CARD_PILL, outline=PRESS, width=S)
    rr(d, [10*S, 2*S, 126*S, 4*S], 1*S, fill=TEMP)
    # Steam waves emblem at top-left (x=28, y=28) + "STEAM MODE" title
    cx_s, cy_s = 28 * S, 28 * S
    rr(d, [14*S, 14*S, 42*S, 42*S], 7*S, fill=ELEV, outline=TEMP, width=S)
    for dx in (-5, 0, 5):
        d.line([(cx_s+dx*S), cy_s+8*S, (cx_s+(dx+2)*S), cy_s, (cx_s+dx*S), cy_s-8*S], fill=TEMP, width=2*S)
    d.text((84*S, 23*S), "STEAM", font=fnt(12*S, True), fill=TXT, anchor="mm")
    d.text((84*S, 36*S), "MODE", font=fnt(9*S, True), fill=PRESS, anchor="mm")
    d.line([16*S, 54*S, 120*S, 54*S], fill=BDR_SOFT, width=S)
    im.resize((136, 145), Image.Resampling.LANCZOS).save(OUT / "steam_panel_bg.png")
    make_btn("btn146_steam_up", 146, 35, 8, BG, CARD, border=PRESS, state="up", top_sheen="#3A2A10", left_bar=PRESS)
    make_btn("btn146_steam_dn", 146, 35, 8, BG, PRESS, border=PRESS, state="dn")

    # Home DOSE / STOP pill (146x35, BG outer corners)
    make_btn("dose_up", 146, 35, 8, BG, CARD, border=WEIGHT, state="up", top_sheen="#19382E")
    make_btn("dose_dn", 146, 35, 8, BG, WEIGHT, border=WEIGHT, state="dn")
    make_btn("dose_act_up", 146, 35, 8, BG, "#102820", border=WEIGHT, state="up", top_sheen="#234D3E", left_bar=WEIGHT)
    make_btn("dose_act_dn", 146, 35, 8, BG, WEIGHT, border=WEIGHT, state="dn")

    # Header Tabs on CARD header (h=26 for comfy 30px-bar touch targets).
    # Selected tab = raised neutral surface + accent underline (never a solid accent
    # fill), so it can't be confused with the solid-accent SAVE action beside it.
    def make_tab_on(name, w, h, accent):
        im = Image.new("RGB", (w * S, h * S), CARD)
        d = ImageDraw.Draw(im)
        rr(d, [0, 0, w * S - 1, h * S - 1], 6 * S, fill=ELEV2, outline=BDR, width=S)
        d.line([7 * S, 1 * S, (w - 7) * S, 1 * S], fill=ELEV_TOP, width=S)
        rr(d, [8 * S, (h - 4) * S, (w - 8) * S, (h - 2) * S], 1 * S, fill=accent)
        im.resize((w, h), Image.Resampling.LANCZOS).save(OUT / f"{name}.png")

    for w in (66, 68, 76, 88):
        make_btn(f"tab{w}_off", w, 26, 6, CARD, CARD_PILL, border=None, state="flat")
        make_tab_on(f"tab{w}_on", w, 26, ACC)
        make_btn(f"tab{w}_dn", w, 26, 6, CARD, ELEV2, border=ACC, state="dn")
    make_tab_on("tab76_flow_on", 76, 26, FLOW)

    # Header SAVE (72x26 on CARD) & Reset Defaults (128x30 on CARD)
    make_btn("btn72_pri_up", 72, 26, 6, CARD, ACC, border=ACC, state="up", top_sheen=ACC_TOP, shadow_col=ACC_BOT)
    make_btn("btn72_pri_dn", 72, 26, 6, CARD, WEIGHT, border=WEIGHT, state="dn")
    make_btn("btn128_danger_up", 128, 30, 7, CARD, ELEV, border=TEMP, state="up", top_sheen="#3A252B")
    make_btn("btn128_danger_dn", 128, 30, 7, CARD, TEMP, border=TEMP, state="dn")

    # 3-button Footer on CARD footer (98x27 across 320px: More | Preview | SAVE) & graphPreview (58x27, 62x27)
    make_btn("btn98_sec_up", 98, 27, 6, CARD, ELEV, border=BDR, state="up", top_sheen=ELEV_TOP)
    make_btn("btn98_sec_dn", 98, 27, 6, CARD, ELEV2, border=ACC, state="dn")
    make_btn("btn98_out_up", 98, 27, 6, CARD, ELEV, border=ACC, state="up", top_sheen=ELEV_TOP)
    make_btn("btn98_out_dn", 98, 27, 6, CARD, ACC, border=ACC, state="dn")
    make_btn("btn98_pri_up", 98, 27, 6, CARD, ACC, border=ACC, state="up", top_sheen=ACC_TOP, shadow_col=ACC_BOT)
    make_btn("btn98_pri_dn", 98, 27, 6, CARD, WEIGHT, border=WEIGHT, state="dn")

    make_btn("btn58_sec_up", 58, 27, 6, CARD, ELEV, border=BDR, state="up", top_sheen=ELEV_TOP)
    make_btn("btn58_sec_dn", 58, 27, 6, CARD, ACC, border=ACC, state="dn")
    make_btn("btn62_pri_up", 62, 27, 6, CARD, ACC, border=ACC, state="up", top_sheen=ACC_TOP, shadow_col=ACC_BOT)
    make_btn("btn62_pri_dn", 62, 27, 6, CARD, WEIGHT, border=WEIGHT, state="dn")

    # Header & Footer chrome bars (320x30 & 320x34 with crisp 1px hairline)
    for name, w, h, line_y in [("hdr_bar", 320, 30, 29), ("ftr_bar", 320, 34, 0)]:
        im = Image.new("RGB", (w, h), CARD)
        d = ImageDraw.Draw(im)
        d.line([0, line_y, w - 1, line_y], fill=BDR_SOFT, width=1)
        im.save(OUT / f"{name}.png")

    # Sub-tabs on BG (sk: 96x24, 98x24; tp: 50x24 RAMP | HOLD)
    for w in (96, 98, 50):
        make_btn(f"sub{w}_off", w, 24, 6, BG, ELEV, border=BDR, state="up", top_sheen=ELEV_TOP)
        make_btn(f"sub{w}_on", w, 24, 6, BG, ACC, border=ACC, state="flat", top_sheen=ACC_TOP)
        make_btn(f"sub{w}_dn", w, 24, 6, BG, ELEV2, border=ACC, state="dn")

    # Borderless Soft-Elevated Surface Cards
    for cname, cw, ch, r in [
        ("card_152x44", 152, 44, 8),
        ("card_152x62", 152, 62, 8),
        ("card_204x34", 204, 34, 7),
        ("card_102x142", 102, 142, 8),
        ("card_308x44", 308, 44, 8),
        ("card_308x34", 308, 34, 7),
        ("card_304x52", 304, 52, 8),
        ("card_308x62", 308, 62, 8),
        ("card_300x188", 300, 188, 10),
    ]:
        make_card(cname, cw, ch, rad=r, border=None)

    # tp HOLD tab explainer (102x142, same footprint as the curve column it replaces)
    for tag, line_col, hold_col, txt_col in (("", PRESS, ACC, DIM), ("_dim", MUTED, MUTED, MUTED)):
        name = f"tp_hold_diag{tag}"
        make_card(name, 102, 142, rad=8, border=None)
        im = Image.open(OUT / f"{name}.png").resize((102 * S, 142 * S), Image.Resampling.LANCZOS)
        d = ImageDraw.Draw(im)
        d.text((51 * S, 12 * S), "HOLD PHASE", font=fnt(9 * S, True), fill=txt_col, anchor="mm")
        x0, x1, x2, ylo, yhi = 12, 50, 90, 92, 44
        d.line([x0 * S, (ylo + 6) * S, x2 * S, (ylo + 6) * S], fill=BDR, width=S)
        pts = []
        for i in range(0, 41):
            u = i / 40
            e = u * u * (3 - 2 * u)
            pts.append(((x0 + (x1 - x0) * u) * S, (ylo - (ylo - yhi) * e) * S))
        d.line(pts, fill=line_col, width=2 * S, joint="curve")
        d.line([x1 * S, yhi * S, x2 * S, yhi * S], fill=hold_col, width=3 * S)
        d.line([x1 * S, (yhi + 4) * S, x1 * S, (ylo + 6) * S], fill=BDR, width=S)
        d.text((31 * S, 104 * S), "RAMP", font=fnt(8 * S, True), fill=txt_col, anchor="mm")
        d.text((70 * S, 104 * S), "HOLD", font=fnt(8 * S, True), fill=hold_col, anchor="mm")
        d.text((70 * S, (yhi - 8) * S), "END", font=fnt(8 * S, True), fill=hold_col, anchor="mm")
        d.text((51 * S, 122 * S), "keeps END for", font=fnt(8 * S, False), fill=txt_col, anchor="mm")
        d.text((51 * S, 132 * S), "HOLD seconds", font=fnt(8 * S, False), fill=txt_col, anchor="mm")
        im.resize((102, 142), Image.Resampling.LANCZOS).save(OUT / f"{name}.png")

    # Telemetry display cards on bM (5 sensor cards 98x64 + 1 distinct slider-linked target card)
    make_card("card_98x64_temp", 98, 64, rad=8, border=BDR_SOFT, top_accent=TEMP)
    make_card("card_98x64_flow", 98, 64, rad=8, border=BDR_SOFT, top_accent=FLOW)
    make_card("card_98x64_time", 98, 64, rad=8, border=BDR_SOFT, top_accent=ACC)
    make_card("card_98x64_press", 98, 64, rad=8, border=BDR_SOFT, top_accent=PRESS)
    make_card("card_98x64_weight", 98, 64, rad=8, border=BDR_SOFT, top_accent=WEIGHT)

    # Distinct Slider-Linked Target Tile (98x64): dark cyan-tinted card, cyan border, inner recessed well, bottom slider chevron
    im = Image.new("RGB", (98 * S, 64 * S), BG)
    d = ImageDraw.Draw(im)
    rr(d, [0, 1 * S, 98 * S - 1, 64 * S - 1], 8 * S, fill=SHADOW)
    rr(d, [0, 0, 98 * S - 1, 63 * S], 8 * S, fill="#0F1D26", outline=FLOW, width=S)
    # Recessed well inside the card for mlPerSec
    rr(d, [7 * S, 22 * S, 91 * S, 54 * S], 6 * S, fill=WELL_BG, outline="#164E63", width=S)
    # Small downward slider-link chevron pointing at the flow slider below
    d.polygon([(45 * S, 57 * S), (53 * S, 57 * S), (49 * S, 61 * S)], fill=FLOW)
    im.resize((98, 64), Image.Resampling.LANCZOS).save(OUT / "card_98x64_target.png")

    # Recessed Value Wells inside Cards
    for w, h in [(66, 27), (64, 28), (82, 28), (56, 27)]:
        make_well(f"well_{w}x{h}", w, h, rad=6, outer_bg=CARD, fill=WELL_BG, border=None)
        make_well(f"well_{w}x{h}_dim", w, h, rad=6, outer_bg=CARD, fill=DIM_BG, border=None)

    # dS Ratio Preset Tiles (74x62, BG outer corners, centered typography baked cleanly)
    ds_specs = [
        ("ds_tile1", "1:1", "Ristretto"),
        ("ds_tile2", "1:2", "Normale"),
        ("ds_tile3", "1:3", "Lungo"),
        ("ds_tile4", "1:4", "Lungo+"),
    ]
    for name, ratio, sub in ds_specs:
        for state, fill, bdr, sheen, r_col, s_col in [
            ("off", CARD, None, CARD_TOP, TXT, DIM),
            ("on", WEIGHT, WEIGHT, WEIGHT_TOP, BG, BG),
        ]:
            im = Image.new("RGB", (74 * S, 62 * S), BG)
            d = ImageDraw.Draw(im)
            if state == "off":
                rr(d, [0, 2 * S, 74 * S - 1, 62 * S - 1], 8 * S, fill=SHADOW)
            rr(d, [0, 0, 74 * S - 1, (60 if state == "off" else 62) * S - 1], 8 * S, fill=fill, outline=bdr, width=(S if bdr else 0))
            if sheen:
                d.line([8 * S, S, (74 - 8) * S, S], fill=sheen, width=S)
            d.text((37 * S, 22 * S), ratio, font=fnt(16 * S, True), fill=r_col, anchor="mm")
            d.text((37 * S, 44 * S), sub, font=fnt(11 * S, state == "on"), fill=s_col, anchor="mm")
            im.resize((74, 62), Image.Resampling.LANCZOS).save(OUT / f"{name}_{state}.png")

    # graphPreview legend pill badges (56x20 & 64x20 on CARD header)
    for name, w, col, lbl in [("leg_bar", 56, PRESS, "BAR"), ("leg_flow", 64, FLOW, "ML/S")]:
        im = Image.new("RGB", (w * S, 20 * S), CARD)
        d = ImageDraw.Draw(im)
        rr(d, [0, 0, w * S - 1, 20 * S - 1], 10 * S, fill=ELEV, outline=BDR_SOFT, width=S)
        d.ellipse([6 * S, 6 * S, 13 * S, 13 * S], fill=col)
        d.text(((w + 10) * S // 2, 10 * S), lbl, font=fnt(10 * S, True), fill=col, anchor="mm")
        im.resize((w, 20), Image.Resampling.LANCZOS).save(OUT / f"{name}.png")

    # popupMSG modal card (284x148, clean border-accented card without SYSTEM NOTICE strip)
    im = Image.new("RGB", (284 * S, 148 * S), BG)
    d = ImageDraw.Draw(im)
    rr(d, [0, 2 * S, 284 * S - 1, 148 * S - 1], 12 * S, fill=SHADOW)
    rr(d, [0, 0, 284 * S - 1, 146 * S], 12 * S, fill=CARD, outline=ACC, width=2 * S)
    rr(d, [24 * S, 2 * S, 260 * S, 4 * S], 1 * S, fill=ACC)
    im.resize((284, 148), Image.Resampling.LANCZOS).save(OUT / "modal_284x148.png")

    # keybdB (Numeric Keypad, BG outer corners)
    make_well("well_226x38", 226, 38, rad=8, outer_bg=BG, fill=CARD, border=ACC, border_w=2)
    make_btn("btn76x38_cancel_up", 76, 38, 8, BG, ELEV, border=BDR, state="up", top_sheen=ELEV_TOP)
    make_btn("btn76x38_cancel_dn", 76, 38, 8, BG, TEMP, border=TEMP, state="dn")
    make_btn("key73x43_up", 73, 43, 7, BG, CARD, border=BDR_SOFT, state="up", top_sheen=CARD_TOP)
    make_btn("key73x43_dn", 73, 43, 7, BG, ACC, border=ACC, state="dn")
    make_btn("key76x43_up", 76, 43, 7, BG, ELEV, border=BDR, state="up", top_sheen=ELEV_TOP)
    make_btn("key76x43_dn", 76, 43, 7, BG, ACC, border=ACC, state="dn")
    make_btn("key154x43_pri_up", 154, 43, 7, BG, ACC, border=ACC, state="up", top_sheen=ACC_TOP, shadow_col=ACC_BOT)
    make_btn("key154x43_pri_dn", 154, 43, 7, BG, WEIGHT, border=WEIGHT, state="dn")

    # keybdA (QWERTY Keyboard, wider keys for improved touch ergonomics)
    make_btn("btn96x26_up", 96, 26, 6, BG, ELEV, border=BDR, state="up", top_sheen=ELEV_TOP)
    make_btn("btn96x26_dn", 96, 26, 6, BG, PRESS, border=PRESS, state="dn")
    make_btn("btn62x26_cancel_up", 62, 26, 6, BG, ELEV, border=BDR, state="up", top_sheen=ELEV_TOP)
    make_btn("btn62x26_cancel_dn", 62, 26, 6, BG, TEMP, border=TEMP, state="dn")
    make_well("well_312x32", 312, 32, rad=8, outer_bg=BG, fill=CARD, border=ACC, border_w=2)

    for w in (29, 27):
        make_btn(f"ka{w}x38_up", w, 38, 5, BG, CARD, border=BDR_SOFT, state="up", top_sheen=CARD_TOP)
        make_btn(f"ka{w}x38_dn", w, 38, 5, BG, ACC, border=ACC, state="dn")
    make_btn("ka41x38_del_up", 41, 38, 6, BG, ELEV, border=BDR, state="up", top_sheen=ELEV_TOP)
    make_btn("ka41x38_del_dn", 41, 38, 6, BG, PRESS, border=PRESS, state="dn")
    make_btn("ka60x38_pri_up", 60, 38, 6, BG, ACC, border=ACC, state="up", top_sheen=ACC_TOP, shadow_col=ACC_BOT)
    make_btn("ka60x38_pri_dn", 60, 38, 6, BG, WEIGHT, border=WEIGHT, state="dn")
    for w in (56, 52):
        make_btn(f"ka{w}x38_off", w, 38, 6, BG, ELEV, border=BDR, state="up", top_sheen=ELEV_TOP)
        make_btn(f"ka{w}x38_on", w, 38, 6, BG, ACC, border=ACC, state="flat", top_sheen=ACC_TOP)
        make_btn(f"ka{w}x38_dn", w, 38, 6, BG, ACC, border=ACC, state="dn")
    make_btn("ka196x38_up", 196, 38, 6, BG, CARD, border=BDR_SOFT, state="up", top_sheen=CARD_TOP)
    make_btn("ka196x38_dn", 196, 38, 6, BG, ACC, border=ACC, state="dn")

gen_rings()
gen_splash()
gen_home()
gen_brewgraph()
gen_widgets()
gen_modern_chrome()

all_pngs = sorted(OUT.glob("*.png")) + sorted(RINGS.glob("*.png"))
print(f"Generated {len(all_pngs)} PNG assets in {OUT}")
