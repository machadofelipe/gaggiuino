#!/usr/bin/env bash
# Rebuild docs/delongui-hmi-review.html: original (81827ca) vs Gemini (75b78f4) vs working tree.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
NX="$(command -v nxwright || echo "$HOME/.local/bin/nxwright")"
PY="$(head -n1 "$NX" | sed 's/^#!//')"
ORIG_REV="${ORIG_REV:-81827ca}"
GEMINI_REV="${GEMINI_REV:-75b78f4}"
C="$ROOT/build/compare"
rm -rf "$C" && mkdir -p "$C/src/gemini"
cd "$ROOT"
git show "$ORIG_REV:lcd-hmi/nextion-lcd-delongui.HMI" > "$C/src/orig.HMI"
"$NX" extract "$C/src/orig.HMI" "$C/src/orig" > /dev/null
git archive "$GEMINI_REV" lcd-hmi/delongui | tar xf - -C "$C/src/gemini"
G="$C/src/gemini/lcd-hmi/delongui"
cd "$ROOT/tools/hmi"
"$PY" capture_screens.py --variant orig --src "$C/src/orig" --tag O --out "$C/orig.json" --png-dir "$C/png/orig" &
"$PY" capture_screens.py --variant redesign --src "$G" --tag G --out "$C/gemini.json" --png-dir "$C/png/gemini" &
"$PY" capture_screens.py --variant redesign --src "$ROOT/lcd-hmi/delongui" --tag C --out "$C/opus.json" --png-dir "$C/png/opus" &
wait
"$PY" probe_bugs.py --gemini "$G" --opus "$ROOT/lcd-hmi/delongui" --out "$C/probe.json"
"$PY" build_review_page.py --orig "$C/orig.json" --gemini "$C/gemini.json" --opus "$C/opus.json" \
  --probe "$C/probe.json" --out "$ROOT/docs/delongui-hmi-review.html" --md "$ROOT/docs/hmi-review.md"
