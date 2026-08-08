#!/usr/bin/env python3
"""Tests for build_guides.py — run with:  python -m pytest test_build_guides.py -v

Builds the whole site into a temp dir (never touching the live files) and checks:
  * all guide pages + the guides hub are generated,
  * sitemap.xml contains every page that exists on disk (>= 27 URLs),
  * sitemap.xml is a superset of the live sitemap.xml (nothing gets de-listed),
  * the superset guard aborts loudly if a listed URL would disappear.
"""
from __future__ import annotations

import html as html_mod
import json
import re
import shutil
from pathlib import Path

import pytest

import build_guides

REPO = Path(__file__).resolve().parent
# Derived from the single source of truth so it never goes stale when a guide is
# added/removed. (Was a hard-coded literal that silently broke the suite on every
# new guide.) +1 for guides/index.html in the page-count assertions.
EXPECTED_GUIDES = len(build_guides.load_articles())


def sitemap_urls(path: Path) -> set[str]:
    return set(re.findall(r"<loc>(.*?)</loc>", path.read_text(encoding="utf-8")))


def make_site_skeleton(root: Path) -> None:
    """Mirror the kit pages (empty placeholders are enough for enumeration) and
    the live sitemap into a scratch site root."""
    (root / "kits").mkdir(parents=True, exist_ok=True)
    for kit in (REPO / "kits").glob("*.html"):
        (root / "kits" / kit.name).touch()
    shutil.copy(REPO / "sitemap.xml", root / "sitemap.xml")


