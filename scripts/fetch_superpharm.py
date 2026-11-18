"""Polite fetch of Super-Pharm online (shop.super-pharm.co.il) strollers and car seats.

Super-Pharm is also a marketplace: many products are sold and shipped by an outside shop. For each product
we read the seller from the page's supplier block ("המוצר ימכר ויסופק ע״י מוכר חיצוני" + shop name);
no block = sold by Super-Pharm itself. Price/availability come from the page's schema.org Product/Offer.
Import status is taken only if the main product block itself says "יבוא רשמי" / "יבוא מקביל".
robots.txt respected, 2 s between requests, stop on block.
Usage: python -I scripts/fetch_superpharm.py      (run from repo root; ~2 s per product)
Writes data/raw/superpharm.json (git-ignored).
"""
import json, re, sys, time, pathlib, html as H, http.client
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from polite import fetch, robots, check

HOST = "shop.super-pharm.co.il"
CATS = {
    "stroller": "/infants-and-toddlers/trolleys-and-cases/strollers/c/25171100",
    "carseat": "/infants-and-toddlers/car-seats/car-safety-seat/c/25151200",
    "booster": "/infants-and-toddlers/car-seats/booster/c/25151100",
    "infant": "/infants-and-toddlers/car-seats/carrycot/c/25151300",
}
DELAY = 2.0
MAX_PAGES = 15


def product_links(html):
    for m in re.findall(r'<script[^>]*ld\+json[^>]*>(.*?)</script>', html, re.S):
        if "CollectionPage" in m:
            try:
                d = json.loads(m)
                return [x["url"] for x in d.get("mainEntity", {}).get("itemListElement", []) if x.get("url")]
            except Exception:
                pass
    return []


def parse_product(html, url):
    prod = None
    for m in re.findall(r'<script[^>]*ld\+json[^>]*>(.*?)</script>', html, re.S):
        if '"Product"' in m:
            try:
                prod = json.loads(m); break
            except Exception:
                # the page's JSON-LD can carry a raw HTML description; fall back to regexes
                prod = {"name": (re.search(r'"name"\s*:\s*"([^"]+)"', m) or [None, None])[1],
                        "brand": {"name": (re.search(r'"brand"[^}]*"name"\s*:\s*"([^"]+)"', m, re.S) or [None, ""])[1]},
                        "offers": {"price": (re.search(r'"price"\s*:\s*"([\d.]+)"', m) or [None, None])[1],
                                   "availability": (re.search(r'"availability"\s*:\s*"([^"]+)"', m) or [None, ""])[1]}}
                break
    if not prod:
        return None
    sup = re.search(r'alt="([^"]+)"\s*/>\s*<div class="supplier-details">', html)
    shop = H.unescape(sup.group(1)).strip() if sup else ""
    # main block = from the start of the product content to the supplier block (or first carousel)
    end = sup.start() if sup else html.find("מוצרים שראו גם")
    start = html.find("<h1")
    block = html[start:end] if 0 <= start < end else ""
    imp = "official" if "יבוא רשמי" in block else ("parallel" if "יבוא מקביל" in block else "")
    off = prod.get("offers") or {}
    price = off.get("price")
    return {"name": H.unescape(prod.get("name") or "").strip(), "brand": (prod.get("brand") or {}).get("name", ""),
            "price": float(price) if price else None, "in_stock": "InStock" in (off.get("availability") or ""),
            "shop": shop, "import": imp, "url": "https://" + HOST + url if url.startswith("/") else url}


def get(u):
    """One retry after a pause when the connection drops mid-page (big pages); a block still stops (polite.Blocked)."""
    for attempt in (1, 2):
        try:
            return fetch(u, "text/html")[0]
        except (http.client.IncompleteRead, ConnectionError, TimeoutError) as e:
            if attempt == 2: raise
            print(f"  retry after drop: {type(e).__name__}", flush=True)
            time.sleep(10)


def main():
    rp = robots(HOST); time.sleep(DELAY)
    links = {}
    for cat, path in CATS.items():
        seen_page = set()
        for page in range(MAX_PAGES):
            u = f"https://{HOST}{path}" + (f"?page={page}" if page else "")
            check(rp, u)
            html = get(u)
            got = [l for l in product_links(html) if l not in seen_page]
            print(f"{cat} page {page}: {len(got)} new", flush=True)
            time.sleep(DELAY)
            if not got:
                break
            seen_page.update(got)
            for l in got: links.setdefault(l, cat)
    cache = pathlib.Path("data/raw/superpharm_partial.json")
    done = json.loads(cache.read_text(encoding="utf-8")) if cache.exists() else {}
    for i, (l, cat) in enumerate(links.items()):
        if l in done: continue
        u = "https://" + HOST + l
        check(rp, u)
        p = parse_product(get(u), l)
        if p: p["cat_page"] = cat
        done[l] = p
        if i % 10 == 0:
            print(f"product {i+1}/{len(links)}", flush=True)
            cache.write_text(json.dumps(done, ensure_ascii=False), encoding="utf-8")
        time.sleep(DELAY)
    out = [p for p in done.values() if p]
    pathlib.Path("data/raw/superpharm.json").write_text(json.dumps(
        {"host": HOST, "fetched": time.strftime("%Y-%m-%d"), "products": out}, ensure_ascii=False, indent=1), encoding="utf-8")
    cache.unlink(missing_ok=True)
    print(f"saved {len(out)} products")


if __name__ == "__main__":
    main()
