# Prices every BOM line of a prototype run at LCSC, TME and Mouser, to compare suppliers
# (excl. VAT, in suppliers.CURRENCY; LCSC's USD converted at the ECB rate).
#   LCSC    the schematic's LCSC field (the LCSC alternative part)
#   TME     the schematic's MPN field (the part actually ordered), plus the Supplier PN
#   Mouser  when that line is ordered from TME / Mouser
# Lines with the same part on several boards are merged. Each cell is the cheapest way to
# buy at least the needed quantity there (minimum order quantity and price breaks included,
# e.g. LCSC's strips of 100 resistors); "-" = not carried or no price, "*" = less in stock
# than needed (left out of the totals). Substitutes aren't searched for: use find_part.py.
# Shipping isn't included.
#
#   python compare.py                10 main boards, 5 UI boards, 5 cables
#   python compare.py 5 2 2
import os, sys
import suppliers as s
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kicad"))
from order_export import bom_lines

runs = (sys.argv[1:] + ["10", "5", "5"][len(sys.argv) - 1:])[:3]
lines = {}
for l in bom_lines(*(int(a) for a in runs)):
    if not (l["MPN"] or l["LCSC"]):
        continue
    m = lines.setdefault((l["MPN"], l["LCSC"]), dict(l, Qty=0, Refs=[]))
    m["Qty"] += l["Qty"]; m["Refs"].append(l["Refs"])
lines = list(lines.values())
usd, usd_date = s.usd_rate()

def tme_pns(l):
    return [l["MPN"]] + ([l["SupplierPN"]] if l["Supplier"] == "TME" else [])

found = s.tme_products(mpns=sorted({l["MPN"] for l in lines if l["MPN"]}),
                       symbols=sorted({l["SupplierPN"] for l in lines if l["Supplier"] == "TME"}))
tme_by = {}
for e in found:
    for m in set(e["manufacturer_symbols"] + [e["symbol"]]):
        tme_by.setdefault(s.norm(m), {})[e["symbol"]] = e
tme_offers = s.tme_offer(sorted({e["symbol"] for e in found}))

def pick(options):
    """Cheapest option with enough stock, else the cheapest one (shown with a '*')."""
    options = [o for o in options if o]
    ok = [o for o in options if o[1]]
    return min(ok or options, key=lambda o: o[0]) if options else None

def tme_cell(l):
    opts = []
    for pn in tme_pns(l):
        for e in tme_by.get(s.norm(pn), {}).values():
            o = tme_offers.get(e["symbol"])
            b = o and s.cheapest_buy(l["Qty"], o["breaks"], e.get("minimal_amount"), e.get("multiples"))
            opts.append(b and (b[1], o["stock"] >= b[0]))
    return pick(opts)

def mouser_cell(l):
    pn = l["SupplierPN"] if l["Supplier"] == "Mouser" else l["MPN"]
    opts = []
    for p in s.mouser_partnumber(pn) if pn else []:
        if s.norm(pn) not in (s.norm(p["ManufacturerPartNumber"]), s.norm(p["MouserPartNumber"])):
            continue
        o = s.mouser_offer(p)
        b = s.cheapest_buy(l["Qty"], o["breaks"], o["moq"], o["mult"])
        opts.append(b and (b[1], o["stock"] >= b[0]))
    return pick(opts)

def lcsc_cell(l):
    p = s.lcsc_product(l["LCSC"]) if l["LCSC"] else None
    b = p and s.cheapest_buy(l["Qty"], p["breaks"], p["moq"], p["mult"])
    return b and (b[1] * usd, p["stock"] >= b[0])

def fmt(c):
    return "%9s" % ("-" if not c else "%.1f%s" % (c[0], "" if c[1] else "*"))

totals = {k: [0, 0] for k in ("LCSC", "TME", "Mouser")}   # SEK, lines counted
print("%-30s %-24s %4s %9s %9s %9s" % ("Refs", "MPN (ordered)", "qty", "LCSC", "TME", "Mouser"))
for l in lines:
    cells = {"LCSC": lcsc_cell(l), "TME": tme_cell(l), "Mouser": mouser_cell(l)}
    for k, c in cells.items():
        if c and c[1]:
            totals[k][0] += c[0]; totals[k][1] += 1
    print("%-30s %-24s %4d %s %s %s" % ("; ".join(l["Refs"])[:30], l["MPN"][:24], l["Qty"],
                                         fmt(cells["LCSC"]), fmt(cells["TME"]), fmt(cells["Mouser"])))
print("%-60s %9.1f %9.1f %9.1f" % ("totals %s (in-stock lines only)" % s.CURRENCY,
                                   totals["LCSC"][0], totals["TME"][0], totals["Mouser"][0]))
print("%-60s %9d %9d %9d   of %d lines; USD at %.4f (ECB %s)" % ("lines covered", totals["LCSC"][1], totals["TME"][1],
                                                                totals["Mouser"][1], len(lines), usd, usd_date))
