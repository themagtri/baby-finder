"""Canonical model names, so the same model at different sellers can be compared on the card.

Sellers spell models differently (Hebrew transliteration vs English, colours appended, ™, line breaks).
Each brand has an ordered alias list: regex (Hebrew | English spellings) -> canonical model. More specific
patterns come first (e.g. "NextFit Zip Max" before "NextFit Zip"). Joie also gets a fallback built from the
English words of the name with colour words removed. If nothing matches, the product is not compared
(better no comparison than a wrong one). Cybex uses the table in manual_source.CYBEX.
"""
import re

ALIASES = {
    "Chicco": [
        (r"פיט ?360 זיפ|fit ?360 zip", "Fit360 Zip"), (r"פיט ?360|fit ?360", "Fit360"),
        (r"פיט 3 ?איקס|fit ?3x", "Fit3X"), (r"אבר וואן|ever ?one", "EverOne"),
        (r"נקסטפיט זיפ מקס|nextfit zip max", "NextFit Zip Max"), (r"נקסטפיט זיפ אייר|nextfit zip air", "NextFit Zip Air"),
        (r"נקסטפיט זיפ|nextfit zip", "NextFit Zip"), (r"וואן פיט מקס|onefit max", "OneFit Max"),
        (r"וואן פיט lx|onefit lx", "OneFit LX"), (r"מיי ?פיט אייר|myfit air", "MyFit Air"),
        (r"קידפיט אדפט|kidfit adapt", "KidFit Adapt Plus"), (r"גופיט פלוס|gofit plus", "GoFit Plus"),
        (r"טאורמינה|taormina", "Taormina"), (r"בלאג'יו 2|bellagio 2", "Bellagio 2"),
        (r"בלאג'יו פרימו|bellagio primo", "Bellagio Primo"), (r"בלאג'יו|bellagio", "Bellagio"),
        (r"גלאם|glam", "Mysa Glam"), (r"מיסה|mysa", "Mysa"), (r"הוללה|ohlala", "Ohlala"),
        (r"גודי אקס פלוס|xplus|x plus", "Goody XPlus"), (r"גודי פרימו|goody primo", "Goody Primo"),
        (r"one4ever|אבר4|וואן4אבר", "One4Ever"), (r"קוויק|kwik", "Kwik One"),
        (r"וואן ?פיט|onefit", "OneFit"), (r"מיי ?פיט|myfit", "MyFit"), (r"גופיט|gofit", "GoFit"),
    ],
    "Bugaboo": [
        (r"דרגונ? ?פליי פלוס|dragonfly plus", "Dragonfly Plus"), (r"דרגונ? ?פליי|dragonfly", "Dragonfly"),
        (r"פוקס 5 ?r\b|fox 5 ?r\b", "Fox 5R"), (r"פוקס 5.*renew|fox 5.*renew", "Fox 5 Renew"), (r"פוקס 5|fox 5", "Fox 5"),
        (r"בטרפלי?י 2|butterfly 2", "Butterfly 2"), (r"(דונקי|donkey).*(duo|דואו)", "Donkey 5 Duo"), (r"(דונקי|donkey).*(twins|טווינס)", "Donkey 5 Twins"),
        (r"(דונקי|donkey).*(mono|מונו)", "Donkey 5 Mono"), (r"דונקי 5|donkey 5", "Donkey 5"), (r"דונקי|donkey", "Donkey"),
        (r"bee ?6|בי 6", "Bee 6"), (r"פוקס 3|fox 3", "Fox 3"), (r"בטרפליי|butterfly", "Butterfly"),
    ],
    "Britax": [
        (r"קידפיקס|kidfix", "Kidfix"), (r"swivel grow max|סוויבל גרו מקס", "Swivel Grow Max"),
        (r"וואן פור לייף slim|one4life slim", "One4Life Slim"), (r"וואן (פור|4) לייף|one ?4 ?life", "One4Life"),
        (r"galaxy ?360", "Galaxy360 Slim"), (r"skyline|סקיילין", "Skyline"), (r"פופלר|poplar", "Poplar S"),
        (r"גרו קליקטייט|grow with you clicktight", "Grow With You ClickTight"), (r"grow ?with ?you|גרו", "Grow With You"),
        (r"אדוונספיקס|advansafix", "Advansafix Pro"), (r"willow", "Willow S"), (r"\brio\b|ריו", "Rio"),
    ],
    "Sport Line": [
        (r"סיאלו xl|cielo xl", "Cielo XL"), (r"סיאלו pro|cielo pro", "Cielo Pro"), (r"נובו|novo", "Novo"),
        (r"פולד|\bfold\b", "Fold"), (r"סלייד|slide", "Slide"), (r"אליקס|alix", "Alix"), (r"unico|יוניקו", "Unico"),
        (r"וייפר", "Viper"), (r"סינקו|cinco", "Cinco"), (r"ultra|אולטרה", "Ultra"),
        (r"cielo ?q|סיילו ?קיו", "Cielo Q"), (r"i-? ?happy", "i-Happy"), (r"i-? ?protec", "I-Protec"),
        (r"protect plus", "Protect Plus"), (r"\bflex\b|פלקס", "Flex"), (r"cielo ?pl|סיילו ?פיאל", "Cielo PL"),
    ],
    "BeSafe": [(r"turn b", "iZi Turn B"), (r"izi flex fix", "iZi Flex Fix"), (r"modular x1", "iZi Modular X1")],
    "Babysafe": [(r"\bg ?409\b", "G409"), (r"\bg ?412\b", "G412"), (r"\bneo\b", "Neo"), (r"everride", "EverRide"),
                 (r"everfit", "EverFit"), (r"\briver\b", "River"), (r"growgo", "GrowGo"), (r"lyb ?960", "LYB960"),
                 (r"elevate", "Elevate"), (r"\borbit\b", "Orbit"), (r"flexride", "FlexRide"), (r"zenda", "Zenda")],
    "Joolz": [(r"aer\+|אייר ?פלוס", "Aer+"), (r"hub\+|האב ?פלוס", "Hub+"), (r"day\+|דיי ?פלוס", "Day+"),
              (r"geo ?3|ג'יאו 3", "Geo3")],
    "Peg Perego": [(r"volo|וולו", "Volo"), (r"selfie|סלפי", "Selfie"), (r"vivace|ויוואצ'ה", "Vivace"),
                   (r"veloce|ולוצ'ה", "Veloce"), (r"ypsi|איפסי", "Ypsi"), (r"\bbook\b|בוק", "Book")],
    "UPPAbaby": [(r"minu ?v3", "Minu V3"), (r"minu ?v2", "Minu V2"), (r"vista ?v3", "Vista V3"), (r"vista ?v2", "Vista V2"),
                 (r"cruz ?v2|קרוז 2", "Cruz V2"), (r"ויסטה 2", "Vista V2")],
    "Anex": [(r"air-?q", "Air-Q"), (r"\beli\b|אלי", "Eli"), (r"\bflo\b|פלו", "Flo"), (r"iq ?pro", "IQ Pro"), (r"\bl/?type", "l/type")],
    "Silver Cross": [(r"reef ?2", "Reef 2"), (r"\breef\b|ריף", "Reef"), (r"tide|טייד", "Tide"), (r"clic ?2", "Clic 2"),
                     (r"dune|דיון", "Dune"), (r"jet|ג'ט", "Jet")],
    "Kikkaboo": [(r"modena 2", "Modena 2"), (r"modena|מודנה", "Modena"), (r"eden|עדן", "Eden")],
    "Graco": [(r"slim ?fit ?3 ?lx|סלימפיט", "SlimFit3 LX"), (r"easyturn|איזי ?טרן", "EasyTurn 360"),
              (r"turn2me ?(™)? ?grow", "Turn2Me Grow"), (r"turn2me", "Turn2Me"),
              (r"nautilus elite|נאוטילוס אליט", "Nautilus Elite"), (r"snug ?lock|סנאג לוק", "Nautilus SnugLock LX"),
              (r"nautilus|נאוטילוס", "Nautilus"), (r"tranzitions|טרנזישנס", "Tranzitions"),
              (r"affix", "Affix"), (r"energi", "Energi"), (r"junior maxi", "Junior Maxi"), (r"booster basic", "Booster Basic"),
              (r"logi[cg]o ?l\b", "Logico L"), (r"eldura", "Eldura"), (r"extend ?(™)? ?lx", "Extend LX"),
              (r"flexigrow", "FlexiGrow"), (r"eversure", "EverSure")],
    "Baby Jogger": [(r"city tour 2 double|סיטי טור 2 (דאבל|double)", "City Tour 2 Double"), (r"city mini 2 double", "City Mini 2 Double"),
                    (r"city tour 2|סיטי טור 2", "City Tour 2"), (r"city mini gt ?2", "City Mini GT2"), (r"city mini 2", "City Mini 2"),
                    (r"city sights|סיטי סייטס", "City Sights"), (r"city select 2", "City Select 2")],
    "Kinderkraft": [(r"fix2go", "FIX2GO"), (r"i-lite", "I-LITE"), (r"comfort up", "Comfort Up"), (r"xpedition", "Xpedition")],
    "Stokke": [(r"yoyo\s*(3|³)|יויו 3", "YOYO³")],
    "Joie": [(r"(basil|באזיל).*(beckless|backless|ללא גב)", "basil backless"), (r"ספרינט|sprint", "sprint"),
             (r"באזיל|basil", "basil")],
}
JOIE_DROP = set("""eclipse oyster carbon pebble cashew raven coal oak evergreen shale sandstone ebony maple cedar
cocoa mink twig toffee pewter dark sky with 4in1 tri""".split())


