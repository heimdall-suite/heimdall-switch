#!/usr/bin/env bash
# Generates the heimdall-switch UI daughter board project (schematic + PCB):
#   J1 (3 wire pads: 1 LED_A, 2 BTN, 3 GND — matches main board J4),
#   LED1 (3mm THT), SW1 (C&K KSC641J, IP67 tactile).
# Usage: gen_ui.sh OUTDIR
set -euo pipefail
OUT="$1"
MAIN=/c/Projekt/heimdall-suite/heimdall-switch/hardware/kicad
GEN=$MAIN/gen_body.sh
FP=/c/Users/svefre/AppData/Local/Programs/KiCad/10.0/share/kicad/footprints
NAME=heimdall-switch-ui
mkdir -p "$OUT"

ROOT_UUID=pending; export ROOT_UUID
eval "$(sed -n '1,/^# ---- pin geometry/p' "$GEN" | grep -v '^set -euo')"
ROOT_UUID=$(gen_uuid); export ROOT_UUID
U_J1=$(gen_uuid) U_LED=$(gen_uuid) U_SW=$(gen_uuid)

# Project file: main project's settings, with names swapped
sed -e "s/\"heimdall-switch\.kicad_pro\"/\"$NAME.kicad_pro\"/" \
    -e "s/\"heimdall-switch\.kicad_sch\"/\"$NAME.kicad_sch\"/" \
    -e "s/\"name\": \"heimdall-switch\"/\"name\": \"$NAME\"/" \
    "$MAIN/heimdall-switch.kicad_pro" > "$OUT/$NAME.kicad_pro"

# ---------------------------------------------------------------- schematic
# sym LIBID REF VALUE FOOTPRINT LCSC UUID X Y ROT MIRROR RX RY VX VY JUST PIN...
sym() {
  local libid="$1" ref="$2" value="$3" fp="$4" lcsc="$5" uuid="$6" x="$7" y="$8" rot="$9"
  local mir="${10}" rx="${11}" ry="${12}" vx="${13}" vy="${14}" just="${15}"
  shift 15
  local m="" j="" fa=0
  [ -n "$mir" ] && m=" (mirror $mir)"
  [ "$just" != center ] && j=" (justify $just)"
  case "$rot" in 90|270) fa=90 ;; esac
  local bom=yes
  printf '\t(symbol (lib_id "%s") (at %s %s %s)%s (unit 1)\n\t\t(exclude_from_sim no) (in_bom %s) (on_board yes) (dnp no)\n\t\t(uuid "%s")\n' \
    "$libid" "$x" "$y" "$rot" "$m" "$bom" "$uuid"
  printf '\t\t(property "Reference" "%s" (at %s %s %s) (effects (font (size 1.27 1.27))%s))\n' "$ref" "$rx" "$ry" "$fa" "$j"
  printf '\t\t(property "Value" "%s" (at %s %s %s) (effects (font (size 1.27 1.27))%s))\n' "$value" "$vx" "$vy" "$fa" "$j"
  printf '\t\t(property "Footprint" "%s" (at %s %s 0) (effects (font (size 1.27 1.27)) (hide yes)))\n' "$fp" "$x" "$y"
  printf '\t\t(property "Datasheet" "" (at %s %s 0) (effects (font (size 1.27 1.27)) (hide yes)))\n' "$x" "$y"
  [ -n "$lcsc" ] && printf '\t\t(property "LCSC" "%s" (at %s %s 0) (effects (font (size 1.27 1.27)) (hide yes)))\n' "$lcsc" "$x" "$y"
  local p
  for p in "$@"; do printf '\t\t(pin "%s" (uuid "%s"))\n' "$p" "$(gen_uuid)"; done
  printf '\t\t(instances (project "%s" (path "/%s" (reference "%s") (unit 1))))\n' "$NAME" "$ROOT_UUID" "$ref"
  printf '\t)\n'
}
# pwr with this project's name in instances
instances() { printf '\t\t(instances (project "%s" (path "/%s" (reference "%s") (unit 1))))\n' "$NAME" "$ROOT_UUID" "$1"; }

FP_J1="Connector_JST:JST_XH_B3B-XH-A_1x03_P2.50mm_Vertical"
FP_LED="LED_THT:LED_D3.0mm"
FP_SW="Button_Switch_SMD:SW_Push_1P1T_NO_CK_KSC6xxJ"

