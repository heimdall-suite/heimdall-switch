# Hardware

- **MCU**: nRF52 — nRF52-DK or Adafruit Feather nRF52 Bluefruit for dev;
  production target is the **Fanstel BT832** module (nRF52832, 14×16×1.9mm,
  integrated PCB trace antenna, no custom RF layout needed). Chosen over the
  smaller Insight SiP ISP1507 (8×8×1mm) specifically for assembly: the
  ISP1507 is a 62-pad bottom-only LGA with no side access, which needs
  stencil+paste reflow — not viable for hand rework. The BT832 instead
  breaks out 16 pins as **castellated edges** (side-accessible, and per
  Fanstel's own datasheet, "SMT equipment is not required for soldering
  castellated pins"), backed by 24 further LGA-only pins for full 32-GPIO
  access if ever needed. Every signal this design needs — VDD, GND,
  SWDCLK/SWDIO/RESET for programming, plus 2 analog-capable GPIOs
  (P0.02/AIN0, P0.03/AIN1) and enough spare digital GPIOs for relay
  SET/RESET drive, ADC feedback, the button interrupt, and the status LED —
  lands on those 16 castellated pins, so the LGA-only pads never need to be
  used. A same-footprint BT832F variant (15×20.8×1.9mm, ~760m vs ~110m
  range) exists if longer BLE range is ever needed; not required for this
  short vehicle-to-module link, so BT832 is the default unless that changes.
- **Radio**: BLE. Chosen over ESP-NOW/WiFi-class radios (too power-hungry to
  listen continuously, ~mA-range RX current with no good sleep/wake story)
  and over sub-GHz CC1101 (lower idle current in theory, but needs its own
  antenna design and a second discrete radio chip — not worth it once
  duty-cycle math showed BLE was already more than adequate).
- **Power**: 2S-3S LiPo (~6-12.6V) off the vehicle's own power bus. Regulator: TI TPS6290x
  family (3-17V in, ~4µA IQ) — single stage is sufficient; a pack this size
  (1500-2500mAh) gives decades of idle life even at a few µA, so don't
  over-engineer the regulator stage further.
- **Switching element**: NOT a bare 10A relay (too bulky) and NOT a
  solid-state CMOS latch (volatile — loses state on power interruption,
  which matters here because of vibration/connector risk in an RC vehicle). Settled
  on: small (1-2A) dual-coil latching relay as a pilot element, driving a
  power MOSFET (rated >10A, matched to bus voltage) for the actual load
  switching. The relay's mechanical/magnetic latch holds state with zero
  power and survives full power loss + vibration by design — this is the
  property that actually mattered.
- **Feedback**: resistor divider on the switched (load-side) output into an
  ADC pin, to confirm actual delivered power downstream — not just "we sent
  a pulse."
- **Local button**: debounced, GPIOTE interrupt-wake (must wake the nRF52
  from deep sleep independent of the normal BLE scan cycle). Held ≥5s but
  <15s → toggle power state locally. Held ≥15s → enter pairing mode.
- **Status LED**: 1 GPIO, visual state indicator.

## Open items

- Real hardware not yet built — wake interval, scan window length, and BLE
  advertising interval (see [protocol.md](protocol.md)) are all first
  estimates, not measured.
- Exact latching relay part number (small pilot relay) and MOSFET part
  number not yet chosen.
