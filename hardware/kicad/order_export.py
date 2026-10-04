# Builds the TME and Mouser order files for a prototype run into hardware/order/:
#   tme-basket.csv     "symbol;quantity" per line, for TME's basket import (upload from file)
#   mouser-bom.csv     Mouser No, Mfr No, Manufacturer, Quantity, Refs, for Mouser's BOM tool
# Parts come from the schematics' Supplier / Supplier PN / MPN / Manufacturer fields, times
# the number of boards; the UI cable isn't in any schematic, so its parts are listed below.
# Parts without a Supplier field (J2/J3 wire pads) are left out.
#
# Run with any python (only kicad-cli is needed); the arguments are the run size:
#   python order_export.py                  10 main boards, 5 UI boards, 5 cables
#   python order_export.py 5 2 2            5 main boards, 2 UI boards, 2 cables
import csv, os, subprocess, sys, tempfile
from collections import OrderedDict

KICAD_CLI = r"C:\Users\svefre\AppData\Local\Programs\KiCad\10.0\bin\kicad-cli.exe"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "order")
main_n, ui_n, cable_n = (int(a) for a in (sys.argv[1:] + ["10", "5", "5"][len(sys.argv) - 1:])[:3])
BOARDS = [(os.path.join(HERE, "heimdall-switch.kicad_sch"), main_n),
          (os.path.join(HERE, "..", "kicad-ui", "heimdall-switch-ui.kicad_sch"), ui_n)]
# per cable: 2 housings, 6 crimp contacts (pin 1 <-> pin 1, 3 wires)
CABLE = [("TME", "GHR-03V-S", "GHR-03V-S", "JST", 2, "cable housing"),
         ("TME", "SSHL-002T-P0.2", "SSHL-002T-P0.2", "JST", 6, "cable crimp contact")]

lines = OrderedDict()   # (supplier, supplier PN) -> [MPN, manufacturer, qty, refs]
def add(supplier, spn, mpn, mfr, qty, refs):
    l = lines.setdefault((supplier, spn), [mpn, mfr, 0, []])
    l[2] += qty; l[3].append(refs)

for sch, n in BOARDS:
    with tempfile.TemporaryDirectory() as tmp:
        f = os.path.join(tmp, "bom.csv")
        subprocess.run([KICAD_CLI, "sch", "export", "bom", "--fields",
                        "Reference,Supplier,Supplier PN,MPN,Manufacturer,${QUANTITY}",
                        "--group-by", "Supplier,Supplier PN", "--exclude-dnp", "-o", f, sch],
                       check=True, stdout=subprocess.DEVNULL)
        rows = list(csv.reader(open(f, encoding="utf8")))[1:]
    board = os.path.basename(sch)[:-len(".kicad_sch")]
    for refs, supplier, spn, mpn, mfr, qty in rows:
        if supplier.strip():
            add(supplier, spn, mpn, mfr, int(qty) * n, "%s: %s" % (board, refs))
for supplier, spn, mpn, mfr, per, what in CABLE:
    add(supplier, spn, mpn, mfr, per * cable_n, what)

os.makedirs(OUT, exist_ok=True)
tme = [(k[1], v[2]) for k, v in lines.items() if k[0] == "TME"]
mouser = [(k[1], v[0], v[1], v[2], "; ".join(v[3])) for k, v in lines.items() if k[0] == "Mouser"]
with open(os.path.join(OUT, "tme-basket.csv"), "w", newline="", encoding="utf8") as fh:
    csv.writer(fh, delimiter=";").writerows(tme)
with open(os.path.join(OUT, "mouser-bom.csv"), "w", newline="", encoding="utf8") as fh:
    w = csv.writer(fh)
    w.writerow(["Mouser No", "Mfr No", "Manufacturer", "Quantity", "Refs"])
    w.writerows(mouser)
other = sorted({k[0] for k in lines} - {"TME", "Mouser"})
print("Run: %d main, %d UI, %d cables -> %s: TME %d lines / %d parts, Mouser %d lines / %d parts%s"
      % (main_n, ui_n, cable_n, os.path.normpath(OUT), len(tme), sum(q for _, q in tme),
         len(mouser), sum(m[3] for m in mouser), "; other suppliers ignored: " + ", ".join(other) if other else ""))
