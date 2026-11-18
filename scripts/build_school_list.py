#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build mirrordash_skolmatsedel/data/schools.json by crawling skolmaten.se.

Crawl order: home page -> provinces -> districts -> schools.
Only the rendered public pages are used (skolmaten.se is a JavaScript app,
so a headless Chrome renders each page). Pages are loaded one at a time with
a short pause in between.
"""
import json
import re
import subprocess
import sys
import time
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

BASE = "https://skolmaten.se"
PAUSE_SECONDS = 1.0
RETRIES = 3
OUTPUT = Path(__file__).resolve().parent.parent / "mirrordash_skolmatsedel" / "data" / "schools.json"

# Single-segment links on a district page that are not schools
NOT_SCHOOLS = {"login", "assets", "about", "p", "d"}


class LinkParser(HTMLParser):
    """Collect (href, visible text) for every <a>, ignoring aria-hidden text (icons, initials)."""

    def __init__(self):
        super().__init__()
        self.links = []
        self._href = None
        self._text = []
        self._hidden_depth = 0  # >0 while inside an aria-hidden element

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and self._href is None:
            self._href, self._text = attrs.get("href"), []
        elif self._href is not None and tag == "span":
            if self._hidden_depth or attrs.get("aria-hidden") == "true":
                self._hidden_depth += 1

    def handle_endtag(self, tag):
        if tag == "span" and self._hidden_depth:
            self._hidden_depth -= 1
        elif tag == "a" and self._href is not None:
            text = " ".join("".join(self._text).split())
            self.links.append((self._href, text))
            self._href = None

    def handle_data(self, data):
        if self._href is not None and not self._hidden_depth:
            self._text.append(data)


def parse_links(html):
    """Return all (href, text) pairs found in the HTML."""
    parser = LinkParser()
    parser.feed(html)
    return parser.links


def unique_entries(entries):
    """Drop duplicate slugs (keep the first, prefer a non-empty name), sort by name."""
    found = {}
    for slug, name in entries:
        if slug not in found or (not found[slug] and name):
            found[slug] = name
    result = [{"slug": slug, "name": name or slug} for slug, name in found.items()]
    return sorted(result, key=lambda item: item["name"].casefold())


def entries_with_prefix(html, prefix):
    """Entries for links like /p/<slug> or /d/<slug>."""
    pairs = []
    for href, text in parse_links(html):
        if href.startswith(prefix) and "/" not in href[len(prefix):] and len(href) > len(prefix):
            pairs.append((href[len(prefix):], text))
    return unique_entries(pairs)


def parse_provinces(html):
    return entries_with_prefix(html, "/p/")


def parse_districts(html):
    return entries_with_prefix(html, "/d/")


def parse_schools(html):
    """Entries for links like /<school-slug> (one segment, not a known site page)."""
    pairs = []
    for href, text in parse_links(html):
        if re.fullmatch(r"/[A-Za-z0-9._-]+", href) and href[1:] not in NOT_SCHOOLS:
            pairs.append((href[1:], text))
    return unique_entries(pairs)


def render_page(url):
    """Render a page with headless Chrome and return its DOM as text."""
    command = ["google-chrome", "--headless=new", "--disable-gpu", "--no-sandbox",
               "--virtual-time-budget=15000", "--dump-dom", url]
    result = subprocess.run(command, capture_output=True, text=True, timeout=60, check=True)
    return result.stdout


def fetch(path, failed):
    """Fetch one page politely; retry a few times, record the path in `failed` on error."""
    for attempt in range(RETRIES):
        time.sleep(PAUSE_SECONDS)
        try:
            return render_page(BASE + path)
        except (subprocess.SubprocessError, OSError) as error:
            print(f"  retry {attempt + 1} for {path}: {error}", file=sys.stderr)
    failed.append(path)
    return ""


def crawl(failed):
    """Walk home -> provinces -> districts -> schools and return the provinces list."""
    provinces = parse_provinces(fetch("/", failed))
    for province in provinces:
        districts = parse_districts(fetch(f"/p/{province['slug']}", failed))
        for district in districts:
            district["schools"] = parse_schools(fetch(f"/d/{district['slug']}", failed))
            print(f"{province['name']} / {district['name']}: {len(district['schools'])}", file=sys.stderr)
        province["districts"] = districts
    return provinces


def write_json(provinces, path):
    """Write compact JSON: one school per line."""
    lines = []
    for province in provinces:
        districts = []
        for district in province["districts"]:
            schools = ",\n".join("      " + json.dumps(s, ensure_ascii=False) for s in district["schools"])
            head = json.dumps({"slug": district["slug"], "name": district["name"]}, ensure_ascii=False)[:-1]
            districts.append(f'    {head}, "schools": [\n{schools}\n    ]}}')
        head = json.dumps({"slug": province["slug"], "name": province["name"]}, ensure_ascii=False)[:-1]
        lines.append(f'  {head}, "districts": [\n' + ",\n".join(districts) + "\n  ]}")
    text = ('{"source": "skolmaten.se", "built": "%s", "provinces": [\n' % date.today().isoformat()
            + ",\n".join(lines) + "\n]}\n")
    json.loads(text)  # sanity check
    path.write_text(text, encoding="utf-8")


def main():
    failed = []
    provinces = crawl(failed)
    write_json(provinces, OUTPUT)
    print(f"Failed pages: {failed}", file=sys.stderr)


if __name__ == "__main__":
    main()
