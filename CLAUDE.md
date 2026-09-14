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
- `.docs/hardware.md`, `.docs/protocol.md` — detailed hardware and BLE
  protocol specs
- `.agents/AGENTS.md` — full cross-tool architecture/context notes (the
  primary reference — this file doesn't repeat it)
- `src/` — firmware source, currently just a placeholder pending the
  toolchain decision

## Suite context

This is one repo in the larger Heimdall Suite (personal RC electronics
project, org `github.com/heimdall-suite`). Full suite-level context —
including `heimdall-module` and `heimdall-nexus`, which this node talks to
— lives in `../heimdall-kickoff.md` (one level up, outside this repo).
