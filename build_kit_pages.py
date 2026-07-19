#!/usr/bin/env python3
"""build_kit_pages.py — generate one SEO landing page per escape-room kit.

Each kit gets its own page at /kits/<slug>.html: keyword-rich title/description,
Product JSON-LD, a direct "Buy" button to that exact Gumroad product (+ Etsy shop),
the 6-puzzle trail, FAQ, and cross-links. Also regenerates index.html's kit cards to
link to these pages, and rebuilds sitemap.xml. Free, on-machine, static — deploys to
GitHub Pages. Purpose: give every Pinterest pin a dedicated high-converting destination
and add 13 indexable pages for long-tail search ("<theme> escape room printable").

    python build_kit_pages.py
"""
from __future__ import annotations
import html, json
from pathlib import Path

import build_guides
from build_guides import utm

ROOT = Path(__file__).resolve().parent
BASE = "https://djsluxx.github.io/escape-in-an-envelope"
ETSY = "https://escapeinanenvelop.etsy.com"
GUM = "https://salama62.gumroad.com"

def esc(s): return html.escape(str(s))

# slug: (emoji, display title, ages, players, minutes, price, hook, [6 puzzles], certificate, gumroad_slug, season, etsy_url)
# etsy_url None = kit not (verifiably) listed on Etsy; CTAs fall back to the shop root.
KITS = {
 "dino-6-8": ("🦖","Dino Escape: Operation Rexy","6-8","3-8","30-45","9",
   "Baby T-Rex Rexy is about to break out of the lab — crack the cage code and stop the escape!",
   ["Count the fossils","Sort the dino food","Cross the lava maze","Reveal a hidden colour","Crack the ranger code","Spot the differences"],
   "Junior Dino Ranger","pyqyvv",None,
   "https://www.etsy.com/listing/4539492669/dinosaur-escape-room-printable-game-ages"),
 "space-5-6": ("🚀","Space Station Escape","5-6","3-8","25-40","9",
   "The space station is offline and a meteor shower is coming — get the lights back on!",
   ["Count the stars","Sort the space gear","Steer past the asteroids","Reveal a hidden colour","Crack the star code","Spot the differences"],
   "Junior Astronaut","jkemsb",None,
   "https://www.etsy.com/listing/4539496989/space-station-escape-room-game-astronaut"),
 "spy-7-9": ("🕵️","Spy HQ Lockdown","7-9","3-8","35-50","10",
   "The thief Shadow has locked down HQ and hidden the Golden Chip — agents, recover it!",
   ["Key-card count","Real-vs-fake sort","The laser hall","Colour-reveal","The spy cipher","Spot the differences"],
   "Secret Agent","wypktg",None,
   "https://www.etsy.com/listing/4539506947/spy-escape-room-kids-printable-secret"),
 "pirate-6-8": ("🏴‍☠️","Pirate Treasure Escape","6-8","3-8","30-45","9",
   "Sneaky Captain Sea-Rat locked away the treasure — young pirates, open the chest!",
   ["Count the gold","Sort treasure from trash","Dodge the sharks","Reveal a hidden number","Crack the pirate code","Spot the differences"],
   "Junior Pirate","egugwl",None,
   "https://www.etsy.com/listing/4539508791/pirate-escape-room-kids-printable"),
 "unicorn-5-7": ("🦄","Rainbow Kingdom Escape","5-7","3-8","25-40","9",
   "The kingdom's magic sparkle is fading and everything's turning grey — bring the rainbow back!",
   ["Count the gems","Sort magic from ordinary","Cross the storm clouds","Reveal a hidden colour","Crack the rainbow code","Spot the differences"],
   "Junior Unicorn Ranger","gwycbb",None,
   "https://www.etsy.com/listing/4539597713/unicorn-escape-room-kids-printable"),
 "superhero-6-9": ("🦸","Superhero Academy Escape","6-9","3-8","30-45","9",
   "The villain Mister Muddle scrambled the whole city — young heroes, switch it back to normal!",
   ["Count the power gems","Spot the real gadgets","Dodge the chaos bolts","Reveal a hidden colour","Crack the hero code","Spot the differences"],
   "Junior Superhero","cgoaw",None,None),
 "princess-4-6": ("👑","Royal Castle Escape","4-6","3-8","20-35","9",
   "The sparkly crown jewels have vanished — little royals, find them before the ball!",
   ["Count the jewels","Sort what belongs to a royal","Skip past the dragon","Reveal a hidden colour","Crack the royal code","Spot the differences"],
   "Junior Royal","zsfgkd",None,None),
 "mermaid-5-7": ("🧜‍♀️","Mermaid Lagoon Escape","5-7","3-8","25-40","9",
   "The Mermaid Queen has lost her magic pearl — swim through the reef and find it before the tide turns!",
   ["Count the pearls","Sort treasure from trash","Swim past the sharks","Reveal a hidden colour","Crack the shell code","Spot the differences"],
   "Junior Mermaid","tajaxj",None,None),
 "jungle-safari-6-8": ("🐒","Jungle Safari Rescue Escape","6-8","3-8","30-45","9",
   "Baby monkey Mango wandered off — safari explorers, bring him home before nightfall!",
   ["Count the bird eggs","Pack the rescue gear","Cross the vine bridge","Reveal a hidden colour","Crack the jungle code","Spot the differences"],
   "Junior Safari Explorer","ylftn",None,None),
 "ninja-7-9": ("🥷","Ninja Dojo Escape","7-9","3-8","30-45","10",
   "A masked thief stole the sacred scroll from the dojo — ninja trainees, recover it!",
   ["Count the shuriken","Spot the real ninja gear","Slip past the traps","Reveal a secret ink message","Crack the shadow code","Spot the differences"],
   "Junior Shinobi","btdxt",None,None),
 "halloween-6-9": ("🎃","Monster Mansion Escape","6-9","3-8","30-45","9",
   "Count Snackula has hidden all the Halloween candy — monster hunters, rescue the treats!",
   ["Count the candy","Sort treats from tricks","Escape the ghosts","Reveal a hidden colour","Crack the monster code","Spot the differences"],
   "Junior Monster Hunter",None,"Halloween",None),
 "christmas-5-8": ("🎄","Santa's Workshop Escape","5-8","3-8","30-45","9",
   "The sleigh code is scrambled and Santa can't take off — little elves, get Christmas back on track!",
   ["Count the presents","Sort naughty from nice","Cross the icy path","Reveal a hidden colour","Crack the elf code","Spot the differences"],
   "Junior Elf",None,"Christmas",None),
 "easter-4-7": ("🐰","Easter Bunny's Egg Hunt Escape","4-7","3-8","20-35","9",
   "Hopscotch the Easter Bunny hid the golden egg — egg hunters, find it before the picnic!",
   ["Count the pink eggs","Sort yummy from yucky","Hop past the puddles","Reveal a hidden colour","Crack the bunny code","Spot the differences"],
   "Junior Egg Hunter",None,"Easter",None),
}