@pytest.fixture(scope="module")
def built_site(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("site")
    make_site_skeleton(root)
    n_articles, n_urls = build_guides.build_site(root)
    assert n_articles == EXPECTED_GUIDES
    return root


def test_all_guide_pages_generated(built_site: Path) -> None:
    pages = sorted(p.name for p in (built_site / "guides").glob("*.html"))
    assert len(pages) == EXPECTED_GUIDES + 1  # 13 guides + index.html
    assert "index.html" in pages
    live_pages = sorted(p.name for p in (REPO / "guides").glob("*.html"))
    assert pages == live_pages  # exactly the same set of files as the live site


def test_guide_pages_not_empty(built_site: Path) -> None:
    for page in (built_site / "guides").glob("*.html"):
        text = page.read_text(encoding="utf-8")
        assert "<h1>" in text, f"{page.name} looks broken (no <h1>)"
        assert len(text) > 4000, f"{page.name} suspiciously small"


def test_sitemap_has_enough_urls(built_site: Path) -> None:
    urls = sitemap_urls(built_site / "sitemap.xml")
    assert len(urls) >= 29, f"sitemap only has {len(urls)} urls"


def test_sitemap_superset_of_live(built_site: Path) -> None:
    live = sitemap_urls(REPO / "sitemap.xml")
    new = sitemap_urls(built_site / "sitemap.xml")
    missing = live - new
    assert not missing, f"rebuilt sitemap dropped live URLs: {sorted(missing)}"


def test_sitemap_lists_every_page_on_disk(built_site: Path) -> None:
    urls = sitemap_urls(built_site / "sitemap.xml")
    for page in (built_site / "guides").glob("*.html"):
        assert f"{build_guides.BASE}/guides/{page.name}" in urls
    for kit in (built_site / "kits").glob("*.html"):
        assert f"{build_guides.BASE}/kits/{kit.name}" in urls


def test_superset_guard_aborts_on_dropped_url(tmp_path: Path) -> None:
    root = tmp_path / "site"
    make_site_skeleton(root)
    poison = f"{build_guides.BASE}/guides/some-page-that-no-longer-exists.html"
    sm = root / "sitemap.xml"
    sm.write_text(
        sm.read_text(encoding="utf-8").replace(
            "</urlset>",
            f"  <url><loc>{poison}</loc><changefreq>weekly</changefreq><priority>0.9</priority></url>\n</urlset>",
        ),
        encoding="utf-8",
    )
    before = sm.read_text(encoding="utf-8")
    with pytest.raises(SystemExit, match="DROP"):
        build_guides.build_site(root)
    assert sm.read_text(encoding="utf-8") == before  # guard left the sitemap untouched


GUM_HREF_RE = re.compile(r'href="(https://salama62\.gumroad\.com[^"]*)"')


def gumroad_hrefs(text: str) -> list[str]:
    return GUM_HREF_RE.findall(text)


def test_every_gumroad_href_is_utm_tagged(built_site: Path) -> None:
    """Any Gumroad link (product /l/ or shop root) that appears must be UTM-tagged.
    Pillar/head-term guides deliberately carry none — they route theme-undecided
    readers to the on-brand kit index instead of the mixed Gumroad profile."""
    for page in (built_site / "guides").glob("*.html"):
        for h in gumroad_hrefs(page.read_text(encoding="utf-8")):
            assert "utm_source=eie-site" in h and "utm_medium=" in h \
                and "utm_campaign=" in h, f"{page.name}: untagged Gumroad href {h}"


def test_pillar_guides_route_to_kit_index(built_site: Path) -> None:
    """Head-term guides (no themed kit) send undecided readers to the on-brand,
    escape-only kit index — never the mixed Gumroad profile (off-theme ebooks)."""
    articles = build_guides.load_articles()
    pillars = [a for a in articles if a.get("kit") not in build_guides.KITS]
    assert pillars, "expected some pillar guides"
    for art in pillars:
        text = (built_site / "guides" / f"{art['slug']}.html").read_text(encoding="utf-8")
        assert 'href="../index.html"' in text, f"{art['slug']} not routed to kit index"
        assert not gumroad_hrefs(text), f"{art['slug']} still links the mixed Gumroad profile"


def test_no_bare_gumroad_product_links(built_site: Path) -> None:
    for page in (built_site / "guides").glob("*.html"):
        for h in gumroad_hrefs(page.read_text(encoding="utf-8")):
            if "/l/" in h:
                assert "?utm_" in h or "&utm_" in h, f"{page.name}: bare product link {h}"


def test_guide_utm_medium_and_campaign(built_site: Path) -> None:
    """Guide pages tag medium=guide + campaign=<own slug>; hub tags medium=index."""
    articles = build_guides.load_articles()
    kit_guides = [a for a in articles if a.get("kit") in build_guides.KITS]
    assert kit_guides, "no guide funnels to a known kit?"
    # every themed guide whose kit has a real Gumroad product must keep its UTM'd
    # deep link (seasonal kits with no Gumroad slug funnel via an override instead).
    checked = 0
    for art in kit_guides:
        if not build_guides.KITS[art["kit"]][2]:  # (emoji,title,gslug,...) gslug is [2]
            continue
        text = (built_site / "guides" / f"{art['slug']}.html").read_text(encoding="utf-8")
        assert f"utm_medium=guide&utm_campaign={art['slug']}" in text, art["slug"]
        checked += 1
    assert checked >= 10, f"expected many deep-linked themed guides, checked {checked}"
    hub = (built_site / "guides" / "index.html").read_text(encoding="utf-8")
    for h in gumroad_hrefs(hub):
        assert "utm_medium=index&utm_campaign=guides-index" in h, f"hub: {h}"


def test_kit_page_gumroad_utm_and_etsy_deep_link() -> None:
    """build_kit_pages: /l/ hrefs tagged medium=kit + campaign=<kit slug>;
    Etsy CTA deep-links to the listing when known, shop root otherwise."""
    import build_kit_pages

    with_listing = "dino-6-8"       # verified live Etsy listing
    without_listing = "ninja-7-9"   # no Etsy listing -> shop-root fallback

    text = build_kit_pages.page(with_listing, build_kit_pages.KITS[with_listing])
    hrefs = gumroad_hrefs(text)
    assert any("/l/" in h for h in hrefs), "kit page lost its buy link"
    for h in hrefs:
        assert "utm_source=eie-site" in h and "utm_medium=kit" in h \
            and f"utm_campaign={with_listing}" in h, h
    assert 'class="btn etsy" href="https://www.etsy.com/listing/4539492669/' in text
    assert f'class="btn etsy" href="{build_kit_pages.ETSY}"' not in text

    text2 = build_kit_pages.page(without_listing, build_kit_pages.KITS[without_listing])
    assert f'class="btn etsy" href="{build_kit_pages.ETSY}"' in text2


def _ld_blocks(text: str) -> list[dict]:
    import json
    out = []
    for m in re.findall(
        r'<script type="application/ld\+json">(.*?)</script>', text, re.DOTALL
    ):
        try:
            out.append(json.loads(m))
        except json.JSONDecodeError:
            pass
    return out


def test_every_guide_has_breadcrumb_ld(built_site: Path) -> None:
    """AEO: every guide page carries a 3-level BreadcrumbList (Home > Party
    Guides > guide) so search + AI answer engines can place a cited page."""
    for page in (built_site / "guides").glob("*.html"):
        if page.name == "index.html":
            continue
        crumbs = [b for b in _ld_blocks(page.read_text(encoding="utf-8"))
                  if b.get("@type") == "BreadcrumbList"]
        assert crumbs, f"{page.name} missing BreadcrumbList JSON-LD"
        items = crumbs[0]["itemListElement"]
        assert [i["name"] for i in items][:2] == ["Home", "Party Guides"], page.name
        assert len(items) == 3, f"{page.name} breadcrumb not 3 levels"


def test_ordered_guides_emit_howto_ld(built_site: Path) -> None:
    """AEO: a guide with a genuine ordered run-of-show/timeline section emits a
    HowTo whose steps mirror those bullets (truthful, auto-derived)."""
    articles = build_guides.load_articles()
    checked = 0
    for art in articles:
        ordered = next(
            (s for s in art["sections"] if s.get("ordered") and s.get("bullets")), None
        )
        if not ordered or len(ordered["bullets"]) < 3 or art.get("no_howto"):
            continue
        text = (built_site / "guides" / f"{art['slug']}.html").read_text(encoding="utf-8")
        howtos = [b for b in _ld_blocks(text) if b.get("@type") == "HowTo"]
        assert howtos, f"{art['slug']} should emit HowTo JSON-LD"
        assert len(howtos[0]["step"]) == len(ordered["bullets"]), art["slug"]
        checked += 1
    assert checked >= 10, f"expected many how-to guides, only checked {checked}"


def test_answer_first_lead_rendered(built_site: Path) -> None:
    """AEO: EVERY guide declares an `answer` and renders it as a visible
    answer-first lead paragraph at the top of the article. Asserting full
    coverage (not a floor) makes a new guide without a lead fail the suite."""
    articles = build_guides.load_articles()
    missing = [a["slug"] for a in articles if not a.get("answer")]
    assert not missing, f"guides with no answer-first lead: {missing}"
    for art in articles:
        text = (built_site / "guides" / f"{art['slug']}.html").read_text(encoding="utf-8")
        assert '<p class="answer">' in text, f"{art['slug']} missing answer lead"


def test_guides_hub_has_collection_itemlist_ld(built_site: Path) -> None:
    """AEO: the hub carries a BreadcrumbList + a CollectionPage whose ItemList
    enumerates every guide URL, so crawlers get a machine-readable index."""
    articles = build_guides.load_articles()
    blocks = _ld_blocks((built_site / "guides" / "index.html").read_text(encoding="utf-8"))
    types = {b.get("@type") for b in blocks}
    assert {"BreadcrumbList", "CollectionPage"} <= types, types

    collection = next(b for b in blocks if b["@type"] == "CollectionPage")
    item_list = collection["mainEntity"]
    assert item_list["@type"] == "ItemList"
    assert item_list["numberOfItems"] == len(articles)

    listed = {i["url"] for i in item_list["itemListElement"]}
    expected = {f"{build_guides.BASE}/guides/{a['slug']}.html" for a in articles}
    assert listed == expected, f"hub ItemList missing: {sorted(expected - listed)}"
    assert [i["position"] for i in item_list["itemListElement"]] == list(range(1, len(articles) + 1))
    assert all(i["name"] and not i["name"][0].isspace() for i in item_list["itemListElement"])


def test_mid_article_cta_present_and_tagged(built_site: Path) -> None:
    """Conversion: multi-section guides carry a mid-article CTA (.midcta) so a
    reader who bounces before the bottom funnel still sees one buy option. On kit
    guides it deep-links the kit's Gumroad product with a distinct `-mid` UTM
    campaign (separating mid-article conversions from the bottom funnel); on pillar
    guides it routes to the on-brand kit index with no Gumroad profile link."""
    articles = build_guides.load_articles()
    kit_mid = pillar_mid = 0
    for art in articles:
        if art["slug"] == build_guides.FREE_SLUG or len(art["sections"]) < 3:
            continue
        text = (built_site / "guides" / f"{art['slug']}.html").read_text(encoding="utf-8")
        kit = art.get("kit")
        if kit in build_guides.KITS and build_guides.KITS[kit][2]:  # has a real Gumroad slug
            assert 'class="midcta"' in text, f"{art['slug']} missing mid-article CTA"
            assert f"utm_campaign={art['slug']}-mid" in text, f"{art['slug']} mid CTA not -mid tagged"
            kit_mid += 1
        elif kit not in build_guides.KITS:  # pillar / head-term
            assert 'class="midcta"' in text, f"{art['slug']} missing mid-article CTA"
            # the mid CTA appears strictly before the bottom funnel
            assert text.index('class="midcta"') < text.index('class="funnel"'), art["slug"]
            pillar_mid += 1
    assert kit_mid >= 10, f"expected many kit guides with a mid CTA, got {kit_mid}"
    assert pillar_mid >= 1, f"expected pillar guides with a mid CTA, got {pillar_mid}"


GUIDE_SHARE_TAGS = (
    '<meta property="og:site_name"',
    '<meta property="og:image:alt"',
    '<meta property="og:locale"',
    '<meta name="twitter:card"',
    '<meta name="twitter:title"',
    '<meta name="twitter:description"',
    '<meta name="twitter:image:alt"',
)


def test_every_guide_has_complete_share_meta(built_site: Path) -> None:
    """Distribution: social sharing is the site's ONE active human-bringing channel,
    so every guide must render a complete Open Graph + Twitter card (Rich Pin data
    on Pinterest, full preview on FB/WhatsApp/X). A guide missing any share tag ships
    a bare link on the exact channel that matters."""
    for page in (built_site / "guides").glob("*.html"):
        if page.name == "index.html":
            continue
        text = page.read_text(encoding="utf-8")
        for tag in GUIDE_SHARE_TAGS:
            assert tag in text, f"{page.name} missing {tag}"
        # image tags must carry a real URL, not an empty attribute
        assert 'content="{' not in text, f"{page.name} has an unrendered template field"


def test_hub_has_complete_share_meta(built_site: Path) -> None:
    """The guides hub is a top share/entry point; it must carry a full OG+Twitter
    card (it previously had only og:title + og:image = a broken share preview)."""
    text = (built_site / "guides" / "index.html").read_text(encoding="utf-8")
    for tag in (
        '<meta property="og:type"',
        '<meta property="og:url"',
        '<meta property="og:description"',
        '<meta property="og:site_name"',
        '<meta name="twitter:card"',
        '<meta name="twitter:title"',
        '<meta name="twitter:description"',
    ):
        assert tag in text, f"guides hub missing {tag}"


def test_kit_pages_have_complete_share_meta() -> None:
    """build_kit_pages: every kit page carries og:site_name + twitter title/desc/alt
    so a shared kit link renders a full branded card, not a bare URL."""
    import build_kit_pages

    for slug in ("dino-6-8", "ninja-7-9"):
        text = build_kit_pages.page(slug, build_kit_pages.KITS[slug])
        for tag in (
            '<meta property="og:site_name"',
            '<meta property="og:image:alt"',
            '<meta name="twitter:title"',
            '<meta name="twitter:description"',
            '<meta name="twitter:image:alt"',
        ):
            assert tag in text, f"kit {slug} missing {tag}"


TITLE_RE = re.compile(r"<title>(.*?)</title>", re.DOTALL)
DESC_RE = re.compile(r'<meta name="description" content="(.*?)">')
H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.DOTALL)
# Google's practical SERP display budget: titles truncate around ~60 chars,
# descriptions around ~155-160. Cycle 007 found 13 kit pages silently shipping
# 81-96 char titles and 194-217 char descriptions since the generator's first
# version — nothing enforced a cap, so the query-relevant words were being cut
# out of every search snippet. These caps make that regression impossible.
TITLE_MAX = 60
DESC_MAX = 160
INTERNAL_LINK_RE = re.compile(r'href="(?!https?://)([^"#]+\.html[^"]*)"')


