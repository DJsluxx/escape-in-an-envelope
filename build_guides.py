#!/usr/bin/env python3
"""build_guides.py — generate SEO "party guide" article pages for the site.

Each guide at /guides/<slug>.html is a genuinely useful, long-form party article that
targets a high-volume long-tail query ("dinosaur birthday party games", "free printable
escape room for kids", ...) and funnels to the matching paid kit + the Etsy/Gumroad shops.
Content comes from guides_content.json (drafted + editor-reviewed upstream); the free-printable
guide additionally embeds the free mini-escape-room from free_puzzle.json and offers the PDF.

Also builds /guides/index.html (the hub) and rebuilds sitemap.xml to include homepage +
all kit pages + all guide pages + the guides hub + the free printable PDF.

    python build_guides.py
"""
from __future__ import annotations
import html, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = "https://djsluxx.github.io/escape-in-an-envelope"
ETSY = "https://escapeinanenvelop.etsy.com"
GUM = "https://salama62.gumroad.com"
FREE_PDF = f"{BASE}/free/mini-escape-room.pdf"

def esc(s): return html.escape(str(s))

# Compact kit map for funnel links (slug -> emoji, short title, gumroad slug, ages, price)
KITS = {
 "dino-6-8": ("🦖", "Dino Escape", "pyqyvv", "6-8", "9"),
 "space-5-6": ("🚀", "Space Station Escape", "jkemsb", "5-6", "9"),
 "spy-7-9": ("🕵️", "Spy HQ Lockdown", "wypktg", "7-9", "10"),
 "pirate-6-8": ("🏴‍☠️", "Pirate Treasure Escape", "egugwl", "6-8", "9"),
 "unicorn-5-7": ("🦄", "Rainbow Kingdom Escape", "gwycbb", "5-7", "9"),
 "superhero-6-9": ("🦸", "Superhero Academy Escape", "cgoaw", "6-9", "9"),
 "princess-4-6": ("👑", "Royal Castle Escape", "zsfgkd", "4-6", "9"),
 "mermaid-5-7": ("🧜‍♀️", "Mermaid Lagoon Escape", "tajaxj", "5-7", "9"),
 "jungle-safari-6-8": ("🐒", "Jungle Safari Rescue", "ylftn", "6-8", "9"),
 "ninja-7-9": ("🥷", "Ninja Dojo Escape", "btdxt", "7-9", "10"),
}

# guide slug -> (funnel kit slug or None for "all", og-image url)
GUIDE_META = {
 "free-printable-escape-room-for-kids": (None, f"{BASE}/pins/free-printable-pin.png"),
 "dinosaur-birthday-party-games": ("dino-6-8", f"{BASE}/pins/dino-6-8-pin.png"),
 "unicorn-party-ideas-for-kids": ("unicorn-5-7", f"{BASE}/pins/unicorn-5-7-pin.png"),
 "space-party-games-for-kids": ("space-5-6", f"{BASE}/pins/space-5-6-pin.png"),
 "pirate-party-games-for-kids": ("pirate-6-8", f"{BASE}/pins/pirate-6-8-pin.png"),
 "superhero-party-ideas-for-kids": ("superhero-6-9", f"{BASE}/pins/superhero-6-9-pin.png"),
 "kids-escape-room-party-guide": (None, f"{BASE}/pins/ultimate-guide-pin.png"),
}
GUIDE_ORDER = list(GUIDE_META.keys())
GUIDE_NAV = {
 "free-printable-escape-room-for-kids": "🗝️ Free Printable Escape Room",
 "dinosaur-birthday-party-games": "🦖 Dinosaur Party Games",
 "unicorn-party-ideas-for-kids": "🦄 Unicorn Party Ideas",
 "space-party-games-for-kids": "🚀 Space Party Games",
 "pirate-party-games-for-kids": "🏴‍☠️ Pirate Party Games",
 "superhero-party-ideas-for-kids": "🦸 Superhero Party Ideas",
 "kids-escape-room-party-guide": "🔐 Kids Escape Room (How-To)",
}