CSS = """
:root{--primary:#3d3a5c;--accent:#c9a227;--ink:#2b2740;--paper:#faf7f0;--band:#e7e0cf;--etsy:#f56400}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:"Segoe UI","Trebuchet MS",system-ui,sans-serif;color:var(--ink);background:var(--paper);line-height:1.6}
a{color:var(--primary)}
.wrap{max-width:820px;margin:0 auto;padding:0 20px}
.top{background:linear-gradient(150deg,var(--band),var(--paper));padding:16px 0}
.top .wrap{display:flex;align-items:center;justify-content:space-between}
.brand{font-weight:800;color:var(--primary);text-decoration:none;font-size:18px}
.crumb{font-size:13px;opacity:.7}
header{text-align:center;padding:40px 20px 8px}
.emoji{font-size:74px;line-height:1}
h1{font-size:clamp(26px,5vw,40px);color:var(--primary);margin:10px 0 6px;font-weight:800}
.meta{font-weight:700;color:var(--accent);letter-spacing:.5px}
.hook{font-size:clamp(17px,2.6vw,21px);margin:16px auto 0;max-width:620px;opacity:.9}
.pin-img{max-width:270px;width:100%;border-radius:16px;box-shadow:0 10px 30px rgba(0,0,0,.15);margin:20px auto 4px;display:block}
.cta{display:flex;gap:14px;justify-content:center;flex-wrap:wrap;margin:26px 0 10px}
.btn{display:inline-block;padding:14px 30px;border-radius:999px;font-weight:800;font-size:17px;text-decoration:none;box-shadow:0 4px 0 rgba(0,0,0,.12)}
.btn.etsy{background:var(--etsy);color:#fff}.btn.gum{background:var(--primary);color:#fff}
.price{text-align:center;opacity:.7;font-size:14px;margin-bottom:8px}
section{padding:30px 0;border-top:1px solid var(--band)}
h2{color:var(--primary);font-size:24px;margin-bottom:14px}
ol.trail{list-style:none;counter-reset:s}
ol.trail li{counter-increment:s;padding:10px 0 10px 46px;position:relative;border-bottom:1px dashed var(--band)}
ol.trail li::before{content:counter(s);position:absolute;left:0;top:8px;width:30px;height:30px;background:var(--accent);color:#fff;border-radius:50%;text-align:center;line-height:30px;font-weight:800}
ul.inc{list-style:none}ul.inc li{padding:7px 0 7px 28px;position:relative}ul.inc li::before{content:"✔";position:absolute;left:0;color:var(--accent);font-weight:800}
.steps{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:18px;text-align:center}
.step .e{font-size:38px}.step b{display:block;color:var(--primary);margin:6px 0 2px}
details{background:#fff;border:2px solid var(--band);border-radius:12px;padding:2px 16px;margin-bottom:10px}
summary{font-weight:800;color:var(--primary);cursor:pointer;padding:12px 0;list-style:none}
summary::-webkit-details-marker{display:none}summary::after{content:"+";float:right}details[open] summary::after{content:"–"}
details p{padding:0 0 12px;opacity:.85}
.more{display:flex;gap:10px;flex-wrap:wrap;justify-content:center}
.chip{background:#fff;border:2px solid var(--band);border-radius:999px;padding:8px 16px;text-decoration:none;color:var(--primary);font-weight:700;font-size:14px}
footer{text-align:center;padding:30px 20px;opacity:.7;font-size:14px}
"""

