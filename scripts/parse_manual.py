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


def parse_shilav(doc, path):
    """Shilav cards are one big link (name + prices). A card cut by a page break continues at the top of the next
    page under the same URL, so join all segments of a URL first. Club price = the number right before 'מחיר מועדון'."""
    parts = {}
    for page in doc:
        for l in page.get_links():
            u = l.get("uri") or ""
            if "shilav.co.il" in u and "/products/" in u:
                t = page.get_textbox(l["from"]).strip()
                if t and t not in parts.setdefault(u, []):
                    parts[u].append(t)
    out = []
    for u, segs in parts.items():
        text = "\n".join(segs)
        head = text.split("₪", 1)[0]
        name = " ".join(head.split())
        if not name or "₪" not in text:
            continue
        it = {"seller": "shilav", "name": name, "url": u, "source_file": path.name}
        m = re.search(r"₪\s*" + NUM, text)
        if m: it["regular"] = money(m.group(1))
        m = re.search(r"₪?\s*" + NUM + r"\s*מחיר מועדון", text)
        if m and money(m.group(1)) < it.get("regular", 1e9): it["club"] = money(m.group(1))
        if re.search(r"אזל|לא במלאי|חסר במלאי", text): it["oos"] = True
        out.append(it)
    return out


CARD_HOSTS = {"agalease-baby.co.il": "agalease", "baby-star.co.il": "babystar", "motsesim.co.il": "motzetzim"}
NOISE = re.compile(r"https?:|www\.|filter|\?|שיווק ופרסום|צדדים שלישיים|שותפי|הסכמה|עוגיות|שימוש באתר|הגלישה|מדיניות|cookies|הנחה|^מבצע$|השוואת מוצרים|^\d+/$|^[()]$|אזל|חדש באתר|יבואן רשמי|יבוא רשמי|יבוא מקביל|^\d+\+$|₪|^\d+%")


LABEL = re.compile(r"^(טיולונים|כסאות בטיחות|כיסאות בטיחות|עגלות תינוק|עגלות תאומים|תאומים / אחים|"
                   r"עגלות תאומים / אחים|סלקלים|בוסטרים)$|נעזור לכם|לשימושים")


def parse_cards(doc, path):
    """Agalease / Baby Star / Motzetzim category PDFs: a product is several link pieces (image, badge, title).
    Join all pieces of one URL into one card area (also across a page break), read its words in RTL order
    (scripts/rtl_text.py), then take name / prices / stock / import status from the card's lines."""
    sys.path.insert(0, str(pathlib.Path(__file__).parent))
    from rtl_text import lines_in
    cards = {}
    for pno, page in enumerate(doc):
        per = {}
        for l in page.get_links():
            u = l.get("uri") or ""
            host = urllib.parse.urlparse(u).netloc.replace("www.", "")
            if host in CARD_HOSTS and "/products/" in u:
                key = "https://" + host + "/products/" + u.split("/products/")[1].split("?")[0].strip("/")
                per.setdefault((key, host), []).append(fitz.Rect(l["from"]))
        for (key, host), rs in per.items():
            r = rs[0]
            for x in rs[1:]: r |= x
            area = fitz.Rect(r.x0 - 3, r.y0, r.x1 + 3, min(r.y1 + 45, page.rect.y1))
            c = cards.setdefault(key, {"seller": CARD_HOSTS[host], "lines": []})
            for ln in lines_in(page, area):
                ln = " ".join(ln.split())
                if ln not in c["lines"]: c["lines"].append(ln)
    out = []
    for url, c in cards.items():
        ls = c["lines"]
        text = "\n".join(ls)
        it = {"seller": c["seller"], "url": url, "source_file": path.name}
        names = [l for l in ls if not NOISE.search(l) and len(l) > 6 and re.search(r"[֐-׿A-Za-z]{3}", l)]
        brand_line = next((l for l in ls if "|" in l and len(l) < 40), "")
        names = [l for l in names if l != brand_line]
        if not names: continue
        # the title = clean lines right before the first price, walking back until a category label / sentence
        first_price = next((i for i, l in enumerate(ls) if "₪" in l), len(ls))
        before = []
        for l in reversed(ls[:first_price]):
            if LABEL.search(l) or "." in l or len(l) > 70: break
            if l in names and l not in before: before.insert(0, l)
        it["name"] = (" ".join(before) if before else max(names, key=len)).replace(" ' ", "'")
        it["brand_hint"] = brand_line
        vals = [money(v) for v in re.findall(r"₪\s*" + NUM, text) if money(v) >= 20]
        club = re.search(r"₪\s*" + NUM + r"\s*מחיר לחברי מועדון", text)
        if club:
            it["club"] = money(club.group(1)); rest = [v for v in vals if v != it["club"]]
            if rest: it["regular"] = max(rest)
        elif len(vals) >= 2:
            it["regular"], it["sale"] = max(vals[:2]), min(vals[:2])
            if it["regular"] == it["sale"]: it.pop("sale")
        elif vals:
            it["regular"] = vals[0]
        if re.search(r"אזל", text): it["oos"] = True
        if re.search(r"יבואן רשמי|יבוא רשמי", text): it["import"] = "official"
        elif "יבוא מקביל" in text: it["import"] = "parallel"
        out.append(it)
    return out