CSS = """
:root{--primary:#3d3a5c;--accent:#c9a227;--ink:#2b2740;--paper:#faf7f0;--band:#e7e0cf;--etsy:#f56400}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:"Segoe UI","Trebuchet MS",system-ui,sans-serif;color:var(--ink);background:var(--paper);line-height:1.65}
a{color:var(--primary)}
.wrap{max-width:760px;margin:0 auto;padding:0 20px}
.top{background:linear-gradient(150deg,var(--band),var(--paper));padding:16px 0}
.top .wrap{display:flex;align-items:center;justify-content:space-between;max-width:820px}
.brand{font-weight:800;color:var(--primary);text-decoration:none;font-size:18px}
.crumb{font-size:13px;opacity:.7}
header.hero{text-align:center;padding:38px 20px 6px}
.emoji{font-size:66px;line-height:1}
h1{font-size:clamp(25px,4.6vw,38px);color:var(--primary);margin:10px auto 8px;font-weight:800;max-width:680px}
.hook{font-size:clamp(16px,2.5vw,20px);margin:8px auto 0;max-width:620px;opacity:.9}
.hero-img{max-width:300px;width:100%;border-radius:16px;box-shadow:0 10px 30px rgba(0,0,0,.15);margin:22px auto 4px;display:block}
.article{padding:8px 0 10px}
.article h2{color:var(--primary);font-size:23px;margin:30px 0 12px}
.article p{margin:0 0 14px}
.article ul,.article ol{margin:0 0 16px 4px;padding-left:22px}
.article li{margin:6px 0}
.cta{display:flex;gap:14px;justify-content:center;flex-wrap:wrap;margin:22px 0 8px}
.btn{display:inline-block;padding:13px 26px;border-radius:999px;font-weight:800;font-size:16px;text-decoration:none;box-shadow:0 4px 0 rgba(0,0,0,.12)}
.btn.etsy{background:var(--etsy);color:#fff}.btn.gum{background:var(--primary);color:#fff}.btn.free{background:var(--accent);color:#fff}
.funnel{background:#fff;border:2px solid var(--band);border-radius:16px;padding:24px 22px;margin:30px 0;text-align:center}
.funnel .e{font-size:44px}
.funnel h3{color:var(--primary);font-size:22px;margin:6px 0 8px}
.funnel p{opacity:.9;max-width:560px;margin:0 auto 8px}
.price{opacity:.7;font-size:13px;margin-top:6px}
details{background:#fff;border:2px solid var(--band);border-radius:12px;padding:2px 16px;margin-bottom:10px}
summary{font-weight:800;color:var(--primary);cursor:pointer;padding:12px 0;list-style:none}
summary::-webkit-details-marker{display:none}summary::after{content:"+";float:right}details[open] summary::after{content:"–"}
details p{padding:0 0 12px;opacity:.88;margin:0}
.puzzle{background:#fff;border:2px dashed var(--band);border-radius:14px;padding:18px 20px;margin:16px 0}
.puzzle h3{color:var(--primary);margin:0 0 6px}
.puzzle .ans{font-size:14px;opacity:.75}
.more{display:flex;gap:10px;flex-wrap:wrap;justify-content:center}
.chip{background:#fff;border:2px solid var(--band);border-radius:999px;padding:8px 15px;text-decoration:none;color:var(--primary);font-weight:700;font-size:14px}
.guidenav{display:flex;gap:8px;flex-wrap:wrap;justify-content:center;margin:10px 0 0}
footer{text-align:center;padding:30px 20px;opacity:.7;font-size:14px;border-top:1px solid var(--band);margin-top:20px}
"""

DOMAIN_VERIFY = '<meta name="p:domain_verify" content="acbbe5c41ba31559d65bd39fffa9f24c">'


def render_sections(sections):
    out = []
    for s in sections:
        out.append(f'<h2>{esc(s["h2"])}</h2>')
        for p in s.get("paragraphs", []) or []:
            out.append(f"<p>{esc(p)}</p>")
        bullets = s.get("bullets") or []
        if bullets:
            tag = "ol" if s.get("ordered") else "ul"
            lis = "".join(f"<li>{esc(b)}</li>" for b in bullets)
            out.append(f"<{tag}>{lis}</{tag}>")
    return "\n".join(out)


def render_faq(faq):
    items = "".join(
        f'<details{" open" if i == 0 else ""}><summary>{esc(f["q"])}</summary><p>{esc(f["a"])}</p></details>'
        for i, f in enumerate(faq)
    )
    return f'<h2>Common questions</h2>{items}'


def funnel_block(funnel_kit, funnel_pitch):
    if funnel_kit and funnel_kit in KITS:
        emoji, title, gslug, ages, price = KITS[funnel_kit]
        return f"""<div class="funnel"><div class="e">{emoji}</div>
<h3>The done-for-you version: {esc(title)}</h3>
<p>{esc(funnel_pitch)}</p>
<div class="cta"><a class="btn gum" href="{GUM}/l/{gslug}" rel="noopener">Get {esc(title)} — ${price} →</a><a class="btn etsy" href="{ETSY}" rel="noopener">Shop on Etsy →</a></div>
<p class="price">Instant PDF · print at home · nothing ships · reusable · <a href="../kits/{funnel_kit}.html">see everything inside →</a></p></div>"""
    # generic funnel (pillar pages)
    return f"""<div class="funnel"><div class="e">🔐✉️</div>
<h3>Want it done for you? Grab a themed kit</h3>
<p>{esc(funnel_pitch)}</p>
<div class="cta"><a class="btn gum" href="{GUM}" rel="noopener">Browse all kits on Gumroad →</a><a class="btn etsy" href="{ETSY}" rel="noopener">Shop on Etsy →</a></div>
<p class="price">13 themes · ages 4–9 · instant PDF · ~$9 each · <a href="../index.html">see all kits →</a></p></div>"""