SCH="$OUT/$NAME.kicad_sch"
{
  printf '(kicad_sch\n\t(version 20231120)\n\t(generator "eeschema")\n\t(generator_version "8.0")\n\t(uuid "%s")\n\t(paper "A5")\n' "$ROOT_UUID"
  printf '\t(title_block\n\t\t(title "heimdall-switch UI daughter board")\n\t\t(comment 1 "Status LED + button, wired to main board J4")\n\t)\n'
  printf '\t(lib_symbols\n'
  for s in "Connector_Generic:Conn_01x03" "Device:LED" "Switch:SW_Push" "power:GND" "power:PWR_FLAG"; do
    n=$(grep -n -F "$(printf '\t\t(symbol "%s"' "$s")" "$MAIN/heimdall-switch.kicad_sch" | head -1 | cut -d: -f1)
    [ -n "$n" ] || { echo "missing lib symbol $s" >&2; exit 1; }
    awk -v start="$n" -f "$MAIN/extract_symbol.awk" "$MAIN/heimdall-switch.kicad_sch" | sed 's/^\t//'
  done
  printf '\t)\n'

  printf '\t(text "Daughter board for heimdall-switch: status LED + button, mounted\\nwherever the vehicle needs them (e.g. LED through a 3mm hole in\\nthe hull). Wire J1 to the main board'"'"'s J4 (1 LED_A, 2 BTN, 3 GND).\\nLED current limit (Q6 + R_LED) and button ESD resistor (R_BTN) are\\non the main board, so this board needs no other parts." (exclude_from_sim no)\n\t\t(at 76.2 55.88 0)\n\t\t(effects (font (size 1.27 1.27)) (justify left bottom))\n\t\t(uuid "%s")\n\t)\n' "$(gen_uuid)"

  # J1, pins facing right at x=106.68: 1=73.66 LED_A, 2=76.2 BTN, 3=78.74 GND
  sym "Connector_Generic:Conn_01x03" J1 "B3B-XH-A" "$FP_J1" C144394 "$U_J1" 101.6 76.2 0 y 101.6 69.85 101.6 67.31 center 1 2 3
  wire 106.68 73.66 132.08 73.66
  label LED_A 109.22 73.66
  wire 106.68 76.2 114.3 76.2
  label BTN 109.22 76.2
  # LED1 rot 90: A (132.08,73.66) top, K (132.08,81.28)
  sym "Device:LED" LED1 "Green 3mm" "$FP_LED" C414645 "$U_LED" 132.08 77.47 90 "" 134.62 76.2 134.62 78.74 right 1 2
  pwr GND GND 132.08 81.28
  # SW1 rot 270: pin 1 (114.3,76.2) BTN, pin 2 (114.3,86.36) GND
  sym "Switch:SW_Push" SW1 "KSC641J" "$FP_SW" C226344 "$U_SW" 114.3 81.28 270 "" 116.84 80.01 116.84 82.55 left 1 2
  pwr GND GND 114.3 86.36
  # J1 pin 3 -> GND, with the net's PWR_FLAG
  wire 106.68 78.74 109.22 78.74
  wire 109.22 78.74 109.22 86.36
  wire 109.22 86.36 109.22 88.9
  printf '\t(symbol (lib_id "power:PWR_FLAG") (at 109.22 86.36 90) (unit 1)\n\t\t(exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)\n\t\t(uuid "%s")\n' "$(gen_uuid)"
  printf '\t\t(property "Reference" "#FLG01" (at 109.22 86.36 0) (effects (font (size 1.27 1.27)) (hide yes)))\n'
  printf '\t\t(property "Value" "PWR_FLAG" (at 109.22 86.36 0) (effects (font (size 1.27 1.27)) (hide yes)))\n'
  printf '\t\t(property "Footprint" "" (at 109.22 86.36 0) (effects (font (size 1.27 1.27)) (hide yes)))\n'
  printf '\t\t(property "Datasheet" "" (at 109.22 86.36 0) (effects (font (size 1.27 1.27)) (hide yes)))\n'
  printf '\t\t(pin "1" (uuid "%s"))\n' "$(gen_uuid)"
  instances "#FLG01"
  printf '\t)\n'
  pwr GND GND 109.22 88.9

  printf '\t(sheet_instances\n\t\t(path "/"\n\t\t\t(page "1")\n\t\t)\n\t)\n)\n'
} > "$SCH"

