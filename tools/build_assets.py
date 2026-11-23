"""Builds the README graphics: banner, impact strip and project grid, each in dark and light
and in a desktop (840 px) and a phone (360 px, "-m") layout: assets/<name>[-m]-<theme>.svg.

All text is converted to outlines (glyph paths), because GitHub serves README
SVGs through <img> with a CSP that blocks web fonts, embedded or not.
Geist (OFL) is read from tools/fonts. Run: python3 tools/build_assets.py
Needs: pip install fonttools brotli
"""
import copy
import os
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "assets")
FONT = os.path.join(HERE, "fonts", "geist-latin-wght-normal.woff2")

THEMES = {
    "dark": dict(bg="#0c0c0e", card="#141417", border="#26262b", text="#f2f2f3", muted="#a1a1aa",
                 accent="#8ea2ff", green="#7dd3a4", chip="#18181b", chip_border="#33333a", off="#33333a"),
    "light": dict(bg="#f6f6f8", card="#ffffff", border="#dcdce2", text="#16161a", muted="#53535e",
                  accent="#3f55c8", green="#17724a", chip="#f1f1f5", chip_border="#cfcfd8", off="#d4d4dc"),
}

_base = TTFont(FONT)
_cache = {}


def face(weight):
    if weight not in _cache:
        f = instancer.instantiateVariableFont(copy.deepcopy(_base), {"wght": weight})
        _cache[weight] = (f, f.getGlyphSet(), f.getBestCmap(), f["hmtx"])
    return _cache[weight]


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


class Canvas:
    def __init__(self, theme, width, height, title, desc):
        self.t = THEMES[theme]
        self.w = width
        self.h = height
        self.title, self.desc = title, desc
        self.defs = {}
        self.body = []

    # text -----------------------------------------------------------
    def width(self, text, size, weight=400, ls=0.0):
        f, gs, cmap, hmtx = face(weight)
        return sum(hmtx[cmap[ord(c)]][0] * size / 1000 + ls * size for c in text) - (ls * size if text else 0)

    def wrap(self, text, size, maxw, weight=400, ls=0.0):
        lines, cur = [], ""
        for word in text.split(" "):
            trial = (cur + " " + word).strip()
            if cur and self.width(trial, size, weight, ls) > maxw:
                lines.append(cur)
                cur = word
            else:
                cur = trial
        if cur:
            lines.append(cur)
        return lines

    def glyph(self, ch, weight):
        gid = "g%d_%d" % (weight, ord(ch))
        if gid not in self.defs:
            f, gs, cmap, hmtx = face(weight)
            pen = SVGPathPen(gs, lambda v: ("%.1f" % v).rstrip("0").rstrip("."))
            gs[cmap[ord(ch)]].draw(TransformPen(pen, (1, 0, 0, -1, 0, 0)))
            self.defs[gid] = pen.getCommands()
        return gid

    def text(self, x, y, s, size, color, weight=400, ls=0.0, anchor="start"):
        f, gs, cmap, hmtx = face(weight)
        total = self.width(s, size, weight, ls)
        if anchor == "middle":
            x -= total / 2
        elif anchor == "end":
            x -= total
        sc = size / 1000
        pos, uses = 0.0, []
        for ch in s:
            adv = hmtx[cmap[ord(ch)]][0]
            if ch != " ":
                uses.append('<use href="#%s" x="%s"/>' % (self.glyph(ch, weight), ("%.1f" % pos).rstrip("0").rstrip(".")))
            pos += adv + ls * 1000
        self.body.append('<g transform="translate(%.1f %.1f) scale(%.5f)" fill="%s">%s</g>' % (x, y, sc, color, "".join(uses)))
        return total

    def para(self, x, y, s, size, color, maxw, lh, weight=400, ls=0.0):
        for i, line in enumerate(self.wrap(s, size, maxw, weight, ls)):
            self.text(x, y + i * lh, line, size, color, weight, ls)
        return len(self.wrap(s, size, maxw, weight, ls))

    # shapes ---------------------------------------------------------
    def rect(self, x, y, w, h, r, fill, stroke=None):
        st = ' stroke="%s" stroke-width="1"' % stroke if stroke else ""
        if stroke:
            x, y, w, h = x + .5, y + .5, w - 1, h - 1
        self.body.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%s" fill="%s"%s/>' % (x, y, w, h, r, fill, st))

    def pill(self, x, y, s, color, size=12.5, weight=500, h=26, fill=None, stroke=None):
        w = self.width(s, size, weight) + 22
        self.rect(x, y, w, h, h / 2, fill or "none", stroke or self.t["chip_border"])
        self.text(x + 11, y + h / 2 + size * 0.35, s, size, color, weight)
        return w

    def render(self):
        defs = "".join('<path id="%s" d="%s"/>' % (k, v) for k, v in sorted(self.defs.items()))
        return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" role="img" aria-labelledby="t d">'
                '<title id="t">%s</title><desc id="d">%s</desc><defs>%s</defs>%s</svg>\n'
                % (self.w, self.h, self.w, self.h, esc(self.title), esc(self.desc), defs, "".join(self.body)))


