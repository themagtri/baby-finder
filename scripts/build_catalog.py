"""Normalize data/raw/*.json (per seller) into data/catalog.csv — one row per product per seller.

Rules (CLAUDE.md):
- Nothing is invented. A field the seller's data/page does not state stays empty (= "unknown" on the site).
- Car-seat specs come only from the seller's structured data or from data/overrides.csv, where each
  value is backed by a quote copied from the seller's product page.
- import_status stays empty unless the seller states official/parallel import (none do so far).
Usage: python -I scripts/build_catalog.py      (run from repo root)
"""
import csv, html, json, pathlib, re, sys, datetime
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from manual_source import from_manual

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
TODAY = datetime.date.today()

FIELDS = ["cat", "type", "seat_group", "brand", "model", "subtitle", "seller", "seller_name", "price", "price_reg",
          "in_stock", "url", "standard", "isofix", "rotating", "age_from_m", "age_to_m", "height_min_cm",
          "height_max_cm", "weight_max_kg", "fold", "import_status", "checked", "source_id", "price_note", "family", "std_src", "iso_src", "spec_url"]

SELLER_NAME = {"besafe": "BeSafe ישראל", "segal": "סגל בייבי", "babyjogger": "Baby Jogger ישראל", "joie": "Joie ישראל",
               "cybex": "Cybex ישראל", "chicco": "Chicco ישראל",
               "shilav": "שילב", "babystar": "בייבי סטאר", "motzetzim": "מוצצים", "agalease": "עגליס", "minena": "מיננה", "balibaby": "בא לי בייבי", "ksp": "KSP", "superpharm": "סופר-פארם"}


