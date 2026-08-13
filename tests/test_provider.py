import pytest
from conftest import FakeHttp

from rom_hub_sdk import PluginContext

from romulation.search import Search


def test_search_maps_platforms_and_drops_the_unmappable(search_html):
    http = FakeHttp([(200, search_html)])
    results = Search(PluginContext(config={}, http=http)).search("contra", None, 20)

    # 5 rows in, 4 out: the Amiga row is dropped because RomuLation does not
    # serve Amiga and there is no mapping for it.
    assert [(r.source_id, r.platform) for r in results] == [
        ("NES/Contra", "nes"),
        ("PS2/Neo-Contra-(U)", "ps2"),
        ("Game_Boy_Color/Contra-Spirits-J-SGB-Enhanced", "gbc"),
        ("GBA/2658-Shinchan-contra-los-Munecos-de-Shock-Gahn-(S)(Independent)", "gba"),
    ]


def test_search_costs_exactly_one_request(search_html):
    http = FakeHttp([(200, search_html)])
    Search(PluginContext(config={}, http=http)).search("contra", None, 20)
    assert http.urls == ["https://www.romulation.org/roms/search?query=contra"]


def test_search_reports_a_real_size(search_html):
    http = FakeHttp([(200, search_html)])
    results = Search(PluginContext(config={}, http=http)).search("contra", None, 20)
    # RomuLation prints sizes on the results page, so unlike the other
    # providers in this family these are measured rather than unknown.
    assert results[0].size_bytes == 164864
    assert results[1].size_bytes == 1116691496
    assert all(r.size_bytes for r in results)


def test_search_carries_region_and_marks_both_actions_unavailable(search_html):
    http = FakeHttp([(200, search_html)])
    first = Search(PluginContext(config={}, http=http)).search("contra", None, 5)[0]
    assert first.title == "Contra"
    assert first.url == "https://www.romulation.org/rom/NES/Contra"
    assert first.extra["region"] == "USA"
    assert first.extra["downloadable"] == "false"
    assert first.extra["playable"] == "false"
    assert first.extra["download_requires_browser"] == "true"
    assert first.extra["account_required"] == "true"


def test_platform_filter_accepts_the_romarr_slug(search_html):
    http = FakeHttp([(200, search_html)])
    results = Search(PluginContext(config={}, http=http)).search("contra", "gbc", 20)
    assert [r.source_id for r in results] == [
        "Game_Boy_Color/Contra-Spirits-J-SGB-Enhanced"
    ]


def test_platform_filter_also_accepts_romulations_own_segment(search_html):
    http = FakeHttp([(200, search_html)])
    results = Search(
        PluginContext(config={}, http=http)
    ).search("contra", "Game_Boy_Color", 20)
    assert [r.source_id for r in results] == [
        "Game_Boy_Color/Contra-Spirits-J-SGB-Enhanced"
    ]


def test_platform_filter_tolerates_the_hyphen_spelling(search_html):
    http = FakeHttp([(200, search_html)])
    assert Search(
        PluginContext(config={}, http=http)
    ).search("contra", "Game-Boy-Color", 20)[0].platform == "gbc"


def test_limit_is_honoured(search_html):
    http = FakeHttp([(200, search_html)])
    assert len(Search(PluginContext(config={}, http=http)).search("contra", None, 2)) == 2


def test_empty_query_makes_no_request():
    http = FakeHttp([])
    assert Search(PluginContext(config={}, http=http)).search("  ", None, 10) == []
    assert http.urls == []


def test_zero_limit_makes_no_request():
    http = FakeHttp([])
    assert Search(PluginContext(config={}, http=http)).search("contra", None, 0) == []
    assert http.urls == []


@pytest.mark.parametrize("status", [403, 429, 503, 500, 404])
def test_a_refusal_is_not_retried(status):
    http = FakeHttp([(status, "")])
    assert Search(PluginContext(config={}, http=http)).search("contra", None, 10) == []
    assert len(http.urls) == 1


def test_no_importer_or_stream_is_exported():
    # The absence is the feature: both are impossible here for independent
    # reasons (robots.txt forbids the download paths; there is no player), so
    # neither may exist as a capability that raises at runtime.
    import romulation

    assert not hasattr(romulation, "importer")
    assert not hasattr(romulation, "stream")
