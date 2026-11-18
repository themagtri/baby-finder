"""Polite one-pass probe of candidate seller sites: robots.txt, then WooCommerce Store API, Shopify
products.json, and the home page. One request per check, 2 s apart; stops on a block for that host."""
import sys, time, re, json, urllib.error, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from polite import fetch, robots, UA, Blocked

def probe(host):
    res = {"host": host}
    try:
        rp = robots(host); time.sleep(2)
    except Blocked as e: res["status"] = f"blocked robots ({e})"; return res
    except Exception as e: res["status"] = f"unreachable: {str(e)[:60]}"; return res
    for name, path in [("woo", "/wp-json/wc/store/v1/products?per_page=2"), ("shopify", "/products.json?limit=2")]:
        u = f"https://{host}{path}"
        if not rp.can_fetch(UA, u): res[name] = "robots-disallow"; continue
        try:
            b, _ = fetch(u, "application/json")
            res[name] = "OK" if b.lstrip()[:1] in "[{" and ("prices" in b or "variants" in b) else "not-json"
        except Blocked as e: res[name] = "BLOCKED " + str(e)[6:30]; res["status"] = "blocked"; return res
        except urllib.error.HTTPError as e: res[name] = f"http {e.code}"
        except Exception as e: res[name] = "err " + str(e)[:40]
        time.sleep(2)
        if res[name] == "OK": res["status"] = name; return res
    try:
        b, _ = fetch(f"https://{host}/", "text/html")
        res["home"] = len(b)
        res["platform"] = next((p for p, k in [("magento", "Magento"), ("wix", "wix"), ("konimbo", "konimbo"),
                                               ("shopify", "cdn.shopify"), ("woo", "woocommerce"), ("next", "__NEXT_DATA__")]
                                if k.lower() in b.lower()), "?")
        res["status"] = "html-ok"
    except Blocked as e: res["status"] = "blocked home"
    except Exception as e: res["status"] = "home err " + str(e)[:40]
    return res

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    for h in sys.argv[1:]:
        print(json.dumps(probe(h), ensure_ascii=False)); time.sleep(2)
