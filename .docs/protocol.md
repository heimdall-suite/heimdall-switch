# BLE protocol

Roles: `heimdall-module`'s ESP32-C3 is the advertiser/sender. The nRF52 node
is a **passive scanner** most of the time — it does not advertise except in
the brief reactive burst described below. This is deliberate: minimizing
radio-on time on the nRF52 side is the main lever for power budget, more so
than chip-level sleep current specifics.

**Pairing** (one-time, power not a concern): standard BLE bonding, exchanges
a shared key and locks in static MAC addresses on both sides.

**Runtime cycle**, per nRF52 wake (currently assuming ~2-3s wake interval —
not yet validated on real hardware):
1. Wake → open short RX scan window (~5-10ms assumed, needs validation
   against chosen advertising interval)
2. If no valid command heard → sleep
3. If valid command (matches paired address + key + unit ID + counter >
   last accepted, for replay protection) → drive the output ON or OFF per
   commanded absolute state (never toggle logic, always an absolute state
   command). If the state changed, persist state + counter to flash
   ([persistence.md](persistence.md)) — the last accepted counter must
   survive reboot or old sniffed frames become valid again.
4. Advertise a short ack burst (a few adverts, ~100-300ms)
5. Sleep

**Command frame** (packed 32-bit value, module → switch node):

| Bits | Field |
|---|---|
| 31:24 | Unit ID |
| 23:16 | Rolling counter (replay protection) |
| 15:8 | Key check byte |
| 1 | State (1=ON, 0=OFF) |
| 0 | Reserved |

**Ack frame** (switch node → module → S.Port telemetry → transmitter Lua
widget):

| Bits | Field |
|---|---|
| 31:24 | Unit ID (echo) |
| 23:16 | Counter (echo) |
| 8 | Valid flag (command checked out AND output-sense ADC confirms power state) |
| 0 | New state |

Multi-unit safety: each node only reacts to its own paired address + unit
ID, so overlapping BLE range between multiple vehicles/units is a
non-issue by design.

## Open items

- **8-bit key check byte is forgeable**: an attacker can spray frames with
  random key bytes and a high counter and get ~1 in 256 accepted — no
  sniffing needed. Proposed fix: replace it with a truncated AES-CMAC/CCM
  MAC (4-8 bytes) over `{unit ID, counter, state}` using the pairing key
  (nRF52832 has hardware AES). Frame grows to ~12-16 bytes, still fits a
  legacy advert. Asymmetric signatures were considered and rejected: they
  don't prevent replay on their own (a counter is still needed), don't fit
  a legacy advert (64-byte Ed25519 signature), and have no hardware
  acceleration on the nRF52832.
- **8-bit counter wraps after 256 commands**: a plain `counter > last`
  check stops accepting at wrap. Widen to 32 bits (preferred, pairs with
  the MAC change) or use serial-number arithmetic.

## Transmitter-side Lua widget

Runs on the GX15 (EdgeTX), in the `heimdall-module` side of the system, not
in this repo. Sends the command via `sportTelemetryPush` when triggered,
shows a countdown, then reads the ack telemetry sensor to display "Hello"
(switched ON) / "Goodbye" (switched OFF) / "No response" based on the ack
frame's bits.