# ---------------------------------------------------------------- PCB
# Nets
N_LED=1 N_BTN=2 N_GND=3
netname() { case "$1" in 1) echo "/LED_A";; 2) echo "/BTN";; 3) echo "GND";; esac; }

# fp FILE LIBID REF VALUE X Y ROT SYMUUID PADNETS(e.g. "1=1 2=2 3=3") LCSC FABREF
# FABREF=1 moves the reference text from silk to the fab layer.
fp() {
  local file="$1" libid="$2" ref="$3" value="$4" x="$5" y="$6" rot="$7" su="$8" pn="$9"
  local lcsc="${10}" fabref="${11:-0}"
  awk -v libid="$libid" -v ref="$ref" -v value="$value" -v x="$x" -v y="$y" -v rot="$rot" \
      -v su="$su" -v pn="$pn" -v uuid="$(gen_uuid)" -v sheet="$NAME.kicad_sch" \
      -v lcsc="$lcsc" -v luuid="$(gen_uuid)" -v fabref="$fabref" '
    BEGIN { n = split(pn, a, " "); for (i = 1; i <= n; i++) { split(a[i], kv, "="); net[kv[1]] = kv[2] }
            nm[1] = "/LED_A"; nm[2] = "/BTN"; nm[3] = "GND" }
    NR == 1 { printf "\t(footprint \"%s\"\n\t\t(layer \"F.Cu\")\n\t\t(uuid \"%s\")\n\t\t(at %s %s%s)\n", libid, uuid, x, y, (rot ? " " rot : "")
              printf "\t\t(path \"/%s\")\n\t\t(sheetname \"/\")\n\t\t(sheetfile \"%s\")\n", su, sheet
              if (lcsc != "") printf "\t\t(property \"LCSC\" \"%s\"\n\t\t\t(at 0 0 0)\n\t\t\t(layer \"F.Fab\")\n\t\t\t(hide yes)\n\t\t\t(uuid \"%s\")\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1 1)\n\t\t\t\t\t(thickness 0.15)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n", lcsc, luuid
              next }
    /^\t\((version|generator|generator_version) / { next }
    /^\t\(layer "F.Cu"\)$/ && !layerdone { layerdone = 1; next }
    /^\t\(property "Reference" / { inref = 1 }
    inref && fabref && /^\t\t\(layer "F.SilkS"\)$/ { sub(/F.SilkS/, "F.Fab"); inref = 0 }
    /^\t\)$/ { inref = 0 }
    { sub(/"REF\*\*"/, "\"" ref "\""); }
    /^\t\(property "Value" / { sub(/"Value" "[^"]*"/, "\"Value\" \"" value "\"") }
    /^\t\(pad "/ { inpad = 1; match($0, /"[^"]*"/); pnum = substr($0, RSTART + 1, RLENGTH - 2) }
    inpad && /^\t\t\(at [-0-9. ]+\)$/ && rot { sub(/\)$/, " " rot ")") }
    inpad && /^\t\)$/ { if (pnum in net) printf "\t\t\t(net %s \"%s\")\n", net[pnum], nm[net[pnum]]; inpad = 0 }
    { print "\t" $0 }
  ' "$file"
}

seg() { printf '\t(segment\n\t\t(start %s %s)\n\t\t(end %s %s)\n\t\t(width 0.4)\n\t\t(layer "%s")\n\t\t(net %s)\n\t\t(uuid "%s")\n\t)\n' "$1" "$2" "$3" "$4" "$5" "$6" "$(gen_uuid)"; }
via() { printf '\t(via\n\t\t(at %s %s)\n\t\t(size 0.8)\n\t\t(drill 0.4)\n\t\t(layers "F.Cu" "B.Cu")\n\t\t(net %s)\n\t\t(uuid "%s")\n\t)\n' "$1" "$2" "$3" "$(gen_uuid)"; }