def save(name, theme, svg, phone=False):
    path = os.path.join(OUT, "%s%s-%s.svg" % (name, "-m" if phone else "", theme))
    with open(path, "w") as fh:
        fh.write(svg)
    print("%-28s %6.1f KB" % (os.path.basename(path), len(svg) / 1024))


# Every number and title below comes from the CV or from a public repository benchmark.
IMPACT = [
    ("40+", "deployments at companies of 20 to 200 people"),
    ("2,770 h", "saved per month in total"),
    ("-43%", "cost per task on the agent platform"),
    ("-55%", "median task time on the agent platform"),
]

PROJECTS = [
    dict(tag="In production", title="Agent hub: multi-agent orchestration",
         text="Manager agent, project supervisors and workers in isolated git worktrees. Test gates, cross-model review, human approval for irreversible actions.",
         foot="-43% cost per task | -55% median time | 7 of 38 experiments kept", foot_color="green"),
    dict(tag="Open source", title="redcon: context budgeting for coding agents",
         text="Selects, compresses, caches and budgets repository context for coding agents. Works as an MCP server.",
         foot="-69% context tokens on average | public benchmark, 4 tasks", foot_color="green"),
    dict(tag="Paper in preparation | code private", title="AAE: self-improving decision system",
         text="Hundreds of strategy variants; one is promoted only after sequential tests and online FDR control. The isolated executor is fail-closed.",
         foot="First domain: on-chain markets, paper trading", foot_color="accent"),
    dict(tag="MTEB-PL | in progress", title="Polish embedding model fine-tune",
         text="multilingual-e5-large-instruct on 7 Polish datasets: hard negatives from BM25 plus a cross-encoder, MNRL + Matryoshka loss.",
         foot="Single RTX 5080", foot_color="accent"),
]


def banner(theme, phone):
    t = THEMES[theme]
    if not phone:
        c = Canvas(theme, 840, 156, "Natalia Szczepanik, Freelance AI Engineer and Forward Deployed Engineer",
                   "LLM agents, RAG, evals, production deployments. Warsaw, Poland, remote only.")
        c.rect(0, 0, c.w, c.h, 16, t["bg"], t["border"])
        c.text(32, 72, "Natalia Szczepanik", 46, t["text"], 700, -0.045)
        c.text(32, 102, "Freelance AI Engineer | Forward Deployed Engineer", 17, t["accent"], 500)
        c.text(32, 130, "LLM agents, RAG, evals, production deployments | Warsaw, Poland | remote only", 13.5, t["muted"], 400)
    else:
        c = Canvas(theme, 360, 144, "Natalia Szczepanik, Freelance AI Engineer and Forward Deployed Engineer",
                   "LLM agents, RAG, evals, production deployments. Warsaw, Poland, remote only.")
        c.rect(0, 0, c.w, c.h, 14, t["bg"], t["border"])
        c.text(20, 54, "Natalia Szczepanik", 32, t["text"], 700, -0.04)
        c.text(20, 82, "Freelance AI Engineer | Forward Deployed Engineer", 13.5, t["accent"], 500)
        c.text(20, 106, "LLM agents, RAG, evals, production deployments", 12.5, t["muted"], 400)
        c.text(20, 124, "Warsaw, Poland | remote only", 12.5, t["muted"], 400)
    save("banner", theme, c.render(), phone)


