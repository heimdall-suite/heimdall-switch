#!/usr/bin/env bash
# Rebuilds heimdall-switch.kicad_sch: keeps the existing header + embedded
# lib_symbols (minus any listed in DROP), appends any symbols listed in ADD
# from the KiCad stock libraries, then regenerates the body via gen_body.sh.
#
# Usage: ./build_sch.sh
set -euo pipefail
cd "$(dirname "$0")"

# RETIRED: the schematic has since been edited in the KiCad GUI and no longer
# matches gen_body.sh. Running this would overwrite that work.
if [ "${FORCE_REGENERATE:-}" != yes ]; then
  echo "build_sch.sh is retired — the .kicad_sch is edited in KiCad now." >&2
  echo "Set FORCE_REGENERATE=yes only if you really want to discard it." >&2
  exit 1
fi

SCH=heimdall-switch.kicad_sch
KICAD_DIR="${KICAD_DIR:-/c/Users/svefre/AppData/Local/Programs/KiCad/10.0}"
KICAD_SYMS="$KICAD_DIR/share/kicad/symbols"
KICAD_CLI="$KICAD_DIR/bin/kicad-cli.exe"

# Embedded symbols to remove (lib_id as used in the schematic)
DROP=("Device:D_Schottky" "Relay:Relay_SPST_Latching_2coil")
# Stock symbols to add, as "Library:Name" (skipped if already embedded)
ADD=("Device:D_Zener" "power:GND" "power:+3V3" "power:+BATT" "power:PWR_FLAG")

tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT

# Header: everything before the lib_symbols block, plus its opening line.
# gen_body.sh writes KiCad 8-era syntax, so the file is assembled under that
# format version and upgraded to the installed KiCad's format at the end.
awk '{ print } /^\t\(lib_symbols$/ { exit }' "$SCH" \
  | sed -E '2s/\(version [0-9]+\)/(version 20231120)/' > "$tmp"

# Existing embedded symbols, minus DROP
while IFS= read -r line; do
  n="${line%%:*}"
  name=$(sed -n "${n}p" "$SCH" | sed -E 's/^\t+\(symbol "([^"]+)".*/\1/')
  skip=0
  for d in "${DROP[@]}"; do [ "$name" = "$d" ] && skip=1; done
  [ "$skip" = 1 ] && continue
  awk -v start="$n" -f extract_symbol.awk "$SCH" >> "$tmp"
done < <(grep -n -E $'^\t\t?\\(symbol "[^"]+:[^"]+"$' "$SCH")  # 1 tab: KiCad 8 layout, 2: KiCad 10

# New stock symbols from ADD
for a in "${ADD[@]}"; do
  grep -q -F "(symbol \"$a\"" "$tmp" && continue
  lib="${a%%:*}" sym="${a#*:}"
  n=$(grep -n -F "	(symbol \"$sym\"" "$KICAD_SYMS/$lib.kicad_sym" | head -1 | cut -d: -f1)
  awk -v start="$n" -f extract_symbol.awk "$KICAD_SYMS/$lib.kicad_sym" \
    | sed "1s/(symbol \"$sym\"/(symbol \"$a\"/" >> "$tmp"
done

# Close lib_symbols, body, footer
{
  printf '\t)\n'
  # gen_body.sh's ";;" section comments are for readability only — KiCad's
  # parser rejects them
  ROOT_UUID=$(sed -n -E 's/^\t\(uuid "([^"]+)"\)$/\1/p' "$SCH" | head -1) \
    bash gen_body.sh | grep -v -E $'^\t;;'
  printf '\t(sheet_instances\n\t\t(path "/" (page "1"))\n\t)\n)\n'
} >> "$tmp"

mv "$tmp" "$SCH"
trap - EXIT
"$KICAD_CLI" sch upgrade --force "$SCH" > /dev/null
echo "wrote $SCH"
