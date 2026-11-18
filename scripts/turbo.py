"""Minimal decoder for React Router 'turbo-stream' payloads embedded in a page
(window.__reactRouterContext.streamController.enqueue("...")).
Read-only parsing of data the page already ships to every visitor."""
import json, re

ENQUEUE = re.compile(r'streamController\.enqueue\(("(?:[^"\\]|\\.)*")\)')


def payload(html):
    chunks = ENQUEUE.findall(html)
    text = "".join(json.loads(c) for c in chunks)
    return [json.loads(line) for line in text.splitlines() if line.strip().startswith("[")]


def decode(arr):
    memo = {}

    def val(i):
        if not isinstance(i, int):
            return i  # typed-tuple payloads carry literals
        if i < 0:
            return None  # special markers (undefined / null / NaN / holes)
        if i in memo:
            return memo[i]
        v = arr[i]
        if isinstance(v, dict):
            out = {}
            memo[i] = out
            for k, j in v.items():
                out[arr[int(k[1:])]] = val(j)
            return out
        if isinstance(v, list):
            if len(v) == 2 and isinstance(v[0], str) and v[0] in ("D", "P", "Z", "R", "E", "Y"):
                return v[1]
            out = []
            memo[i] = out
            out.extend(val(j) for j in v)
            return out
        return v

    return val(0)


def walk(o, pred, found=None, seen=None):
    found = [] if found is None else found
    seen = set() if seen is None else seen
    if id(o) in seen:
        return found
    if isinstance(o, dict):
        seen.add(id(o))
        if pred(o):
            found.append(o)
        for v in o.values():
            walk(v, pred, found, seen)
    elif isinstance(o, list):
        seen.add(id(o))
        for v in o:
            walk(v, pred, found, seen)
    return found
