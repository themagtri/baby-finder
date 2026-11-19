"""Rows for sellers that block automated access, built from the PDFs the owner saved (data/raw/manual.json,
made by scripts/parse_manual.py).

Owner's rules for these (2026-11-18):
- Price shown = the club-member price when the page states one ("מחיר מועדון"), else the sale price, else the
  regular price. The card says it is a club price, and the regular price is kept for comparison.
- A product we are unsure how to classify was looked up on the web in English, only to choose its category
  (stroller type / seat group). Specs shown on the card still come only from the seller's own page.
Colour variants of one model at one price become one card (one card per model per seller).
"""
import json, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parent.parent

# family regex -> (display name, cat, type or seat_group, standard stated in the seller's product name)
# Category sources (web, 2026-11-18): cybex-online.com product/overview pages, chiccousa.com, chicco.in.
CYBEX = [
    (r"Coya 2|קויה 2", "Cybex Coya 2", "stroller", "travel", ""),
    (r"Coya|קויה", "Cybex Coya", "stroller", "travel", ""),
    (r"Mios 4|MIOS 4|מיוס 4", "Cybex Mios 4", "stroller", "stroller", ""),
    (r"Mios 3|MIOS 3|מיוס 3", "Cybex Mios 3", "stroller", "stroller", ""),
    (r"Priam 5|פריאם 5", "Cybex Priam 5", "stroller", "stroller", ""),
    (r"Priam 4|פריאם 4", "Cybex Priam 4", "stroller", "stroller", ""),
    (r"Balios|בליוס", "Cybex Balios S5", "stroller", "full", ""),
    (r"Eezy S Twist|איזי אס טוויסט", "Cybex Eezy S Twist+ 2", "stroller", "travel", ""),
    (r"Beezy|ביזי", "Cybex Beezy", "stroller", "travel", ""),
    (r"Orfeo|אורפאו", "Cybex Orfeo", "stroller", "travel", ""),
    (r"Agis|אגיס", "Cybex Agis", "stroller", "travel", ""),
    (r"Cloud T|קלאוד T|קלאוד טי", "Cybex Cloud T", "carseat", "infant", ""),
    (r"Sirona T|סירונה T|סירונה טי", "Cybex Sirona T i-Size", "carseat", "convertible", "R129"),
    (r"Anoris T2|אנוריס", "Cybex Anoris T2 i-Size Plus", "carseat", "toddler", "R129"),
    (r"Solution T|סולושן T|סולושן טי", "Cybex Solution T i-Fix", "carseat", "booster", ""),
    (r"Solution B|סולושן B", "Cybex Solution B i-Fix", "carseat", "booster", ""),
    (r"Solution G2|סולושן G2", "Cybex Solution G2", "carseat", "booster", ""),
    (r"Pallas G3", "Cybex Pallas G3", "carseat", "toddler", ""),
    (r"Sirona Gi|סירונה Gi", "Cybex Sirona Gi", "carseat", "convertible", ""),
    (r"Cloud G|קלאוד G", "Cybex Cloud G", "carseat", "infant", ""),
    (r"Aton B2|אטון B2", "Cybex Aton B2", "carseat", "infant", ""),
    (r"Gazelle S|גאזל", "Cybex Gazelle S", "stroller", "twin", ""),
]
FRAMES = [("רוזגולד", "שלדת רוזגולד"), ("מט שחור", "שלדה שחור מט"), ("חום כרום", "שלדת כרום חום"),
          ("שחור כרום", "שלדת כרום שחור"), ("כסופה", "שלדה כסופה")]
# special editions, matched on one keyword (PDF line breaks split multi-word names)
EDITIONS = [(r"Wings", "Jeremy Scott Wings"), (r"Jeremy", "Jeremy Scott"), (r"Jewels", "Jewels of Nature"),
            (r"Karolina", "Karolina Kurkova"), (r"Simply", "Simply Flowers"), (r"Urban", "Urban"),
            (r"Rebellious", "Rebellious Denim")]
ACCESSORY = r"פגוש|כילת|מתאם|תיק|שמשי|כיסוי"