def _unescape(s: str) -> str:
    return html_mod.unescape(s)


def test_every_guide_has_seo_essentials(built_site: Path) -> None:
    """Every guide page: unique, length-capped title + description, a real H1,
    and at least 2 internal (on-site) links — the minimum bar for a page to be
    able to rank for anything instead of just existing at a URL."""
    seen_titles, seen_descs = set(), set()
    for page in (built_site / "guides").glob("*.html"):
        text = page.read_text(encoding="utf-8")
        title_m, desc_m, h1_m = TITLE_RE.search(text), DESC_RE.search(text), H1_RE.search(text)
        assert title_m and title_m.group(1).strip(), f"{page.name} missing <title>"
        assert desc_m and desc_m.group(1).strip(), f"{page.name} missing meta description"
        assert h1_m and _unescape(h1_m.group(1)).strip(), f"{page.name} missing real <h1>"
        title, desc = _unescape(title_m.group(1)), _unescape(desc_m.group(1))
        assert len(title) <= TITLE_MAX, f"{page.name} title {len(title)} chars (max {TITLE_MAX}): {title}"
        assert len(desc) <= DESC_MAX, f"{page.name} description {len(desc)} chars (max {DESC_MAX}): {desc}"
        assert title not in seen_titles, f"{page.name} duplicate title: {title}"
        assert desc not in seen_descs, f"{page.name} duplicate description: {desc}"
        seen_titles.add(title)
        seen_descs.add(desc)
        links = set(INTERNAL_LINK_RE.findall(text))
        assert len(links) >= 2, f"{page.name} has fewer than 2 internal links: {links}"


