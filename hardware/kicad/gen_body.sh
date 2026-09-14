#!/usr/bin/env bash
set -euo pipefail

gen_uuid() {
  local h
  h=$(od -An -N16 -tx1 /dev/urandom | tr -d ' \n')
  printf '%s-%s-4%s-%x%s-%s' \
    "${h:0:8}" "${h:8:4}" "${h:13:3}" \
    $(( (0x${h:16:1} & 0x3) | 0x8 )) "${h:17:3}" "${h:20:12}"
}

# label NAME X Y
label() {
  local name="$1" x="$2" y="$3"
  printf '\t(label "%s"\n\t\t(at %s %s 0)\n\t\t(effects (font (size 1.27 1.27)) (justify left bottom))\n\t\t(uuid "%s")\n\t)\n' \
    "$name" "$x" "$y" "$(gen_uuid)"
}

# symbol_header LIBID REF VALUE X Y
symbol_header() {
  local libid="$1" ref="$2" value="$3" x="$4" y="$5"
  printf '\t(symbol (lib_id "%s") (at %s %s 0) (unit 1)\n\t\t(exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)\n\t\t(uuid "%s")\n' "$libid" "$x" "$y" "$(gen_uuid)"
  printf '\t\t(property "Reference" "%s" (at %s %s 0) (effects (font (size 1.27 1.27))))\n' "$ref" "$x" "$(awk "BEGIN{print $y+6}")"
  printf '\t\t(property "Value" "%s" (at %s %s 0) (effects (font (size 1.27 1.27))))\n' "$value" "$x" "$(awk "BEGIN{print $y-6}")"
  printf '\t\t(property "Footprint" "" (at %s %s 0) (effects (font (size 1.27 1.27)) (hide yes)))\n' "$x" "$y"
  printf '\t\t(property "Datasheet" "" (at %s %s 0) (effects (font (size 1.27 1.27)) (hide yes)))\n' "$x" "$y"
}

symbol_pin() {
  printf '\t\t(pin "%s" (uuid "%s"))\n' "$1" "$(gen_uuid)"
}

symbol_footer() { printf '\t)\n'; }

add() { echo "$1" -1p; } # unused placeholder

# ---- per-type emitters ----
# args: ref value x y net1 net2   (vertical 2-pin: pin1=top(+3.81) pin2=bottom(-3.81))
emit_r() { emit_vert2 "Device:R" "$@"; }
emit_c() { emit_vert2 "Device:C" "$@"; }
emit_l() { emit_vert2 "Device:L" "$@"; }
emit_vert2() {
  local libid="$1" ref="$2" value="$3" x="$4" y="$5" n1="$6" n2="$7"
  symbol_header "$libid" "$ref" "$value" "$x" "$y"
  symbol_pin 1; symbol_pin 2
  symbol_footer
  label "$n1" "$x" "$(awk "BEGIN{print $y-3.81}")"
  label "$n2" "$x" "$(awk "BEGIN{print $y+3.81}")"
}

# horizontal 2-pin, pin1=left(-3.81,0) pin2=right(3.81,0): Crystal, D_Schottky, LED
emit_horiz2() {
  local libid="$1" ref="$2" value="$3" x="$4" y="$5" n1="$6" n2="$7"
  symbol_header "$libid" "$ref" "$value" "$x" "$y"
  symbol_pin 1; symbol_pin 2
  symbol_footer
  label "$n1" "$(awk "BEGIN{print $x-3.81}")" "$y"
  label "$n2" "$(awk "BEGIN{print $x+3.81}")" "$y"
}
emit_crystal() { emit_horiz2 "Device:Crystal" "$@"; }
emit_diode() { emit_horiz2 "Device:D_Schottky" "$@"; }
emit_led() { emit_horiz2 "Device:LED" "$@"; }  # n1=cathode(K) n2=anode(A)

# SW_Push horizontal 2-pin, pin1=left(-5.08,0) pin2=right(5.08,0)
emit_sw() {
  local ref="$1" value="$2" x="$3" y="$4" n1="$5" n2="$6"
  symbol_header "Switch:SW_Push" "$ref" "$value" "$x" "$y"
  symbol_pin 1; symbol_pin 2
  symbol_footer
  label "$n1" "$(awk "BEGIN{print $x-5.08}")" "$y"
  label "$n2" "$(awk "BEGIN{print $x+5.08}")" "$y"
}