# Chicco: English name -> (display name, cat, type/group, age stated on the seller listing (months), quote)
CHICCO = [
    ("Fit3X", "Chicco Fit3X ClearTex", "carseat", "convertible", None, None),
    ("OneFit Max", "Chicco OneFit Max ClearTex", "carseat", "convertible", None, None),
    ("Fit360", "Chicco Fit360 ClearTex", "carseat", "convertible", (0, 72), "מתאים מגיל לידה ועד גיל 6 שנים"),
    ("Everone", "Chicco EverOne", "carseat", "convertible", None, None),
    ("OneFit LX", "Chicco OneFit LX ClearTex", "carseat", "convertible", None, None),
    ("NextFit Zip Max", "Chicco NextFit Zip Max", "carseat", "convertible", None, None),
    ("NextFit Zip Air", "Chicco NextFit Zip Air", "carseat", "convertible", None, None),
    ("NextFit Zip", "Chicco NextFit Zip", "carseat", "convertible", None, None),
    ("MyFit Air", "Chicco MyFit Air ClearTex", "carseat", "toddler", (24, None), "מגיל שנתיים ועד גיל בית הספר"),
    ("MyFit™ ClearTex", "Chicco MyFit ClearTex", "carseat", "toddler", None, None),
    ("MyFit™", "Chicco MyFit", "carseat", "toddler", None, None),
    ("KidFit Adapt", "Chicco KidFit Adapt Plus", "carseat", "booster", None, None),
    ("Kidfit Cleartex", "Chicco KidFit ClearTex Plus 2 in 1", "carseat", "booster", None, None),
    ("GoFit – בוסטר גופיט פלוס", "Chicco GoFit Plus", "carseat", "booster", None, None),
    ("GoFit", "Chicco GoFit", "carseat", "booster", None, None),
    ("One4Ever", "Chicco One4Ever", "stroller", "stroller", None, None),
    ("XPlus", "Chicco Goody XPlus", "stroller", "travel", None, None),
    ("Goody – עגלת גודי פרימו", "Chicco Goody Primo", "stroller", "travel", None, None),
    ("Taormina", "Chicco Taormina", "stroller", "travel", None, None),
    ("Glam Dew", "Chicco Mysa Glam Dew Royal Edition", "stroller", "full", None, None),
    ("מיסה שמנת", "Chicco Mysa (שמנת)", "stroller", "full", None, None),
    ("Mysa – עגלה משולבת מיסה Stroller", "Chicco Mysa", "stroller", "full", None, None),
    ("Bellagio 2", "Chicco Bellagio 2", "stroller", "full", None, None),
    ("Bellagio Primo", "Chicco Bellagio Primo", "stroller", "full", None, None),
    ("Bellagio – ", "Chicco Bellagio", "stroller", "full", None, None),
    ("Kwik", "Chicco Kwik One", "stroller", "full", None, None),
    ("Ohlala", "Chicco Ohlala Twin", "stroller", "twin", None, None),
    ("LiteWay", "Chicco LiteWay 3 Basic", "stroller", "travel", None, None),
    ("Snappy", "Chicco Snappy", "stroller", "travel", None, None),
    ("London Up", "Chicco London Up", "stroller", "travel", None, None),
]
SUB = {"travel": "טיולון", "stroller": "עגלה מלידה", "full": "עגלה משולבת", "twin": "עגלת תאומים",
       "infant": "סלקל", "convertible": "כסא בטיחות מלידה", "toddler": "כסא בטיחות לפעוט", "booster": "בוסטר"}


def price_fields(p):
    reg, club, sale = p.get("regular"), p.get("club"), p.get("sale")
    if club:
        return club, reg, "מחיר חבר מועדון"
    if sale:
        return sale, reg, "מחיר מבצע"
    return reg, None, ""


def n(v):
    if v is None or v == "": return ""
    return int(v) if float(v) == int(v) else round(v, 2)


def cybex_rows(prods, base):
    groups = {}
    for p in prods:
        nm = p["name"]
        fam = next((f for f in CYBEX if re.search(f[0], nm, re.I)), None)
        if not fam or re.search(ACCESSORY, nm):
            continue  # accessories (bumper, net) and anything unknown
        frame = next((lbl for k, lbl in FRAMES if k in nm), "")
        ed = next((lbl for k, lbl in EDITIONS if re.search(k, nm, re.I)), "")
        cot = "עריסה" in nm and fam[1] == "Cybex Coya 2"
        key = (fam[1], frame, ed, cot, p.get("regular"), p.get("club"), p.get("sale"))
        groups.setdefault(key, []).append(p)
    rows = []
    for (name, frame, ed, cot, reg, club, sale), vs in groups.items():
        fam = next(f for f in CYBEX if f[1] == name)
        _, _, cat, kind, std = fam
        if cot: kind = "full"
        title = " · ".join(x for x in [name, ("מהדורת " + ed) if ed else "", frame, "עם עריסה" if cot else ""] if x)
        instock = [v for v in vs if not v.get("oos")]
        pick = (instock or vs)[0]
        price, preg, note = price_fields(pick)
        sub = SUB[kind] + (f" · {len(vs)} צבעים" if len(vs) > 1 else "")
        kw = dict(cat=cat, brand="Cybex", model=title, subtitle=sub, price=n(price), price_reg=n(preg),
                  price_note=note, in_stock=int(bool(instock)), url=pick["url"], source_id=pick["source_file"])
        if cat == "stroller": kw["type"] = kind
        else: kw.update(seat_group=kind, standard=std)
        rows.append(base("cybex", **kw))
    return rows


