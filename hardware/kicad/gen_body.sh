#!/usr/bin/env bash
# Emits the body (symbol instances, wires, junctions, labels, power symbols)
# of heimdall-switch.kicad_sch to stdout. Run via build_sch.sh, which wraps
# it with the header and embedded lib_symbols.
#
# Coordinates are schematic mm (y grows downward). Pin positions per symbol
# are documented at each emitter; wires below are hand-placed to land
# exactly on those pin endpoints.
set -euo pipefail

# Root sheet uuid (the schematic's top-level uuid), passed in by build_sch.sh
ROOT_UUID="${ROOT_UUID:?set ROOT_UUID to the schematic uuid}"

gen_uuid() {
  local h
  h=$(od -An -N16 -tx1 /dev/urandom | tr -d ' \n')
  printf '%s-%s-4%s-%x%s-%s' \
    "${h:0:8}" "${h:8:4}" "${h:13:3}" \
    $(( (0x${h:16:1} & 0x3) | 0x8 )) "${h:17:3}" "${h:20:12}"
}

calc() { awk "BEGIN{print $1}"; }

# ---- primitives ----

# wire X1 Y1 X2 Y2
wire() {
  printf '\t(wire (pts (xy %s %s) (xy %s %s))\n\t\t(stroke (width 0) (type default))\n\t\t(uuid "%s")\n\t)\n' \
    "$1" "$2" "$3" "$4" "$(gen_uuid)"
}

# junction X Y
junction() {
  printf '\t(junction (at %s %s) (diameter 0) (color 0 0 0 0)\n\t\t(uuid "%s")\n\t)\n' "$1" "$2" "$(gen_uuid)"
}

# noconn X Y
noconn() {
  printf '\t(no_connect (at %s %s) (uuid "%s"))\n' "$1" "$2" "$(gen_uuid)"
}

# label NAME X Y [ANGLE]  (angle 180 = text extends to the left)
label() {
  local name="$1" x="$2" y="$3" ang="${4:-0}" just="left bottom"
  [ "$ang" = 180 ] && just="right bottom"
  printf '\t(label "%s"\n\t\t(at %s %s %s)\n\t\t(effects (font (size 1.27 1.27)) (justify %s))\n\t\t(uuid "%s")\n\t)\n' \
    "$name" "$x" "$y" "$ang" "$just" "$(gen_uuid)"
}

# pwr LIBNAME VALUE X Y [ROT]  — power symbol / PWR_FLAG, pin at (X,Y).
# Unrotated: GND points down, +3V3/+BATT/PWR_FLAG point up.
PWR_N=0
FLG_N=0
pwr() {
  local lib="$1" value="$2" x="$3" y="$4" rot="${5:-0}" ref vx vy
  if [ "$lib" = PWR_FLAG ]; then FLG_N=$((FLG_N+1)); ref=$(printf '#FLG%02d' $FLG_N)
  else PWR_N=$((PWR_N+1)); ref=$(printf '#PWR%02d' $PWR_N); fi
  # value text: beyond the symbol's tip, in the direction it points
  local d=4.5
  [ "$lib" = GND ] && d=-4.5
  case "$rot" in
    0)   vx=$x; vy=$(calc "$y-($d)") ;;
    180) vx=$x; vy=$(calc "$y+($d)") ;;
    90)  vx=$(calc "$x-($d)"); vy=$y ;;
    270) vx=$(calc "$x+($d)"); vy=$y ;;
  esac
  printf '\t(symbol (lib_id "power:%s") (at %s %s %s) (unit 1)\n\t\t(exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)\n\t\t(uuid "%s")\n' \
    "$lib" "$x" "$y" "$rot" "$(gen_uuid)"
  printf '\t\t(property "Reference" "%s" (at %s %s 0) (effects (font (size 1.27 1.27)) (hide yes)))\n' "$ref" "$x" "$y"
  printf '\t\t(property "Value" "%s" (at %s %s 0) (effects (font (size 1.27 1.27))))\n' "$value" "$vx" "$vy"
  printf '\t\t(property "Footprint" "" (at %s %s 0) (effects (font (size 1.27 1.27)) (hide yes)))\n' "$x" "$y"
  printf '\t\t(property "Datasheet" "" (at %s %s 0) (effects (font (size 1.27 1.27)) (hide yes)))\n' "$x" "$y"
  printf '\t\t(pin "1" (uuid "%s"))\n' "$(gen_uuid)"
  instances "$ref"
  printf '\t)\n'
}

# Annotation record for a symbol on the root sheet. Without it KiCad can't
# name nets made of plain wires between pins, and drops them.
instances() {
  printf '\t\t(instances (project "heimdall-switch" (path "/%s" (reference "%s") (unit 1))))\n' "$ROOT_UUID" "$1"
}

