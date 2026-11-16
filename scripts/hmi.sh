#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_DIR="${HMI_SRC_DIR:-$ROOT_DIR/lcd-hmi/delongui}"
HMI_OUT="${HMI_FILE:-$ROOT_DIR/lcd-hmi/nextion-lcd-delongui.HMI}"
TFT_OUT="${TFT_FILE:-$ROOT_DIR/nextion-lcd-delongui.tft}"

find_nxwright() {
  if command -v nxwright >/dev/null 2>&1; then
    command -v nxwright
  elif [ -x "$HOME/.local/bin/nxwright" ]; then
    echo "$HOME/.local/bin/nxwright"
  else
    echo "error: nxwright not found. Install with: uv tool install --python 3.12 git+https://github.com/nixiewright/nxwright.git" >&2
    exit 1
  fi
}

find_nx_python() {
  local nx_bin="$1"
  local first_line
  first_line="$(head -n 1 "$nx_bin")"
  if [[ "$first_line" == "#!"* ]]; then
    echo "${first_line#\#!}"
  else
    echo "python3"
  fi
}

usage() {
  cat <<'EOF'
Usage: ./scripts/hmi.sh <command> [args...]

Commands for lcd-hmi/delongui (override with HMI_SRC_DIR / HMI_FILE / TFT_FILE):
  check                     Validate source folder (syntax, assets, page RAM limits)
  format [--check]          Format .nx files consistently
  build                     Rebuild lcd-hmi/nextion-lcd-delongui.HMI from source folder
  compile                   Compile nextion-lcd-delongui.tft (uses cached v1.68.2 firmware or --download)
  all                       Run check, build, and compile
  render <page> [out.png]   Render a page headlessly and print component layout + save PNG
  upload <port> [args...]   Upload nextion-lcd-delongui.tft to display over serial
  ports                     List available serial ports
  mcp                       Start nxwright MCP server for interactive AI simulation
  setup                     Install/upgrade nxwright into ~/.local/bin via uv (requires uv)
EOF
}

cmd="${1:-help}"
shift || true

case "$cmd" in
  setup)
    if ! command -v uv >/dev/null 2>&1 && [ ! -x "$HOME/.local/bin/uv" ]; then
      curl -LsSf https://astral.sh/uv/install.sh | sh
    fi
    UV_BIN="$(command -v uv 2>/dev/null || echo "$HOME/.local/bin/uv")"
    "$UV_BIN" tool install --force --python 3.12 git+https://github.com/nixiewright/nxwright.git
    ;;
  check)
    NX="$(find_nxwright)"
    "$NX" check "$SRC_DIR" "$@"
    ;;
  format)
    NX="$(find_nxwright)"
    "$NX" format "$SRC_DIR" "$@"
    ;;
  build)
    NX="$(find_nxwright)"
    "$NX" build "$SRC_DIR" "$HMI_OUT" --overwrite --no-backup "$@"
    ;;
  compile)
    NX="$(find_nxwright)"
    "$NX" compile "$SRC_DIR" "$TFT_OUT" --download --overwrite --no-backup "$@"
    ;;
  all)
    NX="$(find_nxwright)"
    "$NX" check "$SRC_DIR"
    "$NX" build "$SRC_DIR" "$HMI_OUT" --overwrite --no-backup
    "$NX" compile "$SRC_DIR" "$TFT_OUT" --download --overwrite --no-backup
    ;;
  render)
    page="${1:-home}"
    out="${2:-$ROOT_DIR/.hmi-renders/$page.png}"
    NX="$(find_nxwright)"
    PY="$(find_nx_python "$NX")"
    mkdir -p "$(dirname "$out")"
    "$PY" - "$SRC_DIR" "$page" "$out" <<'PYEOF'
import sys
from pathlib import Path
from nxwright.mcp_server.headless import HeadlessSimulation

src_dir = Path(sys.argv[1])
page = sys.argv[2]
out_path = Path(sys.argv[3])

sim = HeadlessSimulation(src_dir, page=page)
try:
    res = sim.screen(picture=True)
    out_path.write_bytes(res["png"])
    print(res["text"])
    print(f"\nSaved screenshot: {out_path}")
finally:
    sim.stop()
PYEOF
    ;;
  upload)
    if [ "$#" -lt 1 ]; then
      echo "Usage: ./scripts/hmi.sh upload <serial-port> [extra nxwright upload args...]" >&2
      exit 1
    fi
    port="$1"
    shift
    NX="$(find_nxwright)"
    "$NX" upload "$TFT_OUT" --port "$port" "$@"
    ;;
  ports)
    NX="$(find_nxwright)"
    "$NX" ports "$@"
    ;;
  mcp)
    NX="$(find_nxwright)"
    exec "$NX" mcp "$@"
    ;;
  help|-h|--help)
    usage
    ;;
  *)
    echo "Unknown command: $cmd" >&2
    usage >&2
    exit 1
    ;;
esac
