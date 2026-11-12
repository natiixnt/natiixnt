"""Builds the README graphics (assets/*-dark.svg and *-light.svg).

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
W = 600

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
    def __init__(self, theme, height, title, desc):
        self.t = THEMES[theme]
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
                % (W, self.h, W, self.h, esc(self.title), esc(self.desc), defs, "".join(self.body)))


def save(name, theme, svg):
    path = os.path.join(OUT, "%s-%s.svg" % (name, theme))
    with open(path, "w") as fh:
        fh.write(svg)
    print("%-28s %6.1f KB" % (os.path.basename(path), len(svg) / 1024))


# ---------------------------------------------------------------- banner
def banner(theme):
    c = Canvas(theme, 236, "Natalia Szczepanik, Senior AI Engineer and Forward Deployed Engineer",
               "LLM agents, RAG, evaluation, production ML. Warsaw, Poland, remote or hybrid.")
    t = c.t
    c.rect(0, 0, W, c.h, 16, t["bg"], t["border"])
    c.text(32, 84, "Natalia Szczepanik", 46, t["text"], 700, -0.045)
    c.text(32, 122, "Senior AI Engineer | Forward Deployed Engineer", 17, t["accent"], 500)
    c.text(32, 154, "LLM agents, RAG, evaluation, production ML", 15, t["muted"], 400)
    c.text(32, 176, "Warsaw, Poland | remote or hybrid", 13.5, t["muted"], 400)
    c.text(32, 205, "Agent hub: 7 of 38 resolved experiments kept, 31 rolled back", 12, t["muted"], 400)
    n, gap = 38, 3
    bw = (W - 64 - gap * (n - 1)) / n
    for i in range(n):
        c.rect(32 + i * (bw + gap), 212, bw, 12, 2, t["green"] if i < 7 else t["off"])
    save("banner", theme, c.render())


# ---------------------------------------------------------------- impact
IMPACT = [
    ("40+", "AI and automation deployments at companies of 20 to 200 people"),
    ("2,770 h", "saved per month in total, as reported in post-deployment case studies"),
    ("-43%", "cost per task on my agent orchestration platform within two weeks, first-pass rate held at 71 to 78%"),
    ("0.86", "clause@1 of the legal RAG on a 234-question golden dataset, MRR 0.975"),
]


def impact(theme):
    tw, th, gap = (W - 12) / 2, 128, 12
    c = Canvas(theme, 2 * th + gap, "Selected impact",
               "; ".join("%s: %s" % x for x in IMPACT))
    t = c.t
    for i, (big, txt) in enumerate(IMPACT):
        x, y = (i % 2) * (tw + gap), (i // 2) * (th + gap)
        c.rect(x, y, tw, th, 14, t["card"], t["border"])
        c.text(x + 22, y + 52, big, 36, t["text"], 700, -0.03)
        c.para(x + 22, y + 78, txt, 13.5, t["muted"], tw - 44, 19)
    save("impact", theme, c.render())


# ---------------------------------------------------------------- scope
SCOPE = [
    ("Backend and APIs", "Python since 2016, FastAPI, Celery, PostgreSQL, Redis. REST APIs, webhooks, OAuth2, KSeF."),
    ("Custom systems and apps", "Built to order: purchasing decision platform, Budibase apps, CRM and invoice workflow."),
    ("AI agents and orchestration", "Multi-agent systems on Claude, OpenAI and Gemini. Test gates, cross-model review, human approval."),
    ("RAG", "Structure-aware chunking, hybrid retrieval, reranking. Every answer cites its source or abstains."),
    ("Fine-tuning and evaluation", "Polish embedding fine-tune, LoRA, golden datasets, A/B tests, drift detection."),
    ("Research and open source", "Redcon, a benchmark on the fly visual system, papers in preparation."),
    ("Integrations and automation", "n8n, ERP and CRM, monday.com, KSeF. 40+ deployments at companies of 20 to 200 people."),
    ("Infrastructure and deployment", "Docker and Kubernetes on client servers or in their AWS accounts. CI/CD, backups, tracing."),
    ("Security by design", "Non-root containers, least privilege, secrets management, prompt-injection defence, audit logs."),
]


def scope(theme):
    cw, ch, gap, pad = (W - 12) / 2, 112, 12, 20
    rows = (len(SCOPE) + 1) // 2
    c = Canvas(theme, rows * ch + (rows - 1) * gap, "What I do",
               "; ".join("%s: %s" % x for x in SCOPE))
    t = c.t
    for i, (title, txt) in enumerate(SCOPE):
        last = i == len(SCOPE) - 1 and len(SCOPE) % 2 == 1
        x, y = (0 if last else (i % 2) * (cw + gap)), (i // 2) * (ch + gap)
        w = W if last else cw
        c.rect(x, y, w, ch, 14, t["card"], t["border"])
        c.text(x + pad, y + 34, title, 16.5, t["text"], 600, -0.01)
        c.para(x + pad, y + 58, txt, 13.5, t["muted"], w - 2 * pad, 19)
    save("scope", theme, c.render())


# ---------------------------------------------------------------- cards
CARDS = [
    dict(name="card-agent-hub", tags=["in production", "runs client deployments"],
         title="Agent hub: multi-agent orchestration with safe self-improvement",
         text="A manager agent, project supervisors and workers in isolated git worktrees run several projects in parallel. Test gates before every merge, code review by a model from a different family, human approval only for irreversible actions. The platform changes its own process through experiments with automatic rollback.",
         metrics=[("-43%", "cost per task"), ("-55%", "median time per task"), ("7 of 38", "experiments kept")]),
    dict(name="card-legal-rag", tags=["client delivery", "core licensed for reuse"],
         title="Legal RAG over 21 Polish statutes",
         text="Every answer cites the provision and the legal-state date; no reliable source means abstention. Hybrid retrieval, RRF and LLM reranking. HyDE, query rewriting and Cohere Rerank were tested and rejected: no gain on this data. Metrics on the 234-question golden dataset.",
         metrics=[("0.86", "clause@1"), ("0.975", "MRR"), ("30/30", "out-of-scope refusals")]),
    dict(name="card-redcon", tags=["open source", "MCP"],
         title="Redcon (ContextBudget)",
         text="Context budgeting layer for coding agents with a public benchmark, context-eval. A/B tests on real agent sessions overturned the original assumption: the main token cost is replayed conversation history, not file selection. I re-planned the roadmap around that finding.",
         ),
    dict(name="card-flyvis", tags=["open source", "paper in preparation"],
         title="flyvis-circuit-bench",
         text="Do circuit-discovery methods recover mechanism or only the connectivity mask? A benchmark against exhaustive ablation on a Drosophila visual-system model (FlyWire, flyvis), preregistered with null models.",
         ),
    dict(name="card-aae", tags=["paper in preparation", "code private"],
         title="AAE: self-improving decision system",
         text="Hundreds of competing strategy variants; one is promoted only after empirical-Bayes shrinkage, anytime-valid sequential tests and online FDR control (e-LOND) under dependent signals. The local LLM has no path to execution; the isolated executor is fail-closed. First domain: on-chain markets, paper trading."),
    dict(name="card-embedding", tags=["MTEB-PL", "in progress"],
         title="Polish embedding model fine-tune",
         text="multilingual-e5-large-instruct on 7 Polish datasets: hard negatives from BM25 plus a cross-encoder, MNRL + Matryoshka loss, MoCo-style memory bank on a single RTX 5080."),
]


def card(theme, d):
    pad = 22
    probe = Canvas(theme, 10, "", "")
    nt = len(probe.wrap(d["title"], 20, W - 2 * pad, 600, -0.02))
    nd = len(probe.wrap(d["text"], 14.5, W - 2 * pad, 400))
    y_title = pad + 26 + 30
    y_text = y_title + (nt - 1) * 26 + 28
    y_end = y_text + (nd - 1) * 22
    extra = 0
    if d.get("metrics"):
        extra = 16 + 56
    elif d.get("foot"):
        extra = 14 + 18
    h = int(y_end + extra + pad + 6)
    c = Canvas(theme, h, d["title"], d["text"])
    t = c.t
    c.rect(0, 0, W, h, 14, t["card"], t["border"])
    x = pad
    for i, tag in enumerate(d["tags"]):
        x += c.pill(x, pad, tag, t["text"] if i == 0 else t["muted"]) + 8
    for i, line in enumerate(c.wrap(d["title"], 20, W - 2 * pad, 600, -0.02)):
        c.text(pad, y_title + i * 26, line, 20, t["text"], 600, -0.02)
    c.para(pad, y_text, d["text"], 14.5, t["muted"], W - 2 * pad, 22)
    if d.get("metrics"):
        gap = 10
        mw = (W - 2 * pad - 2 * gap) / 3
        my = y_end + 22
        for i, (val, lab) in enumerate(d["metrics"]):
            mx = pad + i * (mw + gap)
            c.rect(mx, my, mw, 52, 10, t["bg"], t["border"])
            c.text(mx + 12, my + 24, val, 18, t["green"], 700, -0.02)
            c.text(mx + 12, my + 42, lab, 11.5, t["muted"], 400)
    elif d.get("foot"):
        c.text(pad, y_end + 34, d["foot"], 13.5, t["accent"], 500)
    save(d["name"], theme, c.render())


# ---------------------------------------------------------------- stack
STACK = [
    ("Agents", ["LangGraph", "LangChain", "MCP", "Claude Code", "Temporal", "Prefect", "Pydantic", "tool use"]),
    ("Models", ["Claude", "OpenAI", "Gemini", "AWS Bedrock", "Qwen3", "vLLM", "OpenRouter"]),
    ("RAG", ["pgvector", "Qdrant", "Pinecone", "ChromaDB", "BM25", "RRF", "rerankers"]),
    ("Evals", ["golden datasets", "regression suites", "Langfuse", "LangSmith", "OpenTelemetry", "Prometheus"]),
    ("ML", ["PyTorch", "Hugging Face", "LoRA", "LightGBM", "Optuna"]),
    ("Backend", ["Python", "FastAPI", "Celery", "PostgreSQL", "Redis", "TypeScript", "Node.js", "Next.js"]),
    ("Cloud", ["AWS", "Azure", "Docker", "Kubernetes", "GitHub Actions", "Terraform (basic)"]),
    ("Integrations", ["REST", "webhooks", "OAuth2", "n8n", "monday.com", "KSeF", "Budibase"]),
]


def stack(theme):
    lw, ph, gx, gy = 96, 28, 7, 8
    probe = Canvas(theme, 10, "", "")
    layouts, total = [], 0
    for label, items in STACK:
        rows, x, row = [[]], 0, 0
        for it in items:
            w = probe.width(it, 13, 500) + 22
            if x + w > W - lw - 24 and rows[-1]:
                rows.append([])
                x = 0
            rows[-1].append((it, x, w))
            x += w + gx
        layouts.append(rows)
        total += len(rows) * (ph + gy) + 14
    h = total + 24
    c = Canvas(theme, h, "Stack",
               "; ".join("%s: %s" % (l, ", ".join(i)) for l, i in STACK))
    t = c.t
    c.rect(0, 0, W, h, 14, t["card"], t["border"])
    y = 16
    for (label, _), rows in zip(STACK, layouts):
        c.text(22, y + 19, label, 13.5, t["text"], 600)
        for ri, row in enumerate(rows):
            for it, x, w in row:
                yy = y + ri * (ph + gy)
                c.rect(lw + 22 + x, yy, w, ph, 8, t["chip"], t["chip_border"])
                c.text(lw + 22 + x + 11, yy + 18.5, it, 13, t["text"], 500)
        y += len(rows) * (ph + gy) + 14
    save("stack", theme, c.render())


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for th in THEMES:
        banner(th)
        impact(th)
        scope(th)
        for d in CARDS:
            card(th, d)
        stack(th)
