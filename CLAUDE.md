# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Status

This repo is pre-firmware: structure and docs only, no source code, no build
system. The nRF52 toolchain (nRF5 SDK vs. nRF Connect SDK/Zephyr vs. upstream
Zephyr) has not been chosen yet — do not assume one and do not scaffold a
build system without confirming the choice first. There are currently no
build, lint, or test commands because there is nothing to build.

## Context

This is one repo in the larger Heimdall Suite (personal RC electronics
project, org `github.com/heimdall-suite`). Full suite-level context —
including `heimdall-module` and `heimdall-nexus`, which this node talks to —
lives in `../heimdall-kickoff.md` (one level up, outside this repo). Read
that before assuming intent that isn't captured here.

## What this node does

`heimdall-switch` is an nRF52-based boat-side wireless power switch, replacing
a Jeti SPS-20 magnetic switch. It is controlled by `heimdall-module` (an
ESP32-C3 on the transmitter side) over BLE, deliberately independent of the
boat's normal RadioLink CRSF control link so switching keeps working
regardless of that link's state.

Key architectural properties to preserve in any implementation:

- **Radio roles are asymmetric and fixed**: `heimdall-module` is always the
  BLE advertiser/sender; this node is a passive scanner except for a brief
  reactive ack-advertising burst after accepting a command. Don't invert this
  — it's the main lever for this node's power budget.
- **Commands are absolute state, never toggle**: every command frame carries
  an explicit ON/OFF state, replay-protected by a rolling counter plus a
  paired address + key check. The relay is driven to SET or RESET accordingly.
- **State survives power loss by hardware design, not firmware**: the pilot
  relay is a *latching* relay (mechanical/magnetic latch), driving a power
  MOSFET for the actual load. Firmware must not assume it needs to
  re-assert relay state on boot — the relay already holds it.
- **Feedback is closed-loop**: the ack frame's valid bit must reflect both
  "command checked out" and "load-side ADC confirms the commanded power
  state" — not just that a drive pulse was sent.
- **Multi-boat isolation is per-node, not link-level**: a node only reacts to
  its own paired address + boat ID, so overlapping BLE range between
  boats/units is a non-issue by design — don't add extra multi-boat
  arbitration logic.

Full command/ack frame bit layouts, the pairing flow, and hardware component
choices (MCU, regulator, relay/MOSFET switching stage, feedback divider,
button/LED) are in [README.md](README.md) and the suite-level kickoff doc.
Several hardware parameters (wake interval, scan window, advertising
interval, exact relay/MOSFET part numbers) are unvalidated first estimates —
check README's Open Items before treating any of them as fixed.

## Before scaffolding

Confirm the nRF52 toolchain choice with the user before generating any build
files, SDK vendoring, or firmware source layout — this hasn't been decided
and the three candidate SDKs imply materially different project structures.