# Q_NMOS_GSD / Q_PMOS_GSD: pin1=G(-5.08,0) pin2=S(2.54,-5.08) pin3=D(2.54,5.08)
emit_q() {
  local libid="$1" ref="$2" value="$3" x="$4" y="$5" ng="$6" ns="$7" nd="$8"
  symbol_header "$libid" "$ref" "$value" "$x" "$y"
  symbol_pin 1; symbol_pin 2; symbol_pin 3
  symbol_footer
  label "$ng" "$(awk "BEGIN{print $x-5.08}")" "$y"
  label "$ns" "$(awk "BEGIN{print $x+2.54}")" "$(awk "BEGIN{print $y+5.08}")"
  label "$nd" "$(awk "BEGIN{print $x+2.54}")" "$(awk "BEGIN{print $y-5.08}")"
}
emit_qn() { emit_q "Transistor_FET:Q_NMOS_GSD" "$@"; }
emit_qp() { emit_q "Transistor_FET:Q_PMOS_GSD" "$@"; }

# Conn_01x05: pins at x=-5.08, y = 5.08,2.54,0,-2.54,-5.08
emit_conn5() {
  local ref="$1" value="$2" x="$3" y="$4" n1="$5" n2="$6" n3="$7" n4="$8" n5="$9"
  symbol_header "Connector_Generic:Conn_01x05" "$ref" "$value" "$x" "$y"
  symbol_pin 1; symbol_pin 2; symbol_pin 3; symbol_pin 4; symbol_pin 5
  symbol_footer
  label "$n1" "$(awk "BEGIN{print $x-5.08}")" "$(awk "BEGIN{print $y-5.08}")"
  label "$n2" "$(awk "BEGIN{print $x-5.08}")" "$(awk "BEGIN{print $y-2.54}")"
  label "$n3" "$(awk "BEGIN{print $x-5.08}")" "$y"
  label "$n4" "$(awk "BEGIN{print $x-5.08}")" "$(awk "BEGIN{print $y+2.54}")"
  label "$n5" "$(awk "BEGIN{print $x-5.08}")" "$(awk "BEGIN{print $y+5.08}")"
}

# Conn_01x02: pins at x=-5.08, y=0 and y=-2.54
emit_conn2() {
  local ref="$1" value="$2" x="$3" y="$4" n1="$5" n2="$6"
  symbol_header "Connector_Generic:Conn_01x02" "$ref" "$value" "$x" "$y"
  symbol_pin 1; symbol_pin 2
  symbol_footer
  label "$n1" "$(awk "BEGIN{print $x-5.08}")" "$y"
  label "$n2" "$(awk "BEGIN{print $x-5.08}")" "$(awk "BEGIN{print $y+2.54}")"
}

# Relay_SPST_Latching_2coil: 13=(5.08,-7.62) 14=(7.62,7.62) A1=(-7.62,7.62) A2=(-7.62,-7.62) B1=(-2.54,7.62) B2=(-2.54,-7.62)
emit_relay() {
  local ref="$1" value="$2" x="$3" y="$4" n13="$5" n14="$6" na1="$7" na2="$8" nb1="$9" nb2="${10}"
  symbol_header "Relay:Relay_SPST_Latching_2coil" "$ref" "$value" "$x" "$y"
  symbol_pin 13; symbol_pin 14; symbol_pin A1; symbol_pin A2; symbol_pin B1; symbol_pin B2
  symbol_footer
  label "$n13" "$(awk "BEGIN{print $x+5.08}")" "$(awk "BEGIN{print $y+7.62}")"
  label "$n14" "$(awk "BEGIN{print $x+7.62}")" "$(awk "BEGIN{print $y-7.62}")"
  label "$na1" "$(awk "BEGIN{print $x-7.62}")" "$(awk "BEGIN{print $y-7.62}")"
  label "$na2" "$(awk "BEGIN{print $x-7.62}")" "$(awk "BEGIN{print $y+7.62}")"
  label "$nb1" "$(awk "BEGIN{print $x-2.54}")" "$(awk "BEGIN{print $y-7.62}")"
  label "$nb2" "$(awk "BEGIN{print $x-2.54}")" "$(awk "BEGIN{print $y+7.62}")"
}

