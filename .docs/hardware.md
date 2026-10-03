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
  (P0.02/AIN0, P0.03/AIN1) and enough spare digital GPIOs for the output
  OFF-hold drive, ADC feedback, the button interrupt, and the status LED —
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
- **Switching element**: single high-side P-FET, **fail-on** — see
  [Switching stage](#switching-stage) below. No mechanical or coil relays.
  State across power loss is kept in flash
  ([persistence.md](persistence.md)), the same approach the Jeti SPS-20
  takes (MCU-driven FET switch with remembered state).
- **Feedback**: resistor divider on the switched (load-side) output into an
  ADC pin, to confirm actual delivered power downstream — not just "we sent
  a pulse."
- **Local button**: debounced, GPIOTE interrupt-wake (must wake the nRF52
  from deep sleep independent of the normal BLE scan cycle). Held ≥5s but
  <15s → toggle power state locally. Held ≥15s → enter pairing mode.
- **Status LED**: 1 GPIO, visual state indicator. Must be clearly visible
  **outdoors in sunlight**, typically through a 3mm hole drilled in the
  hull/fuselage (as with the Jeti SPS-20's daughter-board LED). So: 3mm
  through-hole, water-clear lens, narrow beam, high intensity — **Everlight
  204-10SUGC/S400-A4**, emerald green 525nm, 3.2cd at 20mA, 20° (see
  [BOM](#bom)).
  - **Driven from VBAT, not 3.3V**: high-intensity green/blue/white LEDs
    (InGaN) need ~3.0-3.4V forward, which leaves nothing across a
    resistor on the 3.3V rail. Circuit, **high-side switched** so the
    LED's cathode can go straight to GND (3 daughter-board wires, not 4):
    VBAT → Q6 (BSS84 P-FET) → R_LED (680Ω 1206) → LED → GND. Q6's gate is
    pulled up to VBAT by R_Q6_PU (1MΩ) and pulled to GND by Q5 (AO3400A)
    when P0.03 (`LED_DRV`) is high, giving Q6 |V_GS| = full pack voltage
    (within BSS84's ±20V). R_LED_PD (1MΩ) holds Q5 off while the MCU is
    in reset or dead. Plain GPIO drive; no high-drive mode needed. Cost:
    ~6-13µA through R_Q6_PU *only while the LED is lit*; nothing when off.
    Q6 is the same part as Q2 and Q5 as Q1, so no new part numbers.
  - **Current follows pack voltage** (V_F ≈ 3.1V at these currents):
    ~4.3mA at 6.0V (2S LiFePO4 near empty), ~5.1mA at 6.6V (2S LiFePO4
    nominal), ~7.8mA at 8.4V (2S LiPo full), ~14mA at 12.6V (3S full) —
    roughly 0.7-2.2cd, still far above a normal indicator. R_LED
    dissipates ≤0.13W. If an even brightness matters, firmware can PWM
    the LED against the pack voltage it reads through ADC_FB while the
    output is ON.
  - **Short protection**: Q6 and R_LED sit on the main board ahead of J4, so a
    daughter-board wire shorted to GND draws at most 12.6V / 680Ω =
    18.5mA (0.23W, within the 1206's 0.25W).
- **Breakout for a daughter board (J4)**: LED and button can sit on the
  main board (LED1/SW1 fitted) or on a small daughter board, positioned
  wherever the vehicle needs them. J4 is a 3-pin **JST-GH** header
  (SM03B-GHS-TB, 1.25mm pitch, right-angle SMD at the board edge; 1 LED_A,
  2 BTN, 3 GND — the LED cathode and the
  button share the GND wire) wired in parallel with LED1/SW1. In the main
  schematic LED1/SW1 are the *optional on-board positions*; for off-board
  use leave them unfitted and plug a ready-made 3-wire GH cable
  (pin 1 ↔ pin 1) from J4 to the daughter board's GH header. Q5, Q6 and
  R_LED stay on the main board, so the daughter board only needs the LED
  and the switch. See [Daughter board](#daughter-board-ui).
  **R_BTN (1kΩ)** in
  series with P0.20 protects the pin from ESD on the off-board wire (the
  button is the part people touch); with the internal pull-up (~13kΩ) the
  pressed level is ~0.23V, a clean logic low.

## Pin assignment (BT832 castellated edge)

All 16 castellated pins are used or reserved; the 24 LGA-only pads are
untouched. Programming pins (VDD/GND/RESET/SWDCLK/SWDIO) are covered in
[protocol.md](protocol.md)'s scope — this table is the full picture:

| Pin | Net | Function |
|---|---|---|
| 1 | P0.26 | Spare GPIO (was the LED drive; moved to P0.03 so PCB traces from this pin row don't cross the crystal) |
| 2 | P0.27 | Spare GPIO |
| 3 | P0.00/XL1 | 32.768kHz crystal (LFCLK) |
| 4 | P0.01/XL2 | 32.768kHz crystal (LFCLK) |
| 5 | P0.02/AIN0 | ADC feedback (load-side sense divider) |
| 6 | P0.03/AIN1 | Status LED drive (`LED_DRV`, Q5 gate; high = LED on) |
| 7 | P0.09 | Spare GPIO (NFC pin — needs `NFCPINS` UICR cleared to use as GPIO) |
| 8 | P0.10 | Spare GPIO (NFC pin — needs `NFCPINS` UICR cleared to use as GPIO) |
| 9 | VDD | Power |
| 10 | GND | Ground |
| 11 | P0.13 | Output OFF-hold (high = output OFF, released = ON) |
| 12 | P0.18 | SWO (trace output to J1 pin 6) |
| 13 | P0.20 | Button input (GPIOTE, must wake from System OFF) |
| 14 | P0.21/RESET | SWD reset |
| 15 | SWDCLK | SWD clock |
| 16 | SWDIO | SWD data |

Notes:
- **LFCLK**: the module's mandatory 32MHz radio crystal is already onboard
  the BT832 (not exposed on any pin). Pins 3/4 are for the *optional*
  32.768kHz LFCLK crystal. It is **not required**: this node only scans
  and advertises (no BLE connections), and neither needs better than the
  internal RC oscillator's ±500ppm — drift over a 2.5s wake interval is
  ~1ms. The crystal is a small idle-power optimization (Fanstel's datasheet
  recommends it "for lower power consumption at idle state"): the RC
  oscillator draws more (~0.6µA vs ~0.25µA for the crystal oscillator,
  nRF52832 PS typicals — verify) and needs periodic calibration against
  the 32MHz crystal (cheap here: it can piggyback on the scan wake-ups).
  Net saving ~0.4-0.7µA, i.e. 1-2% of the ~34µA OFF budget — hard to
  justify on power alone. **Decision: Y1/C1/C2 stay in the design;
  whether to fit them is decided at assembly.** Firmware must therefore
  support both LFCLK sources (LFXO and calibrated LFRC), ideally
  detecting which is present; with the crystal fitted, the real
  difference can be measured at bring-up. Part: **Epson FC-135** 32.768kHz, CL 12.5pF, ±20ppm
  (3.2×1.5mm, LCSC C32346, JLCPCB basic; the 9pF variant isn't stocked),
  with C1 = C2 = **18pF C0G**: nRF52 formula C = 2·CL − C_pin (4pF) −
  C_pcb (~1-2pF) ≈ 19-20pF → nearest E12 below.
- **DC/DC**: the two inductors for the nRF52832's internal DC/DC regulator
  are inside the BT832 module (per Fanstel's datasheet), so firmware can
  enable DC/DC mode — the lower-current figures in the power budget apply.
- **P0.09/P0.10** default to NFC antenna function at reset; firmware must
  clear the `NFCPINS` UICR register once to use them as plain GPIOs. No
  hardware-side implication, just a firmware bring-up step to remember.
- Programming header: pins 9/10/14/15/16 (VDD/GND/RESET/SWDCLK/SWDIO) are
  grouped on the same edge of the module — worth breaking out to a small
  pogo-pin test-jig footprint or header for repeated flashing during
  bring-up, rather than hand-wiring each time.
- **SWD header J1**: the standard **ARM Cortex Debug 10-pin** connector
  (2×5, 1.27mm pitch), male pins on the board, the probe's ribbon cable
  brings the female socket. J-Link, ST-Link, the Raspberry Pi Debug
  Probe, CMSIS-DAP probes and Nordic DKs' debug-out all plug straight in.
  **hanxia HX PZ1.27-2x5P TP** (SMD, LCSC C41376037, ~$0.10), a generic
  2×5 1.27mm SMD header. The Samtec FTSH-105-01-L-DV-K (C5155080) that
  ARM's spec references is the same thing at ~$1.46. Its recommended land
  pattern (0.74 × 2.50mm pads, 6.50mm overall) matches KiCad's
  `PinHeader_2x05_P1.27mm_Vertical_SMD` (0.74 × 2.40mm, 6.30mm overall,
  same 1.5mm gap between rows) closely enough to keep the stock
  footprint. Fitted on **every** board: each one needs SWD at least once
  to flash the bootloader, and later for recovery. It's unshrouded, so
  the cable can go on either way round: pin 1 is marked on the
  silkscreen, match it to the ribbon's red stripe. Programmer: the nRF52
  DK's Debug out (P19, same 10-pin connector) or any J-Link/CMSIS-DAP
  probe, with a plain 10-pin 1.27mm ribbon cable.

  | J1 pin | Signal | BT832 pin |
  |---|---|---|
  | 1 | VTref (+3V3) | 9 (VDD) |
  | 2 | SWDIO | 16 |
  | 3, 5, 9 | GND (9 = GNDDetect) | 10 |
  | 4 | SWCLK | 15 |
  | 6 | SWO | 12 (P0.18) |
  | 7 | KEY (no pin function) | — |
  | 8 | NC/TDI (not connected) | — |
  | 10 | nRESET (10k pull-up R_RST to +3V3) | 14 (P0.21/RESET) |

  SWO is the nRF52832's trace output, fixed to P0.18 in silicon: wiring
  it gives printf-style logging over the debug probe (e.g. SEGGER SWO
  viewer) without a UART. P0.18 was spare, so it costs nothing.

  Pin 1 is a **voltage reference for the probe, not a power input** — power
  the board from its battery while flashing. A probe set to *supply*
  3.3V with no battery connected back-feeds through the buck onto VBAT,
  and with fail-on Q3 then puts ~3V on the load output.
- 4 spare GPIOs remain (1, 2, 7, 8) if anything else comes up.
- P0.13 must be driven to its saved state as early as possible in boot —
  see [Switching stage](#switching-stage).

## Switching stage

**Load**: receiver, GPS, 4 micro/mini servos, 2 standard servos, on 22-24
AWG leads. ~2-3A continuous, ~6-8A peaks for tens of ms (servos
starting/stalling together). Output is raw pack voltage (up to 3S /
12.6V) — with 3S, a BEC sits downstream of the switch. Nothing else may
feed the output side (no receiver-side battery, no ESC BEC red wire): a
single FET's body diode conducts output→input when off, so back-feed would
defeat the switch. Back-to-back FETs were considered and dropped for this
reason — not needed as long as that rule holds.

**Fail-on principle**: a control-side failure must never kill the output
— losing power in flight/on the water means losing the vehicle. The
hardware default is therefore ON, and the MCU must *actively hold* the
output OFF. The realistic failure causes are firmware hangs, brownout
resets, vibration-cracked solder joints, regulator failure — spontaneous
silicon failure is negligible by comparison — and all of these fall back
to ON. Only a failure in the power path itself (the FET, its gate
pull-down) can drop the output; MOSFETs typically fail short (ON), which is
the benign direction.

**Circuit**:
- **Q3 — load switch**: P-FET, source to VBAT, drain to LOAD_OUT.
  **Selected: AOS AO4407A** (SO-8, LCSC C16072) — −30V V_DS, ±25V V_GS,
  R_DS(on) ≤ 13mΩ at V_GS = −10V, ≤ 17mΩ at −6V (12.7mΩ typ), V_GS(th)
  −1.7 to −3.0V. It is *not* specified at −4.5V, and doesn't need to be:
  the gate is pulled all the way to GND, so |V_GS| = pack voltage, never
  below ~5V on 2S (≈14mΩ typ there per datasheet Fig. 5). Worst case at
  3A ≈ 0.15W; peaks ~1W for ms — fine in SO-8 with a copper pad. Chosen
  over the DFN 3×3 AONR21357 (C431196, ≤12.3mΩ at −4.5V) for easier hand
  assembly/inspection on pre-production boards — AONR21357 is the drop-in
  electrical upgrade if the board is shrunk later. AO4409 (SO-8, −4.5V
  spec) rejected: obsolete. SOT-23 parts (typically 40-60mΩ) run too hot
  at 3A continuous.
- **Gate default ON**: Q3 gate pulled to GND by R_PD1 ‖ R_PD2 (2×2.2MΩ =
  1.1MΩ), split so a single open resistor can't leave the gate floating.
- **Slow turn-on**: C_SS = 220nF gate-source with the 1.1MΩ pull-down →
  τ ≈ 240ms. On battery connect or MCU reset the gate starts at V_GS = 0;
  Q3 only starts conducting once V_GS crosses its threshold (~−1.5V), which
  takes ~30ms at 12.6V and ~60ms at 6.6V. The MCU must assert OFF before
  that — i.e. **within ~20ms of power-up** (bare nRF52 boot to GPIO is a
  few ms, so there's margin, but keep the restore path early and simple).
  Fully enhanced (V_GS = −4.5V) after ~110ms at 12.6V / ~280ms at 6.6V.
  The same RC soft-starts the inrush into the downstream
  BEC/receiver/servo capacitance.
  C_SS is a **50V X7R 0805** (Samsung CL21B224KBFNNNE, LCSC C5378), not a
  25V 0603: it sits at up to 12.6V, and a 25V 0603 X7R loses ~30% of its
  capacitance there, which would cut the ~30ms turn-on delay at 12.6V to
  ~20ms — the whole firmware margin. The 50V 0805 part loses ~10%.
- **Active OFF**: Q2 (P-FET) clamps Q3's gate to VBAT through R_LIM when
  on. Q2's gate is pulled up to VBAT by R_CLAMP_PU (1MΩ) and pulled low by
  Q1 (N-FET), driven from P0.13 via R_G1 (100Ω), with R_OFF_PD (1MΩ)
  holding Q1 off whenever the GPIO floats (reset, unpowered MCU). GPIO
  high → Q1 on → Q2 on → output OFF. Turn-off is fast (~20µs); only
  turn-on is slowed.
  - **Q1: AOS AO3400A** (SOT-23, LCSC C20917, JLCPCB basic part) —
    logic-level (V_GS(th) 0.65-1.45V), fully on from a 3.3V GPIO. The CJ
    2N7002 (C8545, V_GS(th) up to 2.5V) was the placeholder: works, but
    thin margin at 3.3V drive.
  - **Q2: Nexperia BSS84** (SOT-23, LCSC C493579) — V_GS(th) −0.8 to
    −2.0V, I_DSS ≤ 100nA at −40V/25°C. A *high* threshold is deliberate:
    the more gate voltage Q2 needs, the more Q1 leakage it takes to turn it
    on by accident (so low-threshold parts like AO3401A are unsuitable
    here).
  - **R_LIM (100Ω, Q2 drain → Q3 gate)**: when Q2 switches on it shorts
    C_SS (charged to VBAT); without R_LIM the discharge spike is ~1A+ for
    ~µs, above BSS84's ~0.5A pulse rating (tiny energy, ~17µJ — a spec
    violation rather than a likely failure). R_LIM caps it at ~0.1A;
    turn-off goes from ~2µs to ~20µs, irrelevant for this load.
- **Leakage margin for fail-on**: with the MCU dead, a chain of leakages
  would have to (1) pull Q2's gate ~0.8-1V below VBAT — ≈1µA of Q1
  leakage through R_CLAMP_PU — and then (2) push ≈3-9µA through Q2 into
  Q3's gate against R_PD (1.1MΩ) to lift it within ~3V of VBAT. Small
  SOT-23 FETs typically leak tens of nA at 7-13V and warm temperatures:
  10-100× margin. Datasheet worst cases (often "1µA max" at full rated
  V_DS) are looser, so **verify on the first boards**: MCU unpowered,
  output ON — Q3 gate should read within a few mV of GND and Q2 gate
  within a few mV of VBAT. Don't raise R_CLAMP_PU / R_PD further to save
  current without re-checking this.
- **Gate protection**: D_Z, 18V zener gate-source on Q3 (cathode to VBAT)
  — **onsemi MMSZ5248B** (SOD-123, LCSC C2127). At 12.6V max the ±25V gate
  is within spec without it; it's cheap insurance against transients.
  18V rather than 15V because the zener sits reverse-biased at full pack
  voltage whenever the output is ON, and its leakage flows into Q3's gate
  node against R_PD: a 15V zener at 12.6V (84% of V_Z) is near its knee
  and can leak µA, lifting the gate; the 18V part is specified at
  ≤100nA at 14V (≤0.11V gate lift through 1.1MΩ), and still clamps well
  below the 25V gate rating.

**Reverse polarity protection**: servo-style RC plugs are easy to insert
backwards, and a reversed pack would destroy not just this node but the
load — Q3's body diode would conduct and put reversed voltage across the
receiver/servos. So the protection covers the whole power path, right at
the battery input:
- **Q4**: P-FET "ideal diode" in the positive line between J3 and the VBAT
  rail — drain to the battery (+) pin of J3, source to VBAT, gate to GND
  via R_REV (100kΩ), plus an 18V gate-source zener (D_Z2, cathode to
  source, same MMSZ5248B) like Q3's. **Same part as Q3: AO4407A** (SO-8, LCSC C16072).
- Correct polarity: Q4's body diode conducts first, lifting its source to
  ~VBAT, which pulls V_GS to −VBAT and turns it fully on. Reversed: the
  body diode is reverse-biased and V_GS ≈ 0, so Q4 stays off and nothing
  downstream sees negative voltage.
- Cost: zero quiescent current (no DC path below the zener voltage);
  ~135mW / ~45mV extra drop at 3A. A series Schottky was rejected — fine
  for the node's µA supply, but ~1.2W at 3A in the load path.
- Q4 only blocks *reverse polarity*. Once on, it conducts both ways, so it
  doesn't block back-feed from the output side — that's still ruled out by
  the "nothing else feeds the output" rule above.
- Out of scope: a reversed *load-side* connector (J2) can't be protected
  here — that's the load's own wiring.

**Cost of fail-on**: see [Power budget](#power-budget) — ~15µA extra while
OFF. A dead MCU while OFF turns the output ON, so a stored vehicle with the
battery connected could power up and drain the pack — **disconnect the
battery for storage** (standard practice; Jeti's SPS-20 manual says the
same).

**Firmware requirements** (see also [persistence.md](persistence.md)):
- Restore the saved state to P0.13 early in boot — within ~20ms of
  power-up, before Q3 starts conducting (see Slow turn-on).
- **Watchdog is mandatory**: firmware hung with P0.13 held high is the one
  failure the hardware default can't cover. The nRF52 WDT (LFCLK-clocked,
  can't be stopped once started) resets the MCU, which releases P0.13 →
  output falls back to ON → firmware restores the saved state.

## Power budget

Estimates, not measurements — every radio/MCU figure here needs checking on
real hardware. Reference pack: **1500mAh 2S LiFePO4 RX pack (6.6V
nominal)**. Resistor currents scale with pack voltage (roughly ×1.9 on 3S).

**Assumptions**:
- TPS629206 quiescent 4µA (datasheet typical).
- nRF52832 System ON sleep, RTC + 32kHz crystal, RAM retained: ~2µA.
- Scan cycle per [protocol.md](protocol.md): wake every 2.5s, 7.5ms scan
  window + ~1.5ms wake overhead at ~6.5mA (radio RX with the nRF52's
  internal DC/DC enabled — the BT832 has the DC/DC inductors onboard) →
  ~23µA average. LDO-mode figures below are kept only as the fallback if
  DC/DC is left disabled in firmware (RX roughly doubles → ~45µA).
- Buck efficiency at these µA loads ~85% → a 3.3V-side current appears at
  the pack as ×0.59 (3.3V / (6.6V × 0.85)).

**Always on (both states)**, at the pack:

| Item | 3.3V side | At pack |
|---|---|---|
| TPS629206 quiescent | — | 4µA |
| nRF52 sleep | 2µA | 1.2µA |
| BLE scan duty cycle | 23µA (LDO: 45µA) | 13.5µA (LDO: 26.5µA) |
| **Subtotal** | | **~19µA (LDO: ~32µA)** |

**Extra in OFF** (fail-on hold active):

| Item | Current |
|---|---|
| R_PD1‖R_PD2 across VBAT (Q2 clamping) | 6.6V / 1.1MΩ = 6.0µA |
| R_CLAMP_PU across VBAT (Q1 on) | 6.6V / 1MΩ = 6.6µA |
| R_OFF_PD on the 3.3V GPIO | 3.3µA → 1.9µA at pack |
| ADC divider (output is 0V) | 0 |
| **OFF total** | **~34µA (LDO: ~47µA)** |

**Extra in ON**: the gate network draws nothing (Q1/Q2 off, Q3 gate at
0V). The ADC divider (100k + 33k across LOAD_OUT) draws 6.6V / 133kΩ =
50µA → **ON total ~69µA** for the node itself. That's irrelevant next to
the load (receiver + GPS + 6 idle servos ≈ 150-200mA), but could drop to
~5µA with a 1M/330k divider if it ever matters (needs a longer SAADC
acquisition time for the higher source impedance).

**Storage time, OFF, battery left connected** (1500mAh pack, counted down
to 20% remaining = 1200mAh usable):

| Case | Drain | Time to 20% |
|---|---|---|
| Node only, DC/DC | 34µA | ~35,000h ≈ **4 years** |
| Node only, LDO | 47µA | ~25,500h ≈ **2.9 years** |
| Node + LiFePO4 self-discharge (~2%/month ≈ 41µA equivalent), DC/DC | ~75µA | ≈ **1.8 years** |
| For comparison: Jeti SPS-20 (160µA OFF, per its manual), node only | 160µA | ≈ 10 months |

The node's OFF draw is about the same as the pack's own self-discharge, so
leaving the pack connected costs roughly half its shelf life — acceptable,
but "disconnect for storage" still stands, mainly because of the fail-on
case above. Left **ON** by mistake, the same pack is flat in ~6-8h from
the idle load alone; the switch's own draw doesn't matter there.

Biggest levers if OFF draw needs to drop: the scan interval (2.5s → 5s
halves the ~13.5µA scan share) and the fail-on hold resistors (limited by
the leakage constraint above).

## Schematic

**Circuit at a glance** (each block is also labelled on the schematic
sheet). Four ideas explain most of it: a P-FET turns on when its gate is
pulled well below its source; an N-FET pulling a P-FET's gate down lets
a 3.3V GPIO switch a 12V path (Q1/Q2, Q5/Q6); the 1-2.2MΩ resistors set
the safe default when the MCU isn't driving (output ON, LED off); the
rest is supply plumbing.

| # | Block | Parts | Job |
|---|---|---|---|
| 1 | Battery in + reverse polarity | J3, Q4, R1, D1 | Q4 is an ideal diode: body diode lifts VBAT, R1 pulls the gate to GND, Q4 turns fully on; a reversed pack leaves it off. D1 clamps V_GS. |
| 2 | Load switch (fail-on) | Q3, R9, R10, C7, D2 | Q3 is the switch. R9 ‖ R10 hold it ON by default, C7 slows turn-on (gives the MCU time after reset), D2 clamps V_GS. |
| 3 | Switch-off circuit | Q1, R5, R6, Q2, R7, R8 | P0.13 high → Q1 on → Q2 on → R8 pulls Q3's gate to VBAT → output OFF. R6/R7 keep the chain idle when the MCU is dead. |
| 4 | Load out + voltage sense | J2, R11, R12, C8 | R11/R12 scale LOAD_OUT to the ADC (12.6V → 3.1V), C8 filters: pack voltage while ON, ~0V while OFF. |
| 5 | 3.3V regulator | R2, C3, U2, R3, L1, C4 | R2 + C3 damp the plug-in spike; U2 buck with L1/C4; R3 sets its mode. |
| 6 | MCU | U1, C5, C6, Y1, C1, C2, R4, J1 | BT832 (nRF52832 + antenna), supply decoupling, 32kHz crystal, reset pull-up, SWD header. |
| 7 | Status LED + button | Q5, Q6, R13, R14, R15, LED1, SW1, R16, J4 | P0.03 high → Q5 pulls Q6's gate low → Q6 feeds VBAT through R14 to the LED (off by default). SW1 to GND with R16 protecting the pin. J4 breaks LED/BTN/GND out to the daughter board. |

A first-draft KiCad schematic implementing everything on this page lives in
[hardware/kicad/](../hardware/kicad/) (`heimdall-switch.kicad_pro` +
`.kicad_sch`), with a rendered [heimdall-switch.svg](../hardware/kicad/heimdall-switch.svg)
for quick viewing without opening KiCad. Custom symbols for the BT832 and
TPS629206 (neither has an official KiCad library part) live in
`heimdall-switch.kicad_sym`; opening the project should resolve them
automatically via the project-local `sym-lib-table`.

Drawn with real wires within each block (regulator, MCU + crystal/SWD,
status LED + button + J4 breakout, switching stage + load output), KiCad power symbols (`GND`,
`+3V3`, `VBAT` — the latter is the stock `+BATT` symbol renamed) with
PWR_FLAGs, and no-connect markers on the intentionally-open pins
(VSET/PG, spare GPIOs). Signals cross between blocks as net labels:
`OUT_OFF` (P0.13 → switching stage), `ADC_FB` (divider → P0.02),
`LED_DRV` (P0.03 → Q5 gate), `BTN` (P0.20 → R_BTN/SW1/J4), and the debug
signals `nRESET`, `SWDCLK`, `SWDIO`, `SWO` (U1 → J1).
Within the LED/button block, the `LED_A` label carries the LED anode to
J4.
J3 is the battery input connector.

Verified with `kicad-cli sch erc`, netlist export (every pin checked
against the intended net) and `sch export svg` (kicad-cli is installed
but not on PATH — `AppData/Local/Programs/KiCad/10.0/bin/`). ERC: **0
errors, 0 warnings**. All custom-symbol pins (BT832, TPS629206) sit on
the 2.54mm grid — keep it that way when editing `heimdall-switch.kicad_sym`:
an off-grid pin makes GUI-drawn wires snap past it and silently not
connect (this happened once, to SWDCLK/SWDIO).

Sheet layout: the reverse polarity block (J3 → Q4 → VBAT, with D_Z2 and
R_REV) sits on its own below the regulator and connects to it through the
`VBAT` power symbol; J3's pin 1 net is labelled `BATT+`. The debug
header J1 (with R_RST) sits in its own block right of the crystal,
linked to U1 by labels, so no wires cross.

Reading the schematic:
- **Power symbols** (`VBAT` arrow, `+3V3` arrow, `GND`) connect by name
  across the whole sheet — two `VBAT` arrows are the same net even with no
  wire between them.
- **PWR_FLAG** (small diamond, text hidden) is not a component and not in
  the BOM. It tells ERC "this net is powered from outside" — needed where
  power arrives through pins KiCad sees as passive (battery connector, Q4,
  L1, R_IN). One each on VBAT (at Q4), GND (at J3), +3V3 (at C_OUT) and
  the regulator input node after R_IN.
- One GND symbol has its "GND" text hidden where it collided with
  wires (U2 pin 5) — an ordinary GND connection.

**Annotation and footprints**: the schematic is annotated with standard
references and every part has a footprint. The design notes on this page
keep the descriptive names (`R_PD1`, `C_SS`, …); each renamed symbol
carries its old name in a hidden `Function` field, and the mapping is:

| Ref | Name in these docs | Ref | Name in these docs |
|---|---|---|---|
| C3 | C_IN | R7 | R_CLAMP_PU |
| C4 | C_OUT | R8 | R_LIM |
| C5 | C_VDD1 | R9 | R_PD1 |
| C6 | C_VDD2 | R10 | R_PD2 |
| C7 | C_SS | R11 | R_FB_TOP |
| C8 | C_FB | R12 | R_FB_BOT |
| R1 | R_REV | R13 | R_Q6_PU |
| R2 | R_IN | R14 | R_LED |
| R3 | R_MODE | R15 | R_LED_PD |
| R4 | R_RST | R16 | R_BTN |
| R5 | R_G1 | D1 | D_Z2 |
| R6 | R_OFF_PD | D2 | D_Z |

Unchanged: C1/C2 (crystal caps), Q1–Q6, U1, U2, L1, Y1, LED1, SW1, J1–J4.
Footprints are KiCad stock (0603 passives; 0805/1206 where the BOM says;
SOT-23, SOIC-8, SOD-123, SOT-583-8, 1008, 3215 crystal, JST-GH, 2×5
1.27mm SMD header, solder-wire pads) except two project-local items:
- **`heimdall-switch:Fanstel_BT832`** (in `heimdall-switch.pretty`, via
  the project `fp-lib-table`), drawn from Fanstel's datasheet (Ver 2.12,
  p.8): 14.0 × 16.0mm module, 16 castellated pads at 1.10mm pitch, pins
  1–8 down the left side and 9–16 up the right, pin 8/9 1.10mm above the
  bottom edge. Pads are 0.70 × 1.75mm, reaching 0.85mm beyond the module
  edge for the soldering iron. The 24 LGA pads are left off (unused; the
  module's LGA pads then sit on solder mask). A copper keep-out (tracks,
  vias, pads, pours, both layers) covers the 6.43mm antenna section.
  **Check the printed footprint against a real module before ordering.**
- **`heimdall-switch:AO4407A`** symbol (in `heimdall-switch.kicad_sym`):
  the generic P-FET drawing with SO-8 pin numbers — G = 4, S = 1/2/3,
  D = 5–8, the duplicates stacked on the same pin — so Q3/Q4 map onto the
  stock SOIC-8 footprint without moving any wires.

Verified after the change: ERC 0/0; the netlist is identical net-for-net
(old references mapped, Q3/Q4 S/D pins expanded); every symbol pin has a
matching footprint pad. Every part with an LCSC number carries it in a
hidden `LCSC` field, so `kicad-cli sch export bom --fields
"Reference,Value,Footprint,LCSC"` gives an order list.

Known simplifications in this draft, worth revisiting before layout:
- BT832 VDD decoupling (C5 4.7µF + C6 100nF, as on Fanstel's eval
  board) sits left of U1 on the sheet; on the PCB both sit at U1's VDD
  pin.
- The switching stage implements the fail-on design in
  [Switching stage](#switching-stage) (Q1 driver, Q2 gate clamp, Q3 load
  switch, R_LIM, R_PD1/R_PD2, C_SS, D_Z).
- **The KiCad file is now the source of truth.** `gen_body.sh` /
  `build_sch.sh` generated the first wired draft, but the schematic has
  since been rearranged in the GUI and patched (J1 layout, reverse
  polarity protection, gridded symbols) — the generator no longer matches
  it. Don't run `build_sch.sh`: it would overwrite all of that. Kept only
  as a record of how the draft was produced.
- ADC divider (R_FB_TOP=100k, R_FB_BOT=33k) assumes sensing a ~12.6V max
  load rail scaled to a safe ADC input; revisit once the actual load
  voltage range is known.

## PCB layout

**Rev 2** (current), in [hardware/kicad/](../hardware/kicad/)
(`heimdall-switch.kicad_pcb`). Views:
[top](../hardware/kicad/layout-top.png),
[bottom](../hardware/kicad/layout-bottom.png) (mirrored, as seen from
below), 3D [top](../hardware/kicad/render-top.png) /
[bottom](../hardware/kicad/render-bottom.png). Status: DRC 0 violations,
0 unconnected, full schematic parity; reviewed by eye in the KiCad GUI.
Rev 1 (53 × 23mm, power path on top) was never ordered; it stays in git
under the tag `main-pcb-rev1`.

| Top | Bottom (mirrored, as seen from below) |
|---|---|
| ![Main board, 3D top](../hardware/kicad/render-top.png) | ![Main board, 3D bottom](../hardware/kicad/render-bottom.png) |
| ![Main board layout, top](../hardware/kicad/layout-top.png) | ![Main board layout, bottom](../hardware/kicad/layout-bottom.png) |

**Board**: 45.5 × 23mm, 2 layers, 1.6mm FR4, parts on both sides, laid
out in **zones by function**, like a high-voltage and a low-voltage side:
everything that carries or switches pack power (blocks 1–5 in the
[Schematic](#schematic) table) is on the **bottom**, the MCU and the
user interface (blocks 6–7) on the **top**.
- **Left end**: J3 (BAT) and J2 (OUT) wire pads, + and − of each pair
  3.5mm apart, wires entering from the left. The end is cut into **two
  symmetric tabs**, one per pair (mirror images about the board's
  centreline), as on the Jeti SPS-20: straight edges, 1mm corner radii,
  and each tab runs past its pads as bare board (no pour on either
  layer). Each pair gets its own heat shrink over tab, solder joints and
  wire insulation, so the shrink grips the board and the insulation, not
  the joints. "BAT"/"OUT" and "+"/"−" are on the top silkscreen.
- **Middle**: the BT832 at its native orientation, antenna over a
  **15 × 6.3mm notch** in the top edge (no board or copper under the
  antenna, as Fanstel recommends). Its left pin column (crystal, ADC, LED
  drive) faces the power end, the right column (debug, button, VDD) faces
  J1/J4.
- **Top side** (what you see, touch or plug in): U1; Y1 with C1/C2 in a
  column beside U1's crystal pins; the LED driver (Q5/Q6 with R13–R15)
  between the wire tabs and U1; LED1 and SW1 below the module; at the
  right end J1 (SWD header, top-right corner) and J4 (right-angle GH,
  cable entry flush with the right edge), with C5, C6 (VDD decoupling),
  R4 (reset pull-up) and R16 (button) in one row between them. **J1 stays
  on the top** (needed for the debug cable with the board in its case).
- **Bottom side** (power), left to right: Q4 with D1/R1 behind the BAT
  tab (reverse polarity), Q3 with R9/R10/C7/D2 behind the OUT tab (load
  switch), R11 in the corner below Q3; the switch-off chain (Q1, R5, R6,
  Q2, R7, R8) and the ADC divider bottom (R12/C8) under the module; the
  regulator chain R2/C3 → U2 (R3) → L1/C4 under J4. The board goes into a
  **3D-printed case**, so tall SMD parts on the bottom are fine; what
  must not stick out are through-hole leads: J2/J3 wires and LED1's leads
  are **trimmed flush** after soldering.
- **Silkscreen**: reference designators horizontal, right beside their
  part (left of it or above it where there's room), **0.85mm text /
  0.15mm stroke** throughout, rows of parts with their labels on one line.
  BAT/OUT 1.0mm, +/− 1.2mm. Values are on the fab layer only. Silk lines
  are clipped ≥0.15mm clear of pad mask openings and holes (so the
  footprints differ from the library: `lib_footprint_mismatch` is set to
  ignore in the project).

**Copper**:
- **Power path on the bottom as solid copper**: BATT+ pour (J3+ → Q4
  drain), the **VBAT bar** (pour joining Q4's and Q3's sources, ~7.9mm
  wide, with a no-tracks rule area across its middle so no other net cuts
  it in two), LOAD_OUT pour (Q3 drain → J2+).
- **GND**: pours on both layers, stitched. The **load return** (OUT− →
  BAT−) runs along the left end as a **top-side GND strap**: a no-tracks
  rule area (~6mm wide, past both − pads) filled by the F.Cu GND pour, so
  no signal can cut it. J2/J3's GND pads connect solid (no thermal
  relief), since they carry the load return. No GND pour around the + pads
  on the top (rule areas), so the + pad never sits next to GND copper.
- **No copper on top under the BT832 body** (rule area, tracks and pours):
  its unused LGA pads sit there and would only be separated from traces by
  solder mask.
- Only **45° corners** (no 90° bends).
- Net classes: Power 0.3mm (VBAT branches, BATT+, LOAD_OUT, GND traces),
  Reg 0.25mm (+3V3, regulator VIN, switch node; fits U2's 0.5mm pitch),
  Default 0.2mm; vias 0.6–0.7/0.3mm. Solder mask expansion 0.05mm
  (0.025mm on U2's 0.5mm-pitch pins, keeping 0.15mm webs). A custom rule
  (`heimdall-switch.kicad_dru`) allows neck-down to 0.15mm where traces
  enter fine-pitch pads (U1, U2), well inside JLCPCB's 0.127mm minimum.
- 32 vias in total, ~520mm of track (~215mm top, ~305mm bottom).

**Current capacity** (design target **5A continuous, 15A peaks <1s**).
Expected load, per servo: analog standard servos stall at ~0.8-1.2A
(4.8-6V); digital high-torque standard ~2.5-3.5A at 6V; HV high-torque
standard up to ~4-5A at 7.4-8.4V. Six digital servos all stalled at once
would be ~18-20A, which in practice doesn't happen; realistic peaks are
6-12A for 10-100ms when everything moves at once, with 2-5A continuous.
Short peaks barely heat copper; the continuous figure sets the width.
IPC-2221 (outer layer, 1oz/35µm, 20°C rise): 1.4mm for 3A, 2.5mm for 5A,
4.8mm for 10A. The power path's narrowest copper: BATT+ and LOAD_OUT
pours ~5.5mm, VBAT bar ~7.9mm, so roughly 10A continuous on 1oz; the GND
strap on top is ~6mm. Both − pads are plated through-holes, so the return
current changes layer in the pad barrels.
AO4407A: −12A continuous, −60A pulsed; at 10A its ~13mΩ is 1.3W, too
warm for SO-8 continuously, fine for the expected 2-5A (≤0.3W).
**2oz copper** (a JLCPCB option, extra cost) roughly doubles the copper
figures if long stalls are expected. **Decision: first iterations are
ordered with standard 1oz**; 2oz is an option for later boards. Before
switching, check JLCPCB's minimum trace/space for 2oz: heavier copper
usually raises it, and this layout has 0.15mm neck-downs at U1/U2's
pins and 0.2mm clearances, which may need widening. The wire pads take
0.75mm² (18AWG), good for ~10A in a harness.

**How it was made**: rev 2 was placed by script from the rev 1 board
(parts moved to their zones, power parts flipped to the bottom), the power
pours, rule areas and the critical runs (J1 ↔ U1 SWD fan-out, ADC lane,
VBAT/gate-drive runs) laid by hand-written scripts, the rest routed by
[Freerouting](https://github.com/freerouting/freerouting) 2.4, then
cleaned up (GND stitching, 90° corners turned into two 45° bends) and
finished by hand in the KiCad GUI. **The `.kicad_pcb` is the source of
truth**; `place_pcb.py`/`route_pcb.py` in `hardware/kicad/` are the rev 1
generators (coordinates of the earlier 63.5mm board) and don't produce
rev 2, so don't run them on it.

**Ordering (JLCPCB)**: `python jlc_export.py` (KiCad's python, from
`hardware/kicad/`) writes the whole order package to `gerber/`
(`python jlc_export.py ../kicad-ui` does the same for the UI board, into
`hardware/kicad-ui/gerber/`; see [Daughter board (UI)](#daughter-board-ui)):
- `heimdall-switch.zip`: Gerbers + Excellon drill (board plot settings:
  Protel extensions, mask subtracted from silk). Order options: 2 layers,
  1.6mm, **HASL with lead**, 1oz.
- BOM + CPL in JLC's format, three sets: both sides
  (`-BOM.csv`/`-CPL.csv`), **top only** (`-top`) and **bottom only**
  (`-bottom`), for one-sided "Economic" PCBA of either side if a batch is
  ever machine-assembled. The plan for now is bare boards and hand
  assembly; see [BOM](#bom).
- Parts without an LCSC number are left out (U1 BT832, J2/J3 wire pads):
  JLC can't place them, they're hand-soldered either way.
- **Rotation**: JLC reads bottom-side angles mirrored, so the script
  writes `180° − KiCad angle` for bottom parts (KiCad angle on top), plus
  a per-footprint correction (`ROT_OFFSET`) where JLC's 3D model doesn't
  share KiCad's zero angle (SOT-23 +180°, SOT-583-8 +270°). The
  corrections come from rev 1's placement preview, where D1/D2/U2/Q1/Q2
  sat on the bottom at 180°. **Check the placement preview every time**,
  and for rev 2 especially: **D1** (the first diode at 90° on the bottom;
  cathode band = pad 1 = the VBAT end, a reversed zener keeps Q4 off),
  D2, **Q3/Q4** (SO-8, on the bottom for the first time: pin 1 dot),
  U2, Q1/Q2.
- Position = centre of the part's pads (as JLC expects), Y negated.

**Check before ordering**:
- Print the BT832 footprint 1:1 and lay a module on it (drawn from a
  low-resolution datasheet drawing).
- Run JLC's DFM check on the rev 2 Gerbers (rev 1 was clean except the
  "THT to SMD" assembly rule, irrelevant for bare boards).
- Through-hole GND pads (J2/J3 pin 2, LED1 pin 1) connect solid to the
  pours (no thermal relief): use a hot iron.

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
- L1 = 2.2µH — **selected: Murata DFE252012PD-2R2M=P2** (LCSC C237482),
  from TI's tested-inductor list (datasheet Table 9-4): 1008 / 2.5×2.0×1.2mm,
  shielded, DCR 84mΩ, I_sat 2.8A (30% drop), rated 2.2A. Sizing: switch
  current limit I_LIM_HS 1.1-1.7A plus ~0.2A propagation overshoot at
  12.6V in (datasheet Eq. 2) ≈ 1.9A worst case — the inductor must not
  saturate even in overload/short. Normal operation peaks only ~0.6A
  (power-save pulses: T_ON ≈ 100ns × VIN/(VIN−VOUT), Eq. 5-6).
- Soft-start is **internal** (T_SS 600-700µs after a 1-1.8ms start-up
  delay) — no soft-start capacitor needed.
- C_out = 22µF ceramic, X7R/X5R, low ESR — **selected: Samsung
  CL21A226MAQNNNE** (22µF 25V X5R 0805, LCSC C45783); the 25V rating
  keeps DC-bias derating at 3.3V small.
- C_in: TI's reference is 4.7µF 25V 1206. **Selected: Samsung
  CL31B106KBHNNNE, 10µF 50V X7R 1206** (LCSC C89632): same
  footprint, and at 12.6V it keeps roughly 5-6µF effective, where a
  4.7µF 25V part drops to ~2µF. The 50V rating also gives headroom for
  hot-plug ringing (below).

**Hot-plug damping (R_IN, 22Ω 0603, LCSC C23345)**: plugging a pack into a
board whose input is only ceramic capacitance rings. The battery leads'
inductance and the near-zero-ESR ceramic form an undamped LC circuit, and
the first peak approaches **2× the pack voltage** (~25V on 3S; connector
bounce can repeat it). The TPS629206 is rated for 17V in. The usual fix, a
bulk electrolytic (≈47µF 25V) whose ESR damps the ring, is bigger than
this board, so instead R_IN sits between VBAT and the regulator's input
node (C_IN + VIN/EN):
- Critical damping for this LC is ~0.4Ω; 22Ω is far past it, so C_IN
  charges with no overshoot, and plug-in inrush into C_IN is capped at
  ~0.6A. Ringing on VBAT itself (now only small capacitance) is filtered
  by R_IN·C_IN (τ ≈ 110µs) before it reaches the regulator.
- The regulator's own draw is tiny (µA asleep, a few mA peak during radio
  bursts at pack voltage), so R_IN drops ≤0.1V. Its switching pulses come
  from C_IN, downstream of R_IN.
- Converter input-filter stability: |Z_in| of the buck at these loads is
  ≥1kΩ (V_IN² / P_IN), orders of magnitude above R_IN.
- The rest of VBAT tolerates the ring: Q3/Q4 (AO4407A) and Q1/Q5
  (AO3400A, via 1MΩ) are 30V parts, Q2/Q6 (BSS84) 50V, Q3/Q4 gates are
  zener-clamped, and Q6's gate sits at V_GS ≈ 0 at plug-in (LED off).
  The load path through Q3 doesn't go through R_IN.
- **Verify on the first boards**: scope VBAT and U2 VIN while plugging in
  a full 3S pack a few times.

**Superseded**: an earlier pass at this section spec'd the TPS62901 (same
family, VQFN-HR package) with a classic-mode R1/R2 divider (402k/100k for
3.0V, 453k/100k for 3.3V) computed from that part's equation. Kept here
for reference only in case the VSET-preset approach above doesn't pan out
during bring-up and a fallback to classic external-divider mode is needed
— the same R1/R2 math applies to the TPS629206 too (also VFB = 0.6V).

## Assembly

- **PCBs**: bare boards from JLCPCB, surface finish **HASL with lead**
  (pre-tinned with leaded solder, matches the hand-assembly solder).
- **Parts**: from LCSC (ships with the JLCPCB order), except the BT832
  and J4 (Mouser, see [BOM](#bom)), preferring JLCPCB
  "basic" parts where that doesn't compromise the design — keeps JLCPCB
  assembly possible for a later batch.
- **Hand assembly**: hot-air station + Sn63/Pb37 leaded paste for SMD,
  soldering iron (60/40) for the BT832's castellated edges and connectors.
  **No 0402** — passives 0603, 0805 where voltage/capacitance needs it.
  No-lead packages (DFN, SOT-5X3) are fine with hot air.
- **Battery in (J3) / load out (J2): solder pads, not connectors.** Wire
  pigtails soldered to the board, with whatever plug the vehicle needs on
  the end (JR/Futaba, XT30, …) — the same approach as the Jeti SPS-20, and
  the most vibration-proof option (no board-mounted connector to rattle
  loose or lever the joints). Footprint: KiCad
  `heimdall-switch:SolderWire-0.75sqmm_1x02_P3.5mm_D1.25mm_OD2.3mm`
  (KiCad's `Connector_Wire` P4.8mm footprint with the pads moved to
  3.5mm, so a pair sits side by side under one heat shrink)
  — through-hole pads (1.6mm drill) for 0.75mm² (≈18 AWG) wire, which
  carries 3A continuous / 6-8A peaks comfortably and also accepts 20-22
  AWG. Strain relief is heat shrink: the slot between the battery and
  load pairs makes two 7.3mm-wide tabs reaching 4mm past the pads, and
  a piece of heat shrink (~9-10mm, adhesive-lined is best) over each tab,
  its two solder joints and the first few mm of insulation keeps flexing
  off the joints (SPS-20 style).
  This replaced the "Relief" footprint variant (wire looped through
  extra holes), which cost ~14mm of board length.
- **Clean the board** (IPA, brush) after assembly, especially around the
  switching stage. R_PD1/R_PD2 (2.2MΩ) and R_CLAMP_PU (1MΩ) set the
  fail-on margin at a few µA, and flux residue plus humidity (boat use)
  can create leakage paths in the MΩ range. Conformal coating after
  bring-up is worth considering for the same reason.

## BOM

Schematic references (the descriptive names used elsewhere on this page are
in brackets; see [Schematic](#schematic) for the mapping). Every part with
an LCSC number carries it in the schematic's `LCSC` field, so the KiCad BOM
export and `jlc_export.py` (see [PCB layout](#pcb-layout)) produce the
order lists. Side: **T** top, **B** bottom (rev 2). "Basic" = JLCPCB basic
part (only matters if a batch is ever JLC-assembled). Resistors are
UNI-ROYAL 0603WAF thick film 1% unless noted. Stock and prices checked
**2026-10-03**.

**Main board** (42 parts; 39 from LCSC, U1 from Mouser, J2/J3 are wire pads):

| Ref | Value | Part | Package | Side | Source | Basic |
|---|---|---|---|---|---|---|
| U1 | BT832 (nRF52832) | Fanstel BT832 | 14 × 16mm module | T | [Mouser](https://www.mouser.com/ProductDetail/Fanstel/BT832?qs=wUXugUrL1qzkqriNuICYIQ%3D%3D) | |
| U2 | 3.3V buck | TI TPS629206DRLR | SOT-583-8 | B | [LCSC C5219292](https://www.lcsc.com/product-detail/C5219292.html) | |
| L1 | 2.2µH | Murata DFE252012PD-2R2M=P2 | 1008 | B | [LCSC C237482](https://www.lcsc.com/product-detail/C237482.html) | |
| Q1, Q5 | N-FET | AOS AO3400A | SOT-23 | B, T | [LCSC C20917](https://www.lcsc.com/product-detail/C20917.html) | ✓ |
| Q2, Q6 | P-FET | Nexperia BSS84,215 | SOT-23 | B, T | [LCSC C493579](https://www.lcsc.com/product-detail/C493579.html) | |
| Q3, Q4 | P-FET | AOS AO4407A | SO-8 | B | [LCSC C16072](https://www.lcsc.com/product-detail/C16072.html) | |
| D1, D2 (D_Z2, D_Z) | 18V zener | JSCJ MMSZ5248B | SOD-123 | B | [LCSC C2127](https://www.lcsc.com/product-detail/C2127.html) | |
| Y1 | 32.768kHz, CL 12.5pF | Epson FC-135 (Q13FC13500004) | 3215 | T | [LCSC C32346](https://www.lcsc.com/product-detail/C32346.html) | ✓ |
| C1, C2 | 18pF 50V C0G | Samsung CL10C180JB8NNNC | 0603 | T | [LCSC C1647](https://www.lcsc.com/product-detail/C1647.html) | ✓ |
| C3 (C_IN) | 10µF 50V X7R | Samsung CL31B106KBHNNNE | 1206 | B | [LCSC C89632](https://www.lcsc.com/product-detail/C89632.html) | |
| C4 (C_OUT) | 22µF 25V X5R | Samsung CL21A226MAQNNNE | 0805 | B | [LCSC C45783](https://www.lcsc.com/product-detail/C45783.html) | ✓ |
| C5 (C_VDD1) | 4.7µF 16V X5R | Samsung CL10A475KO8NNNC | 0603 | T | [LCSC C19666](https://www.lcsc.com/product-detail/C19666.html) | ✓ |
| C6, C8 (C_VDD2, C_FB) | 100nF 50V X7R | Yageo CC0603KRX7R9BB104 | 0603 | T, B | [LCSC C14663](https://www.lcsc.com/product-detail/C14663.html) | ✓ |
| C7 (C_SS) | 220nF 50V X7R | Samsung CL21B224KBFNNNE | 0805 | B | [LCSC C5378](https://www.lcsc.com/product-detail/C5378.html) | ✓ |
| R1, R11 (R_REV, R_FB_TOP) | 100kΩ | 0603WAF1003T5E | 0603 | B | [LCSC C25803](https://www.lcsc.com/product-detail/C25803.html) | ✓ |
| R2 (R_IN) | 22Ω | 0603WAF220JT5E | 0603 | B | [LCSC C23345](https://www.lcsc.com/product-detail/C23345.html) | ✓ |
| R3 (R_MODE) | 27.4kΩ | 0603WAF2742T5E | 0603 | B | [LCSC C22964](https://www.lcsc.com/product-detail/C22964.html) | |
| R4 (R_RST) | 10kΩ | Yageo RC0603FR-0710KL | 0603 | T | [LCSC C98220](https://www.lcsc.com/product-detail/C98220.html) | ✓ |
| R5, R8 (R_G1, R_LIM) | 100Ω | 0603WAF1000T5E | 0603 | B | [LCSC C22775](https://www.lcsc.com/product-detail/C22775.html) | ✓ |
| R6, R7, R13, R15 (R_OFF_PD, R_CLAMP_PU, R_Q6_PU, R_LED_PD) | 1MΩ | 0603WAF1004T5E | 0603 | B, B, T, T | [LCSC C22935](https://www.lcsc.com/product-detail/C22935.html) | ✓ |
| R9, R10 (R_PD1, R_PD2) | 2.2MΩ | 0603WAF2204T5E | 0603 | B | [LCSC C22938](https://www.lcsc.com/product-detail/C22938.html) | |
| R12 (R_FB_BOT) | 33kΩ | 0603WAF3302T5E | 0603 | B | [LCSC C4216](https://www.lcsc.com/product-detail/C4216.html) | ✓ |
| R14 (R_LED) | 680Ω 1/4W | 1206W4F6800T5E | 1206 | T | [LCSC C17975](https://www.lcsc.com/product-detail/C17975.html) | |
| R16 (R_BTN) | 1kΩ | 0603WAF1001T5E | 0603 | T | [LCSC C21190](https://www.lcsc.com/product-detail/C21190.html) | ✓ |
| LED1 | green 525nm, 3.2cd, 20° | Everlight 204-10SUGC/S400-A4 | 3mm THT, water clear | T | [LCSC C414645](https://www.lcsc.com/product-detail/C414645.html) | |
| SW1 | tactile | C&K PTS810 SJM 250 SMTR LFS | 4.2 × 3.2mm SMD | T | [LCSC C116501](https://www.lcsc.com/product-detail/C116501.html) | |
| J1 | ARM 10-pin SWD | hanxia HX PZ1.27-2x5P TP | 2×5 1.27mm SMD | T | [LCSC C41376037](https://www.lcsc.com/product-detail/C41376037.html) | |
| J4 | UI breakout | JST SM03B-GHS-TB(LF)(SN) | GH 1×3 1.25mm SMD right-angle | T | [Mouser](https://www.mouser.com/c/?q=SM03B-GHS-TB(LF)(SN)) (LCSC [C514175](https://www.lcsc.com/product-detail/C514175.html): 0 in stock) | |
| J2, J3 | wire pads | see [Assembly](#assembly) | THT pads | — | — | |

**UI daughter board** (see [Daughter board (UI)](#daughter-board-ui)):

| Ref | Value | Part | Package | Side | Source |
|---|---|---|---|---|---|
| LED1 | green 3mm | Everlight 204-10SUGC/S400-A4 | 3mm THT | front | [LCSC C414645](https://www.lcsc.com/product-detail/C414645.html) |
| SW1 | tactile, IP67, 3.4N | C&K KSC641J LFS | 6.2 × 6.2mm SMD | front | [LCSC C226344](https://www.lcsc.com/product-detail/C226344.html) |
| J1 | UI cable | JST BM03B-GHS-TBT(LF)(SN) | GH 1×3 1.25mm SMD vertical | back | [LCSC C161691](https://www.lcsc.com/product-detail/C161691.html) / [Mouser](https://www.mouser.com/ProductDetail/JST-Commercial/BM03B-GHS-TBTLFSN?qs=cdbOS8ANM9Du45wKC780vQ%3D%3D) |

**UI cable** (J4 ↔ UI J1, pin 1 ↔ pin 1), per cable:

| Qty | Part | Source |
|---|---|---|
| 2 | JST GHR-03V-S housing, GH 3-pin | [LCSC C160417](https://www.lcsc.com/product-detail/C160417.html) (only 20 in stock; also at Mouser/DigiKey) |
| 6 | JST SSHL-002T-P0.2 crimp contact, 26-30 AWG | [LCSC C189897](https://www.lcsc.com/product-detail/C189897.html) |
| 3 | 26-28 AWG wire, to length | — |

GH crimps need a fine crimp tool (or buy ready-made GH 3-pin
"pre-crimped" leads, often sold for drones/Pixhawk; check pin 1 ↔ pin 1).

Notes:
- **R3 (R_MODE) must be exactly 27.4kΩ (E96)**: it selects the TPS629206's
  mode by resistor window, so a 27kΩ E24 substitute is not safe.
- **U1: plain BT832, not BT832-P / newer nRF52832 revisions with locked
  APPROTECT**: those lock the debug port unless the firmware keeps it
  open (needs a recent SDK); the plain module is easier for prototypes.
  Fanstel's own store sells in 1000s; Mouser stocks single modules.
- **LED1: 3mm green, high intensity, narrow beam** for sunlight
  visibility through a 3mm hole in the hull (see Status LED above for the
  VBAT drive and currents). Chosen over Hubei KENTO 3AG2HD (C2843819,
  2-3cd, 23°) for the higher intensity and Everlight datasheet quality;
  the -A5 variant (C2927624) is the same die with a 30° beam if 20° turns
  out too narrow to see off-axis. It only blinks on events, so its current
  doesn't show in the power budget.
- **SW1 (main board)**: C&K PTS810 SJM 250 SMTR LFS, 4.2 × 3.2mm
  J-lead tactile (KiCad `Button_Switch_SMD:SW_SPST_PTS810` matches
  exactly). The on-board button sits inside the hull, so it needn't be
  sealed, and the KSC641J's 6.2mm body was too big for the main board.
  Alps SKRPACE010 (C139797) is the same size/package if stock runs out
  (check its land pattern against the PTS810 footprint).
- **SW1 (daughter board)**: C&K KSC641J — IP67 sealed tactile switch,
  J-lead (easy to solder by hand), 3.4N actuation (firm enough to resist
  vibration presses), for the outside housing. KiCad's stock
  `Button_Switch_SMD:SW_Push_1P1T_NO_CK_KSC6xxJ` footprint matches it
  exactly.
- **J4 / UI J1**: both JST GH 1.25mm, the main board's right-angle (cable
  leaves along the board), the UI board's vertical (cable leaves straight
  back through the housing).

### Cost estimate (prototype run)

For **10 main boards + 5 UI boards + 5 cables**, prices 2026-10-03,
excl. VAT, ~9.5 SEK/USD. LCSC sells most passives in reels/strips of
50–100 minimum, so the order costs more than 10× the per-board figure.

| Item | Where | Order | ≈ SEK |
|---|---|---|---|
| BT832 × 10 | Mouser | ~$10 each; 10 pcs + shipping quoted at 996 SEK | ~1000 |
| J4 SM03B-GHS-TB × 10 | Mouser (not in stock at LCSC) | ~$0.8 each | ~80 |
| Main-board parts × 10 (rest of the BOM) | LCSC | $40.7 (min-order quantities included; $3.4/board at those prices) | ~390 |
| UI-board parts × 5 | LCSC | $5.2 | ~50 |
| Cable parts × 5 | LCSC | $2.1 | ~20 |
| Main PCB × 10 (45.5 × 23mm, 2L, 1.6mm, leaded HASL) | JLCPCB | estimate, get a quote | ~50–100 |
| UI PCB × 5 (35 × 13mm, 2L, **2.0mm**) | JLCPCB | estimate, get a quote (2.0mm adds cost) | ~50–100 |
| Shipping LCSC + JLCPCB (combined) | | estimate | ~150–250 |
| **Total** | | | **~1800–2000** |

Per finished main board that's **~150–170 SEK** in parts, PCB and a share
of the shipping at this quantity, about **100 SEK of it the BT832**. For comparison, a Jeti SPS-20
is around $60. Mouser ships free above 800 SEK, so the BT832 order covers
J4 too; other parts for the suite (e.g. an ESP32-C3 for heimdall-module)
can ride along on the same order.

## Daughter board (UI)

Separate KiCad project in [hardware/kicad-ui/](../hardware/kicad-ui/)
(`heimdall-switch-ui.kicad_pro/.kicad_sch/.kicad_pcb`, rendered
[schematic](../hardware/kicad-ui/heimdall-switch-ui.svg),
[top](../hardware/kicad-ui/render-top.png) and
[bottom](../hardware/kicad-ui/render-bottom.png) views). Use it when the
LED and button need to sit away from the main board, e.g. in a housing
on the outside of the hull, as on the Jeti SPS-20.

| Front | Back |
|---|---|
| ![UI board, front](../hardware/kicad-ui/render-top.png) | ![UI board, back](../hardware/kicad-ui/render-bottom.png) |

- **Parts**: LED1 (Everlight 204-10SUGC, 3mm green), SW1 (C&K KSC641J),
  J1 (JST BM03B-GHS-TBT, vertical SMD GH, the same series as the main
  board's right-angle J4), H1/H2 (tapped M3 holes, not parts). LED and
  button are the same part numbers as the main board's on-board ones;
  nothing else, since the
  LED driver, current limit and button ESD resistor live on the main
  board.
- **Cable**: 3-wire JST-GH (GHR-03V-S housings, SSHL-002T-P0.2
  contacts, see [BOM](#bom)), crimped to length, pin 1 ↔ pin 1 (1 LED_A,
  2 BTN, 3 GND).
- **Board**: 35 × 13mm, **2.0mm FR4** (order option at JLCPCB; the main
  board stays 1.6mm), 2 layers, two **tapped M3 holes** (H1/H2): 2.5mm
  tap drill, 28.5mm apart on the board's centreline, H1 3.2mm from the
  left edge. The board itself is tapped M3 and the screws come in from
  the housing, so no head/washer/nut clearance is needed on the board,
  only ~2mm around the thread (project-local footprint
  `heimdall-switch-ui:MountingHole_2.5mm_M3_Tapped`). 2.0mm FR4 holds 4
  threads (0.5mm pitch; 1.6mm would give ~3) and is stiffer under button
  presses: fine for clamping a light board, don't over-tighten. Worn
  threads: drill to 3.2mm and use screw + nut. From H1:
  button centre +6.8mm, LED centre +15.6mm, all on the centreline. LED
  and button on the front, facing out; the GH header is mounted on the
  **back** (SMD, so nothing comes through to the front), so the cable
  leaves straight backwards. J1's pin row runs along the board (body
  117.4–124.5mm from the left edge, ≥2mm clear of H2's hole) so it
  doesn't crowd the screw. Back silk carries the board name; the cable
  is pin 1 ↔ pin 1.
- **Mounting**: in a 3D-printed housing screwed to the **outside** of the
  hull (like the SPS-20's), the LED protruding through the housing and
  the button sealed with an O-ring, so the only hull penetration is the
  cable hole. The KSC641J is IP67 itself, so a leaking O-ring doesn't
  kill the button.
- Verified: ERC 0/0; DRC 0 violations, 0 unconnected, full schematic
  parity (`kicad-cli pcb drc --schematic-parity`).
- **Ordering**: `python jlc_export.py ../kicad-ui` (from
  `hardware/kicad/`) writes `hardware/kicad-ui/gerber/`: Gerber + drill
  zip and BOM/CPL (all, `-top`, `-bottom`), same format as the main
  board. Select **2.0mm** thickness on the JLCPCB order form (the Gerbers
  don't carry it). If it's ever assembled: SW1 is SMD on the front, J1
  SMD on the back (two "Economic" sides), LED1 is through-hole (hand
  solder, or JLC's Standard PCBA); J1/SW1 have no rotation corrections
  yet, so check the placement preview.
- `gen_ui.sh` generated the first version (schematic + routed PCB, with
  KiCad's Python API flipping J1 to the back), with the XH header that
  has since been swapped for the GH; don't re-run it. As with the main
  board, the KiCad files are the source of truth.

## Open items

- Real hardware not yet built — wake interval, scan window length, and BLE
  advertising interval (see [protocol.md](protocol.md)) are all first
  estimates, not measured.
- **Component selection, annotation and footprints: done** (see
  [BOM](#bom) and [Schematic](#schematic)). **Main board rev 2 layout:
  done and reviewed** (see [PCB layout](#pcb-layout)). Before ordering:
  BT832 footprint print-out check, JLC DFM check on the rev 2 Gerbers,
  a JLCPCB quote (see [Cost estimate](#cost-estimate-prototype-run)).
- **Y1/C1/C2**: kept in the design; fitted or not is decided at
  assembly. Firmware supports both clock sources (see LFCLK note above).
- Power budget is estimated, not measured.
