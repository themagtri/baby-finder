"""Brand logos from Wikimedia Commons - public domain / CC0 files only (same rule as bike-finder).

For each brand: search Commons (File namespace) for "<brand> logo", read each candidate's licence from
the API (extmetadata.LicenseShortName), accept only Public domain / PD-* / CC0, prefer SVG, and save to
logos/<slug>.svg|png with an entry in logos/credits.json. Brands without such a file get no logo (the site
shows a monogram). 1.5 s between API calls. Trademarks are shown for identification only.
Usage: python -I scripts/fetch_logos.py      (run from repo root)

IMPORTANT: the search is by name only and finds other companies with the same name (Cybex International =
fitness, Joie de Vivre = hotels, ANEX Tour = travel). Every result must be checked by hand (description and
categories on Commons) before it is kept; on 2026-11-18 only Chicco, Graco, Recaro and Thule passed.
"""
import json, re, sys, time, pathlib, urllib.parse, urllib.request

sys.stdout.reconfigure(encoding="utf-8")
UA = "baby-finder-research/0.1 (+https://github.com/themagtri/baby-finder)"
API = "https://commons.wikimedia.org/w/api.php"
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "logos"
DELAY = 1.5
BRANDS = ["Cybex", "Chicco", "Joie", "BeSafe", "Bugaboo", "Nuna", "Maxi-Cosi", "Britax", "Stokke", "UPPAbaby",
          "Baby Jogger", "Inglesina", "Doona", "Joolz", "Graco", "Evenflo", "Kinderkraft", "Anex", "Twigy",
          "Sport Line", "Moona", "Silver Cross", "Peg Perego", "Recaro", "Thule", "Bebe Confort", "Babyzen"]
OK_LICENCE = re.compile(r"public domain|^pd\b|pd-|cc0", re.I)


def api(**params):
    params.update(format="json")
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(params), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        out = json.loads(r.read().decode("utf-8"))
    time.sleep(DELAY)
    return out


def slug(b):
    return re.sub(r"[^a-z0-9]+", "-", b.lower()).strip("-")


def best_file(brand):
    res = api(action="query", list="search", srnamespace=6, srsearch=f"{brand} logo", srlimit=10)
    titles = [h["title"] for h in res.get("query", {}).get("search", [])]
    # the file name must contain the brand name (avoid unrelated logos)
    key = re.sub(r"[^a-z]", "", brand.lower())
    titles = [t for t in titles if key in re.sub(r"[^a-z]", "", t.lower())]
    if not titles:
        return None
    info = api(action="query", titles="|".join(titles), prop="imageinfo", iiprop="url|extmetadata|mime")
    cands = []
    for p in info.get("query", {}).get("pages", {}).values():
        ii = (p.get("imageinfo") or [{}])[0]
        md = ii.get("extmetadata", {})
        lic = (md.get("LicenseShortName", {}) or {}).get("value", "")
        if not OK_LICENCE.search(lic):
            continue
        author = re.sub(r"<[^>]+>", "", (md.get("Artist", {}) or {}).get("value", "")).strip()
        cands.append({"title": p["title"], "url": ii.get("url"), "mime": ii.get("mime", ""),
                      "page": ii.get("descriptionurl"), "license": lic, "author": author})
    cands.sort(key=lambda c: (c["mime"] != "image/svg+xml", len(c["title"])))
    return cands[0] if cands else None


def main():
    OUT.mkdir(exist_ok=True)
    credits = {}
    for b in BRANDS:
        try:
            f = best_file(b)
        except Exception as e:
            print(f"{b}: error {str(e)[:60]}"); continue
        if not f:
            print(f"{b}: no public-domain logo found"); continue
        ext = ".svg" if f["mime"] == "image/svg+xml" else ".png"
        req = urllib.request.Request(f["url"], headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
        time.sleep(DELAY)
        path = OUT / (slug(b) + ext)
        path.write_bytes(data)
        credits[b] = {"file": f"logos/{path.name}", "commons_title": f["title"], "source_page": f["page"],
                      "license": f["license"], "author": f["author"]}
        print(f"{b}: {f['title']} [{f['license']}]")
    (OUT / "credits.json").write_text(json.dumps(credits, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(credits)} logos saved")


if __name__ == "__main__":
    main()
