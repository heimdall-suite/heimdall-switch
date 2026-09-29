# Agent instructions

Cross-tool instructions for any AI coding agent working in this repo (Claude
Code has its own additional notes in `/CLAUDE.md` at the repo root).

## Status

Pre-firmware: structure and docs only, no source code, no build system. The
nRF52 toolchain (nRF5 SDK vs. nRF Connect SDK/Zephyr vs. upstream Zephyr) has
not been chosen — do not assume one and do not scaffold a build system
without confirming the choice first. There are no build, lint, or test
commands yet.

## Context

Part of the Heimdall Suite (personal RC electronics project, org
`github.com/heimdall-suite`). Suite-level context — including
`heimdall-module` and `heimdall-helm`, which this node talks to — lives in
`../heimdall-kickoff.md`, one level up in the local workspace (not tracked
in this repo). Read that before assuming intent not captured here.

## What this node does

`heimdall-switch` is an nRF52-based wireless power switch node for RC
vehicles (boats, planes, cars) — it originated as a replacement for a
boat's Jeti SPS-20 magnetic switch but is not boat-specific. It is
controlled by `heimdall-module` (an ESP32-C3 external RF module on the
transmitter side) over BLE, deliberately independent of the vehicle's
normal RC control link (e.g. CRSF) so switching keeps working regardless
of that link's state.

Key architectural properties to preserve in any implementation:

- **Radio roles are asymmetric and fixed**: `heimdall-module` is always the
  BLE advertiser/sender; this node is a passive scanner except for a brief
  reactive ack-advertising burst after accepting a command. Don't invert
  this — it's the main lever for this node's power budget.
- **Commands are absolute state, never toggle**: every command frame
  carries an explicit ON/OFF state, replay-protected by a rolling counter
  plus a paired address + key check. The output is driven ON or OFF
  accordingly.
- **Fail-on: control failure must never kill the output**: the load switch
  is a P-FET whose hardware default is ON. The MCU must *actively hold* a
  GPIO to keep the output OFF; any control-side failure (MCU dead, reset,
  brownout, regulator failure, firmware hang) releases it and the output
  falls back to ON. Never invert this polarity — an unpowered or crashed
  controller killing the output means loss of the vehicle. No mechanical
  or coil relays.
- **State survives power loss via flash, and firmware must restore it**:
  the commanded state (plus replay counter) is persisted to flash on every
  state change ([persistence.md](../.docs/persistence.md)) and must be
  re-asserted early on boot — within ~20ms of power-up, before the
  hardware's slow turn-on lets the load switch start conducting, so a
  saved OFF state never blips the output.
- **Watchdog is mandatory**: firmware hung with the OFF-hold asserted is
  the one failure the hardware default can't cover; the nRF52 WDT must be
  enabled so a hang resets the MCU and releases the output.
- **Feedback is closed-loop**: the ack frame's valid bit must reflect both
  "command checked out" and "load-side ADC confirms the commanded power
  state" — not just that the GPIO was set.
- **Multi-unit isolation is per-node, not link-level**: a node only reacts
  to its own paired address + unit ID, so overlapping BLE range between
  vehicles/units is a non-issue by design — don't add extra multi-unit
  arbitration logic.

Full details: [hardware.md](../.docs/hardware.md) (MCU, power, switching,
feedback, button/LED) and [protocol.md](../.docs/protocol.md) (BLE command/
ack frames, pairing, Lua widget) and [persistence.md](../.docs/persistence.md)
(flash storage of state + replay counter). Several hardware parameters (wake
interval, scan window, advertising interval, exact MOSFET part
numbers) are unvalidated first estimates — check hardware.md's Open Items
before treating any of them as fixed.

## Before scaffolding

Confirm the nRF52 toolchain choice with the user before generating any
build files, SDK vendoring, or firmware source layout under `src/` — this
hasn't been decided and the three candidate SDKs imply materially different
project structures.
