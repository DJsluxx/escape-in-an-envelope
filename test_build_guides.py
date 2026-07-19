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
EXPECTED_GUIDES = 13  # article pages; +1 for guides/index.html


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
    assert len(urls) >= 27, f"sitemap only has {len(urls)} urls"


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


def test_build_writes_only_guides_and_sitemap(built_site: Path) -> None:
    """The builder must never create verification/key files."""
    top_level = {p.name for p in built_site.iterdir()}
    assert top_level == {"guides", "kits", "sitemap.xml"}
    for forbidden in ("googlece5528dcc695b197.html", ".indexnow_key",
                      "586b557f6de25d530c55390b156f265f.txt"):
        assert not (built_site / forbidden).exists()