def card_lines(doc, match, area_of):
    """Join every link piece of one product URL per page; read the card's lines (RTL order) from area_of(rect, page)."""
    sys.path.insert(0, str(pathlib.Path(__file__).parent))
    from rtl_text import lines_in
    cards = {}
    for page in doc:
        per = {}
        for l in page.get_links():
            u = (l.get("uri") or "").split("?")[0]
            if match(u): per.setdefault(u, []).append(fitz.Rect(l["from"]))
        for u, rs in per.items():
            r = rs[0]
            for x in rs[1:]: r |= x
            ls = cards.setdefault(u, [])
            for ln in lines_in(page, area_of(r, page)):
                ln = " ".join(ln.split())
                if ln and ln not in ls: ls.append(ln)
    return cards


def parse_ksp(doc, path):
    """KSP category PDF. Card: 'מק"ט KSP', name lines, then prices: struck regular, struck Eilat price, KSP price,
    'אילת: ₪x' (VAT-free Eilat price, ignored). Price = the last price before the Eilat line."""
    cards = card_lines(doc, lambda u: "ksp.co.il/web/item/" in u,
                       lambda r, page: fitz.Rect(r.x0 - 5, r.y0, r.x1 + 5, min(r.y1 + 260, page.rect.y1)))
    out = []
    for u, ls in cards.items():
        i = next((k for k, l in enumerate(ls) if "KSP" in l and "ט" in l), None)
        if i is None: continue
        name = []
        for l in ls[i + 1:]:
            if "₪" in l: break
            name.append(l)
        vals, eilat = [], False
        for l in ls[i + 1:]:
            if "אילת" in l: eilat = True; break
            vals += [money(v) for v in re.findall(r"₪\s*" + NUM, l)]
        if not name or not vals: continue
        it = {"seller": "ksp", "name": " ".join(name), "url": u, "source_file": path.name}
        if len(vals) >= 2 and vals[0] > vals[-1]: it["regular"], it["sale"] = vals[0], vals[-1]
        else: it["regular"] = vals[-1]
        text = "\n".join(ls)
        if re.search(r"אזל|לא במלאי|אין במלאי", text): it["oos"] = True
        if re.search(r"יבואן רשמי|יבוא רשמי", text): it["import"] = "official"
        elif "יבוא מקביל" in text: it["import"] = "parallel"
        out.append(it)
    return out


def parse_superpharm(doc, path):
    """Super-Pharm category PDF (a marketplace). Name from the product URL (the card title is cut with '...').
    Card: price ('החל מ' = lowest of several offers), struck price, 'נמכר ע״י X' (the actual seller) or
    'מוכר חיצוני' + 'להצעות נוספות' (several outside sellers, not named), 'יבוא רשמי' when printed."""
    cards = card_lines(doc, lambda u: "/infants-and-toddlers/car-seats/" in u and "/p/" in u,
                       lambda r, page: fitz.Rect(r.x0 - 5, r.y0, r.x1 + 5, min(r.y1 + 24, page.rect.y1)))
    out = []
    for u, ls in cards.items():
        slug = urllib.parse.unquote(u.split("/p/")[0].rstrip("/").split("/")[-1])
        name = slug.replace("-", " ").strip()
        sub = u.split("/car-seats/")[1].split("/")[0]
        it = {"seller": "superpharm", "name": name, "url": u, "source_file": path.name, "sp_cat": sub}
        joined = []
        for l in ls:  # superscript agorot: '₪56' then '90' on its own line
            if joined and re.fullmatch(r"\d{2}", l) and re.search(r"₪\s*\d+$", joined[-1]): joined[-1] += "." + l
            else: joined.append(l)
        text = "\n".join(joined)
        vals = [money(v) for v in re.findall(r"₪\s*" + NUM, text) if money(v) >= 10]
        if not vals: continue
        if len(vals) >= 2 and max(vals[:2]) > min(vals[:2]): it["regular"], it["sale"] = max(vals[:2]), min(vals[:2])
        else: it["regular"] = vals[0]
        if "החל מ" in text: it["from"] = True
        m = re.search(r"נמכר ע\s*[״\"']\s*י\s+(.+)", text)
        if m: it["vendor"] = m.group(1).strip()
        elif "מוכר חיצוני" in text: it["vendor"] = ""
        if re.search(r"אזל|לא במלאי|אין במלאי", text): it["oos"] = True
        if "יבוא רשמי" in text: it["import"] = "official"
        elif "יבוא מקביל" in text: it["import"] = "parallel"
        out.append(it)
    return out


def parse_pdf(path):
    doc = fitz.open(path)
    if "KSP" in path.name:
        return parse_ksp(doc, path)
    if "סופר-פארם" in path.name:
        return parse_superpharm(doc, path)
    if "shilav" in path.name.lower():
        return parse_shilav(doc, path)
    if re.search(r"עגליס|בייביסטאר|מוצצים", path.name):
        return parse_cards(doc, path)
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
    by_url, files = {}, {}
    for it in all_items:  # same product saved in two PDFs: keep the one with more fields, remember every file
        k = it["url"]
        files.setdefault(k, set()).add(it["source_file"])
        if k not in by_url or len(it) > len(by_url[k]): by_url[k] = it
    for k, it in by_url.items():
        it["source_files"] = sorted(files[k])
    out = ROOT / "data" / "raw" / "manual.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    mtime = max(f.stat().st_mtime for f in folder.rglob("*.pdf"))
    out.write_text(json.dumps({"fetched": time.strftime("%Y-%m-%d", time.localtime(mtime)),
                               "products": list(by_url.values())}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"saved {len(by_url)} products -> {out.relative_to(ROOT)}", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT)