def page(slug, k):
    emoji,title,ages,players,mins,price,hook,puzzles,cert,gslug,season,etsy_url = k
    seo_title = f"{title} — Printable Escape Room for Kids Ages {ages} | Escape in an Envelope"
    desc = f"{title}: a print-at-home escape room for kids ages {ages}. Six puzzles, zero prep, instant PDF download. {hook}"
    gum_url = utm(f"{GUM}/l/{gslug}" if gslug else GUM, "kit", slug)
    etsy_href = etsy_url or ETSY
    buy_gum = f'<a class="btn gum" href="{gum_url}" rel="noopener">Buy on Gumroad — ${price} →</a>' if gslug else ""
    season_line = f'<p class="price">⏰ Seasonal — a {season} favourite. Grab it a few weeks ahead.</p>' if season else ""
    trail = "".join(f"<li>{esc(p)}</li>" for p in puzzles)
    others = "".join(
        f'<a class="chip" href="{s}.html">{KITS[s][0]} {esc(KITS[s][1].split(":")[0])}</a>'
        for s in KITS if s != slug)[:1400]
    ld = {
      "@context":"https://schema.org","@type":"Product",
      "name":f"{title} — Printable Kids Escape Room (Ages {ages})",
      "image":f"{BASE}/pins/{slug}-pin.png",
      "description":desc,"brand":{"@type":"Brand","name":"Escape in an Envelope"},
      "category":"Toys & Games > Games > Party Games",
      "audience":{"@type":"PeopleAudience","suggestedMinAge":ages.split("-")[0],"suggestedMaxAge":ages.split("-")[1]},
      "offers":{"@type":"Offer","price":price,"priceCurrency":"USD","availability":"https://schema.org/InStock","url":gum_url}
    }
    return f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="p:domain_verify" content="acbbe5c41ba31559d65bd39fffa9f24c">
