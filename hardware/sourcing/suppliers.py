# Minimal clients for the supplier APIs used by the scripts in this folder (stdlib only):
#   TME     API v2 (OAuth2 client_credentials -> Bearer), https://developers.tme.eu/en/api-doc/v2
#           Tokens created after 2026-05-14 only work with v2. Prices come back incl. VAT
#           ("GROSS"); tme_offer() converts them to excl. VAT.
#   Mouser  Search API v1 (needs a *Search* API key, not the Order API key). Prices come back
#           in the account's currency and are taken as excl. VAT.
#   LCSC    the product-detail JSON the lcsc.com product pages load (no key, USD prices).
#
# Keys: environment variables TME_TOKEN, TME_APP_SECRET, MOUSER_API_KEY, else the same names
# as KEY=value lines in ~/.config/heimdall/api-keys.env (or the file in $HEIMDALL_API_KEYS).
# Keep that file out of the repo.
import base64, json, math, os, re, time, urllib.error, urllib.parse, urllib.request

KEYS_FILE = os.environ.get("HEIMDALL_API_KEYS", os.path.expanduser("~/.config/heimdall/api-keys.env"))
COUNTRY, CURRENCY = "SE", "SEK"

def key(name):
    if os.environ.get(name):
        return os.environ[name]
    if os.path.exists(KEYS_FILE):
        for line in open(KEYS_FILE, encoding="utf8"):
            k, _, v = line.strip().partition("=")
            if k == name and v:
                return v
    raise SystemExit("missing API key %s (set it in the environment or in %s)" % (name, KEYS_FILE))

def _json(req, timeout=30, retries=2):
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            body = e.read()
            try:
                return dict(json.loads(body), _http=e.code)
            except ValueError:
                return {"_http": e.code, "_body": body[:300].decode(errors="replace")}
        except (TimeoutError, OSError):
            if attempt == retries:
                raise
            time.sleep(2)

def cheapest_buy(need, breaks, moq=1, mult=1):
    """Cheapest way to buy >= need: (qty, total, unit). Jumping to a higher price break
    is allowed when that makes the total cheaper. breaks = [(qty, unit price)]."""
    breaks = sorted(breaks)
    best = None
    for q0 in [need] + [a for a, _ in breaks if a > need]:
        q = math.ceil(max(q0, moq or 1) / (mult or 1)) * (mult or 1)
        unit = [p for a, p in breaks if a <= q]
        if unit and (best is None or q * unit[-1] < best[1]):
            best = (q, q * unit[-1], unit[-1])
    return best

# --- TME --------------------------------------------------------------------------------
_tme_token = {"value": None, "exp": 0}

def _tme_access_token():
    if _tme_token["value"] and time.time() < _tme_token["exp"] - 30:
        return _tme_token["value"]
    basic = base64.b64encode(("%s:%s" % (key("TME_TOKEN"), key("TME_APP_SECRET"))).encode()).decode()
    r = _json(urllib.request.Request("https://api.tme.eu/auth/token",
              data=urllib.parse.urlencode({"grant_type": "client_credentials"}).encode(),
              headers={"Authorization": "Basic " + basic,
                       "Content-Type": "application/x-www-form-urlencoded"}))
    if "access_token" not in r:
        raise SystemExit("TME auth failed: %s" % r)
    _tme_token.update(value=r["access_token"], exp=time.time() + r.get("expires_in", 300))
    return _tme_token["value"]

def tme_get(path, params):
    """GET an API v2 endpoint; params is a list of (key, value) so 'symbols[]' can repeat."""
    url = "https://api.tme.eu%s?%s" % (path, urllib.parse.urlencode([("country", COUNTRY)] + list(params)))
    return _json(urllib.request.Request(url, headers={"Authorization": "Bearer " + _tme_access_token(),
                                                      "Accept-Language": "en"}))

def _chunks(xs, n=50):
    return [xs[i:i + n] for i in range(0, len(xs), n)]

def tme_products(symbols=(), mpns=()):
    """Product info by TME symbol or by manufacturer part number (max 50 per call, batched)."""
    out = []
    for kind, xs in (("symbols[]", list(symbols)), ("mpns[]", list(mpns))):
        for c in _chunks(xs):
            out += tme_get("/products", [(kind, x) for x in c]).get("data", {}).get("elements", [])
    return out

def tme_search(phrase, limit=20):
    r = tme_get("/products/search", [("scope[]", "products"), ("phrase", phrase[:40]), ("limit", limit)])
    p = r.get("data", {}).get("products", {})
    return (p.get("elements") if isinstance(p, dict) else p) or []

