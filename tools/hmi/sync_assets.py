#!/usr/bin/env python3
"""Copy generated bitmaps from build/hmi-assets/ into lcd-hmi/delongui/pictures/.

Only PNGs whose pixels differ are rewritten. New assets are appended to the
`pictures` list in app.toml (after picture-0099, so numeric ring indices stay
stable). Use --check to report differences without writing.
"""
import argparse
import re
import sys
from pathlib import Path

from PIL import Image, ImageChops

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "build" / "hmi-assets"
PROJECT = REPO / "lcd-hmi" / "delongui"
PICS = PROJECT / "pictures"
APP_TOML = PROJECT / "app.toml"


def same_pixels(a: Path, b: Path) -> bool:
    if not b.exists():
        return False
    ia, ib = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    return ia.size == ib.size and ImageChops.difference(ia, ib).getbbox() is None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="report only")
    args = ap.parse_args()

    generated = sorted(SRC.glob("*.png")) + sorted((SRC / "rings").glob("*.png"))
    if not generated:
        print(f"no assets in {SRC}; run tools/hmi/gen_assets.py first", file=sys.stderr)
        return 1

    app = APP_TOML.read_text(encoding="utf-8")
    pic_block = re.search(r"pictures = \[\n(.*?)\n\]", app, flags=re.S).group(1)
    listed = set(re.findall(r'"([^"]+)"', pic_block))
    changed, added = [], []
    for png in generated:
        dst = PICS / png.name
        if same_pixels(png, dst):
            continue
        (added if png.stem not in listed else changed).append(png.stem)
        if not args.check:
            dst.write_bytes(png.read_bytes())

    if added and not args.check:
        block = "".join(f'    "{n}",\n' for n in added)
        app = re.sub(r"(pictures = \[\n(?:    \"[^\"]+\",\n)+)", lambda m: m.group(1) + block, app, count=1)
        APP_TOML.write_text(app, encoding="utf-8")

    unused = sorted(listed - {p.stem for p in generated})
    print(f"changed: {len(changed)} {changed}")
    print(f"added:   {len(added)} {added}")
    if unused:
        print(f"listed in app.toml but not generated: {unused}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
