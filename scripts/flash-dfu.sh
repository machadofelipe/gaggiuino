#!/usr/bin/env bash
# flash-dfu.sh — Build, backup, and flash via USB DFU (Blackpill F411CE)
# Usage: ./scripts/flash-dfu.sh [--skip-build]
#
# Requirements:
#   dfu-util >= 0.9    (sudo apt install dfu-util)
#   pio                (PlatformIO CLI)

set -euo pipefail

ENV="delongui-51mm-forced-predictive-dfu"
FIRMWARE=".pio/build/${ENV}/firmware.bin"
BACKUP_DIR="firmware-backups"
DFU_VID_PID="0483:df11"          # STM32 ROM DFU VID:PID
FLASH_ADDR="0x08000000"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }
die()   { error "$*"; exit 1; }

# ── 1. Pre-flight checks ────────────────────────────────────────────────────
preflight() {
    info "=== Pre-flight checks ==="

    command -v dfu-util >/dev/null 2>&1 \
        || die "dfu-util not found. Install with: sudo apt install dfu-util"
    info "dfu-util: $(dfu-util --version 2>&1 | head -1)"

    # Prefer system pio, fall back to the default PlatformIO home location
    if ! command -v pio >/dev/null 2>&1; then
        if [[ -x "${HOME}/.platformio/penv/bin/pio" ]]; then
            export PATH="${HOME}/.platformio/penv/bin:${PATH}"
        else
            die "pio (PlatformIO CLI) not found. See https://docs.platformio.org/en/latest/core/installation/index.html"
        fi
    fi
    info "pio:      $(pio --version)"

    # Script must run from project root
    [[ -f "platformio.ini" ]] \
        || die "Run this script from the project root (where platformio.ini lives)"
}

# ── 2. Build ────────────────────────────────────────────────────────────────
build() {
    if [[ "${1:-}" == "--skip-build" ]]; then
        warn "Skipping build (--skip-build passed)"
        [[ -f "${FIRMWARE}" ]] || die "Firmware not found at ${FIRMWARE}. Run without --skip-build first."
        return
    fi

    info "=== Building ${ENV} ==="
    pio run -e "${ENV}"
    [[ -f "${FIRMWARE}" ]] || die "Build succeeded but firmware not found at ${FIRMWARE}"
    info "Firmware: $(du -sh "${FIRMWARE}" | cut -f1)  →  ${FIRMWARE}"
}

# ── 3. Connection test ───────────────────────────────────────────────────────
check_dfu_device() {
    info "=== Checking DFU device ==="

    # lsusb check first (fast)
    if ! lsusb -d "${DFU_VID_PID}" >/dev/null 2>&1; then
        echo
        warn "STM32 DFU device (${DFU_VID_PID}) not found."
        echo "  ► Hold BOOT0 button, then press/release RESET, then release BOOT0."
        echo "  ► Alternatively: hold BOOT0, disconnect then reconnect USB."
        echo
        read -rp "Press ENTER when the board is in DFU mode (or Ctrl+C to abort)..."
        lsusb -d "${DFU_VID_PID}" >/dev/null 2>&1 \
            || die "Still no DFU device. Check USB cable and BOOT0 pin."
    fi

    info "DFU device found: $(lsusb -d "${DFU_VID_PID}")"

    # Detailed dfu-util probe
    DFU_LIST=$(dfu-util -l 2>&1)
    echo "${DFU_LIST}" | grep -q "Found DFU" \
        || die "dfu-util cannot enumerate the device. Try: sudo dfu-util -l  (udev rule may be missing)"
    info "dfu-util enumeration OK"
}

# ── 4. Backup current firmware ───────────────────────────────────────────────
backup_firmware() {
    info "=== Backing up current firmware ==="

    mkdir -p "${BACKUP_DIR}"
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="${BACKUP_DIR}/firmware_backup_${TIMESTAMP}.bin"

    # F411CE flash: 512 KB = 0x80000 bytes
    if dfu-util -a 0 -s "${FLASH_ADDR}:0x80000" -U "${BACKUP_FILE}" 2>&1; then
        info "Backup saved: ${BACKUP_FILE}  ($(du -sh "${BACKUP_FILE}" | cut -f1))"
    else
        warn "Backup failed (this is non-fatal — some DFU implementations block reads)."
        warn "Proceeding without backup."
    fi
}

# ── 5. Flash ─────────────────────────────────────────────────────────────────
flash_firmware() {
    info "=== Flashing ${FIRMWARE} ==="
    dfu-util -a 0 -s "${FLASH_ADDR}:leave" -D "${FIRMWARE}"
    info "Flash command completed."
}

# ── 6. Confirm ───────────────────────────────────────────────────────────────
confirm_flash() {
    info "=== Confirming flash ==="

    # 'leave' in the flash command triggers a reset; give the MCU a moment to boot
    sleep 2

    # If the board re-enumerates as a CDC device the firmware is running
    if lsusb | grep -iq "stm32"; then
        info "Board re-enumerated as STM32 device — firmware running OK."
    else
        warn "Board did not re-enumerate as STM32. It may still be running correctly"
        warn "if the USB serial port appears under /dev/ttyACM* or /dev/ttyUSB*."
        ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null && info "Serial ports found: $(ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null)" || true
    fi

    # Verify by reading back first 4 bytes (the stack pointer in the vector table)
    # Only attempt if device is still in DFU mode (the :leave flag should have exited DFU)
    if lsusb -d "${DFU_VID_PID}" >/dev/null 2>&1; then
        warn "Device still in DFU mode after :leave — performing readback verification."
        VERIFY_FILE=$(mktemp /tmp/fw_verify_XXXXXX.bin)
        if dfu-util -a 0 -s "${FLASH_ADDR}:4" -U "${VERIFY_FILE}" 2>&1; then
            WRITTEN=$(xxd -l 4 "${FIRMWARE}")
            READBACK=$(xxd -l 4 "${VERIFY_FILE}")
            if [[ "${WRITTEN}" == "${READBACK}" ]]; then
                info "Readback verification PASSED (first 4 bytes match)."
            else
                warn "Readback mismatch — reflash may be needed."
                warn "Expected: ${WRITTEN}"
                warn "Got:      ${READBACK}"
            fi
        fi
        rm -f "${VERIFY_FILE}"
        warn "Manually set BOOT0=0 and press RESET to boot into your new firmware."
    else
        info "Board has left DFU mode and booted — flash confirmed."
    fi
}

# ── Main ─────────────────────────────────────────────────────────────────────
main() {
    echo
    info "╔══════════════════════════════════════════════╗"
    info "║  Gaggiuino DFU Flash  —  ${ENV}  ║"
    info "╚══════════════════════════════════════════════╝"
    echo

    preflight
    build "${1:-}"
    check_dfu_device
    backup_firmware
    flash_firmware
    confirm_flash

    echo
    info "Done. Enjoy your espresso ☕"
}

main "$@"
