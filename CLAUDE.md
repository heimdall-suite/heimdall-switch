# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Cross-tool agent instructions (also valid for Claude Code) live in
[.agents/AGENTS.md](.agents/AGENTS.md) — read that first. This file only
adds Claude-Code-specific notes on top.

## Status

This repo is pre-firmware: structure and docs only, no source code, no build
system. The nRF52 toolchain (nRF5 SDK vs. nRF Connect SDK/Zephyr vs. upstream
Zephyr) has not been chosen yet — do not assume one and do not scaffold a
build system without confirming the choice first. There are currently no
build, lint, or test commands because there is nothing to build.

## Layout

- `README.md` — short overview + status, points into the docs below
- `.docs/hardware.md`, `.docs/protocol.md`, `.docs/persistence.md` —
  detailed hardware, BLE protocol and flash persistence specs
- `hardware/kicad/` — KiCad 10 schematic (the `.kicad_sch` is the source
  of truth, edited in the KiCad GUI; `build_sch.sh`/`gen_body.sh` are the
  retired generator for the first draft — don't run them). `kicad-cli`
  lives in `AppData/Local/Programs/KiCad/10.0/bin/` (not on PATH); run
  `sch erc` after any schematic change. The PCB (`heimdall-switch.kicad_pcb`)
  came from `place_pcb.py` + `route_pcb.py` + Freerouting; once edited in
  the GUI it is the source of truth too. Run `pcb drc --schematic-parity`
  after PCB changes.
- `hardware/kicad-ui/` — separate KiCad project for the optional UI
  daughter board (LED + button, JST-XH to the main board's J4), with a
  routed PCB. Same rules: the KiCad files are the source of truth
  (`gen_ui.sh` made the first version); run `sch erc` and
  `pcb drc --schematic-parity` after changes.
- `.agents/AGENTS.md` — full cross-tool architecture/context notes (the
  primary reference — this file doesn't repeat it)
- `src/` — firmware source, currently just a placeholder pending the
  toolchain decision

## Suite context

This is one repo in the larger Heimdall Suite (personal RC electronics
project, org `github.com/heimdall-suite`). Full suite-level context —
including `heimdall-module` and `heimdall-helm`, which this node talks to
— lives in `../heimdall-kickoff.md` (one level up, outside this repo).
