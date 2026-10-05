# Searches TME and Mouser for a part number or phrase and lists what's in stock, with the
# price at a given quantity (excl. VAT, in suppliers.CURRENCY) — for finding substitutes
# when a BOM part runs out. Mouser's keyword search only returns in-stock parts.
#
#   python find_part.py "10uF 50V X5R 1206"
#   python find_part.py BSS84 -q 20          price at 20 pcs (default 10)
import argparse
import suppliers as s

ap = argparse.ArgumentParser()
ap.add_argument("query", nargs="+")
ap.add_argument("-q", "--qty", type=int, default=10)
ap.add_argument("-n", type=int, default=8, help="results per supplier")
a = ap.parse_args()

def row(supplier, pn, mfr, stock, buy, desc):
    price = "%d @ %.2f = %.1f" % buy if buy else "-"
    print("  %-6s %-26s %-16s %8d  %-24s %s" % (supplier, pn[:26], mfr[:16], stock, price, desc[:60]))

for q in a.query:
    print("## %s" % q)
    found = s.tme_search(q)
    offers = s.tme_offer([e["symbol"] for e in found])
    res = []
    for e in found:
        o = offers.get(e["symbol"], {"stock": 0, "breaks": []})
        b = s.cheapest_buy(a.qty, o["breaks"], e.get("minimal_amount"), e.get("multiples"))
        res.append((o["stock"], e["symbol"], e["manufacturer"]["name"], b, e.get("description", "")))
    for st, pn, mfr, b, d in sorted(res, key=lambda r: -r[0])[:a.n]:
        row("TME", pn, mfr, st, b and (b[0], b[2], b[1]), d)
    # Mouser's keyword search matches loosely (any word), so keep its relevance order
    for p in s.mouser_keyword(q)[:a.n]:
        o = s.mouser_offer(p)
        b = s.cheapest_buy(a.qty, o["breaks"], o["moq"], o["mult"])
        row("Mouser", p["MouserPartNumber"], p["Manufacturer"], o["stock"], b and (b[0], b[2], b[1]),
            p.get("Description") or "")
