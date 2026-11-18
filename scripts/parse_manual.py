"""Parse seller pages the owner saved as PDF (sites that block automated access).

Input: a folder of PDFs (default: the owner's Desktop folder). For every product link in a PDF we read
the text in the area below the link (same column, until the next product) and take:
regular price, club price ("מחיר מועדון"), sale price, and "out of stock".
Nothing is guessed: a value that is not printed stays empty.
Usage: python -I scripts/parse_manual.py ["<folder>"]      (run from repo root)
Writes data/raw/manual.json (git-ignored).
"""
import json, pathlib, re, sys, time, urllib.parse
import pymupdf as fitz

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT = pathlib.Path(r"C:\Users\USER\Desktop\עגלות וכסאות בטיחות")

SELLERS = {"cybexonline.co.il": "cybex", "chiccoisrael.co.il": "chicco", "shilav.co.il": "shilav",
           "baby-star.co.il": "babystar", "motsesim.co.il": "motzetzim", "agalease-baby.co.il": "agalease",
           "minene.co.il": "minena", "minena.co.il": "minena"}
NUM = r"([\d,]+(?:\.\d+)?)"


def money(s):
    return float(s.replace(",", ""))


def parse_block(text):
    t = " ".join(text.split())
    out = {}
    # Cybex lists "מחיר", "מחיר מועדון" and Eilat prices (VAT-free, ignored). PDF text comes out word-reversed.
    m = re.search(r"₪\s*" + NUM + r"\s*:מחיר(?!\s*באילת)", t)
    if m: out["regular"] = money(m.group(1))
    m = re.search(r"₪\s*" + NUM + r"\s*:מועדון מחיר", t)
    if m: out["club"] = money(m.group(1))
    if "regular" not in out:  # Chicco style: one or two "₪1,234.00" values (sale shows old + new)
        vals = [money(v) for v in re.findall(r"₪\s?" + NUM, t)]
        vals = [v for v in vals if v >= 20]
        if len(vals) == 1:
            out["regular"] = vals[0]
        elif len(vals) >= 2:
            out["regular"], out["sale"] = max(vals[:2]), min(vals[:2])
    if re.search(r"המלאי אזל|אזל\s*מהמלאי|מהמלאי\s*אזל", t):
        out["oos"] = True
    return out


def parse_pdf(path):
    doc = fitz.open(path)
    items = []
    for page in doc:
        links = []
        for l in page.get_links():
            u = l.get("uri") or ""
            host = urllib.parse.urlparse(u).netloc.replace("www.", "")
            if host in SELLERS and re.search(r"/products?/", u):
                name = " ".join(page.get_textbox(l["from"]).split())
                if name:
                    links.append((l["from"], u, host, name))
        for i, (r, u, host, name) in enumerate(links):
            # area below this link, same column, up to the next product link that starts lower in the column
            nxt = [r2.y0 for (r2, *_rest) in links if r2.y0 > r.y1 + 2 and abs(r2.x0 - r.x0) < 60]
            y1 = min(nxt) if nxt else r.y1 + 220
            area = fitz.Rect(r.x0 - 30, r.y0, r.x1 + 30, y1)
            block = page.get_textbox(area)
            items.append({"seller": SELLERS[host], "name": name, "url": u, **parse_block(block),
                          "source_file": path.name})
    # dedupe by url (a link can appear twice: image + title)
    seen, out = set(), []
    for it in items:
        if it["url"] in seen: continue
        seen.add(it["url"]); out.append(it)
    return out


def main(folder):
    folder = pathlib.Path(folder)
    all_items = []
    for f in sorted(folder.rglob("*.pdf")):
        got = parse_pdf(f)
        print(f"{f.name[:55]:55} {len(got)} products", file=sys.stderr)
        all_items += got
    by_url = {}
    for it in all_items:  # same product saved in two PDFs: keep the one with more fields
        k = it["url"]
        if k not in by_url or len(it) > len(by_url[k]): by_url[k] = it
    out = ROOT / "data" / "raw" / "manual.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    mtime = max(f.stat().st_mtime for f in folder.rglob("*.pdf"))
    out.write_text(json.dumps({"fetched": time.strftime("%Y-%m-%d", time.localtime(mtime)),
                               "products": list(by_url.values())}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"saved {len(by_url)} products -> {out.relative_to(ROOT)}", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT)