# part LIBID REF VALUE X Y ROT MIRROR PIN...  (MIRROR: "", x or y)
# ROT is KiCad's CCW-on-screen angle. Ref/value text goes 6mm below/above.
part() {
  local libid="$1" ref="$2" value="$3" x="$4" y="$5" rot="$6" mir="$7"
  shift 7
  local m=""
  [ -n "$mir" ] && m=" (mirror $mir)"
  printf '\t(symbol (lib_id "%s") (at %s %s %s)%s (unit 1)\n\t\t(exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)\n\t\t(uuid "%s")\n' \
    "$libid" "$x" "$y" "$rot" "$m" "$(gen_uuid)"
  printf '\t\t(property "Reference" "%s" (at %s %s 0) (effects (font (size 1.27 1.27))))\n' "$ref" "$(calc "$x+3")" "$(calc "$y+5")"
  printf '\t\t(property "Value" "%s" (at %s %s 0) (effects (font (size 1.27 1.27))))\n' "$value" "$(calc "$x+3")" "$(calc "$y-5")"
  printf '\t\t(property "Footprint" "" (at %s %s 0) (effects (font (size 1.27 1.27)) (hide yes)))\n' "$x" "$y"
  printf '\t\t(property "Datasheet" "" (at %s %s 0) (effects (font (size 1.27 1.27)) (hide yes)))\n' "$x" "$y"
  local p
  for p in "$@"; do printf '\t\t(pin "%s" (uuid "%s"))\n' "$p" "$(gen_uuid)"; done
  instances "$ref"
  printf '\t)\n'
}

# ---- pin geometry (schematic coords, relative to part origin) ----
# Device:R / C / L, rot 0:   pin1 (0,-3.81) top, pin2 (0,+3.81) bottom
#                   rot 90:  pins at (-3.81,0) and (+3.81,0)
# Device:Crystal / LED / D_Zener, rot 0: pin1 (-3.81,0) left, pin2 (+3.81,0) right
#   (LED: pin1=K pin2=A; D_Zener: pin1=K pin2=A)
#   rot 90: pin1 bottom (0,+3.81), pin2 top;  rot 180: pin1 right, pin2 left;
#   rot 270: pin1 top (0,-3.81), pin2 bottom
# Switch:SW_Push: pin1 (-5.08,0), pin2 (+5.08,0)
# Q_NMOS_GSD / Q_PMOS_GSD: G (-5.08,0); unmirrored D (2.54,-5.08) top,
#   S (2.54,+5.08) bottom; (mirror x) swaps them: S top, D bottom
# Conn_01x02: pin1 (-5.08,0), pin2 (-5.08,+2.54); (mirror y) → x = +5.08
# Conn_01x05: pin n at (-5.08, -5.08 + 2.54*(n-1))
# heimdall-switch:BT832: VDD (-15.08,-10), GND (-15.08,+10); right side at
#   x=+15.08: P1 -17.78, P2 -15.24, P3 -12.7, P4 -10.16, P5 -7.62, P6 -5.08,
#   P7 -2.54, P8 0, P11 +2.54, P12 +5.08, P13 +7.62, P14 +10.16,
#   P15 +12.7, P16 +15.24
# heimdall-switch:TPS629206: left x=-15.08: VIN -7.62, EN -2.54, GND +2.54,
#   MODE +7.62; right x=+15.08: SW -7.62, VOS -2.54, FB/VSET +2.54, PG +7.62

echo "	;; ================= Power input & regulator ================="
# J3 battery input, pins facing right: pin1 VBAT (33.02,48.26), pin2 GND (33.02,50.8)
part "Connector_Generic:Conn_01x02" J3 "BATT_IN" 27.94 48.26 0 y 1 2
pwr "+BATT" VBAT 33.02 48.26
# VBAT rail → C_IN → EN/VIN
wire 33.02 48.26 45.72 48.26
wire 45.72 48.26 71.12 48.26
wire 71.12 48.26 76.36 48.26
wire 71.12 48.26 71.12 53.34
wire 71.12 53.34 76.36 53.34
junction 45.72 48.26
junction 71.12 48.26
pwr PWR_FLAG PWR_FLAG 45.72 48.26
part "Device:C" C_IN "4.7uF 25V" 45.72 52.07 0 "" 1 2
pwr GND GND 45.72 55.88
# Battery GND + flag
wire 33.02 50.8 38.1 50.8
wire 38.1 50.8 38.1 55.88
wire 38.1 55.88 38.1 58.42
pwr PWR_FLAG PWR_FLAG 38.1 55.88 270
pwr GND GND 38.1 58.42

