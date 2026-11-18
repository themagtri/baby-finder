"""Polite fetch of joiebaby.co.il (Bambino K, official Joie importer) category pages.

The site is a React Router app; each category page ships its product list as an embedded
turbo-stream payload, which we decode (scripts/turbo.py). Two requests total, 2 s apart.
Usage: python -I scripts/fetch_joie.py      (run from repo root)
Writes data/raw/joie.json (git-ignored).
"""
import json, sys, time, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from polite import fetch, robots, check, Blocked
from turbo import payload, decode, walk

HOST = "joiebaby.co.il"
CATEGORIES = {"strollers": "/category/5027", "carseats": "/category/219"}
DELAY = 2.0

KEEP = ("id", "name", "catalogNumber", "quantity", "wasInStock", "title", "price", "discount",
        "brand", "age", "color", "isMainColor", "mainColorProductId", "types", "isofix",
        "foldType", "standard", "description", "specifications")


def main():
    rp = robots(HOST)
    byid = {}
    for cat, path in CATEGORIES.items():
        time.sleep(DELAY)
        url = f"https://{HOST}{path}"
        check(rp, url)
        html, _ = fetch(url, "text/html")
        ps = payload(html)
        if not ps:
            raise Blocked(f"STOP: no embedded data at {url} (layout changed or blocked)")
        prods = walk(decode(ps[0]), lambda d: "catalogNumber" in d and "price" in d)
        print(f"{cat}: {len(prods)} product objects")
        for p in prods:
            byid[p["id"]] = {k: p.get(k) for k in KEEP}
    out = pathlib.Path("data/raw"); out.mkdir(parents=True, exist_ok=True)
    (out / "joie.json").write_text(json.dumps({"host": HOST, "fetched": time.strftime("%Y-%m-%d"),
                                              "products": list(byid.values())}, ensure_ascii=False), encoding="utf-8")
    print(f"saved {len(byid)} unique products")


if __name__ == "__main__":
    main()
