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
| 11 | P0.13 | Output OFF-hold (high = output OFF, released = ON) |
| 12 | P0.18 | Spare GPIO |
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
  justify on power alone. Currently in the schematic (Y1/C1/C2); the
  keep / leave unfitted (DNP) / remove decision is open. Leaving it
  unfitted needs no hardware change, only the firmware's clock-source
  config.
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
- **SWD header J1** (5-pin, no universal standard for this count — order
  chosen to follow the BT832's pin order so the signals route without
  crossings):

  | J1 pin | Signal | BT832 pin |
  |---|---|---|
  | 1 | +3V3 (VTref) | 9 (VDD) |
  | 2 | GND | 10 |
  | 3 | nRESET (10k pull-up R_RST to +3V3) | 14 (P0.21/RESET) |
  | 4 | SWDCLK | 15 |
  | 5 | SWDIO | 16 |

  Pin 1 is a **voltage reference for the probe, not a power input** — power
  the board from its battery while flashing. A probe set to *supply*
  3.3V with no battery connected back-feeds through the buck onto VBAT,
  and with fail-on Q3 then puts ~3V on the load output.
- 5 spare GPIOs remain (2, 6, 7, 8, 12) if anything else comes up.
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
- **Gate protection**: D_Z, 15V zener gate-source on Q3 (cathode to VBAT).
  At 12.6V max a ±20V-rated gate is within spec without it; it's cheap
  insurance against transients.

**Reverse polarity protection**: servo-style RC plugs are easy to insert
backwards, and a reversed pack would destroy not just this node but the
load — Q3's body diode would conduct and put reversed voltage across the
receiver/servos. So the protection covers the whole power path, right at
the battery input:
- **Q4**: P-FET "ideal diode" in the positive line between J3 and the VBAT
  rail — drain to the battery (+) pin of J3, source to VBAT, gate to GND
  via R_REV (100kΩ), plus a 15V gate-source zener (D_Z2, cathode to
  source) like Q3's. **Same part as Q3: AO4407A** (SO-8, LCSC C16072).
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

A first-draft KiCad schematic implementing everything on this page lives in
[hardware/kicad/](../hardware/kicad/) (`heimdall-switch.kicad_pro` +
`.kicad_sch`), with a rendered [heimdall-switch.svg](../hardware/kicad/heimdall-switch.svg)
for quick viewing without opening KiCad. Custom symbols for the BT832 and
TPS629206 (neither has an official KiCad library part) live in
`heimdall-switch.kicad_sym`; opening the project should resolve them
automatically via the project-local `sym-lib-table`.

Drawn with real wires within each block (regulator, MCU + crystal/LED/
button/SWD, switching stage + load output), KiCad power symbols (`GND`,
`+3V3`, `VBAT` — the latter is the stock `+BATT` symbol renamed) with
PWR_FLAGs, and no-connect markers on the intentionally-open pins
(VSET/PG, spare GPIOs). Only two signals cross between blocks as net
labels: `OUT_OFF` (P0.13 → switching stage) and `ADC_FB` (divider →
P0.02). J3 is the battery input connector.

Verified with `kicad-cli sch erc`, netlist export (every pin checked
against the intended net) and `sch export svg` (kicad-cli is installed
but not on PATH — `AppData/Local/Programs/KiCad/10.0/bin/`). ERC: **0
errors, 0 warnings**. All custom-symbol pins (BT832, TPS629206) sit on
the 2.54mm grid — keep it that way when editing `heimdall-switch.kicad_sym`:
an off-grid pin makes GUI-drawn wires snap past it and silently not
connect (this happened once, to SWDCLK/SWDIO).

Sheet layout: the reverse polarity block (J3 → Q4 → VBAT, with D_Z2 and
R_REV) sits on its own below the regulator and connects to it through the
`VBAT` power symbol; J3's pin 1 net is labelled `BATT+`. SWDCLK/SWDIO are
routed nested below the nRESET path so no wires cross.

Reading the schematic:
- **Power symbols** (`VBAT` arrow, `+3V3` arrow, `GND`) connect by name
  across the whole sheet — two `VBAT` arrows are the same net even with no
  wire between them.