DEMO=/c/Users/svefre/AppData/Local/Programs/KiCad/10.0/share/kicad/demos/ecc83/ecc83-pp.kicad_pcb
PCB="$OUT/$NAME.kicad_pcb"
{
  printf '(kicad_pcb\n\t(version 20241229)\n\t(generator "pcbnew")\n\t(generator_version "9.0")\n'
  printf '\t(general\n\t\t(thickness 1.6)\n\t\t(legacy_teardrops no)\n\t)\n\t(paper "A5")\n'
  printf '\t(title_block\n\t\t(title "heimdall-switch UI daughter board")\n\t)\n'
  awk '/^\t\(layers$/,/^\t\)$/' "$DEMO"
  awk '/^\t\(setup$/,/^\t\)$/' "$DEMO"
  printf '\t(net 0 "")\n\t(net 1 "/LED_A")\n\t(net 2 "/BTN")\n\t(net 3 "GND")\n'

  # SW1 centre (106,106): pad 1 (BTN) at y 104, pad 2 (GND) at y 108
  fp "$FP/Button_Switch_SMD.pretty/SW_Push_1P1T_NO_CK_KSC6xxJ.kicad_mod" "$FP_SW" SW1 KSC641J 106 106 "" "$U_SW" "1=2 2=3" C226344
  # LED1: pad 1 = K (113.5,106), pad 2 = A (116.04,106)
  fp "$FP/LED_THT.pretty/LED_D3.0mm.kicad_mod" "$FP_LED" LED1 "Green 3mm" 113.5 106 "" "$U_LED" "1=3 2=1" C414645
  # J1 (JST XH, flipped to the back afterwards) rot 270: pads 1 (121.5,103.5)
  # LED_A, 2 (121.5,106) BTN, 3 (121.5,108.5) GND
  fp "$FP/Connector_JST.pretty/JST_XH_B3B-XH-A_1x03_P2.50mm_Vertical.kicad_mod" "$FP_J1" J1 B3B-XH-A 121.5 103.5 270 "$U_J1" "1=1 2=2 3=3" C144394 1

  # Board outline 26 x 13 mm
  printf '\t(gr_rect\n\t\t(start 100 100)\n\t\t(end 126 113)\n\t\t(stroke\n\t\t\t(width 0.05)\n\t\t\t(type default)\n\t\t)\n\t\t(fill no)\n\t\t(layer "Edge.Cuts")\n\t\t(uuid "%s")\n\t)\n' "$(gen_uuid)"
  # Back silk: board name
  printf '\t(gr_text "heimdall UI"\n\t\t(at 106 110.9 0)\n\t\t(layer "B.SilkS")\n\t\t(uuid "%s")\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 0.8 0.8)\n\t\t\t\t(thickness 0.12)\n\t\t\t)\n\t\t\t(justify mirror)\n\t\t)\n\t)\n' "$(gen_uuid)"

  # LED_A (top): J1.1 -> LED anode
  seg 121.5 103.5 118.54 103.5 F.Cu $N_LED
  seg 118.54 103.5 116.04 106 F.Cu $N_LED
  # BTN (bottom, above the LED), via to SW1 pad 1 on top
  seg 121.5 106 118.5 103 B.Cu $N_BTN
  seg 118.5 103 112.5 103 B.Cu $N_BTN
  seg 112.5 103 111.5 104 B.Cu $N_BTN
  via 111.5 104 $N_BTN
  seg 111.5 104 108.9 104 F.Cu $N_BTN
  # SW1's paired pads (internally connected) also joined in copper
  seg 103.1 104 108.9 104 F.Cu $N_BTN
  seg 103.1 108 108.9 108 F.Cu $N_GND
  # GND (top): J1.3 -> SW1 pad 2, LED cathode
  seg 121.5 108.5 119.5 110.5 F.Cu $N_GND
  seg 119.5 110.5 111.4 110.5 F.Cu $N_GND
  seg 111.4 110.5 108.9 108 F.Cu $N_GND
  seg 113.5 106 113.5 110.5 F.Cu $N_GND

  printf '\t(embedded_fonts no)\n)\n'
} > "$PCB"

# Flip the XH header to the back side (LED + button face the hull, the
# cable plugs in from behind) using KiCad's own footprint flip.
"/c/Users/svefre/AppData/Local/Programs/KiCad/10.0/bin/python.exe" - "$(cygpath -w "$PCB")" <<'PY'
import sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
fp = b.FindFootprintByReference("J1")
fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
pcbnew.SaveBoard(sys.argv[1], b)
print("J1 flipped to", fp.GetLayerName())
PY
echo "generated $SCH $PCB"
