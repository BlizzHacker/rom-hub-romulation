"""RomuLation platform segment -> RomM/ROMarr platform slug.

Exact-match lookup, no fallback. Same rule as every other provider in this
family: a platform that is not spelled out resolves to nothing and its
results are dropped, because guessing files a ROM under the wrong machine
and nothing afterwards reports it.

**All 17 values were checked with `romarr.platforms.resolve()`** and
`tests/test_platforms.py` re-runs that check whenever ROMarr is importable.
This is the happiest of the mappings in this family: RomuLation carries 17
platforms and every single one has a ROMarr slug, so nothing is skipped and
there is no "counted and skipped" section to read.

The keys are the path segment RomuLation puts in a detail URL
(`/rom/<PLATFORM>/<slug>`), which uses underscores. Its *navigation* links
sometimes use hyphens for the same platform (`/roms/Game-Boy-Color` beside
`/rom/Game_Boy_Color/...`), so `platform_for` folds hyphens to underscores
rather than the table carrying both spellings of three names.

The ROM counts are from RomuLation's own `sitemap.xml` (12,243 detail URLs,
surveyed 2026-08-12) and are **incomplete on purpose** -- see below.
"""

#: RomuLation platform segment -> ROMarr slug. Counts are RomuLation's own
#: sitemap, which does not list every platform it serves (see NOTE).
PLATFORMS: dict[str, str] = {
    "3ds": "3ds",                                 # 715
    "dreamcast": "dc",                            # 267
    "gba": "gba",                                 # 1,340
    "game_boy_color": "gbc",                      # not in sitemap
    "gamecube": "ngc",                            # 445
    "n64": "n64",                                 # 300
    "nds": "nds",                                 # 3,742
    "nes": "nes",                                 # not in sitemap
    "ps2": "ps2",                                 # 1,317
    "ps3": "ps3",                                 # 323
    "psp": "psp",                                 # 1,180
    "psx": "psx",                                 # 1,215
    "snes": "snes",                               # not in sitemap
    "sega_genesis": "genesis-slash-megadrive",    # not in sitemap
    "sega_saturn": "saturn",                      # 189
    "wii": "wii",                                 # 1,129
    "xbox": "xbox",                               # 81
}

# NOTE -- the sitemap is not the catalogue.
#
# `sitemap.xml` lists 12,243 detail URLs across only **13** platforms, yet a
# live search returns `/rom/NES/Contra` and `/rom/Game_Boy_Color/Contra-J`,
# and the site publishes `/roms/NES` and `/roms/SNES` listing pages. So four
# of the seventeen platforms are served but unlisted, and the sitemap's
# `lastmod` values are all 2022.
#
# This is why the provider searches live instead of ingesting the sitemap:
# a mirror built from that file would silently be missing NES, SNES,
# Game Boy Color and Sega Genesis entirely, and would look complete while
# doing it. The counts above are kept as the measured floor they are, not
# as a catalogue size.


def platform_for(segment: str) -> str | None:
    """The ROMarr slug for a RomuLation platform segment, or nothing.

    Folds case and treats a hyphen as an underscore, because the site's own
    navigation and its detail URLs disagree about which one separates the
    words in `Game_Boy_Color`.
    """
    key = str(segment or "").strip().casefold().replace("-", "_")
    return PLATFORMS.get(key)