def hand_prices(seller):
    """Prices transcribed by hand from the saved PDF (layout too irregular to parse safely)."""
    import csv
    with open(ROOT / "data" / "manual_prices.csv", encoding="utf-8") as f:
        return {r["key"]: r for r in csv.DictReader(f) if r["seller"] == seller}


def chicco_rows(prods, base):
    rows, hp = [], hand_prices("chicco")
    for p in prods:
        nm = p["name"]
        hit = next((c for c in CHICCO if c[0].lower() in nm.lower()), None)
        if not hit:
            continue  # adapters, bags, parasol etc.
        key, title, cat, kind, age, quote = hit
        h = hp.get(key)
        if h is None:
            raise SystemExit(f"chicco {key}: missing from data/manual_prices.csv")
        kw = dict(cat=cat, brand="Chicco", model=title, subtitle=SUB[kind], price=h["price"], price_reg="",
                  price_note="", in_stock=int(h["in_stock"]), url=p["url"], source_id=h["source_file"])
        if cat == "stroller": kw["type"] = kind
        else:
            kw["seat_group"] = kind
            if age: kw.update(age_from_m=age[0], age_to_m=age[1])
        rows.append(base("chicco", **kw))
    return rows


# ---- multi-brand chains (Shilav, Baby Star, Motzetzim, Agalease, Minena) ----
BRANDS = ["Cybex", "Chicco", "Joie", "BeSafe", "Bugaboo", "Nuna", "Maxi-Cosi", "UPPAbaby", "Stokke", "Babyzen",
          "YOYO", "Baby Jogger", "Britax", "Peg Perego", "Inglesina", "Joolz", "Silver Cross", "Kinderkraft",
          "Graco", "Evenflo", "Doona", "Thule", "Recaro", "Mutsy", "Bumprider", "Twigy", "Safety 1st", "Petite",
          "Anex", "ABC Design", "Lionelo", "Kikkaboo", "Kikka Boo", "Bebe Confort", "Hauck", "Cosatto", "Babyark", "Moona",
          "Babysafe", "Dearlee", "Mountain Buggy", "Phil&Teds", "Sport Line", "Coccolle", "Espiro", "Kinder Kraft"]
BRANDS_HE = {"סייבקס": "Cybex", "צ'יקו": "Chicco", "ציקו": "Chicco", "ג'ואי": "Joie", "בי סייף": "BeSafe",
             "בוגבו": "Bugaboo", "נונה": "Nuna", "מקסי קוזי": "Maxi-Cosi", "סטוקי": "Stokke", "יויו": "YOYO",
             "בריטקס": "Britax", "פג פרגו": "Peg Perego", "אינגלזינה": "Inglesina", "ג'ולז": "Joolz",
             "סילבר קרוס": "Silver Cross", "קינדרקראפט": "Kinderkraft", "גרקו": "Graco", "דונה": "Doona",
             "אנקס": "Anex", "ספורט ליין": "Sport Line", "טוויגי": "Twigy", "מונה": "Moona", "בייביארק": "Babyark",
             "ברייטקס": "Britax", "בוגבו": "Bugaboo", "דיליאנס": "Dilians"}
ACCESSORY_ANY = r"שכחת ילדים|מכשיר ל|^עריסה|^סל שכיבה|מתאם|תיק|שמשי|כיסוי|כילה|כילת|פגוש|מזרן|בסיס|מראה|ארגונית|מחזיק כוס|שק שינה|מגן|^שלדה? "


def brand_of(name):
    low = name.lower()
    for b in BRANDS:
        if b.lower() in low: return b
    for he, b in BRANDS_HE.items():
        if he in name: return b
    return ""