# brand from a distinctive model name, for listings whose name leaves the brand out (e.g. Super-Pharm
# "Affix™ R129 בוסטר"). Only trademarked model names that belong to one brand.
MODEL_BRAND = [
    (r"solution (b|g2|t)|סולושן|cloud (g|t)\b|קלאוד|sirona|סירונה|aton b2|אטון|pallas g3|melio|מליו|gazelle s", "Cybex"),
    (r"affix|junior maxi|energi|logi[cg]o ?l\b|booster basic|turn2me|extend ?(™)? ?lx|flexigrow|eversure|eldura|slim ?fit ?3|easyturn|tranzitions|nautilus", "Graco"),
    (r"basil|chili spin|i-?snug|i-?level|i-?traver|i-?spin|every ?stage|trillo|duallo|elevate™|stages", "Joie"),
    (r"advansafix|kidfix|one ?4 ?life|poplar|grow ?with ?you|swivel|galaxy ?360", "Britax"),
    (r"nextfit|onefit|myfit|kidfit|gofit|fit ?360|fit ?3x", "Chicco"),
]


def brand_from_model(name):
    for rx, b in MODEL_BRAND:
        if re.search(rx, name, re.I):
            return b
    return ""


def canonical(brand, name):
    low = name.lower().replace("™", "").replace("®", "")
    key = next((k for k in ALIASES if k.lower() == (brand or "").lower()), brand)
    for rx, canon in ALIASES.get(key, []):
        if re.search(rx, low, re.I):
            return canon
    if brand == "Joie":
        words = re.findall(r"[a-z0-9]+", low.replace("i-", "i "))
        words = [w for w in words if w not in JOIE_DROP and w != "joie"]
        return " ".join(words) or None
    return None
