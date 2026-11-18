"""Cross-check our catalog against BabyGearLab (owner's request, 2026-11-18).

What is checked: for every product of ours that BabyGearLab reviews (exact model match only, e.g.
"NextFit Zip Air" is NOT the reviewed "NextFit Zip"), its category (infant / convertible / booster /
travel / full-size / double) must agree with ours. Products BabyGearLab does not cover are left as they are
(owner: verify what can be verified). Their scores are never used or shown (owner + car-seat rule).

Polite: robots.txt, 2 s between requests; cached in data/raw/bgl_*.json (git-ignored).
Usage: python -I scripts/check_bgl.py [--refresh]      (run from repo root)
Writes data/bgl_check.csv; exits non-zero if a category disagrees, so it can gate a publish.
"""
import csv, json, pathlib, re, sys, time, html, datetime
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from polite import fetch, robots, check

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
HOST = "https://www.babygearlab.com"
LISTS = ["/catalog/car-seats", "/t/strollers"]
DELAY = 2.0

# BabyGearLab category -> our categories that agree with it
AGREE = {
    "infant-car-seat": {"infant"},
    "convertible-car-seat": {"convertible", "toddler"},
    "booster-seat": {"booster"},
    "travel-stroller": {"travel"},
    "full-size-stroller": {"stroller", "full"},   # BGL rates the frame; "full" = seller sells it with cot/seat
    "jogging-stroller": {"stroller", "full", "travel"},
    "double-stroller": {"twin"},
    "double-travel-stroller": {"twin"},
}
# a seller listing that adds a newborn pack / bassinet to a reviewed travel stroller is still the same stroller
BUNDLE_OK = {("travel-stroller", "full")}


def slug(s):
    s = s.lower().replace("™", "").replace("®", "").replace("‎", "").replace("³", "-3")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def catalog(refresh):
    cache = RAW / "bgl_catalog.json"
    if cache.exists() and not refresh:
        return json.loads(cache.read_text())
    rp = robots("www.babygearlab.com"); time.sleep(DELAY)
    paths = set()
    for pg in LISTS:
        u = HOST + pg; check(rp, u)
        h, _ = fetch(u, "text/html")
        paths |= set(re.findall(r"/reviews/[a-z0-9-]+/[a-z0-9-]+/[a-z0-9-]+", h))
        time.sleep(DELAY)
    cache.write_text(json.dumps(sorted(paths), indent=0))
    return sorted(paths)


def our_slug(r):
    base = r["model"].split("·")[0]
    latin = " ".join(re.findall(r"[A-Za-z0-9³™®\- ]+", base)).strip()  # drop the Hebrew part of mixed names
    s = slug(latin)
    b = slug(r["brand"]) if r["brand"] else ""
    if b == "stokke" and "yoyo" in s: s = s  # brand already implied
    if b and not s.startswith(b): s = b + "-" + s
    s = re.sub(r"-(stroller|car-seat|cleartex|with-ramble-xl)$", "", s)
    return s.replace("-3", "-3")


def main(refresh=False):
    sys.stdout.reconfigure(encoding="utf-8")
    paths = catalog(refresh)
    by_slug = {p.rsplit("/", 1)[1]: p for p in paths}
    rows = list(csv.DictReader(open(ROOT / "data" / "catalog.csv", encoding="utf-8")))
    out, bad = [], 0
    for r in rows:
        s = our_slug(r)
        s2 = re.sub(r"-(black|white|grey|gray|beige)$", "", s)
        p = by_slug.get(s) or by_slug.get(s2)
        if not p:
            continue
        bcat = p.split("/")[3]
        ours = r["type"] or r["seat_group"]
        ok = ours in AGREE.get(bcat, set()) or (bcat, ours) in BUNDLE_OK
        bad += not ok
        out.append({"seller": r["seller"], "model": r["model"], "our_category": ours, "bgl_category": bcat,
                    "bgl_url": HOST + p, "result": "match" if ok else "MISMATCH",
                    "checked": datetime.date.today().isoformat()})
    with open(ROOT / "data" / "bgl_check.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, ["seller", "model", "our_category", "bgl_category", "bgl_url", "result", "checked"])
        w.writeheader(); w.writerows(out)
    print(f"BabyGearLab covers {len(out)} of {len(rows)} products; mismatches: {bad}")
    for o in out:
        print(f"  {o['result']:8} {o['seller']:10} {o['model'][:45]:45} ours={o['our_category']:11} bgl={o['bgl_category']}")
    return bad


if __name__ == "__main__":
    sys.exit(1 if main("--refresh" in sys.argv) else 0)
