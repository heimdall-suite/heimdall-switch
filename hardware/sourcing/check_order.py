# Checks the order files from hardware/kicad/order_export.py against the live TME and
# Mouser APIs before ordering: every line exists, is orderable, meets the minimum order
# quantity / multiple and is in stock; prints the cost per line and the order totals
# (excl. VAT, in suppliers.CURRENCY). Also points out where a higher price break would
# cost no more than the quantity ordered.
#
#   python check_order.py            checks ../order/tme-basket.csv and ../order/mouser-bom.csv
import csv, os, sys
import suppliers as s

ORDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "order")
BLOCKING = {"CANNOT_BE_ORDERED", "NOT_IN_OFFER", "PRODUCT_BLOCKED", "ONLY_FOR_SPECIAL_ORDER"}
problems = 0

def line(supplier, pn, qty, offer, moq, mult, notes):
    global problems
    if qty < moq: notes.append("below MOQ %d" % moq)
    if mult and qty % mult: notes.append("not a multiple of %d" % mult)
    if offer["stock"] < qty: notes.append("only %d in stock" % offer["stock"])
    unit = [p for a, p in sorted(offer["breaks"]) if a <= qty]
    cost = qty * unit[-1] if unit else None
    if cost is None: notes.append("no price at this quantity")
    best = s.cheapest_buy(qty, offer["breaks"], moq, mult)
    hint = " (buy %d for %.1f)" % (best[0], best[1]) if best and cost and best[0] > qty and best[1] <= cost else ""
    bad = [n for n in notes if not n.startswith("lifecycle")]   # lifecycle is a warning only
    problems += bool(bad)
    print("%-6s %-24s %5d  %8s%s%s" % (supplier, pn, qty, "%.1f" % cost if cost else "-", hint,
                                        "  <-- " + ", ".join(notes) if notes else ""))
    return cost or 0

tme = [(r[0], int(r[1])) for r in csv.reader(open(os.path.join(ORDER, "tme-basket.csv"), encoding="utf8"), delimiter=";") if r]
info = {e["symbol"]: e for e in s.tme_products(symbols=[p for p, _ in tme])}
offers = s.tme_offer([p for p, _ in tme if p in info])
tme_total = 0
for pn, qty in tme:
    if pn not in info:
        print("TME    %-24s %5d  not found" % (pn, qty)); problems += 1; continue
    e = info[pn]
    notes = ["status " + x for x in e.get("product_status", []) if x in BLOCKING]
    tme_total += line("TME", pn, qty, offers.get(pn, {"stock": 0, "breaks": []}),
                      e.get("minimal_amount") or 1, e.get("multiples") or 1, notes)

mouser = [(r["Mouser No"], int(r["Quantity"])) for r in csv.DictReader(open(os.path.join(ORDER, "mouser-bom.csv"), encoding="utf8"))]
mouser_total = 0
for pn, qty in mouser:
    part = next((p for p in s.mouser_partnumber(pn) if p["MouserPartNumber"] == pn), None)
    if not part:
        print("Mouser %-24s %5d  not found" % (pn, qty)); problems += 1; continue
    o = s.mouser_offer(part)
    notes = ["lifecycle " + o["lifecycle"]] if o["lifecycle"] else []
    mouser_total += line("Mouser", pn, qty, o, o["moq"], o["mult"], notes)

print("\nTME %.1f + Mouser %.1f = %.1f %s excl. VAT, shipping not included; %d line(s) with problems"
      % (tme_total, mouser_total, tme_total + mouser_total, s.CURRENCY, problems))
sys.exit(1 if problems else 0)
