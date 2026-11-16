# Repository Guide for AI Agents

## Branch Context (`mac_delongui`)
- This branch targets a **DeLonghi 51mm retrofit** (`delongui-51mm-*` environments in `platformio.ini`).
- The active Nextion display project is **`lcd-hmi/delongui/`** (plain-text `nxwright` source), which builds **`lcd-hmi/nextion-lcd-delongui.HMI`** and compiles **`nextion-lcd-delongui.tft`** (`NX3224F024` Discovery 2.4", `320x240`, rotation `90`).

## Editing & Verifying HMI Screens (No Windows Editor Needed)
Read `docs/hmi-workflow.md` before modifying any screen.

- **Edit plain text in `lcd-hmi/delongui/`** (`app.toml`, `program.nx`, `pages/*.page.toml`, `pages/*.nx`, `pictures/`, `fonts/`) — never hand-edit `.HMI` or `.tft` binaries.
- **Validate, build `.HMI`, and compile `.tft`:**
  ```bash
  ./scripts/hmi.sh all
  ```
- **Visually verify screens before finishing:**
  - Use the `nxwright` MCP server configured in `.mcp.json` (`start_simulation`, `screen`, `tap`, `wait`, `send`), **or**
  - Render screenshots from CLI with `./scripts/hmi.sh render <page>` (writes `.hmi-renders/<page>.png`).
- **Preserve the STM32 UART contract** in `src/lcd/lcd.h` and `src/lcd/nextion.cpp`:
  - Keep `printh 00 00 00 ff ff ff 88 ff ff ff` in `program.nx`.
  - Keep `printh 23 02 50 <id>` (page IDs) and `printh 23 02 54 <trigger>` (trigger IDs) in `pages/*.nx`.
  - Keep global/component names read or written by `src/lcd/nextion.cpp` unless updating the C++ firmware in lockstep.
- **Watch page RAM limits (`3584` bytes max):** `./scripts/hmi.sh build` prints per-page RAM; `brewGraph` (`3520/3584`) and `graphPreview` (`3400/3584`) have very little headroom.