# U2 at (91.44,55.88): VIN (76.36,48.26) EN (76.36,53.34) GND (76.36,58.42)
# MODE (76.36,63.5) SW (106.52,48.26) VOS (106.52,53.34) FB (106.52,58.42) PG (106.52,63.5)
part "heimdall-switch:TPS629206" U2 "TPS629206" 91.44 55.88 0 "" 6 7 5 8 4 3 1 2
wire 76.36 58.42 73.66 58.42
pwr GND GND 73.66 58.42
wire 76.36 63.5 66.04 63.5
part "Device:R" R_MODE "27.4k" 66.04 67.31 0 "" 1 2
pwr GND GND 66.04 71.12
noconn 106.52 58.42
noconn 106.52 63.5
# SW → L1 → +3V3, VOS sensing the output
wire 106.52 48.26 114.3 48.26
part "Device:L" L1 "2.2uH" 114.3 52.07 0 "" 1 2
wire 106.52 53.34 109.22 53.34
wire 109.22 53.34 109.22 55.88
wire 109.22 55.88 114.3 55.88
wire 114.3 55.88 124.46 55.88
junction 114.3 55.88
part "Device:C" C_OUT "22uF" 124.46 59.69 0 "" 1 2
pwr GND GND 124.46 63.5
wire 124.46 55.88 132.08 55.88
junction 124.46 55.88
pwr PWR_FLAG PWR_FLAG 124.46 55.88
pwr "+3V3" "+3V3" 132.08 55.88

echo "	;; ================= MCU ================="
# U1 at (180.34,88.9): VDD (165.26,78.9) GND (165.26,98.9); right pins x=195.42
part "heimdall-switch:BT832" U1 "BT832" 180.34 88.9 0 "" 9 10 1 2 3 4 5 6 7 8 11 12 13 14 15 16
wire 165.26 78.9 160.02 78.9
pwr "+3V3" "+3V3" 160.02 78.9
wire 165.26 98.9 160.02 98.9
pwr GND GND 160.02 98.9
# Spare GPIOs: P0.27 (2), P0.03 (6), P0.09 (7), P0.10 (8), P0.18 (12)
noconn 195.42 73.66
noconn 195.42 83.82
noconn 195.42 86.36
noconn 195.42 88.9
noconn 195.42 93.98

# Status LED: P0.26 (pin 1, y=71.12) → R_LED → LED1 → GND
wire 195.42 71.12 199.39 71.12
part "Device:R" R_LED "330R" 203.2 71.12 90 "" 1 2
wire 207.01 71.12 210.82 71.12
part "Device:LED" LED1 "LED" 214.63 71.12 180 "" 1 2
wire 218.44 71.12 223.52 71.12
pwr GND GND 223.52 71.12

# 32.768kHz crystal: XL1 (pin 3, y=76.2) → node A, XL2 (pin 4, y=78.74) → node B
wire 195.42 76.2 236.22 76.2
wire 236.22 76.2 243.84 76.2
junction 236.22 76.2
part "Device:Crystal" Y1 "32.768kHz" 236.22 80.01 90 "" 1 2
part "Device:C" C1 "12pF" 243.84 80.01 0 "" 1 2
pwr GND GND 243.84 83.82
wire 195.42 78.74 231.14 78.74
wire 231.14 78.74 231.14 83.82
wire 231.14 83.82 236.22 83.82
junction 231.14 83.82
part "Device:C" C2 "12pF" 231.14 87.63 0 "" 1 2
pwr GND GND 231.14 91.44

# ADC feedback and output drive leave the MCU block as labels
wire 195.42 81.28 200.66 81.28
label ADC_FB 200.66 81.28
wire 195.42 91.44 200.66 91.44
label OUT_OFF 200.66 91.44

# Button: P0.20 (pin 13, y=96.52) → SW1 → GND (internal pull-up in firmware)
wire 195.42 96.52 203.2 96.52
part "Switch:SW_Push" SW1 "SW_Push" 208.28 96.52 0 "" 1 2
pwr GND GND 213.36 96.52 90

# SWD: RESET (pin 14), SWDCLK (15), SWDIO (16) straight across to J1 pins 3-5
wire 195.42 99.06 236.22 99.06
wire 236.22 99.06 241.3 99.06
junction 236.22 99.06
wire 195.42 101.6 241.3 101.6
wire 195.42 104.14 241.3 104.14
part "Device:R" R_RST "10k" 236.22 95.25 0 "" 1 2
pwr "+3V3" "+3V3" 236.22 91.44
# J1 at (246.38,99.06): pin1 +3V3 (241.3,93.98) pin2 GND (241.3,96.52)
part "Connector_Generic:Conn_01x05" J1 "SWD" 246.38 99.06 0 "" 1 2 3 4 5
wire 241.3 93.98 238.76 93.98
wire 238.76 93.98 238.76 91.44
wire 238.76 91.44 236.22 91.44
junction 236.22 91.44
pwr GND GND 241.3 96.52 270

