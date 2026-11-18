"""Read text from a PDF area in logical (reading) order for Hebrew/English mixed lines.
PyMuPDF returns words in visual order; for an RTL line we sort words right-to-left and keep runs of
Latin/number words left-to-right. Hebrew geresh words come out as "יקו'צ" and are put back as "צ'יקו"."""
import re

HEB = re.compile(r"[\u0590-\u05FF]")


def fix_word(w):
    m = re.fullmatch(r"(.+)'([צגזתח])", w)
    return f"{m.group(2)}'{m.group(1)}" if m and HEB.search(m.group(1)) else w


def lines_in(page, rect):
    import pymupdf as fitz
    words = [w for w in page.get_text("words") if rect.contains(fitz.Point((w[0] + w[2]) / 2, (w[1] + w[3]) / 2))]
    groups = {}
    for w in words:
        groups.setdefault((w[5], w[6]), []).append(w)
    out = []
    for key in sorted(groups, key=lambda k: min(w[1] for w in groups[k])):
        ws = groups[key]
        if any(HEB.search(w[4]) for w in ws):
            ws = sorted(ws, key=lambda w: -w[0])
            toks, run = [], []
            for w in ws:
                if HEB.search(w[4]):
                    toks += reversed(run); run = []; toks.append(fix_word(w[4]))
                else:
                    run.append(w[4])
            toks += reversed(run)
        else:
            toks = [w[4] for w in sorted(ws, key=lambda w: w[0])]
        out.append(" ".join(toks))
    return out
