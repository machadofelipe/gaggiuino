# Nextion HMI Screen Workflow (No Windows Editor Required)

This repository uses **[`nxwright`](https://github.com/nixiewright/nxwright)** to edit, simulate, check, and compile Nextion screens from plain-text files on Linux/macOS/Windows without the Windows-only Nextion Editor GUI.

## Active Target (`mac_delongui` Branch)

- **Plain-text source of truth:** `lcd-hmi/delongui/`
- **Rebuilt Nextion Editor project:** `lcd-hmi/nextion-lcd-delongui.HMI`
- **Compiled display firmware:** `nextion-lcd-delongui.tft`
- **Display hardware:** `NX3224F024` (Nextion Discovery 2.4", Series F, `320x240`, `rotation = 90`, `encoding = "iso-8859-1"`)
- **Wrapper script:** `scripts/hmi.sh`

> Other `.HMI` files in `lcd-hmi/` (`nextion-lcd.HMI`, `scales-calibrate.HMI`) can also be extracted/built with `nxwright` or by overriding `HMI_SRC_DIR`, `HMI_FILE`, and `TFT_FILE` when invoking `scripts/hmi.sh`.

---

## Directory Layout (`lcd-hmi/delongui/`)

```text
lcd-hmi/delongui/
├── app.toml          # Screen model, rotation, encoding, page order, picture/font tables
├── defaults.toml     # Component default attributes
├── program.nx        # Global integer declarations, UART baud (115200), startup handshake
├── pages/
│   ├── <page>.page.toml   # Component layout (type, x, y, w, h, colors, fonts, pictures, etc.)
│   └── <page>.nx          # Event handlers (load, loadend, down, up, slide, timer, ...)
├── pictures/         # PNG assets (new SVG or PNG assets can be added via `nxwright picture`)
└── fonts/            # Nextion .zi font files (add via `nxwright font`)
```

---

## Daily Commands

All standard tasks go through `scripts/hmi.sh`:

```bash
# 1. Validate syntax, references, assets, and page RAM limits
./scripts/hmi.sh check

# 2. Format .nx files consistently
./scripts/hmi.sh format

# 3. Rebuild .HMI and compile .tft (first run caches Nextion v1.68.2 firmware)
./scripts/hmi.sh all

# Or run separately:
./scripts/hmi.sh build     # -> lcd-hmi/nextion-lcd-delongui.HMI
./scripts/hmi.sh compile   # -> nextion-lcd-delongui.tft

# 4. Render any page headlessly to inspect layout + PNG screenshot
./scripts/hmi.sh render home
./scripts/hmi.sh render brewGraph /tmp/brewGraph.png
```

If `nxwright` is missing on a fresh machine, run `./scripts/hmi.sh setup` (requires Python ≥ 3.11 via `uv`, which `setup` installs automatically into `~/.local/bin`).

---

## Editing Screens Safely (Rules for AI Agents & Humans)

### 1. Edit plain text, then rebuild `.HMI` and `.tft`
- Always edit files inside `lcd-hmi/delongui/` (`.page.toml`, `.nx`, `app.toml`, `program.nx`, `pictures/`, `fonts/`).
- Never hand-edit binary `.HMI` or `.tft` files.
- Always run `./scripts/hmi.sh all` after screen changes so `lcd-hmi/nextion-lcd-delongui.HMI` and `nextion-lcd-delongui.tft` stay in sync.

### 2. Preserve the STM32 ↔ Nextion UART Contract
The STM32 firmware in `src/lcd/lcd.h`, `src/lcd/nextion.cpp`, and `src/gaggiuino.ino` communicates with the display at `115200` baud using `EasyNextionLibrary`. Unless you intentionally update the C++ firmware in lockstep, **do not break**:

- **Boot handshake** (`lcd-hmi/delongui/program.nx`):
  - `baud=115200` and `printh 00 00 00 ff ff ff 88 ff ff ff` (matched by `lcdCheckSerialInit("\x88\xFF\xFF\xFF", 4)` in `src/lcd/nextion.cpp`).
- **Page ID notifications** (`printh 23 02 50 <hex_id>` in each page's `on <page>.load:` event):
  - `EasyNextionLibrary` sets `myNex.currentPageId` from these bytes — **not** from the page's index in `app.toml`.
  - Mapping in `src/lcd/lcd.h` (`enum class NextionPage`) vs `lcd-hmi/delongui/pages/`:
    - `0x00` `Home` → `home`
    - `0x01` `BrewPreinfusion` → `pi`
    - `0x02` `BrewSoak` → `sk`
    - `0x03` `BrewProfiling` → `pf`
    - `0x04` `BrewManual` → `bM`
    - `0x05` `Flush` → `cleanFlush`
    - `0x07` `SettingsBoiler` → `sT`
    - `0x08` `SettingsSystem` → `sP`
    - `0x09` `BrewGraph` → `brewGraph`
    - `0x0A` `BrewMore` → `bS`
    - `0x0B` `ShotSettings` → `dS`
    - `0x0C` `BrewTransitionProfile` → `tp`
    - `0x0D` `GraphPreview` → `graphPreview`
    - `0x0E` `KeyboardNumeric` → `keybdB`
- **Trigger codes** (`printh 23 02 54 <hex_trigger>` → `trigger1`..`trigger10` in `src/lcd/nextion.cpp`):
  - `01` → `lcdSaveSettingsTrigger()`
  - `02` → `lcdScalesTareTrigger()`
  - `03` → `lcdHomeScreenScalesTrigger()`
  - `04` → `lcdBrewGraphScalesTareTrigger()`
  - `06` → `lcdRefreshElementsTrigger()`
  - `07` → `lcdQuickProfileSwitch()`
  - `08` → `lcdSaveProfileTrigger()`
  - `09` → `lcdResetSettingsTrigger()`
  - `0A` → `lcdLoadDefaultProfileTrigger()`
- **Named globals, page names, and components accessed by `src/lcd/nextion.cpp`**:
  - Globals in `program.nx`: `currentTemp`, `modeSelect`, `targetState`, `timerState`, `warmupState`, `activeBrewTime`, `shotState`, `shotPreset`, `piState`, `piFlowState`, `piRPressure`, `basketPrefill`, `bckHome`, `deltaState`, `skState`, `skCrv`, `ppState`, `ppType`, `paType`, `paState`, `pfCrv`, `paCrv`, `pId`, `ledNum`, `systemUpTime`, `debug1`, `debug2` (if used).
  - Page + component names: `splash.build_version.txt`, `home.qPf1`..`qPf5`, `popupMSG.t0.txt` (plus `page popupMSG`), `pi.*` (`piTime`, `piFlow`, `piBar`, `piPumped`, `piAbove`), `sk.*` (`skTime`, `skBar`, `skFlow`, `skBelow`, `skAbv`, `skWAbv`, `skRamp`), `pf.*` (`pStart`, `pEnd`, `pSlope`, `pLim`), `tp.*` (`tStart`, `tEnd`, `tHold`, `hLim`, `tSlope`, `tLim`), `dS.*` (`numDose`, `numDoseForced`), `sT.*` (`setPoint`, `steamSetPoint`, `offSet`, `hpwr`, `mDiv`, `bDiv`), `sP.*` (`n1`, `lc1`, `lc2`, `pump_zero`), and active-page elements (`pressure.val`, `flow.val`, `weight.txt`, `dE.val`, `j0.val`, `h0.val`, `scEn.val`).

### 3. Watch Per-Page Memory Limits (`3584` bytes max)
`./scripts/hmi.sh build` prints each page's RAM usage. On `delongui`, some pages are already close to the `3584`-byte Nextion page limit:
- `brewGraph`: `3520 / 3584` bytes (**only 64 bytes free**)
- `graphPreview`: `3400 / 3584` bytes (184 bytes free)
- `dS`: `2700 / 3584` bytes

Keep component names/attributes lean on `brewGraph` and `graphPreview` and verify `./scripts/hmi.sh check` / `build` after every edit.

### 4. Nextion Language Syntax
`lcd-hmi/delongui/` currently uses Nextion syntax (`language = "nextion_do_not_change_manually"` in `app.toml`):
- Expressions evaluate strictly **left-to-right** (`a + b * 2` means `(a + b) * 2`), without arbitrary parentheses in arithmetic.
- `nxwright` accepts comfortable spacing around `=`, `+`, `if (...) { ... }`, and compiles it to strict Nextion syntax automatically.
- `nxwright check` warns on `left-to-right` surprises and syntax/type errors before build.

### 5. Adding or Replacing Pictures & Fonts
Use `nxwright` resource commands directly on `lcd-hmi/delongui` so `app.toml` indices stay consistent (note: code referencing `@pic(name)` or numeric IDs must stay valid):
- Add picture (PNG or SVG): `nxwright picture lcd-hmi/delongui path/to/icon.svg`
- Replace picture in-place (keeps existing ID & references): `nxwright replace lcd-hmi/delongui picture picture-0042 new-icon.png`
- Generate font from `.ttf`/`.otf`: `nxwright font lcd-hmi/delongui path/to/font.ttf 24`

---

## Visual Verification & Simulation

### Option A: Quick CLI Render
```bash
./scripts/hmi.sh render home
./scripts/hmi.sh render brewGraph
```
This prints every visible component's bounding box/text and writes `.hmi-renders/<page>.png` (`320x240`), which you can open or inspect directly.

### Option B: Interactive AI Simulation via MCP (`nxwright mcp`)
`.mcp.json` at the repo root registers the `nxwright` MCP server. In any MCP-capable client, an AI agent can:
1. `start_simulation` on `lcd-hmi/delongui`
2. `screen` to inspect the rendered PNG and component layout
3. `tap` buttons/hotspots, `wait` for timers (e.g., splash → `home`), and `send` serial commands (e.g., `pressure.val=90`, `weight.txt="18.5g"`, `page brewGraph`) to test interactions end-to-end.

---

## Flashing to the Display

- **Firmware version note:** `nxwright compile` uses Nextion Editor `1.68.2` display firmware (cached automatically in `~/.cache/nxwright/firmware/1.68.2` on first `--download`). Test a compiled `.tft` on your physical display after major changes.
- **Via microSD card (recommended):** Copy `nextion-lcd-delongui.tft` onto an empty FAT32 microSD card (< 32 GB, single `.tft` file on the card), insert into the powered-off display, power on until flashing completes, power off, and remove the card.
- **Via USB-UART adapter:**
  ```bash
  ./scripts/hmi.sh ports
  ./scripts/hmi.sh upload /dev/ttyUSB0 --upload-baud 921600
  ```