def clean(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def load(slug):
    p = RAW / f"{slug}.json"
    if not p.exists():
        print(f"skip {slug}: no raw file", file=sys.stderr)
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def woo_price(p):
    pr = p["prices"]
    mu = pr.get("currency_minor_unit", 0)
    def num(v):
        if not v: return None
        n = int(v) / 10 ** mu
        return int(n) if n == int(n) else n
    cur, reg = num(pr.get("price")), num(pr.get("regular_price"))
    if not cur: return None, None
    return cur, (reg if reg and reg != cur else None)


def overrides():
    out = {}
    with open(ROOT / "data" / "overrides.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out[(r["seller"], r["source_id"])] = r
    return out


def base(seller, fetched, **kw):
    row = {k: "" for k in FIELDS}
    row.update(seller=seller, seller_name=SELLER_NAME.get(seller, seller), checked=fetched)
    row.update({k: ("" if v is None else (CTRL.sub("", v).strip() if isinstance(v, str) else v)) for k, v in kw.items()})
    return row


CTRL = re.compile("[\\x00-\\x1f\\u200e\\u200f]")  # control / direction marks that PDFs leave in names


def stroller_type(name, cats):
    c = " ".join(cats)
    if "תאומים" in c or "תאומים" in name or "Double" in name or "twin" in name.lower():
        return "twin"
    if re.search(r"trio|travel system|ramble|ניובורן|סל שכיבה|אמבטיה|משולבת", name, re.I):
        return "full"
    if "טיולון" in name or "טיולונים" == c or "אולטרה קומפקט" in c:
        return "travel"
    return "stroller"


def apply_override(row, ov):
    if not ov: return row
    for k in ("seat_group", "age_from_m", "age_to_m", "height_min_cm", "height_max_cm", "weight_max_kg",
              "standard", "isofix", "rotating"):
        if ov.get(k):
            row[k] = ov[k]
    return row


def from_woo(slug, brand, ovs):
    d = load(slug)
    if not d: return []
    rows = []
    for p in d["products"]:
        name = clean(p["name"])
        cats = [c["name"] for c in p["categories"]]
        cur, reg = woo_price(p)
        ov = ovs.get((slug, str(p["id"])))
        common = dict(brand=brand, model=name, price=cur, price_reg=reg, in_stock=int(bool(p["is_in_stock"])),
                      url=p["permalink"], source_id=p["id"])
        is_seat_cat = any(k in c for c in cats for k in ("כיסאות בטיחות", "סלקלים", "בוסטרים", "בטיחות ברכב"))
        if ov is not None:
            rows.append(apply_override(base(slug, d["fetched"], cat="carseat", **common), ov))
        elif is_seat_cat and not re.search(r"בסיס|מתאם|כיסוי|מגן|חגורת", name):
            print(f"  NOTE {slug} {p['id']} car seat without override (skipped): {name}", file=sys.stderr)
        elif "טסטים" in cats:
            continue
        elif any("עגלות" in c for c in cats) and re.match(r"^(עגלת|עגלה)", name):
            rows.append(base(slug, d["fetched"], cat="stroller", type=stroller_type(name, cats), **common))
    return rows


STD = {"ISIZE": "R129", "FMVSS213": "FMVSS 213", "ECER4404": "R44/04"}
HEIGHT = re.compile(r"(?:גובה|גובהם|בגובה)[^.]{0,40}?(\d{2,3})\s*[-–]\s*(\d{2,3})\s*ס[\"”'’]?מ")


def joie_price(p):
    reg = p["price"] or None
    disc = p.get("discount") or {}
    cur = reg
    if disc.get("type") == "overwrite" and disc.get("amount"):
        try:
            s = datetime.datetime.strptime(disc["startDate"], "%m/%d/%Y").date()
            e = datetime.datetime.strptime(disc["endDate"], "%m/%d/%Y").date()
            if s <= TODAY <= e:
                cur = disc["amount"]
        except (KeyError, ValueError):
            pass
    if not reg: return None, None
    return cur, (reg if cur != reg else None)


def from_joie():
    d = load("joie")
    if not d: return []
    prods = d["products"]
    stock = {}
    for p in prods:
        key = p.get("mainColorProductId") or p["id"]
        stock[key] = stock.get(key, 0) + (p.get("quantity") or 0)
    rows = []
    for p in prods:
        if not p.get("isMainColor"):
            continue
        types = [t["name"] for t in (p.get("types") or [])]
        tj = " ".join(types)
        name = clean(p["name"]).replace("‎", "")
        cur, reg = joie_price(p)
        text = clean((p.get("description") or "") + " " + (p.get("specifications") or ""))
        age = p.get("age") or {}
        common = dict(brand="Joie", model=name, subtitle=clean(p.get("title")), price=cur, price_reg=reg,
                      in_stock=int(stock.get(p["id"], 0) > 0),
                      url=f"https://joiebaby.co.il/products/product/{p['catalogNumber']}", source_id=p["id"])
        if any(k in tj for k in ("עגלות", "טיולונים")) and "אביזרים" not in tj:
            if "תאומים" in tj: typ = "twin"
            elif "טיולונים" in tj: typ = "travel"
            elif re.search(r"trio|travel system|ramble", name, re.I): typ = "full"
            else: typ = "stroller"
            rows.append(base("joie", d["fetched"], cat="stroller", type=typ,
                             fold={"book": "book", "threeDimensional": "3d", "umbrella": "umbrella"}.get(p.get("foldType"), ""),
                             age_from_m=age.get("from"), age_to_m=age.get("to"), **common))
        elif "בסיסים" in tj:
            continue  # bases are accessories, not seats
        elif any(k in tj for k in ("סלקלים", "כסאות בטיחות", "בוסטרים")):
            a0, a1 = age.get("from"), age.get("to")
            if "סלקלים" in tj: grp = "infant"
            elif "בוסטרים" in tj and (a0 or 0) >= 12: grp = "booster"
            elif a0 == 0: grp = "convertible"
            else: grp = "toddler"
            hs = [(int(a), int(b)) for a, b in HEIGHT.findall(text) if 30 <= int(a) < int(b) <= 160]
            # rotating: only when the seat itself is said to rotate (infant carriers rotate only on an optional base)
            rot = 1 if grp != "infant" and re.search(r"מסתובב|360|סיבוב (?:מלא|חלק|של)", text) else ""
            std = STD.get(p.get("standard") or "", p.get("standard") or "")
            if std == "R44/04" and "R129" in text.upper().replace(" ", ""):
                std = "?"  # page text and structured data disagree -> unknown ("?" stops name_facts filling it)
            rows.append(base("joie", d["fetched"], cat="carseat", seat_group=grp,
                             standard=std,
                             isofix={"included": "included", "optional": "optional", "without": "without"}.get(p.get("isofix") or "", ""),
                             rotating=rot, age_from_m=a0, age_to_m=a1,
                             height_min_cm=min(h[0] for h in hs) if hs else "", height_max_cm=max(h[1] for h in hs) if hs else "",
                             **common))
    return rows


def from_superpharm():
    """Super-Pharm online incl. marketplace shops: the card's seller is the shop that actually sells it."""
    from manual_source import kind_of, CYBEX, TAGS
    d = load("superpharm")
    if not d: return []
    rows = []
    for p in d["products"]:
        name = clean(p["name"])
        if re.search(r"מתאם|כיסוי|תיק|בסיס|שמשי|מראה|מגן|פגוש|כילה", name): continue
        shop = p.get("shop") or ""
        seller = "superpharm" + (("-" + re.sub(r"[^a-z0-9]+", "", shop.lower()) or "-" + str(abs(hash(shop)) % 10**6)) if shop else "")
        sname = f"{shop} (דרך סופר-פארם)" if shop else "סופר-פארם"
        brand = p.get("brand") or ""
        cp = p["cat_page"]
        cat, kind = kind_of(name)
        if cp == "stroller":
            cat = "stroller"; kind = kind if kind in ("twin", "full", "travel") else ("travel" if "טיולון" in name else "stroller")
        else:
            cat = "carseat"
            if cp == "booster": kind = "booster"
            elif cp == "infant": kind = "infant"
            elif not kind or kind not in ("infant", "convertible", "toddler", "booster"):
                kind = next((t["seat_group"] for t in TAGS if re.search(t["pattern"], name, re.I)), "")
        price = p.get("price")
        price = (int(price) if price == int(price) else price) if price else None
        row = base("superpharm", d["fetched"], cat=cat, brand=brand, model=name, seller_name=sname,
                   price=price, in_stock=int(bool(p.get("in_stock"))), url=p["url"],
                   import_status=p.get("import") or "", source_id=p["url"].rsplit("/", 1)[-1])
        row["seller"] = seller
        if cat == "stroller": row["type"] = kind
        else: row["seat_group"] = kind
        rows.append(row)
    return rows


def family(r):
    """Same-model key across sellers (for the price comparison on each card). Canonical model names come from
    scripts/models.py (Hebrew/English aliases) or manual_source.CYBEX; same edition, same bundle and same type
    are required (a stroller sold with a bassinet / car seat / electric frame is a different offer)."""
    from manual_source import CYBEX, EDITIONS
    from models import canonical
    name, brand = r["model"], r["brand"]
    if brand == "Cybex":
        f = next((f for f in CYBEX if re.search(f[0], name, re.I)), None)
        fam = f[1] if f else None
    else:
        c = canonical(brand, name)
        fam = f"{brand} {c}" if c else None
    if not fam:
        return ""
    ed = next((lbl for k, lbl in EDITIONS if re.search(k, name, re.I)), "")
    bundle = "+carseat" if r["cat"] == "stroller" and re.search(r"סל קל|סלקל|קלאוד|cloud", name, re.I) else ""
    if re.search(r"חשמלי|e-priam|\be\b", name, re.I): bundle += "+electric"
    if re.search(r"bonpoint|בונפואה", name, re.I): ed = "Bonpoint"
    return f"{fam}|{ed}|{bundle}|{r['cat']}|{r['type'] or r['seat_group']}"


GENERIC = set("""עגלת עגלה עגלות תינוק טיולון כיסא כסא כ בטיחות סלקל סל קל בוסטר מושב לרכב משולבת דגם חדש החדשה
הזמנה מוקדמת - / + של עם צבע i""".split())


ISO_NO = re.compile(r"ללא (?:חיבור )?(?:איזופיקס|isofix)", re.I)
ISO_BASE_SEP = re.compile(r"ללא בסיס|בסיס (?:נמכר )?בנפרד", re.I)
ISO_YES = re.compile(r"איזופיקס|isofix|i[- ]?fix\b|kidfix|rodifix|isofit|iso-?fix", re.I)
STD_RULES = [(re.compile(r"i[- ]?size|r ?129", re.I), "R129"), (re.compile(r"\br ?44", re.I), "R44/04"),
             (re.compile(r"fmvss", re.I), "FMVSS 213")]
ROT = re.compile(r"מסתובב|\b360|360\b|swivel|סיבוב", re.I)


def name_facts(rows):
    """The product name is the seller's own text: if it states ISOFIX / standard / rotation, use it.
    Fill only empty fields; when the name contradicts a value we already have, keep ours and report it
    (printed for manual review)."""
    conflicts = []
    for r in rows:
        if r["cat"] != "carseat":
            continue
        nm = r["model"]
        iso = "without" if ISO_NO.search(nm) else ("optional" if ISO_BASE_SEP.search(nm) else ("included" if ISO_YES.search(nm) else ""))
        std = next((v for rx, v in STD_RULES if rx.search(nm)), "")
        rot = "1" if r["seat_group"] != "infant" and ROT.search(nm) else ""
        for field, val in (("isofix", iso), ("standard", std), ("rotating", rot)):
            if not val:
                continue
            cur = str(r.get(field) or "")
            if not cur:
                r[field] = val
            elif cur != val:
                conflicts.append((r["seller"], nm, field, cur, val))
    for r in rows:   # seller contradicts itself -> shown as unknown
        if r.get("standard") == "?": r["standard"] = ""
    for c in conflicts:
        print("  NAME CONFLICT", c, file=sys.stderr)
    return conflicts


IMPORTER_SITES = {"joie", "besafe", "cybex", "chicco", "babyjogger", "segal"}


def importer_fill(rows):
    """Same model (same family key) sold by a chain: copy standard / ISOFIX that the official importer's own
    site states. Marked std_src / iso_src = 'importer' so the card says where it came from."""
    src = {}
    for r in rows:
        if r["seller"] in IMPORTER_SITES and r["family"] and r["cat"] == "carseat":
            d = src.setdefault(r["family"].rsplit("|", 1)[0], {})  # same model/edition/bundle; seat type may be unknown
            if r["standard"] and r["standard"] != "?": d.setdefault("standard", r["standard"])
            if r["isofix"]: d.setdefault("isofix", r["isofix"])
    for r in rows:
        if r["cat"] != "carseat" or r["seller"] in IMPORTER_SITES or not r["family"]:
            continue
        d = src.get(r["family"].rsplit("|", 1)[0], {})
        if not r["standard"] and d.get("standard"):
            r["standard"], r["std_src"] = d["standard"], "importer"
        if not r["isofix"] and d.get("isofix"):
            r["isofix"], r["iso_src"] = d["isofix"], "importer"


def maker_fill(rows):
    """data/maker_specs.csv: one row per model checked on the maker's site (or another reliable source), with
    a regex on the product name and the source URL. Fills only empty fields; disagreement is reported."""
    path = ROOT / "data" / "maker_specs.csv"
    if not path.exists():
        return
    specs = list(csv.DictReader(open(path, encoding="utf-8")))
    for r in rows:
        if r["cat"] != "carseat":
            continue
        for m in specs:
            if m["brand"].lower() != (r["brand"] or "").lower() and m["brand"] != "*":
                continue
            if not re.search(m["pattern"], r["model"], re.I):
                continue
            for field, key, srcf in (("standard", "standard", "std_src"), ("isofix", "isofix", "iso_src")):
                val = m.get(key) or ""
                if not val:
                    continue
                if not r[field] or r[field] == "?":
                    if r[field] == "?":
                        continue  # the seller contradicts itself: stays unknown
                    r[field], r[srcf], r["spec_url"] = val, "maker", m["source_url"]
                elif r[field] != val:
                    print("  MAKER CONFLICT", (r["seller"], r["model"][:50], field, r[field], val), file=sys.stderr)
            break


def merge_colours(rows):
    """One card per model per seller per price (owner: no card per colour, say 'מגוון צבעים').
    Key = seller + brand + category + type + both prices + model (canonical family if known, else the first two
    distinctive words of the name). Stock = in stock if any colour is."""
    def core(r):
        if r["family"]:
            return r["family"]
        drop = GENERIC | {w.lower() for w in r["brand"].split()} | set(r["brand"].lower().split())
        m = re.split(r"\bצבע\b|\bבצבע\b", r["model"].lower().replace("™", ""))[0]  # colour words follow 'צבע'
        toks = [t for t in re.split(r"[\s/–\-]+", m) if t and t not in drop]
        toks = [t for t in toks if t not in {"צ'יקו", "סייבקס", "בוגבו", "ג'ואי", "גוי", "נונה", "ברייטקס", "טוויגי"}]
        return " ".join(toks[:2])
    def ncol(r):
        m = re.search(r"(\d+) צבעים", r["subtitle"])
        return int(m.group(1)) if m else 1
    groups = {}
    for r in rows:
        key = (r["seller"], r["seller_name"], r["brand"], r["cat"], r["type"] or r["seat_group"], r["price"], r["price_reg"], core(r))
        groups.setdefault(key, []).append(r)
    out = []
    for g in groups.values():
        best = next((r for r in g if r["in_stock"] in (1, "1")), g[0])
        best = dict(best)
        n = sum(ncol(r) for r in g)
        sub = re.sub(r"\s*·\s*(\d+ צבעים|מגוון צבעים \(\d+\))", "", best["subtitle"]).strip(" ·")
        if n > 1:
            sub = (sub + " · " if sub else "") + f"מגוון צבעים ({n})"
            best["model"] = shortest_name(g)
        best["subtitle"] = sub
        best["in_stock"] = int(any(r["in_stock"] in (1, "1") for r in g))
        out.append(best)
    return out


def shortest_name(g):
    """For a merged card show the plainest name (fewest words = usually without a colour)."""
    return min((r["model"] for r in g), key=lambda m: (len(m.split()), len(m)))


def main():
    ovs = overrides()
    rows = from_woo("besafe", "BeSafe", ovs) + from_woo("segal", "Stokke", ovs) + \
        from_woo("babyjogger", "Baby Jogger", ovs) + from_joie() + from_manual(base) + from_superpharm()
    conflicts = name_facts(rows)
    for r in rows:
        r["family"] = family(r)
    importer_fill(rows)
    maker_fill(rows)
    for r in rows:
        r["family"] = family(r)
    rows = merge_colours(rows)
    rows.sort(key=lambda r: (r["cat"], r["seller"], r["model"]))
    out = ROOT / "data" / "catalog.csv"
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        w.writeheader()
        w.writerows(rows)
    by = {}
    for r in rows:
        by[(r["seller"], r["cat"])] = by.get((r["seller"], r["cat"]), 0) + 1
    print(f"wrote {len(rows)} rows -> {out.relative_to(ROOT)}", by)


if __name__ == "__main__":
    main()
