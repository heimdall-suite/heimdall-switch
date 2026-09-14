# heimdall-switch

Boat-side wireless power switch node, part of the [Heimdall Suite](../heimdall-kickoff.md).

Replaces a boat's Jeti SPS-20 magnetic switch with a custom wireless switch,
controlled from `heimdall-module` over BLE. Deliberately out-of-band from the
boat's normal RadioLink CRSF control link — this switch has its own independent
radio path so it keeps working regardless of the state of the main control link.

Built as a generic building block (not a single-purpose commercial part like
Jeti's RCPS10) so the same design can serve other "generic function" switching
needs in the suite later.

## Hardware

- **MCU**: nRF52 — nRF52-DK or Adafruit Feather nRF52 Bluefruit for dev;
  production target is the ISP1507 module (8×8×1mm, integrated antenna).
- **Radio**: BLE, chosen over ESP-NOW/WiFi (too power-hungry to listen
  continuously) and sub-GHz CC1101 (needs its own antenna design + a second
  radio chip). Duty-cycle math showed BLE is more than adequate.
- **Power**: 2S-3S LiPo boat battery (~6-12.6V) through a TI TPS6290x
  regulator (3-17V in, ~4µA IQ), single stage.
- **Switching**: small (1-2A) dual-coil latching relay as a pilot element,
  driving a power MOSFET (>10A, matched to bus voltage) for the load. The
  relay's mechanical latch holds state with zero power and survives a full
  power loss + vibration — a bare relay was too bulky, a solid-state CMOS
  latch is volatile, so this hybrid approach covers both requirements.
- **Feedback**: resistor divider on the switched output into an ADC pin, to
  confirm actual delivered power downstream, not just that a pulse was sent.
- **Local button**: debounced, GPIOTE interrupt-wake. Held 5-15s toggles power
  state locally; held ≥15s enters pairing mode.
- **Status LED**: single GPIO.

## BLE protocol

`heimdall-module` (ESP32-C3) is the advertiser/sender. This node is a
**passive scanner** most of the time, advertising only in a brief reactive ack
burst — minimizing nRF52 radio-on time is the main lever for power budget.

Runtime cycle per wake (~2-3s interval, not yet validated on hardware):
wake → short RX scan window → if a valid command is heard (paired address +
key + boat ID + counter > last accepted) drive the relay to the *absolute*
commanded state (never a toggle) → advertise a short ack burst → sleep.

See [heimdall-kickoff.md](../heimdall-kickoff.md#heimdall-switch-boat-side-wireless-power-switch)
for the full command/ack frame bit layouts, pairing flow, and the
transmitter-side EdgeTX Lua widget this pairs with.

## Status

No firmware yet. nRF52 toolchain (nRF5 SDK vs. nRF Connect SDK/Zephyr vs.
upstream Zephyr) is not yet decided — see Open Items below. This repo
currently holds structure/docs only.

## Open items

- nRF52 firmware toolchain not chosen
- Wake interval, scan window length, and BLE advertising interval are first
  estimates, unvalidated against real hardware
- Latching relay and MOSFET part numbers not yet chosen
- No hardware built yet
