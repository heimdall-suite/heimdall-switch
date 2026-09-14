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
   last accepted, for replay protection) → drive relay coil (SET or RESET
   per commanded absolute state — never toggle logic, always an absolute
   state command)
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

## Transmitter-side Lua widget

Runs on the GX15 (EdgeTX), in the `heimdall-module` side of the system, not
in this repo. Sends the command via `sportTelemetryPush` when triggered,
shows a countdown, then reads the ack telemetry sensor to display "Hello"
(switched ON) / "Goodbye" (switched OFF) / "No response" based on the ack
frame's bits.