def kind_of(name):
    """Category from the seller's own product name. A known model (Cybex/Chicco tables) wins; car-seat group stays
    empty when the name does not say it (the age-stage filter then hides it rather than guessing)."""
    fam = next((f for f in CYBEX if re.search(f[0], name, re.I)), None)
    if fam: return fam[2], fam[3]
    ch = next((c for c in CHICCO if c[0].lower() in name.lower()), None)
    if ch: return ch[2], ch[3]
    if re.search(r"בוסטר|booster", name, re.I): return "carseat", "booster"
    if re.search(r"סלקל", name): return "carseat", "infant"
    if re.search(r"כסא בטיחות|כיסא בטיחות|מושב בטיחות|car seat", name, re.I): return "carseat", ""
    if re.search(r"תאומים|twin|double|duo", name, re.I): return "stroller", "twin"
    if re.search(r"משולבת|סל שכיבה|אמבטיה|עריסה|trio|travel system", name, re.I): return "stroller", "full"
    if re.search(r"טיולון", name): return "stroller", "travel"
    if re.search(r"עגלה|עגלת|stroller", name, re.I): return "stroller", "stroller"
    return None, None


def chain_rows(seller, prods, base):
    rows = []
    for p in prods:
        nm = p["name"]
        if re.search(ACCESSORY_ANY, nm): continue
        cat, kind = kind_of(nm)
        if not cat: continue
        price, preg, note = price_fields(p)
        kw = dict(cat=cat, brand=brand_of(nm), model=nm, subtitle=SUB.get(kind, ""), price=n(price), price_reg=n(preg),
                  price_note=note, in_stock=int(not p.get("oos")), url=p["url"], source_id=p["source_file"])
        if cat == "stroller": kw["type"] = kind
        else: kw["seat_group"] = kind
        rows.append(base(seller, **kw))
    return rows


CHAINS = ("babystar", "motzetzim", "agalease", "minena")

# ---- Shilav: names from the product URL (logical word order), category from the saved category page ----
FILE_KIND = [("בוסטר רצועות", ("carseat", "toddler")), ("בוסטר", ("carseat", "booster")),
             ("סלקלים ומושבים מגיל לידה", ("carseat", "from_birth")), ("סלקלים", ("carseat", "infant")),
             ("All in one", ("carseat", "convertible")), ("כיסאות בטיחות מגיל לידה", ("carseat", "from_birth")),
             ("מסתובבים", ("carseat", "")), ("כיסאות בטיחות", ("carseat", "")),
             ("תאומים", ("stroller", "twin")), ("טיולונים", ("stroller", "travel")), ("קומפקטיות", ("stroller", "travel")),
             ("עגלות תינוק מגיל לידה", ("stroller", "from_birth")), ("משולבים מלידה", ("stroller", "from_birth")),
             ("עגלות תינוק", ("stroller", "from_birth"))]
COLORS = set("""שחור שחורה לבן לבנה אפור אפורה כחול כחולה ורוד ורודה ירוק ירוקה בז חום חומה אדום אדומה קאמל לאטה
זית שמנת כסף כסוף זהב גולד חול סהרה נייבי אינדיגו תכלת סגול צהוב כתום מוקה פסטל עמוק כהה בהיר שוקולד קרם אבן
black white grey gray beige brown blue green pink red navy sand taupe love
מגיק פוג לאווה ספיה אופוויט אוף וויט שח בג סי של סקיי בלו מודפס סייבקס פחם טראפל מלאנז מינרלי ארנב פיל נמר מיקי מיני
cozy off peach sepia mirage almond magic stormy canvas moss lava fog candy latte camel coconut city sage pastel ebony shale
sandstone maple caviar cedar granite thunder midnight graphite""".split())
BRAND_WORDS = ["Sport Line", "Shilav"] + BRANDS


def _tags():
    """Seat type for models whose type the seller's page does not state; each row cites the web source used
    (owner: look unclear products up in English, only to choose the category)."""
    import csv
    with open(ROOT / "data" / "manual_tags.csv", encoding="utf-8") as f:
        return list(csv.DictReader(f))


TAGS = _tags()


def shilav_name(url):
    import urllib.parse
    h = urllib.parse.unquote(url.split("/products/")[1]).split("?")[0]
    h = re.sub(r"-\d+$", "", h)
    h = re.sub(r"(^|-)\d{6,}(?=-|$)", r"", h)  # catalogue numbers in Motzetzim handles
    return " ".join(h.replace("-", " ").split())