def test_every_kit_page_has_seo_essentials() -> None:
    """Same bar as guides, applied to the 13 kit landing pages (build_kit_pages.py
    has its own generator, so its own regression check)."""
    import build_kit_pages

    seen_titles, seen_descs = set(), set()
    for slug, k in build_kit_pages.KITS.items():
        text = build_kit_pages.page(slug, k)
        title_m, desc_m, h1_m = TITLE_RE.search(text), DESC_RE.search(text), H1_RE.search(text)
        assert title_m and title_m.group(1).strip(), f"{slug} missing <title>"
        assert desc_m and desc_m.group(1).strip(), f"{slug} missing meta description"
        assert h1_m and _unescape(h1_m.group(1)).strip(), f"{slug} missing real <h1>"
        title, desc = _unescape(title_m.group(1)), _unescape(desc_m.group(1))
        assert len(title) <= TITLE_MAX, f"{slug} title {len(title)} chars (max {TITLE_MAX}): {title}"
        assert len(desc) <= DESC_MAX, f"{slug} description {len(desc)} chars (max {DESC_MAX}): {desc}"
        assert title not in seen_titles, f"{slug} duplicate title: {title}"
        assert desc not in seen_descs, f"{slug} duplicate description: {desc}"
        seen_titles.add(title)
        seen_descs.add(desc)
        links = set(INTERNAL_LINK_RE.findall(text))
        assert len(links) >= 2, f"{slug} has fewer than 2 internal links: {links}"


