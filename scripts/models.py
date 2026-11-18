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
    ],
    "Bugaboo": [
        (r"דרגונ? ?פליי פלוס|dragonfly plus", "Dragonfly Plus"), (r"דרגונ? ?פליי|dragonfly", "Dragonfly"),
        (r"פוקס 5 ?r\b|fox 5 ?r\b", "Fox 5R"), (r"פוקס 5.*renew|fox 5.*renew", "Fox 5 Renew"), (r"פוקס 5|fox 5", "Fox 5"),
        (r"בטרפלי?י 2|butterfly 2", "Butterfly 2"), (r"דונקי 5|donkey 5", "Donkey 5"), (r"דונקי|donkey", "Donkey"),
        (r"bee ?6|בי 6", "Bee 6"),
    ],
    "Britax": [
        (r"קידפיקס|kidfix", "Kidfix"), (r"swivel grow max|סוויבל גרו מקס", "Swivel Grow Max"),
        (r"וואן פור לייף slim|one4life slim", "One4Life Slim"), (r"וואן פור לייף|one4life", "One4Life"),
        (r"galaxy ?360", "Galaxy360 Slim"), (r"skyline|סקיילין", "Skyline"), (r"פופלר|poplar", "Poplar S"),
        (r"גרו קליקטייט|grow with you clicktight", "Grow With You ClickTight"), (r"grow with you|גרו", "Grow With You"),
        (r"אדוונספיקס|advansafix", "Advansafix Pro"), (r"willow", "Willow S"), (r"\brio\b|ריו", "Rio"),
    ],
    "Sport Line": [
        (r"סיאלו xl|cielo xl", "Cielo XL"), (r"סיאלו pro|cielo pro", "Cielo Pro"), (r"נובו|novo", "Novo"),
        (r"פולד|\bfold\b", "Fold"), (r"סלייד|slide", "Slide"), (r"אליקס|alix", "Alix"), (r"unico|יוניקו", "Unico"),
        (r"וייפר", "Viper"), (r"סינקו|cinco", "Cinco"),
    ],
    "BeSafe": [(r"turn b", "iZi Turn B")],
    "Stokke": [(r"yoyo\s*(3|³)|יויו 3", "YOYO³")],
    "Joie": [(r"(basil|באזיל).*(beckless|backless|ללא גב)", "basil backless"), (r"ספרינט|sprint", "sprint"),
             (r"באזיל|basil", "basil")],
}
JOIE_DROP = set("""eclipse oyster carbon pebble cashew raven coal oak evergreen shale sandstone ebony maple cedar
cocoa mink twig toffee pewter dark sky with 4in1 tri""".split())


def canonical(brand, name):
    low = name.lower().replace("™", "").replace("®", "")
    for rx, canon in ALIASES.get(brand, []):
        if re.search(rx, low, re.I):
            return canon
    if brand == "Joie":
        words = re.findall(r"[a-z0-9]+", low.replace("i-", "i "))
        words = [w for w in words if w not in JOIE_DROP and w != "joie"]
        return " ".join(words) or None
    return None