def tme_offer(symbols):
    """{symbol: {"stock": n, "breaks": [(qty, unit excl. VAT)]}} in CURRENCY."""
    out = {}
    for c in _chunks(list(symbols)):
        r = tme_get("/products/data", [("currency", CURRENCY), ("scope[]", "prices"), ("scope[]", "stock")]
                    + [("symbols[]", s) for s in c])
        for e in r.get("data", {}).get("elements", []):
            pr = e.get("prices") or {}
            vat = 1 + pr["tax"]["rate"] / 100 if pr.get("type") == "GROSS" and pr.get("tax") else 1
            out[e["symbol"]] = {"stock": e.get("stock_quantity") or 0,
                                "breaks": [(p["amount"], p["price"] / vat) for p in pr.get("elements") or []]}
    return out

# --- Mouser -----------------------------------------------------------------------------
class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None   # surface the 3xx as an HTTPError instead of re-sending the POST as a GET

_no_redirect = urllib.request.build_opener(_NoRedirect)

def _mouser(endpoint, body, attempts=4):
    req = urllib.request.Request("https://api.mouser.com/api/v1/search/%s?apiKey=%s" % (endpoint, key("MOUSER_API_KEY")),
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "Accept": "application/json"})
    # The API now and then answers with a redirect or stalls; both pass after a short wait.
    for attempt in range(attempts):
        try:
            with _no_redirect.open(req, timeout=30) as resp:
                r = json.load(resp)
            break
        except (urllib.error.HTTPError, TimeoutError, OSError) as e:
            if attempt == attempts - 1:
                raise SystemExit("Mouser API unreachable (%s), try again later" % e)
            time.sleep(5 * (attempt + 1))
    time.sleep(0.7)   # stay well inside the API's rate limit
    if r.get("Errors"):
        raise SystemExit("Mouser API: %s" % r["Errors"])
    return (r.get("SearchResults") or {}).get("Parts") or []

def mouser_partnumber(pn, exact=True):
    body = {"SearchByPartRequest": {"mouserPartNumber": pn, "partSearchOptions": "Exact" if exact else "None"}}
    # the API now and then returns an empty result for a part it carries: ask once more
    return _mouser("partnumber", body) or (time.sleep(2) or _mouser("partnumber", body))

def mouser_keyword(kw, records=50, in_stock=True):
    return _mouser("keyword", {"SearchByKeywordRequest": {"keyword": kw, "records": records, "startingRecord": 0,
                                                          "searchOptions": "InStock" if in_stock else "None",
                                                          "searchWithYourSignUpLanguage": "false"}})

def mouser_price(s):
    """'1 234,56 kr' / '$1,234.56' -> float (the last ',' or '.' is the decimal mark)."""
    s = re.sub(r"[^0-9,.]", "", s)
    if "," in s and "." in s:
        dec = "," if s.rfind(",") > s.rfind(".") else "."
        s = s.replace("." if dec == "," else ",", "")
    return float(s.replace(",", "."))

def mouser_offer(part):
    return {"stock": int(part.get("AvailabilityInStock") or 0),
            "breaks": [(b["Quantity"], mouser_price(b["Price"])) for b in part.get("PriceBreaks") or []],
            "moq": int(part.get("Min") or 1), "mult": int(part.get("Mult") or 1),
            "lifecycle": part.get("LifecycleStatus")}

# --- LCSC -------------------------------------------------------------------------------
def lcsc_product(code):
    r = _json(urllib.request.Request("https://wmsc.lcsc.com/ftps/wm/product/detail?productCode=" + code,
                                     headers={"User-Agent": "Mozilla/5.0"}))
    time.sleep(0.5)
    p = r.get("result") or {}
    return p and {"mpn": p.get("productModel"), "stock": p.get("stockNumber") or 0,
                  "moq": p.get("minBuyNumber") or 1, "mult": p.get("split") or 1,
                  "breaks": [(x["ladder"], x["usdPrice"]) for x in p.get("productPriceList") or []]}

def usd_rate(to=CURRENCY):
    """ECB reference rate via frankfurter.dev."""
    r = _json(urllib.request.Request("https://api.frankfurter.dev/v1/latest?from=USD&to=" + to,
                                     headers={"User-Agent": "Mozilla/5.0"}))
    if "rates" not in r:
        raise SystemExit("exchange rate lookup failed: %s" % r)
    return r["rates"][to], r["date"]

def norm(pn):
    return re.sub(r"[^A-Z0-9]", "", pn.upper())
