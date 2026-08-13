"""Search RomuLation through the site's own public search endpoint.

`GET /roms/search?query=<q>` is what RomuLation's own search box submits, so
a query costs the site exactly one page render. It returns a single page --
there is no pagination in the results markup -- which makes this the
simplest search in the family: one request per query, always.

Results whose platform has no ROMarr slug are dropped rather than renamed.
In practice that branch never fires today, because all 17 of RomuLation's
platforms map; it is kept because an eighteenth appearing upstream must
default to "not answered for" rather than to a guess.
"""

from __future__ import annotations

from rom_hub_sdk import SearchProvider, SearchResult

from .listing import parse_search, search_url
from .platforms import platform_for


class Search(SearchProvider):
    def search(self, query: str, platform: str | None, limit: int) -> list[SearchResult]:
        limit = max(0, limit)
        text = (query or "").strip()
        if not text or not limit:
            return []

        wanted = str(platform or "").strip().casefold().replace("-", "_")
        response = self.ctx.http.get(search_url(text))
        # 403 and 429 are answers, not hiccups. There is nothing to retry
        # and nothing to vary -- that is where routing around a refusal
        # would start.
        if response.status_code != 200:
            return []

        results: list[SearchResult] = []
        for entry in parse_search(response.text):
            mapped = platform_for(entry.platform_seg)
            if mapped is None:
                continue
            if wanted and wanted not in (
                mapped.casefold().replace("-", "_"),
                entry.platform_seg.casefold(),
            ):
                continue
            results.append(SearchResult(
                source_id=entry.path,
                title=entry.title,
                platform=mapped,
                # RomuLation is the one provider in this family that prints
                # a real size on the results page, so this is measured
                # rather than left unknown.
                size_bytes=entry.size_bytes,
                url=entry.page_url,
                extra={
                    "region": entry.region,
                    "romulation_platform": entry.platform_seg,
                    # Both false, and for two independent reasons -- see the
                    # README. Stated per result so a caller does not have to
                    # discover it by trying.
                    "playable": "false",
                    "downloadable": "false",
                    # The site's token and entitlement live in the
                    # operator's paid browser session, not in this plugin.
                    "download_requires_browser": "true",
                    "account_required": "true",
                },
            ))
            if len(results) >= limit:
                break
        return results
