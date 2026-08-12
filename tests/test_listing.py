import pytest

from romulation.listing import (
    Entry,
    clean_title,
    parse_search,
    parse_size,
    search_url,
    split_path,
)


def test_parses_every_row(search_html):
    entries = parse_search(search_html)
    assert [e.path for e in entries] == [
        "NES/Contra",
        "PS2/Neo-Contra-(U)",
        "Game_Boy_Color/Contra-Spirits-J-SGB-Enhanced",
        "GBA/2658-Shinchan-contra-los-Munecos-de-Shock-Gahn-(S)(Independent)",
        "Amiga/Contra-Amiga-Port",
    ]


def test_the_paywall_anchor_is_not_mistaken_for_the_rom(search_html):
    # Every row also holds <a href="/buy/premium">. If that were picked up the
    # id would be a checkout page.
    assert all("buy" not in e.path and "premium" not in e.path
               for e in parse_search(search_html))


def test_title_drops_the_repeated_platform_prefix(search_html):
    first = parse_search(search_html)[0]
    assert first.title == "Contra"       # not "[NES] Contra"
    assert first.platform_seg == "NES"


def test_region_and_size_come_off_the_row(search_html):
    entries = parse_search(search_html)
    assert entries[0].region == "USA"
    assert entries[0].size_bytes == parse_size("161.0 KB")
    assert entries[2].region == "Japan"


@pytest.mark.parametrize("text,expected", [
    ("161.0 KB", 164864),
    ("1.04 GB", 1116691496),
    ("8.4 MB", 8808038),
    ("512 B", 512),
])
def test_sizes_are_binary_units(text, expected):
    assert parse_size(text) == expected


@pytest.mark.parametrize("text", ["", "unknown", "lots", "12", "MB", "-4 MB"])
def test_unparseable_size_is_none_not_zero(text):
    # Zero would read as an empty file; None reads as unknown, which is true.
    assert parse_size(text) is None


def test_clean_title_leaves_an_ordinary_title_alone():
    assert clean_title("Contra") == "Contra"
    assert clean_title("[Game Boy Color] Contra Spirits") == "Contra Spirits"


def test_case_is_preserved_because_the_urls_are_case_sensitive():
    # /rom/nes/contra is a 404; /rom/NES/Contra is the ROM. Folding here
    # would mint ids that do not resolve.
    assert split_path("NES/Contra")[0] == "NES/Contra"


@pytest.mark.parametrize("path", [
    "NES/Contra",
    "PS2/Neo-Contra-(U)",
    "GBA/2658-Shinchan-contra-los-Munecos-de-Shock-Gahn-(S)(Independent)",
    "Game_Boy_Color/Contra-Spirits-J-SGB-Enhanced",
])
def test_accepts_real_sitemap_shapes(path):
    assert split_path(path) is not None


@pytest.mark.parametrize("path", [
    "", "NES", "../../etc/passwd", "NES/Contra/extra",
    "NES/Contra?x=1", "NES/Contra#frag", "https://evil.example/rom/NES/Contra",
    "NES/Contra/../../admin", "evil.example/NES/Contra",
])
def test_rejects_anything_that_is_not_exactly_a_rom_path(path):
    assert split_path(path) is None


def test_url_encodes_the_slug_without_mangling_its_real_characters():
    entry = Entry("PS2/Neo-Contra-(U)", "PS2", "Neo-Contra-(U)", "Neo Contra")
    # Parens are part of the id, so they must survive rather than be escaped.
    assert entry.page_url == "https://www.romulation.org/rom/PS2/Neo-Contra-(U)"


def test_rows_without_a_rom_link_are_skipped_not_raised_on():
    assert parse_search("<table><tr><th>Region</th><th>Name</th></tr></table>") == []
    assert parse_search("") == []


def test_duplicate_rows_collapse():
    row = '<tr><td>USA</td><td><a href="/rom/NES/Contra">[NES] Contra</a></td></tr>'
    assert len(parse_search(f"<table>{row}{row}</table>")) == 1


def test_search_url_is_the_sites_own_shape():
    assert search_url("contra") == (
        "https://www.romulation.org/roms/search?query=contra"
    )
    assert "query=mike+tyson%27s" in search_url("mike tyson's")