- **PWR_FLAG** (small diamond, text hidden) is not a component and not in
  the BOM. It tells ERC "this net is powered from outside" — needed where
  power arrives through pins KiCad sees as passive (battery connector, Q4,
  L1). One each on VBAT (at Q4), GND (at J3) and +3V3 (at C_OUT).
- A few GND symbols have their "GND" text hidden where it collided with
  wires (U2 pin 5, LED1 cathode, SW1) — they're ordinary GND connections.

Known simplifications in this draft, worth revisiting before layout:
- No footprints assigned yet (schematic-only pass).
- No decoupling cap at the BT832's VDD pin — check the module datasheet
  for whether onboard decoupling is sufficient.
- The switching stage implements the fail-on design in
  [Switching stage](#switching-stage) (Q1 driver, Q2 gate clamp, Q3 load
  switch, R_LIM, R_PD1/R_PD2, C_SS, D_Z). All four FETs are selected
  (Q1 AO3400A, Q2 BSS84, Q3/Q4 AO4407A) on generic FET symbols —
  footprints not yet assigned.
- **The KiCad file is now the source of truth.** `gen_body.sh` /
  `build_sch.sh` generated the first wired draft, but the schematic has
  since been rearranged in the GUI and patched (J1 layout, reverse
  polarity protection, gridded symbols) — the generator no longer matches
  it. Don't run `build_sch.sh`: it would overwrite all of that. Kept only
  as a record of how the draft was produced.
- ADC divider (R_FB_TOP=100k, R_FB_BOT=33k) assumes sensing a ~12.6V max
  load rail scaled to a safe ADC input; revisit once the actual load
  voltage range is known.
- **Not annotated**: references are descriptive names (`R_PD1`, `C_SS`,
  `D_Z2`…) which KiCad treats as unannotated (`R_PD1?` in a BOM). Run
  Tools → Annotate Schematic before PCB work; the names in these docs will
  then need a mapping to the new references.

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

## Assembly

- **PCBs**: bare boards from JLCPCB, surface finish **HASL with lead**
  (pre-tinned with leaded solder, matches the hand-assembly solder).
- **Parts**: from LCSC (ships with the JLCPCB order), preferring JLCPCB
  "basic" parts where that doesn't compromise the design — keeps JLCPCB
  assembly possible for a later batch.
- **Hand assembly**: hot-air station + Sn63/Pb37 leaded paste for SMD,
  soldering iron (60/40) for the BT832's castellated edges and connectors.
  **No 0402** — passives 0603, 0805 where voltage/capacitance needs it.
  No-lead packages (DFN, SOT-5X3) are fine with hot air.

## Open items

- Real hardware not yet built — wake interval, scan window length, and BLE
  advertising interval (see [protocol.md](protocol.md)) are all first
  estimates, not measured.
- **Component selection** (next step) — values are fixed, part numbers
  and footprints are not:
  - ~~Q3, Q4~~: **done — AO4407A** (LCSC C16072), see Switching stage
  - ~~Q1, Q2~~: **done — AO3400A** (C20917) / **Nexperia BSS84**
    (C493579), plus R_LIM 100Ω added; see Switching stage
  - L1: 2.2µH shielded, I_sat ≈ 1A or more
  - J2, J3: must carry 6-8A peaks (JST-XH at 3A is too small; XT30 or
    soldered leads)
  - SW1: sealed tactile switch (boat use)
  - Y1: only if kept — match C1/C2 to its load capacitance (12pF assumes a
    9pF-CL crystal)
  - Capacitor voltage ratings / dielectrics, LED colour
- **BT832 decoupling**: add 4.7µF + 100nF at VDD (Fanstel's eval board has
  them) — not yet in the schematic.
- **Y1/C1/C2**: keep, leave unfitted, or remove (see LFCLK note above).
- Power budget is estimated, not measured.
- TPS629206 soft-start behavior/capacitor (if any is needed) not yet
  checked against the datasheet — carried over from the TPS62901
  investigation, never resolved for either part.
