# Builds the TME and Mouser order files for a prototype run into hardware/order/:
#   tme-basket.csv     "symbol;quantity" per line, for TME's basket import (upload from file)
#   mouser-bom.csv     Mouser No, Mfr No, Manufacturer, Quantity, Refs, for Mouser's BOM tool
# Parts come from the schematics' Supplier / Supplier PN / MPN / Manufacturer fields, times
# the number of boards; the UI cable isn't in any schematic, so its parts are listed below.
# Parts without a Supplier field (J2/J3 wire pads) are left out.
# hardware/sourcing/check_order.py checks the result against the live supplier APIs.
#
# Run with any python (only kicad-cli is needed); the arguments are the run size:
#   python order_export.py                  10 main boards, 5 UI boards, 5 cables
#   python order_export.py 5 2 2            5 main boards, 2 UI boards, 2 cables
import csv, os, subprocess, sys, tempfile

KICAD_CLI = r"C:\Users\svefre\AppData\Local\Programs\KiCad\10.0\bin\kicad-cli.exe"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "order")
SCHEMATICS = {"main": os.path.join(HERE, "heimdall-switch.kicad_sch"),
              "ui": os.path.join(HERE, "..", "kicad-ui", "heimdall-switch-ui.kicad_sch")}
# per cable: 2 housings, 6 crimp contacts (pin 1 <-> pin 1, 3 wires)
CABLE = [dict(Supplier="TME", SupplierPN="GHR-03V-S", MPN="GHR-03V-S", Manufacturer="JST", LCSC="C160417",
              Value="GH 3-pin housing", per=2),
         dict(Supplier="TME", SupplierPN="SSHL-002T-P0.2", MPN="SSHL-002T-P0.2", Manufacturer="JST", LCSC="C189897",
              Value="GH crimp contact", per=6)]

def bom_lines(main_n=10, ui_n=5, cable_n=5):
    """One dict per BOM line and board (Refs, Value, MPN, Manufacturer, Supplier, SupplierPN,
    LCSC, Qty = per-board quantity times the board count), plus the cable parts."""
    lines = []
    for board, n in (("main", main_n), ("ui", ui_n)):
        with tempfile.TemporaryDirectory() as tmp:
            f = os.path.join(tmp, "bom.csv")
            subprocess.run([KICAD_CLI, "sch", "export", "bom", "--fields",
                            "Reference,Value,MPN,Manufacturer,Supplier,Supplier PN,LCSC,${QUANTITY}",
                            "--group-by", "Value,MPN,Supplier PN,LCSC", "--exclude-dnp", "-o", f, SCHEMATICS[board]],
                           check=True, stdout=subprocess.DEVNULL)
            rows = list(csv.reader(open(f, encoding="utf8")))[1:]
        for refs, value, mpn, mfr, supplier, spn, lcsc, qty in rows:
            lines.append(dict(Refs="%s: %s" % (board, refs), Value=value, MPN=mpn, Manufacturer=mfr,
                              Supplier=supplier, SupplierPN=spn, LCSC=lcsc, Qty=int(qty) * n))
    for c in CABLE:
        lines.append(dict({k: v for k, v in c.items() if k != "per"}, Refs="cable", Qty=c["per"] * cable_n))
    return lines

if __name__ == "__main__":
    main_n, ui_n, cable_n = (int(a) for a in (sys.argv[1:] + ["10", "5", "5"][len(sys.argv) - 1:])[:3])
    merged = {}   # (supplier, supplier PN) -> line, quantities and refs summed across boards
    for l in bom_lines(main_n, ui_n, cable_n):
        if not l["Supplier"].strip():
            continue
        m = merged.setdefault((l["Supplier"], l["SupplierPN"]), dict(l, Qty=0, Refs=[]))
        m["Qty"] += l["Qty"]; m["Refs"].append(l["Refs"])
    os.makedirs(OUT, exist_ok=True)
    tme = [(k[1], m["Qty"]) for k, m in merged.items() if k[0] == "TME"]
    mouser = [(k[1], m["MPN"], m["Manufacturer"], m["Qty"], "; ".join(m["Refs"])) for k, m in merged.items() if k[0] == "Mouser"]
    with open(os.path.join(OUT, "tme-basket.csv"), "w", newline="", encoding="utf8") as fh:
        csv.writer(fh, delimiter=";").writerows(tme)
    with open(os.path.join(OUT, "mouser-bom.csv"), "w", newline="", encoding="utf8") as fh:
        w = csv.writer(fh)
        w.writerow(["Mouser No", "Mfr No", "Manufacturer", "Quantity", "Refs"])
        w.writerows(mouser)
    other = sorted({k[0] for k in merged} - {"TME", "Mouser"})
    print("Run: %d main, %d UI, %d cables -> %s: TME %d lines / %d parts, Mouser %d lines / %d parts%s"
          % (main_n, ui_n, cable_n, os.path.normpath(OUT), len(tme), sum(q for _, q in tme),
             len(mouser), sum(m[3] for m in mouser), "; other suppliers ignored: " + ", ".join(other) if other else ""))
