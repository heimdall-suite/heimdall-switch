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
- **Power**: 2S-3S LiPo (~6-12.6V) off the vehicle's own power bus. Regulator:
  **TI TPS629206** (verified against the actual datasheet — 3-17V in, 4µA
  typical IQ, 0.6A max output — same TPS6292xx low-IQ family as the
  originally-considered TPS62901, ~30x this design's actual peak draw) —
  single stage is sufficient; a pack this size (1500-2500mAh) gives years
  of idle life even at a few µA, so don't over-engineer the regulator stage
  further. Chosen over the TPS62901 specifically for assembly: TPS62901 is
  only offered in a 9-pin VQFN-HR (0.5mm pitch, no-lead, recessed pins —
  reflow/hot-air-only with no visible solder joint), while the TPS629206 is
  in an **8-pin SOT-5X3 (1.6×2.1mm) with genuine gull-wing leads** (confirmed
  from the package outline's lead foot-angle dimensions) — same 4µA
  efficiency, no assembly trade-off. Full reference-design BOM below.
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

## Schematic

A first-draft KiCad schematic implementing everything on this page lives in
[hardware/kicad/](../hardware/kicad/) (`heimdall-switch.kicad_pro` +
`.kicad_sch`), with a rendered [heimdall-switch.svg](../hardware/kicad/heimdall-switch.svg)
for quick viewing without opening KiCad. Custom symbols for the BT832 and
TPS629206 (neither has an official KiCad library part) live in
`heimdall-switch.kicad_sym`; opening the project should resolve them
automatically via the project-local `sym-lib-table`.

Verified with `kicad-cli sch export svg` and `kicad-cli sch erc` (both
tools already installed on this machine, just not on PATH — full path is
`AppData/Local/Programs/KiCad/10.0/bin/`). ERC comes back clean except for
expected items: the intentionally-open VSET/PG/spare-GPIO pins, and
"power pin not driven" on VDD/GND/VIN — the last one is a modeling
artifact of using plain net labels (`GND`, `+3V3`, `VBAT`) instead of
dedicated KiCad power-flag symbols, done to keep the generation simpler;
electrically correct either way, but swap in real power symbols later if
you want ERC fully silent.

Known simplifications in this draft, worth revisiting before layout:
- No footprints assigned yet (schematic-only pass).
- The relay driver stage (Q1/Q2 pilot transistors, D1/D2 flyback diodes,
  K1 latching relay, Q3 P-channel high-side load switch) uses generic
  Device-library parts as placeholders — exact relay/MOSFET part numbers
  are still an open item (see below), so values/footprints aren't final.
- ADC divider (R_FB_TOP=100k, R_FB_BOT=33k) assumes sensing a ~12.6V max
  load rail scaled to a safe ADC input; revisit once the actual load
  voltage range is known.
- Component placement is a plain generated grid (correctness-first, not
  routed/tidied) — expect to rearrange freely in the KiCad GUI.

## Buck regulator (TPS629206) reference design

Output is **3.3V**, chosen over 3.0V specifically because it's directly
available as an internal VSET preset with zero feedback components (see
below) — 3.0V isn't a VSET option at all (the preset table jumps 2.5V →
3.8V), so it would force the classic 2-resistor external-divider mode
instead. 3.3V is comfortably within the BT832's 1.7-3.6V VDD range.

**Output voltage configuration** (confirmed against the actual datasheet
tables, Table 8-1 and Table 8-2 — cross-checked against a user-provided
screenshot of Table 8-1 after an initial OCR pass mismapped which resistor
values select which mode):
- **MODE/S-CONF pin**: 27.40kΩ to GND — selects VSET (internal divider)
  mode, "up to 2.5MHz" switching (auto-adjusted for actual VIN/VOUT),
  output discharge enabled, Auto PFM/PWM with AEE (best light-load
  efficiency, which matters here since the system is asleep almost all the
  time)
- **FB/VSET pin**: left open (no component) — Table 8-2 row 18 shows
  "249kΩ or larger, or open" both select the top VSET preset, 3.3V
- No R1/R2 feedback divider needed at all — simpler and cheaper than the
  classic external-divider mode this part also supports

**Output filter** (Table 9-3 / component selection sections):
- L1 = 2.2µH nominal
- C_out = 22µF ceramic, X7R/X5R, low ESR
- C_in = 4.7µF ceramic, X7R/X5R, voltage-rated well above the 12.6V max
  (use a 25V-rated part to avoid DC-bias capacitance derating)

**Superseded**: an earlier pass at this section spec'd the TPS62901 (same
family, VQFN-HR package) with a classic-mode R1/R2 divider (402k/100k for
3.0V, 453k/100k for 3.3V) computed from that part's equation. Kept here
for reference only in case the VSET-preset approach above doesn't pan out
during bring-up and a fallback to classic external-divider mode is needed
— the same R1/R2 math applies to the TPS629206 too (also VFB = 0.6V).

## Open items

- Real hardware not yet built — wake interval, scan window length, and BLE
  advertising interval (see [protocol.md](protocol.md)) are all first
  estimates, not measured.
- Exact latching relay part number (small pilot relay) and MOSFET part
  number not yet chosen.
- TPS629206 soft-start behavior/capacitor (if any is needed) not yet
  checked against the datasheet — carried over from the TPS62901
  investigation, never resolved for either part.