# BT832 custom: left VDD(9)@(-15.08,10) GND(10)@(-15.08,-10)
# right (15.08, y): 1@17.78 2@15.24 3@12.7 4@10.16 5@7.62 6@5.08 7@2.54 8@0 11@-2.54 12@-5.08 13@-7.62 14@-10.16 15@-12.7 16@-15.24
emit_bt832() {
  local ref="$1" value="$2" x="$3" y="$4"
  shift 4
  local n9="$1" n10="$2" n1="$3" n2="$4" n3="$5" n4="$6" n5="$7" n6="$8" n7="$9" n8="${10}" n11="${11}" n12="${12}" n13="${13}" n14="${14}" n15="${15}" n16="${16}"
  symbol_header "heimdall-switch:BT832" "$ref" "$value" "$x" "$y"
  for p in 9 10 1 2 3 4 5 6 7 8 11 12 13 14 15 16; do symbol_pin "$p"; done
  symbol_footer
  [ -n "$n9" ]  && label "$n9"  "$(awk "BEGIN{print $x-15.08}")" "$(awk "BEGIN{print $y-10}")" || true
  [ -n "$n10" ] && label "$n10" "$(awk "BEGIN{print $x-15.08}")" "$(awk "BEGIN{print $y+10}")" || true
  [ -n "$n1" ]  && label "$n1"  "$(awk "BEGIN{print $x+15.08}")" "$(awk "BEGIN{print $y-17.78}")" || true
  [ -n "$n2" ]  && label "$n2"  "$(awk "BEGIN{print $x+15.08}")" "$(awk "BEGIN{print $y-15.24}")" || true
  [ -n "$n3" ]  && label "$n3"  "$(awk "BEGIN{print $x+15.08}")" "$(awk "BEGIN{print $y-12.7}")" || true
  [ -n "$n4" ]  && label "$n4"  "$(awk "BEGIN{print $x+15.08}")" "$(awk "BEGIN{print $y-10.16}")" || true
  [ -n "$n5" ]  && label "$n5"  "$(awk "BEGIN{print $x+15.08}")" "$(awk "BEGIN{print $y-7.62}")" || true
  [ -n "$n6" ]  && label "$n6"  "$(awk "BEGIN{print $x+15.08}")" "$(awk "BEGIN{print $y-5.08}")" || true
  [ -n "$n7" ]  && label "$n7"  "$(awk "BEGIN{print $x+15.08}")" "$(awk "BEGIN{print $y-2.54}")" || true
  [ -n "$n8" ]  && label "$n8"  "$(awk "BEGIN{print $x+15.08}")" "$y" || true
  [ -n "$n11" ] && label "$n11" "$(awk "BEGIN{print $x+15.08}")" "$(awk "BEGIN{print $y+2.54}")" || true
  [ -n "$n12" ] && label "$n12" "$(awk "BEGIN{print $x+15.08}")" "$(awk "BEGIN{print $y+5.08}")" || true
  [ -n "$n13" ] && label "$n13" "$(awk "BEGIN{print $x+15.08}")" "$(awk "BEGIN{print $y+7.62}")" || true
  [ -n "$n14" ] && label "$n14" "$(awk "BEGIN{print $x+15.08}")" "$(awk "BEGIN{print $y+10.16}")" || true
  [ -n "$n15" ] && label "$n15" "$(awk "BEGIN{print $x+15.08}")" "$(awk "BEGIN{print $y+12.7}")" || true
  [ -n "$n16" ] && label "$n16" "$(awk "BEGIN{print $x+15.08}")" "$(awk "BEGIN{print $y+15.24}")" || true
}

# TPS629206 custom: left VIN(6)@(-15.08,7.62) EN(7)@(-15.08,2.54) GND(5)@(-15.08,-2.54) MODE(8)@(-15.08,-7.62)
# right SW(4)@(15.08,7.62) VOS(3)@(15.08,2.54) FBVSET(1)@(15.08,-2.54) PG(2)@(15.08,-7.62)
emit_tps() {
  local ref="$1" value="$2" x="$3" y="$4" nvin="$5" nen="$6" ngnd="$7" nmode="$8" nsw="$9" nvos="${10}" nfb="${11}" npg="${12}"
  symbol_header "heimdall-switch:TPS629206" "$ref" "$value" "$x" "$y"
  for p in 6 7 5 8 4 3 1 2; do symbol_pin "$p"; done
  symbol_footer
  [ -n "$nvin" ]  && label "$nvin"  "$(awk "BEGIN{print $x-15.08}")" "$(awk "BEGIN{print $y-7.62}")" || true
  [ -n "$nen" ]   && label "$nen"   "$(awk "BEGIN{print $x-15.08}")" "$(awk "BEGIN{print $y-2.54}")" || true
  [ -n "$ngnd" ]  && label "$ngnd"  "$(awk "BEGIN{print $x-15.08}")" "$(awk "BEGIN{print $y+2.54}")" || true
  [ -n "$nmode" ] && label "$nmode" "$(awk "BEGIN{print $x-15.08}")" "$(awk "BEGIN{print $y+7.62}")" || true
  [ -n "$nsw" ]   && label "$nsw"   "$(awk "BEGIN{print $x+15.08}")" "$(awk "BEGIN{print $y-7.62}")" || true
  [ -n "$nvos" ]  && label "$nvos"  "$(awk "BEGIN{print $x+15.08}")" "$(awk "BEGIN{print $y-2.54}")" || true
  [ -n "$nfb" ]   && label "$nfb"   "$(awk "BEGIN{print $x+15.08}")" "$(awk "BEGIN{print $y+2.54}")" || true
  [ -n "$npg" ]   && label "$npg"   "$(awk "BEGIN{print $x+15.08}")" "$(awk "BEGIN{print $y+7.62}")" || true
}

