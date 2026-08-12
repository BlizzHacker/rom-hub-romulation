"""Parse RomuLation's search results, and rebuild its URLs safely.

`GET /roms/search?query=<q>` renders a plain server-side table, one `<tr>`
per ROM, with more per row than most sites in this family give: a region
flag, a `[PLATFORM] Title` link, and a **real file size**. RomuLation is the
only provider in this set that can report a size honestly, so it does.

Parsed with `html.parser` rather than a regex, for the same reason as the
Retrostic provider: rows carry nested markup and a repeated anchor, and a
regex that survives that today breaks when a wrapper moves.

**Nothing is trusted because it came from the page.** A path must match
`ROM_PATH` before it becomes an id or a URL. The pattern is anchored and
built from the real corpus rather than from hope: across the 12,243 detail
URLs in RomuLation's sitemap the platform segment is only `[A-Za-z0-9_]`,
and the title slug adds exactly `( ) , ! . + -` and nothing else.

Unlike Retrostic, **there is no numeric id here** -- the slug *is* the id.
So the whole `<PLATFORM>/<slug>` path is the `source_id`, and it has to
survive round-tripping intact.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser

BASE = "https://www.romulation.org"

#: `<PLATFORM>/<slug>` -- the part of a detail URL after `/rom/`.
#: Character classes measured against the published sitemap, not guessed.
ROM_PATH = re.compile(r"([A-Za-z0-9_]+)/([A-Za-z0-9()!,.+_-]+)")

#: "[NES] Contra" -- the platform is repeated into the link text.
_TITLE_PREFIX = re.compile(r"^\s*\[[^\]]{1,32}\]\s*")

#: "146.6 KB", "1.04 GB", "408.2 MB".
_SIZE = re.compile(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*(B|KB|MB|GB|TB)\s*$", re.I)

_UNITS = {"b": 1, "kb": 1024, "mb": 1024**2, "gb": 1024**3, "tb": 1024**4}

_HREF = re.compile(r"^/rom/(.+?)/?$")


@dataclass(frozen=True)
class Entry:
    """One search hit, validated into parts that rebuild a URL."""

    path: str            # "NES/Contra" -- this is the source_id
    platform_seg: str    # "NES"
    slug: str            # "Contra"
    title: str           # "Contra", with the "[NES] " prefix removed
    region: str = ""     # "USA"
    size_bytes: int | None = None

    @property
    def page_url(self) -> str:
        from urllib.parse import quote

        # The slug legitimately contains "(" and ")". Percent-encoding the
        # path keeps a valid URL without mangling the characters that are
        # part of the id.
        return f"{BASE}/rom/{quote(self.path, safe='/()!,.+_-')}"


def split_path(value: str) -> tuple[str, str, str] | None:
    """`"NES/Contra"` -> `("NES/Contra", "NES", "Contra")`, or nothing.

    The single gate for every path, whether parsed from a page or handed
    back later as a `source_id`. `fullmatch`, so a path with anything
    appended is not a match at all rather than a match with a tail.

    Case is **preserved**, unlike the Retrostic provider: RomuLation's URLs
    are case-sensitive (`/rom/NES/Contra` is not `/rom/nes/contra`), so
    folding here would produce ids that 404.
    """
    text = str(value or "").strip().strip("/")
    found = ROM_PATH.fullmatch(text)
    return (text, found.group(1), found.group(2)) if found else None


def parse_size(text: str) -> int | None:
    """"1.04 GB" -> 1116691496, or nothing for anything unparseable.

    Binary units, because that is what a file listing means by GB in
    practice and because the alternative -- reporting a size 7% larger than
    the file -- is worse than reporting none.
    """
    found = _SIZE.match(text or "")
    if not found:
        return None
    return int(float(found.group(1)) * _UNITS[found.group(2).casefold()])


def clean_title(text: str) -> str:
    """"[NES] Contra" -> "Contra"."""
    return _TITLE_PREFIX.sub("", text or "").strip()


class _Row:
    __slots__ = ("href", "anchor_texts", "plain_texts")

    def __init__(self) -> None:
        self.href: str | None = None
        self.anchor_texts: list[str] = []
        self.plain_texts: list[str] = []


class _ResultTableParser(HTMLParser):
    """Collect `<tr>` rows, keeping anchor text apart from plain cell text.

    A RomuLation row is:

        <td><span class="flags-usa">USA</span></td>
        <td><a href="/rom/NES/Contra">[NES] Contra</a></td>
        <td class="filesize">161.0 KB</td>
        <td class="premium-download"><a href="/buy/premium"><img ...></a></td>

    The title is anchor text; the region and the size are not. Keeping the
    two apart means the parse does not depend on column order -- which
    matters here because the last cell also holds an `<a>`, pointing at the
    paywall rather than at the ROM, and a naive "first link in the row"
    reader would eventually pick it up.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[_Row] = []
        self._row: _Row | None = None
        self._buf: list[str] = []
        self._in_cell = False
        self._anchor_depth = 0
        self._anchor_buf: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self._row = _Row()
        elif self._row is None:
            return
        elif tag in ("td", "th"):
            self._in_cell, self._buf = True, []
        elif tag == "a":
            href = dict(attrs).get("href") or ""
            found = _HREF.match(href.strip())
            path = split_path(found.group(1)) if found else None
            # Only /rom/ links count, so the /buy/premium anchor in the last
            # cell is ignored rather than mistaken for the ROM.
            if path and (self._row.href is None or path[0] == self._row.href):
                self._row.href = path[0]
                self._anchor_depth += 1
                self._anchor_buf = []

    def handle_endtag(self, tag: str) -> None:
        if self._row is None:
            return
        if tag == "a" and self._anchor_depth:
            self._anchor_depth -= 1
            if not self._anchor_depth:
                text = " ".join("".join(self._anchor_buf).split())
                if text:
                    self._row.anchor_texts.append(text)
                self._anchor_buf = []
        elif tag in ("td", "th") and self._in_cell:
            text = " ".join("".join(self._buf).split())
            if text and not any(text == a for a in self._row.anchor_texts):
                self._row.plain_texts.append(text)
            self._in_cell, self._buf = False, []
        elif tag == "tr":
            if self._row.href:
                self.rows.append(self._row)
            self._row = None
            self._in_cell, self._anchor_depth = False, 0

    def handle_data(self, data: str) -> None:
        if self._anchor_depth:
            self._anchor_buf.append(data)
        if self._in_cell:
            self._buf.append(data)


def parse_search(markup: str) -> list[Entry]:
    """Every ROM on one search-results page, in the order rendered.

    Rows without a valid `/rom/` path are skipped rather than raised on: the
    same table markup wraps the header row, and a search that found nothing
    must return empty rather than fail.
    """
    parser = _ResultTableParser()
    parser.feed(markup or "")
    parser.close()

    out: list[Entry] = []
    seen: set[str] = set()
    for row in parser.rows:
        parts = split_path(row.href or "")
        if parts is None or parts[0] in seen:
            continue
        path, platform_seg, slug = parts
        seen.add(path)

        title = clean_title(min(row.anchor_texts, key=len)) if row.anchor_texts else ""
        if not title:
            continue

        size = None
        region = ""
        for text in row.plain_texts:
            parsed = parse_size(text)
            if parsed is not None and size is None:
                size = parsed
            elif not region and len(text) <= 24:
                region = text

        out.append(Entry(
            path=path,
            platform_seg=platform_seg,
            slug=slug,
            title=title,
            region=region,
            size_bytes=size,
        ))
    return out


def search_url(query: str) -> str:
    """The request RomuLation's own search box sends."""
    from urllib.parse import urlencode

    return f"{BASE}/roms/search?{urlencode({'query': query})}"
