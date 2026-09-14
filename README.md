# heimdall-switch

Boat-side wireless power switch node, part of the [Heimdall Suite](../heimdall-kickoff.md).

Replaces a boat's Jeti SPS-20 magnetic switch with a custom wireless switch,
controlled from `heimdall-module` over BLE. Deliberately out-of-band from
the boat's normal RadioLink CRSF control link — this switch has its own
independent radio path so it keeps working regardless of the state of the
main control link.

Built as a generic building block (not a single-purpose commercial part
like Jeti's RCPS10) so the same design can serve other "generic function"
switching needs in the suite later.

## Docs

- [.docs/hardware.md](.docs/hardware.md) — MCU, power, switching stage,
  feedback, button/LED, open hardware items
- [.docs/protocol.md](.docs/protocol.md) — BLE roles, pairing, runtime
  cycle, command/ack frame layouts, the transmitter-side Lua widget
- [.agents/AGENTS.md](.agents/AGENTS.md) / [CLAUDE.md](CLAUDE.md) —
  instructions for AI coding agents working in this repo

## Status

No firmware yet. nRF52 toolchain (nRF5 SDK vs. nRF Connect SDK/Zephyr vs.
upstream Zephyr) is not yet decided. `src/` is a placeholder until that's
settled.