<title>{esc(seo_title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="keywords" content="{esc(slug.rsplit('-',2)[0])} escape room, printable escape room kids, {esc(slug.rsplit('-',2)[0])} party game, kids escape room ages {ages}, print at home party game, instant download">
<link rel="canonical" href="{BASE}/kits/{slug}.html">
<meta name="theme-color" content="#3d3a5c">
<meta property="og:type" content="product"><meta property="og:title" content="{esc(title)} — Printable Kids Escape Room">
<meta property="og:description" content="{esc(hook)}"><meta property="og:url" content="{BASE}/kits/{slug}.html">
<meta property="og:image" content="{BASE}/pins/{slug}-pin.png">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{BASE}/pins/{slug}-pin.png">
<script type="application/ld+json">{json.dumps(ld)}</script>
<style>{CSS}</style></head><body>
<div class="top"><div class="wrap"><a class="brand" href="../index.html">🔐✉️ Escape in an Envelope</a><span class="crumb">Kids Escape Rooms › {esc(title.split(':')[0])}</span></div></div>
<header>
<div class="emoji">{emoji}</div>
<h1>{esc(title)}</h1>
<p class="meta">Printable · Ages {ages} · {players} players · {mins} min</p>
<p class="hook">{esc(hook)}</p>
<img class="pin-img" src="{BASE}/pins/{slug}-pin.png" alt="{esc(title)} printable kids escape room" width="270" loading="lazy" />
<div class="cta">{buy_gum}<a class="btn etsy" href="{etsy_href}" rel="noopener">Shop on Etsy →</a></div>
<p class="price">Instant PDF download · nothing ships · prints on any home printer · reusable</p>
{season_line}
</header>
<div class="wrap">
<section><h2>The 6-puzzle trail</h2><ol class="trail">{trail}</ol>
<p style="margin-top:12px;opacity:.85">Every puzzle is designed and <b>verified to actually solve at ages {ages}</b> — no frustrated kids, no missing clues, no wrong answers.</p></section>
<section><h2>What's in the download</h2><ul class="inc">
<li>6 illustrated clue cards (a full clue-to-clue trail)</li>
<li>7 themed zone signs — tape them anywhere</li>
<li>A code card + finale keypad card</li>
<li>Printable {esc(cert)} certificates for every child</li>
<li>A full host guide with the complete answer key</li></ul></section>
<section><h2>How it works</h2><div class="steps">
<div class="step"><div class="e">🛒</div><b>1. Buy &amp; download</b>Instant PDF — nothing ships.</div>
<div class="step"><div class="e">🖨️</div><b>2. Print &amp; hide</b>Print the cards, tape up the signs.</div>
<div class="step"><div class="e">🔎</div><b>3. Play</b>Kids solve the trail and crack the code!</div></div>
<div class="cta" style="margin-top:22px">{buy_gum}<a class="btn etsy" href="{etsy_href}" rel="noopener">Shop on Etsy →</a></div></section>
<section><h2>Questions</h2>
<details open><summary>What do I get?</summary><p>An instant PDF: 6 clue cards, 7 zone signs, a code card and finale keypad, {esc(cert)} certificates, and a full host guide with the answer key. Nothing is shipped — you print at home.</p></details>
<details><summary>Do I need anything special?</summary><p>Just a home printer (colour recommended) and some tape. No app, no props, no batteries, zero prep.</p></details>
<details><summary>Is it right for ages {ages}?</summary><p>Yes — every puzzle was built and tested to solve at this age band. There's a host guide with hints if anyone gets stuck.</p></details>
<details><summary>Can I reuse it?</summary><p>Absolutely — print it again for the next party, sleepover, rainy day, or classroom.</p></details></section>
<section><h2>More kids escape rooms</h2><div class="more">{others}</div>
<p style="text-align:center;margin-top:18px"><a href="../index.html">← See all 13 kits</a></p></section>
</div>
<footer>Escape in an Envelope · print-at-home escape rooms for kids ages 4–9 · <a href="{ETSY}">Etsy</a> · <a href="{utm(GUM, "kit", slug)}">Gumroad</a></footer>
</body></html>"""

def main():
    kdir = ROOT / "kits"; kdir.mkdir(exist_ok=True)
    for slug,k in KITS.items():
        (kdir / f"{slug}.html").write_text(page(slug,k), encoding="utf-8")
    # sitemap — delegate to build_guides.build_sitemap so the superset guard runs
    # (a kit-only sitemap here used to silently drop every /guides/ URL).
    guide_order = [a["slug"] for a in build_guides.load_articles()]
    n = build_guides.build_sitemap(ROOT, guide_order)
    print(f"Built {len(KITS)} kit pages + sitemap ({n} urls).")

if __name__ == "__main__":
    main()