def free_download_block():
    return f"""<div class="funnel" style="border-color:var(--accent)"><div class="e">🗝️</div>
<h3>Grab the free printable pack (PDF)</h3>
<p>The complete 3-puzzle mini escape room below, ready to print — clue cards, the setup guide, and a "You Escaped!" certificate. No email required.</p>
<div class="cta"><a class="btn free" href="{FREE_PDF}" rel="noopener" download>⬇ Download the free printable</a></div>
<p class="price">One page to print · set up in 5 minutes · household items only</p></div>"""


def render_free_puzzle_html(pz):
    if not pz:
        return ""
    parts = [f'<h2>Your free mini escape room: “{esc(pz["title"])}”</h2>']
    parts.append(f'<p><b>Read this aloud to start:</b> {esc(pz["story_intro"])}</p>')
    parts.append(f'<p><b>5-minute setup:</b> {esc(pz["host_setup"])}</p>')
    for p in pz["puzzles"]:
        parts.append(
            f'<div class="puzzle"><h3>Puzzle {p["n"]}: {esc(p["name"])}</h3>'
            f'<p>{esc(p["instructions"])}</p>'
            f'<p class="ans"><b>You need:</b> {esc(p["materials"])}<br><b>Answer:</b> {esc(p["answer"])} → write down the digit <b>{esc(p["yields_digit"])}</b></p></div>'
        )
    parts.append(
        f'<div class="puzzle" style="border-style:solid"><h3>🔓 The final code</h3>'
        f'<p>Put the three digits together in order to get <b>{esc(pz["final_code"])}</b>. {esc(pz["final_instruction"])}</p>'
        f'<p class="ans">🏅 {esc(pz["certificate_line"])}</p></div>'
    )
    return "\n".join(parts)