def test_kit_page_offers_no_false_instock(built_site: Path) -> None:
    """JSON-LD honesty: a kit with no live Gumroad slug must never claim an
    ``offers`` block (that would be a false InStock signal to search/AI engines
    for a product that cannot actually be bought — the bug cycle 006 fixed)."""
    import build_kit_pages

    for slug, k in build_kit_pages.KITS.items():
        text = build_kit_pages.page(slug, k)
        blocks = _ld_blocks(text)
        product = next(b for b in blocks if b.get("@type") == "Product")
        available = k[9] is not None  # gslug
        if available:
            assert "offers" in product, f"{slug} is available but has no Offer"
        else:
            assert "offers" not in product, f"{slug} has no product but claims an Offer"


BANNED_CLAIMS_RE = re.compile(
    r"zero prep|no props|no special supplies|kids run it themselves|\bno[- ]prep\b",
    re.IGNORECASE,
)

# Cycle 008 (WARDEN addendum, RULING A) found index.html:178 carrying the bare
# claim "no prep" about OUR OWN free printable, live on the homepage, and
# proved this suite did not catch it: the regex above previously matched only
# "zero prep", not "no prep" (with or without a hyphen). That gap is now
# closed by the `\bno[- ]prep\b` alternative.
#
# One guide legitimately uses that same phrase: last-minute-party-ideas-for-kids
# describes GENERIC party games (Freeze Dance, Sleeping Lions, ...) as
# "no-prep games" — that is not a claim about our kits, and WARDEN explicitly
# CLEARED those hits in the same ruling, warning not to over-correct them
# away. The exemption below is scoped to that one slug only. The guard
# function keeps the exemption honest: if that page ever stops being about
# generic games, the guard fails loudly instead of silently protecting
# whatever replaces it.
GENERIC_GAMES_EXEMPT_SLUG = "last-minute-party-ideas-for-kids"