def impact(theme, phone):
    t = THEMES[theme]
    desc = "; ".join("%s: %s" % x for x in IMPACT)
    if not phone:
        c = Canvas(theme, 840, 104, "Selected impact", desc)
        c.rect(0, 0, c.w, c.h, 14, t["card"], t["border"])
        cw = c.w / 4
        for i, (big, txt) in enumerate(IMPACT):
            x = i * cw
            if i:
                c.rect(x, 18, 1, c.h - 36, 0, t["border"])
            c.text(x + 24, 48, big, 34, t["text"], 700, -0.03)
            c.para(x + 24, 71, txt, 12.5, t["muted"], cw - 40, 16)
    else:
        cw, ch = 180, 84
        c = Canvas(theme, 360, 2 * ch, "Selected impact", desc)
        c.rect(0, 0, c.w, c.h, 14, t["card"], t["border"])
        c.rect(c.w / 2, 14, 1, c.h - 28, 0, t["border"])
        c.rect(14, ch, c.w - 28, 1, 0, t["border"])
        for i, (big, txt) in enumerate(IMPACT):
            x, y = (i % 2) * cw, (i // 2) * ch
            c.text(x + 18, y + 36, big, 26, t["text"], 700, -0.03)
            c.para(x + 18, y + 55, txt, 11.5, t["muted"], cw - 30, 14)
    save("impact", theme, c.render(), phone)


def projects(theme, phone):
    t = THEMES[theme]
    desc = "; ".join("%s: %s" % (p["title"], p["text"]) for p in PROJECTS)
    cols = 1 if phone else 2
    gap, cw = (10, 360) if phone else (12, 414)
    pad = 18
    tsz, bsz, fsz = (15.5, 12.5, 11.5) if phone else (17, 13, 11.5)
    probe = Canvas(theme, 10, 10, "", "")

    def parts(p):
        tl = probe.wrap(p["title"], tsz, cw - 2 * pad, 600, -0.02)
        bl = probe.wrap(p["text"], bsz, cw - 2 * pad, 400)
        fl = probe.wrap(p["foot"], fsz, cw - 2 * pad, 600 if p["foot_color"] == "green" else 500)
        return tl, bl, fl

    def need(p):
        tl, bl, fl = parts(p)
        return 54 + (len(tl) - 1) * 22 + 24 + (len(bl) - 1) * 18.5 + 10 + 16 + (len(fl) - 1) * 16 + pad + 4
    rows = [PROJECTS[i:i + cols] for i in range(0, len(PROJECTS), cols)]
    heights = [int(max(need(p) for p in r)) for r in rows]
    total = sum(heights) + gap * (len(rows) - 1)
    c = Canvas(theme, cw * cols + gap * (cols - 1), total, "Projects and research", desc)
    y = 0
    for r, h in zip(rows, heights):
        for k, p in enumerate(r):
            x = k * (cw + gap)
            c.rect(x, y, cw, h, 14, t["card"], t["border"])
            c.text(x + pad, y + 28, p["tag"], 11.5, t["accent"], 500)
            tl, bl, fl = parts(p)
            for n, line in enumerate(tl):
                c.text(x + pad, y + 54 + n * 22, line, tsz, t["text"], 600, -0.02)
            by = y + 54 + (len(tl) - 1) * 22 + 24
            for n, line in enumerate(bl):
                c.text(x + pad, by + n * 18.5, line, bsz, t["muted"], 400)
            fy = y + h - pad - 4 - (len(fl) - 1) * 16
            for n, line in enumerate(fl):
                c.text(x + pad, fy + n * 16, line, fsz, t[p["foot_color"]], 600 if p["foot_color"] == "green" else 500)
        y += h + gap
    save("projects", theme, c.render(), phone)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for th in THEMES:
        for phone in (False, True):
            banner(th, phone)
            impact(th, phone)
            projects(th, phone)
