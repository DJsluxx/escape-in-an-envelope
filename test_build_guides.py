#!/usr/bin/env python3
"""Tests for build_guides.py — run with:  python -m pytest test_build_guides.py -v

Builds the whole site into a temp dir (never touching the live files) and checks:
  * all guide pages + the guides hub are generated,
  * sitemap.xml contains every page that exists on disk (>= 27 URLs),
  * sitemap.xml is a superset of the live sitemap.xml (nothing gets de-listed),
  * the superset guard aborts loudly if a listed URL would disappear.
"""
from __future__ import annotations

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
    """No Gumroad link (product /l/ or shop root) may leave the site untagged."""
    for page in (built_site / "guides").glob("*.html"):
        hrefs = gumroad_hrefs(page.read_text(encoding="utf-8"))
        assert hrefs, f"{page.name} has no Gumroad links at all"
        for h in hrefs:
            assert "utm_source=eie-site" in h and "utm_medium=" in h \
                and "utm_campaign=" in h, f"{page.name}: untagged Gumroad href {h}"


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
    for art in kit_guides[:3]:
        text = (built_site / "guides" / f"{art['slug']}.html").read_text(encoding="utf-8")
        assert f"utm_medium=guide&utm_campaign={art['slug']}" in text, art["slug"]
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


def test_build_writes_only_guides_and_sitemap(built_site: Path) -> None:
    """The builder must never create verification/key files."""
    top_level = {p.name for p in built_site.iterdir()}
    assert top_level == {"guides", "kits", "sitemap.xml"}
    for forbidden in ("googlece5528dcc695b197.html", ".indexnow_key",
                      "586b557f6de25d530c55390b156f265f.txt"):
        assert not (built_site / forbidden).exists()
