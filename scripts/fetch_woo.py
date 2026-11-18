"""Polite fetch of a WooCommerce store's public Store API (/wp-json/wc/store/v1/products).

Rules (CLAUDE.md): respects robots.txt, >= 2 s between requests, stops on 401/403/429/503 or a block page.
Usage: python -I scripts/fetch_woo.py <host> <slug>      (run from repo root)
Writes data/raw/<slug>.json (git-ignored).
"""
import json, sys, time, pathlib, urllib.error
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from polite import fetch, robots, check, Blocked

DELAY = 2.0

def main(host, slug):
    rp = robots(host); time.sleep(DELAY)
    out, page = [], 1
    while True:
        url = f"https://{host}/wp-json/wc/store/v1/products?per_page=100&page={page}"
        check(rp, url)
        try:
            body, hdr = fetch(url, "application/json")
        except urllib.error.HTTPError as e:
            if e.code == 400 and page > 1: break  # past the last page
            raise Blocked(f"STOP: HTTP {e.code} at {url}")
        if not body.lstrip().startswith("["):
            raise Blocked(f"STOP: unexpected (block?) page at {url}")
        prods = json.loads(body)
        total = int(hdr.get("X-WP-TotalPages") or 0)
        print(f"page {page}/{total or '?'}: {len(prods)}")
        out += prods
        if not prods or (total and page >= total): break
        page += 1
        time.sleep(DELAY)
    p = pathlib.Path("data/raw"); p.mkdir(parents=True, exist_ok=True)
    (p / f"{slug}.json").write_text(json.dumps({"host": host, "fetched": time.strftime("%Y-%m-%d"), "products": out}, ensure_ascii=False), encoding="utf-8")
    print(f"saved {len(out)} products")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