# ---------------- component list ----------------

echo "	;; --- Power input & regulator ---"
emit_c   "C_IN" "4.7uF" 90 67.62 "VBAT" "GND"
emit_tps "U2" "TPS629206" 120 60 "VBAT" "VBAT" "GND" "MODE_CONF" "SW_NODE" "+3V3" "" ""
emit_r   "R_MODE" "27.4k" 104.92 40 "MODE_CONF" "GND"
emit_l   "L1" "2.2uH" 135.08 80 "SW_NODE" "+3V3"
emit_c   "C_OUT" "22uF" 150 62.54 "+3V3" "GND"

echo "	;; --- MCU ---"
emit_bt832 "U1" "BT832" 220 60 "+3V3" "GND" "LED_DRV" "" "XTAL1" "XTAL2" "ADC_FB" "" "" "" "RELAY_SET_GPIO" "RELAY_RESET_GPIO" "BTN" "RESET_N" "SWDCLK" "SWDIO"

echo "	;; --- Crystal ---"
emit_crystal "Y1" "32.768kHz" 220 100 "XTAL1" "XTAL2"
emit_c "C1" "12pF" 216.19 115 "XTAL1" "GND"
emit_c "C2" "12pF" 223.81 115 "XTAL2" "GND"

echo "	;; --- SWD header ---"
emit_conn5 "J1" "SWD" 280 60 "+3V3" "GND" "RESET_N" "SWDCLK" "SWDIO"
emit_r "R_RST" "10k" 250 49.84 "+3V3" "RESET_N"

echo "	;; --- LED ---"
emit_r   "R_LED" "330R" 250 77.78 "LED_DRV" "LED_A"
emit_led "LED1" "LED" 265 73.97 "GND" "LED_A"

echo "	;; --- Button ---"
emit_sw "SW1" "SW_Push" 250 90 "BTN" "GND"

echo "	;; --- ADC feedback divider ---"
emit_r "R_FB_TOP" "100k" 235.08 20 "LOAD_OUT" "ADC_FB"
emit_r "R_FB_BOT" "33k" 235.08 5 "ADC_FB" "GND"
emit_c "C_FB" "100nF" 250 12 "ADC_FB" "GND"

echo "	;; --- Relay driver: SET side ---"
emit_r    "R_G1" "100R" 40 120 "RELAY_SET_GPIO" "RELAY_SET_G"
emit_qn   "Q1" "Q_NMOS_GSD" 60 120 "RELAY_SET_G" "GND" "RELAY_SET_D"
emit_diode "D1" "D_Schottky" 75 130 "VBAT" "RELAY_SET_D"

echo "	;; --- Relay driver: RESET side ---"
emit_r    "R_G2" "100R" 160 120 "RELAY_RESET_GPIO" "RELAY_RESET_G"
emit_qn   "Q2" "Q_NMOS_GSD" 140 120 "RELAY_RESET_G" "GND" "RELAY_RESET_D"
emit_diode "D2" "D_Schottky" 75 145 "VBAT" "RELAY_RESET_D"

echo "	;; --- Latching relay ---"
emit_relay "K1" "Relay_SPST_Latching_2coil" 100 130 "GND" "MOSFET_GATE" "RELAY_SET_D" "VBAT" "RELAY_RESET_D" "VBAT"

echo "	;; --- Main load switch ---"
emit_r  "R_GATE_PULL" "10k" 120 150 "VBAT" "MOSFET_GATE"
emit_qp "Q3" "Q_PMOS_GSD" 150 150 "MOSFET_GATE" "VBAT" "LOAD_OUT"

echo "	;; --- Load output ---"
emit_conn2 "J2" "LOAD_OUT" 150 175 "LOAD_OUT" "GND"
