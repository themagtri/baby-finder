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
    (r"Coya 2", "Cybex Coya 2", "stroller", "travel", ""),
    (r"Coya", "Cybex Coya", "stroller", "travel", ""),
    (r"Mios 4", "Cybex Mios 4", "stroller", "stroller", ""),
    (r"Mios 3", "Cybex Mios 3", "stroller", "stroller", ""),
    (r"Priam 5", "Cybex Priam 5", "stroller", "stroller", ""),
    (r"Priam 4", "Cybex Priam 4", "stroller", "stroller", ""),
    (r"Balios", "Cybex Balios S5", "stroller", "full", ""),
    (r"Eezy S Twist", "Cybex Eezy S Twist+ 2", "stroller", "travel", ""),
    (r"Beezy", "Cybex Beezy", "stroller", "travel", ""),
    (r"Orfeo", "Cybex Orfeo", "stroller", "travel", ""),
    (r"Agis", "Cybex Agis", "stroller", "travel", ""),
    (r"Cloud T", "Cybex Cloud T", "carseat", "infant", ""),
    (r"Sirona T", "Cybex Sirona T i-Size", "carseat", "convertible", "R129"),
    (r"Anoris T2", "Cybex Anoris T2 i-Size Plus", "carseat", "toddler", "R129"),
    (r"Solution T", "Cybex Solution T i-Fix", "carseat", "booster", ""),
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
          "Graco", "Evenflo", "Doona", "Thule", "Recaro", "Mutsy", "Bumprider", "Twigy", "Safety 1st", "Petite"]
BRANDS_HE = {"סייבקס": "Cybex", "צ'יקו": "Chicco", "ציקו": "Chicco", "ג'ואי": "Joie", "בי סייף": "BeSafe",
             "בוגבו": "Bugaboo", "נונה": "Nuna", "מקסי קוזי": "Maxi-Cosi", "סטוקי": "Stokke", "יויו": "YOYO",
             "בריטקס": "Britax", "פג פרגו": "Peg Perego", "אינגלזינה": "Inglesina", "ג'ולז": "Joolz",
             "סילבר קרוס": "Silver Cross", "קינדרקראפט": "Kinderkraft", "גרקו": "Graco", "דונה": "Doona"}
ACCESSORY_ANY = r"מתאם|תיק|שמשי|כיסוי|כילה|כילת|פגוש|מזרן|בסיס לסלקל|בסיס איזופיקס|מראה|ארגונית|מחזיק כוס|שק שינה|מגן"


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


CHAINS = ("shilav", "babystar", "motzetzim", "agalease", "minena")


def from_manual(base_fn):
    p = ROOT / "data" / "raw" / "manual.json"
    if not p.exists():
        return []
    d = json.loads(p.read_text(encoding="utf-8"))
    b = lambda seller, **kw: base_fn(seller, d["fetched"], **kw)
    prods = d["products"]
    rows = cybex_rows([x for x in prods if x["seller"] == "cybex"], b) + \
        chicco_rows([x for x in prods if x["seller"] == "chicco"], b)
    for ch in CHAINS:
        rows += chain_rows(ch, [x for x in prods if x["seller"] == ch], b)
    return rows