def _assert_exemption_still_about_generic_games(text: str, where: str) -> None:
    assert "Freeze Dance" in text, (
        f"{where} no longer matches the generic-party-games content WARDEN "
        "cleared (cycle 008 addendum) — re-verify before keeping the "
        "'no prep' exemption for this slug"
    )


def test_no_unsupportable_claims_in_guides(built_site: Path) -> None:
    """Honesty regression (cycle 007, ECHO; tightened cycle 008 after WARDEN
    found the bare "no prep" gap live on index.html). These claims are false
    on the kits' own terms: host_guide.md says ~15 minutes of setup (print,
    cut, hide the clues), and the kit is host-run, not self-running. WARDEN
    ruled them UNSUPPORTABLE for the Pinterest pins
    (cycles/006-warden-pinterest.md, condition C4); cycle 008 re-ruled them
    unsupportable on the website too, everywhere except the one exempted
    slug above."""
    for page in (built_site / "guides").glob("*.html"):
        text = page.read_text(encoding="utf-8")
        if page.stem == GENERIC_GAMES_EXEMPT_SLUG:
            _assert_exemption_still_about_generic_games(text, page.name)
            continue
        m = BANNED_CLAIMS_RE.search(text)
        assert not m, f"{page.name} contains banned claim: {m.group(0)!r}"


def test_no_unsupportable_claims_in_kit_pages() -> None:
    import build_kit_pages

    for slug, k in build_kit_pages.KITS.items():
        text = build_kit_pages.page(slug, k)
        m = BANNED_CLAIMS_RE.search(text)
        assert not m, f"kit {slug} contains banned claim: {m.group(0)!r}"


def test_no_unsupportable_claims_in_static_pages() -> None:
    """index.html and llms.txt are hand-authored with no generator (the source
    file IS the live output) — scan the live files directly rather than a
    build artifact. This is the exact test that would have caught
    index.html:178 ("Run it today · no prep") had the regex already covered
    the bare "no prep" phrasing — cycle 008 closed that gap."""
    for name in ("index.html", "llms.txt"):
        text = (REPO / name).read_text(encoding="utf-8")
        m = BANNED_CLAIMS_RE.search(text)
        assert not m, f"{name} contains banned claim: {m.group(0)!r}"


def test_no_unsupportable_claims_in_guides_content_source() -> None:
    """Defense in depth: scan the raw JSON data source too, so a banned claim
    added to guides_content.json fails the suite even before it's rendered
    into a page. Scoped per-article (not one whole-file regex) so the single
    WARDEN-cleared exemption above can be skipped without blinding the check
    for every other article."""
    content = json.loads((REPO / "guides_content.json").read_text(encoding="utf-8"))
    for art in content["articles"]:
        text = json.dumps(art)
        if art["slug"] == GENERIC_GAMES_EXEMPT_SLUG:
            _assert_exemption_still_about_generic_games(text, f"guides_content.json[{art['slug']}]")
            continue
        m = BANNED_CLAIMS_RE.search(text)
        assert not m, f"guides_content.json[{art['slug']}] contains banned claim: {m.group(0)!r}"


def test_build_writes_only_guides_and_sitemap(built_site: Path) -> None:
    """The builder must never create verification/key files."""
    top_level = {p.name for p in built_site.iterdir()}
    assert top_level == {"guides", "kits", "sitemap.xml"}
    for forbidden in ("googlece5528dcc695b197.html", ".indexnow_key",
                      "586b557f6de25d530c55390b156f265f.txt"):
        assert not (built_site / forbidden).exists()