def no_color(name):
    return " ".join(t for t in name.split() if t.strip("'\"/").lower() not in COLORS and not re.fullmatch(r"\d{1,2}", t) or t in ("2", "3", "4", "5"))


def dedupe_title(nm):
    """'עגלת תאומים צ'יקו הוללה עגלת תאומים צ'יקו הוללה' -> keep the first copy (two colour titles joined)."""
    t = nm.split()
    for k in range(min(4, len(t) // 2), 1, -1):
        head = t[:k]
        for j in range(k, len(t) - k + 1):
            if t[j:j + k] == head:
                return " ".join(t[:j])
    return nm


def chain_file_rows(seller, prods, base, url_name=True):
    """Chain category PDFs: category from the seller's own category page (file name), colours of one
    model at one price grouped, rotation when the seller's category page is 'מסתובבים', import status
    only when the card itself states it."""
    groups = {}
    for p in prods:
        nm = shilav_name(p["url"]) if url_name else dedupe_title(p["name"])
        if p.get("brand_hint"):
            lat = re.findall(r"[A-Za-z][A-Za-z&' ]+", p["brand_hint"])
            p["_brand"] = lat[0].strip() if lat else ""
        if re.search(ACCESSORY_ANY, nm): continue
        brand = p.get("_brand") or next((b for b in BRAND_WORDS if b.lower() in p.get("name", "").lower()), "") or brand_of(nm)
        srcs = " ".join(p.get("source_files") or [p["source_file"]])
        fk = next((v for k, v in FILE_KIND if k in srcs), (None, None))  # FILE_KIND is ordered specific-first
        cat, kind = kind_of(nm)
        fam = next((f for f in CYBEX if re.search(f[0], nm, re.I)), None) if brand == "Cybex" else None
        if fam: cat, kind = fam[2], fam[3]
        if fk[0] and not fam:  # the seller's own category page decides, unless it is a model we already know
            cat = fk[0]
            if fk[1] == "from_birth":
                if cat == "carseat": kind = "infant" if re.search(r"סלקל|סל קל", nm) else "convertible"
                else: kind = "full" if re.search(r"סל קל|עריסה|משולבת|אמבטיה|סל שכיבה|טריו", nm) else (kind if kind in ("full", "twin") else "stroller")
            elif fk[1]: kind = fk[1]
        if not cat: continue
        tag = next((t["seat_group"] for t in TAGS if re.search(t["pattern"], nm, re.I)), "") if cat == "carseat" else ""
        if tag and kind not in ("booster", "infant"): kind = tag
        if cat == "stroller" and kind != "twin" and re.search(r"עריסה|סל קל|סלקל|משולבת|סל שכיבה|אמבטיה|קומפלט|complete", nm, re.I): kind = "full"
        rot = 1 if cat == "carseat" and "מסתובב" in srcs else ""
        key = (brand, no_color(nm), cat, kind, p.get("regular"), p.get("club"), p.get("sale"), rot, p.get("import", ""))
        groups.setdefault(key, []).append((nm, p))
    rows = []
    for (brand, base_nm, cat, kind, reg, club, sale, rot, imp), vs in groups.items():
        instock = [p for _, p in vs if not p.get("oos")]
        pick = (instock or [p for _, p in vs])[0]
        price, preg, note = price_fields(pick)
        title = base_nm if brand.lower() in base_nm.lower() else f"{brand} {base_nm}".strip()
        sub = SUB.get(kind, "") + (f" · {len(vs)} צבעים" if len(vs) > 1 else "")
        kw = dict(cat=cat, brand=brand, model=title, subtitle=sub, price=n(price), price_reg=n(preg), price_note=note,
                  in_stock=int(bool(instock)), url=pick["url"], source_id=pick["source_file"], import_status=imp)
        if cat == "stroller": kw["type"] = kind
        else: kw.update(seat_group=kind, rotating=rot)
        rows.append(base(seller, **kw))
    return rows


def ksp_rows(prods, base):
    """KSP strollers PDF: type from the product name (the file name mixes strollers and travel strollers)."""
    rows = []
    for p in prods:
        nm = p["name"].replace(" '", "'")
        if re.search(ACCESSORY_ANY, nm): continue
        cat, kind = kind_of(nm)
        if cat != "stroller": continue
        price, preg, note = price_fields(p)
        brand = next((b for b in BRAND_WORDS if b.lower() in nm.lower()), "") or brand_of(nm)
        rows.append(base("ksp", cat=cat, type=kind, brand=brand, model=nm, subtitle=SUB.get(kind, ""), price=n(price),
                         price_reg=n(preg), price_note=note, in_stock=int(not p.get("oos")), url=p["url"],
                         source_id=p["source_file"], import_status=p.get("import", "")))
    return rows


SP_KIND = {"booster": "booster", "carrycot": "infant", "car-safety-seat": ""}


def superpharm_rows(prods, base):
    """Super-Pharm is a marketplace: most cards are sold by another store ('נמכר ע״י X') or by several outside
    sellers ('מוכר חיצוני', price 'החל מ'). The card names Super-Pharm and the actual seller as printed."""
    rows = []
    for p in prods:
        kind = SP_KIND.get(p.get("sp_cat"))
        if kind is None: continue  # accessories
        nm = p["name"]
        if re.search(ACCESSORY_ANY, nm): continue
        if not kind:
            ch = next((c for c in CHICCO if c[0].lower() in nm.lower()), None)
            kind = ch[3] if ch else next((t["seat_group"] for t in TAGS if re.search(t["pattern"], nm, re.I)), "")
        price, preg, note = price_fields(p)
        if p.get("from"): note = "החל מ-" + (" · " + note if note else "")
        v = p.get("vendor")
        v = re.sub(r"\s*\.\s*", ".", v or "").replace(' " ', '"').replace(" ) ", " (").replace(" ( ", ") ").strip(" -")
        sname = "סופר-פארם" + (f" (מוכר: {v})" if v else (" (כמה מוכרים חיצוניים)" if p.get("vendor") == "" else ""))
        brand = next((b for b in BRAND_WORDS if b.lower() in nm.lower()), "") or brand_of(nm)
        rows.append(base("superpharm", cat="carseat", seat_group=kind, brand=brand, model=nm, subtitle=SUB.get(kind, ""),
                         seller_name=sname, price=n(price), price_reg=n(preg), price_note=note,
                         in_stock=int(not p.get("oos")), url=p["url"], source_id=p["source_file"],
                         import_status=p.get("import", "")))
    return rows


def balibaby_rows(base):
    """Bali Baby blocks automated access (bot check). The owner screen-recorded its category pages; each row of
    data/manual_balibaby.csv is one listing read by eye from a frame of those videos / screenshots (source column).
    The recordings carry no product links, so the card links to the store's home page (the site says so)."""
    import csv
    p = ROOT / "data" / "manual_balibaby.csv"
    if not p.exists():
        return []
    rows = []
    with open(p, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            price, reg = float(r["price"]), (float(r["price_reg"]) if r["price_reg"] else None)
            if reg is not None and reg <= price: reg = None  # struck price not above the price: no saving shown
            kw = dict(cat=r["cat"], brand=r["brand"], model=r["name"], subtitle=SUB.get(r["kind"], ""), price=n(price),
                      price_reg=n(reg), price_note="מחיר מבצע" if reg else "", in_stock=1,
                      url="https://www.balibaby.co.il/", source_id=r["source"])
            if r["cat"] == "stroller": kw["type"] = r["kind"]
            else: kw["seat_group"] = r["kind"]
            rows.append(base("balibaby", "2026-11-18", **kw))
    return rows


def from_manual(base_fn):
    p = ROOT / "data" / "raw" / "manual.json"
    if not p.exists():
        return []
    d = json.loads(p.read_text(encoding="utf-8"))
    b = lambda seller, **kw: base_fn(seller, d["fetched"], **kw)
    prods = d["products"]
    rows = cybex_rows([x for x in prods if x["seller"] == "cybex"], b) + \
        chicco_rows([x for x in prods if x["seller"] == "chicco"], b)
    rows += chain_file_rows("shilav", [x for x in prods if x["seller"] == "shilav"], b)
    rows += chain_file_rows("motzetzim", [x for x in prods if x["seller"] == "motzetzim"], b)       # full name in URL
    rows += chain_file_rows("agalease", [x for x in prods if x["seller"] == "agalease"], b, url_name=False)
    rows += chain_file_rows("babystar", [x for x in prods if x["seller"] == "babystar"], b, url_name=False)
    rows += chain_rows("minena", [x for x in prods if x["seller"] == "minena"], b)
    rows += balibaby_rows(base_fn)
    rows += ksp_rows([x for x in prods if x["seller"] == "ksp"], b)
    rows += superpharm_rows([x for x in prods if x["seller"] == "superpharm"], b)
    return rows
