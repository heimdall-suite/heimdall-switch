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

## Pin assignment (BT832 castellated edge)

All 16 castellated pins are used or reserved; the 24 LGA-only pads are
untouched. Programming pins (VDD/GND/RESET/SWDCLK/SWDIO) are covered in
[protocol.md](protocol.md)'s scope — this table is the full picture:

| Pin | Net | Function |
|---|---|---|
| 1 | P0.26 | Status LED |
| 2 | P0.27 | Spare GPIO |
| 3 | P0.00/XL1 | 32.768kHz crystal (LFCLK) |
| 4 | P0.01/XL2 | 32.768kHz crystal (LFCLK) |
| 5 | P0.02/AIN0 | ADC feedback (load-side sense divider) |
| 6 | P0.03/AIN1 | Spare GPIO (analog-capable) |
| 7 | P0.09 | Spare GPIO (NFC pin — needs `NFCPINS` UICR cleared to use as GPIO) |
| 8 | P0.10 | Spare GPIO (NFC pin — needs `NFCPINS` UICR cleared to use as GPIO) |
| 9 | VDD | Power |
| 10 | GND | Ground |
| 11 | P0.13 | Relay coil drive — SET |
| 12 | P0.18 | Relay coil drive — RESET |
| 13 | P0.20 | Button input (GPIOTE, must wake from System OFF) |
| 14 | P0.21/RESET | SWD reset |
| 15 | SWDCLK | SWD clock |
| 16 | SWDIO | SWD data |

Notes:
- **LFCLK**: the module's mandatory 32MHz radio crystal is already onboard
  the BT832 (not exposed on any pin). Pins 3/4 are for the *optional*
  32.768kHz LFCLK crystal, populated here rather than using the internal RC
  oscillator — accuracy matters for the tightly-timed wake/scan cycle (see
  protocol.md), and the internal RC would otherwise need periodic
  HFCLK-powered recalibration, working against the power budget. Costs 2
  GPIOs + a crystal and 2 load caps on the BOM; reversible pin-for-pin if
  that trade turns out not to be worth it once real numbers are measured.
- **P0.09/P0.10** default to NFC antenna function at reset; firmware must
  clear the `NFCPINS` UICR register once to use them as plain GPIOs. No
  hardware-side implication, just a firmware bring-up step to remember.
- Programming header: pins 9/10/14/15/16 (VDD/GND/RESET/SWDCLK/SWDIO) are
  grouped on the same edge of the module — worth breaking out to a small
  pogo-pin test-jig footprint or header for repeated flashing during
  bring-up, rather than hand-wiring each time.
- 4 spare GPIOs remain (2, 6, 7, 8) if anything else comes up.

## Open items

- Real hardware not yet built — wake interval, scan window length, and BLE
  advertising interval (see [protocol.md](protocol.md)) are all first
  estimates, not measured.
- Exact latching relay part number (small pilot relay) and MOSFET part
  number not yet chosen.