echo "	;; ================= Switching stage (fail-on) ================="
# VBAT rail y=127
pwr "+BATT" VBAT 60.96 127
wire 60.96 127 66.04 127
wire 66.04 127 81.28 127
wire 81.28 127 106.68 127
wire 106.68 127 114.3 127
wire 114.3 127 129.54 127
junction 66.04 127
junction 81.28 127
junction 106.68 127
junction 114.3 127

# OFF-hold driver: OUT_OFF → R_G1 → Q1 gate; R_OFF_PD holds Q1 off when the GPIO floats
label OUT_OFF 38.1 154.94 180
wire 38.1 154.94 44.45 154.94
part "Device:R" R_G1 "100R" 48.26 154.94 90 "" 1 2
wire 52.07 154.94 54.61 154.94
wire 54.61 154.94 58.42 154.94
junction 54.61 154.94
part "Device:R" R_OFF_PD "1M" 54.61 158.75 0 "" 1 2
pwr GND GND 54.61 162.56
# Q1 at (63.5,154.94): G (58.42,154.94) D (66.04,149.86) S (66.04,160.02)
part "Transistor_FET:Q_NMOS_GSD" Q1 "2N7002" 63.5 154.94 0 "" 1 2 3
pwr GND GND 66.04 160.02

# Gate clamp: R_CLAMP_PU holds Q2 off; Q1 on pulls Q2 gate low → Q2 clamps Q3 gate to VBAT
part "Device:R" R_CLAMP_PU "1M" 66.04 140.97 0 "" 1 2
wire 66.04 137.16 66.04 127
wire 66.04 149.86 66.04 144.78
wire 66.04 144.78 73.66 144.78
junction 66.04 144.78
# Q2 at (78.74,144.78) mirrored: G (73.66,144.78) S (81.28,139.7) D (81.28,149.86)
part "Transistor_FET:Q_PMOS_GSD" Q2 "BSS84" 78.74 144.78 0 x 1 2 3
wire 81.28 139.7 81.28 127
wire 81.28 149.86 81.28 154.94

# Q3 gate line y=154.94: pull-downs (default ON), turn-on cap, zener
wire 81.28 154.94 91.44 154.94
wire 91.44 154.94 99.06 154.94
wire 99.06 154.94 106.68 154.94
wire 106.68 154.94 114.3 154.94
wire 114.3 154.94 121.92 154.94
junction 91.44 154.94
junction 99.06 154.94
junction 106.68 154.94
junction 114.3 154.94
label Q3_GATE 83.82 154.94
part "Device:R" R_PD1 "2.2M" 91.44 158.75 0 "" 1 2
pwr GND GND 91.44 162.56
part "Device:R" R_PD2 "2.2M" 99.06 158.75 0 "" 1 2
pwr GND GND 99.06 162.56
part "Device:C" C_SS "220nF" 106.68 151.13 0 "" 1 2
wire 106.68 147.32 106.68 127
# D_Z rot 270: K top (114.3,147.32) to VBAT, A bottom (114.3,154.94) to gate
part "Device:D_Zener" D_Z "15V" 114.3 151.13 270 "" 1 2
wire 114.3 147.32 114.3 127

# Q3 load switch at (127,154.94) mirrored: G (121.92,154.94) S (129.54,149.86) D (129.54,160.02)
part "Transistor_FET:Q_PMOS_GSD" Q3 "AO4407A" 127 154.94 0 x 1 2 3
wire 129.54 149.86 129.54 127

# LOAD_OUT → J2, with the ADC feedback divider tapped off it
wire 129.54 160.02 129.54 167.64
wire 129.54 167.64 142.24 167.64
wire 142.24 167.64 165.1 167.64
junction 142.24 167.64
label LOAD_OUT 152.4 167.64
part "Device:R" R_FB_TOP "100k" 142.24 171.45 0 "" 1 2
part "Device:R" R_FB_BOT "33k" 142.24 179.07 0 "" 1 2
pwr GND GND 142.24 182.88
wire 142.24 175.26 149.86 175.26
wire 149.86 175.26 154.94 175.26
junction 142.24 175.26
junction 149.86 175.26
part "Device:C" C_FB "100nF" 149.86 179.07 0 "" 1 2
pwr GND GND 149.86 182.88
label ADC_FB 154.94 175.26
# J2 at (170.18,167.64): pin1 LOAD_OUT (165.1,167.64) pin2 GND (165.1,170.18)
part "Connector_Generic:Conn_01x02" J2 "LOAD_OUT" 170.18 167.64 0 "" 1 2
pwr GND GND 165.1 170.18 270