def guide_page(art, pz=None):
    slug = art["slug"]
    funnel_kit, og_img = GUIDE_META[slug]
    is_free = slug == "free-printable-escape-room-for-kids"
    other_guides = "".join(
        f'<a class="chip" href="{s}.html">{GUIDE_NAV[s]}</a>' for s in GUIDE_ORDER if s != slug
    )
    kit_chips = "".join(
        f'<a class="chip" href="../kits/{s}.html">{KITS[s][0]} {esc(KITS[s][1])}</a>' for s in list(KITS)[:6]
    )

    body = []
    if is_free:
        body.append(free_download_block())
    body.append(f'<div class="article">{render_sections(art["sections"])}')
    if is_free and pz:
        body.append(render_free_puzzle_html(pz))
    body.append("</div>")
    body.append(funnel_block(funnel_kit, art["funnel_pitch"]))
    body.append(render_faq(art["faq"]))
    body.append(f'<section style="padding-top:24px"><h2>More free party guides</h2><div class="more">{other_guides}</div></section>')
    body.append(f'<section style="padding-top:6px"><h2>Popular printable escape rooms</h2><div class="more">{kit_chips}</div>'
                f'<p style="text-align:center;margin-top:16px"><a href="../index.html">← See all 13 kits</a></p></section>')
    body_html = "\n".join(body)

    faq_ld = {
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": f["q"],
             "acceptedAnswer": {"@type": "Answer", "text": f["a"]}} for f in art["faq"]
        ],
    }
    article_ld = {
        "@context": "https://schema.org", "@type": "Article",
        "headline": art["h1"], "description": art["meta_description"],
        "image": og_img, "author": {"@type": "Organization", "name": "Escape in an Envelope"},
        "publisher": {"@type": "Organization", "name": "Escape in an Envelope"},
        "mainEntityOfPage": f"{BASE}/guides/{slug}.html",
    }
    kw = ", ".join(art["keywords"])
    return f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
{DOMAIN_VERIFY}
<title>{esc(art["seo_title"])}</title>
<meta name="description" content="{esc(art["meta_description"])}">
<meta name="keywords" content="{esc(kw)}">
<link rel="canonical" href="{BASE}/guides/{slug}.html">
<meta name="theme-color" content="#3d3a5c">
<meta property="og:type" content="article"><meta property="og:title" content="{esc(art["h1"])}">
<meta property="og:description" content="{esc(art["meta_description"])}"><meta property="og:url" content="{BASE}/guides/{slug}.html">
<meta property="og:image" content="{og_img}">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{og_img}">
<script type="application/ld+json">{json.dumps(article_ld)}</script>
<script type="application/ld+json">{json.dumps(faq_ld)}</script>
<style>{CSS}</style></head><body>
<div class="top"><div class="wrap"><a class="brand" href="../index.html">🔐✉️ Escape in an Envelope</a><span class="crumb">Party Guides › {esc(art["h1"][:40])}</span></div></div>
<header class="hero">
<div class="emoji">{esc(art["emoji"])}</div>
<h1>{esc(art["h1"])}</h1>
<p class="hook">{esc(art["hook"])}</p>
<img class="hero-img" src="{og_img}" alt="{esc(art["h1"])}" width="300" loading="lazy" />
</header>
<div class="wrap">
{body_html}
</div>
<footer>Escape in an Envelope · print-at-home escape rooms for kids ages 4–9 · <a href="index.html">Party guides</a> · <a href="{ETSY}">Etsy</a> · <a href="{GUM}">Gumroad</a></footer>
</body></html>"""


def guides_index(articles):
    cards = "".join(
        f'<a class="chip" href="{a["slug"]}.html" style="padding:14px 18px;font-size:15px">{GUIDE_NAV[a["slug"]]}</a>'
        for a in articles
    )
    return f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
{DOMAIN_VERIFY}
<title>Free Kids Party Games &amp; Escape Room Guides | Escape in an Envelope</title>
<meta name="description" content="Free, practical party guides: dinosaur, unicorn, space, pirate &amp; superhero party games, plus how to make a kids escape room at home — with a free printable.">
<link rel="canonical" href="{BASE}/guides/index.html">
<meta name="theme-color" content="#3d3a5c">
<meta property="og:title" content="Free Kids Party Games &amp; Escape Room Guides">
<meta property="og:image" content="{BASE}/pins/free-printable-pin.png">
<style>{CSS}</style></head><body>
<div class="top"><div class="wrap"><a class="brand" href="../index.html">🔐✉️ Escape in an Envelope</a><span class="crumb">Party Guides</span></div></div>
<header class="hero"><div class="emoji">🎉</div>
<h1>Free kids party guides</h1>
<p class="hook">Real, usable party plans — games, food, decorations and timings — plus a free printable escape room you can run today.</p>
<div class="guidenav" style="margin-top:22px">{cards}</div></header>
<div class="wrap"><section style="padding-top:26px"><h2>Ready-made escape room kits</h2>
<p class="hook" style="margin:0 0 14px">Love the ideas but short on time? Every themed kit is an instant-download, print-at-home escape room — zero prep.</p>
<div class="cta"><a class="btn gum" href="{GUM}" rel="noopener">Browse kits on Gumroad →</a><a class="btn etsy" href="{ETSY}" rel="noopener">Shop on Etsy →</a></div>
<p style="text-align:center;margin-top:16px"><a href="../index.html">← See all 13 kits</a></p></section></div>
<footer>Escape in an Envelope · print-at-home escape rooms for kids ages 4–9 · <a href="{ETSY}">Etsy</a> · <a href="{GUM}">Gumroad</a></footer>
</body></html>"""


def build_sitemap(guide_slugs):
    kit_slugs = ["dino-6-8","space-5-6","spy-7-9","pirate-6-8","unicorn-5-7","superhero-6-9",
                 "princess-4-6","mermaid-5-7","jungle-safari-6-8","ninja-7-9",
                 "halloween-6-9","christmas-5-8","easter-4-7"]
    urls = [(f"{BASE}/", "1.0")]
    urls += [(f"{BASE}/guides/index.html", "0.9")]
    urls += [(f"{BASE}/guides/{s}.html", "0.9") for s in guide_slugs]
    urls += [(f"{BASE}/kits/{s}.html", "0.8") for s in kit_slugs]
    sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for u, pr in urls:
        sm += f"  <url><loc>{u}</loc><changefreq>weekly</changefreq><priority>{pr}</priority></url>\n"
    sm += "</urlset>\n"
    (ROOT / "sitemap.xml").write_text(sm, encoding="utf-8")
    return len(urls)


def main():
    content = json.loads((ROOT / "guides_content.json").read_text(encoding="utf-8"))
    articles = content["articles"] if isinstance(content, dict) else content
    pz_path = ROOT / "free_puzzle.json"
    pz = json.loads(pz_path.read_text(encoding="utf-8")) if pz_path.exists() else None

    gdir = ROOT / "guides"; gdir.mkdir(exist_ok=True)
    # keep canonical order
    by_slug = {a["slug"]: a for a in articles}
    ordered = [by_slug[s] for s in GUIDE_ORDER if s in by_slug]
    for a in ordered:
        (gdir / f"{a['slug']}.html").write_text(guide_page(a, pz), encoding="utf-8")
    (gdir / "index.html").write_text(guides_index(ordered), encoding="utf-8")
    n = build_sitemap([a["slug"] for a in ordered])
    print(f"Built {len(ordered)} guide pages + guides/index.html + sitemap ({n} urls).")


if __name__ == "__main__":
    main()
