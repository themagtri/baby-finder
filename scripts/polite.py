"""Shared polite-fetch helpers: our UA, robots.txt read with our UA, fixed delay, stop on block."""
import time, urllib.request, urllib.robotparser

UA = "baby-finder-research/0.1 (+https://github.com/themagtri/baby-finder)"

class Blocked(SystemExit):
    pass

def fetch(url, accept="*/*", timeout=40):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8", "replace")
            return body, r.headers
    except urllib.error.HTTPError as e:
        if e.code in (401, 403, 429, 503):
            raise Blocked(f"STOP: HTTP {e.code} at {url}")
        raise
    
def robots(host):
    """Parse robots.txt fetched with OUR user-agent (the stdlib reader uses Python-urllib and some sites 403 it)."""
    rp = urllib.robotparser.RobotFileParser()
    try:
        body, _ = fetch(f"https://{host}/robots.txt", "text/plain")
        rp.parse(body.splitlines())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            rp.parse([])
        else:
            raise
    return rp

def check(rp, url):
    if not rp.can_fetch(UA, url):
        raise Blocked(f"STOP: robots.txt disallows {url}")
