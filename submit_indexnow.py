#!/usr/bin/env python3
"""Submit every sitemap URL to IndexNow (Bing / Yandex / Seznam / AI answer engines).

WHY: djsluxx.github.io is a GitHub Pages *project* site. Crawlers only read robots.txt
from the domain root (https://djsluxx.github.io/robots.txt), which 404s because no
user-page repo exists — so the project's own `Sitemap:` directive is never auto-discovered.
GSC covers Google, but the strategy's traffic backbone is "autonomous search + AI answer
engines". IndexNow pushes URLs straight to Bing (which feeds Copilot / ChatGPT search),
Yandex and Seznam — no login, no token, instant. This is the login-free companion to the
GSC "request indexing" step.

The key is already hosted at the site root of the project path and must stay reachable:
    https://djsluxx.github.io/escape-in-an-envelope/586b557f6de25d530c55390b156f265f.txt
IndexNow scopes a submission to the key file's folder + subfolders, and every sitemap URL
lives under /escape-in-an-envelope/, so this key is valid for the whole site.

USAGE:
    python submit_indexnow.py            # submit all sitemap URLs
    python submit_indexnow.py --dry-run  # print the payload, send nothing

Stdlib only (urllib) — no extra dependencies on the GitHub Pages build box.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

HOST = "djsluxx.github.io"
BASE = f"https://{HOST}/escape-in-an-envelope"
ENDPOINT = "https://api.indexnow.org/indexnow"
KEY_FILE = Path(__file__).resolve().parent / ".indexnow_key"
SITEMAP_FILE = Path(__file__).resolve().parent / "sitemap.xml"
SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
# IndexNow accepts at most 10,000 URLs per request; we are far under that.
MAX_URLS = 10_000


def _read_key() -> str:
    if not KEY_FILE.exists():
        sys.exit(f"ERROR: key file missing: {KEY_FILE}")
    key = KEY_FILE.read_text(encoding="utf-8").strip()
    if not key:
        sys.exit("ERROR: .indexnow_key is empty")
    return key


def _read_sitemap_urls() -> list[str]:
    if not SITEMAP_FILE.exists():
        sys.exit(f"ERROR: sitemap missing: {SITEMAP_FILE}")
    root = ET.fromstring(SITEMAP_FILE.read_text(encoding="utf-8"))
    urls = [loc.text.strip() for loc in root.findall(".//sm:url/sm:loc", SITEMAP_NS) if loc.text]
    # Only submit URLs on our host under the key's folder — IndexNow rejects the rest.
    scoped = [u for u in urls if u.startswith(BASE)]
    dropped = len(urls) - len(scoped)
    if dropped:
        print(f"WARN: dropped {dropped} URL(s) outside {BASE} (IndexNow scope)")
    if len(scoped) > MAX_URLS:
        print(f"WARN: {len(scoped)} URLs exceeds IndexNow's {MAX_URLS} cap; truncating")
        scoped = scoped[:MAX_URLS]
    return scoped


def submit(urls: list[str], key: str, dry_run: bool) -> int:
    payload = {
        "host": HOST,
        "key": key,
        "keyLocation": f"{BASE}/{key}.txt",
        "urlList": urls,
    }
    if dry_run:
        print(json.dumps(payload, indent=2))
        print(f"\n[dry-run] would submit {len(urls)} URL(s) to {ENDPOINT}")
        return 0

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            code = resp.getcode()
            body = resp.read().decode("utf-8", "replace").strip()
    except urllib.error.HTTPError as e:
        code = e.code
        body = e.read().decode("utf-8", "replace").strip()
    except urllib.error.URLError as e:
        print(f"ERROR: network failure contacting IndexNow: {e.reason}")
        return 1

    # 200 = OK, 202 = accepted (key validation pending). Both are success.
    if code in (200, 202):
        print(f"OK: IndexNow accepted {len(urls)} URL(s) (HTTP {code})")
        return 0
    print(f"ERROR: IndexNow returned HTTP {code}: {body or '(no body)'}")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Submit sitemap URLs to IndexNow.")
    parser.add_argument("--dry-run", action="store_true", help="print payload, send nothing")
    args = parser.parse_args()

    key = _read_key()
    urls = _read_sitemap_urls()
    if not urls:
        print("Nothing to submit — sitemap had no in-scope URLs.")
        return 0
    print(f"Submitting {len(urls)} URL(s) from sitemap.xml to IndexNow ...")
    return submit(urls, key, args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
