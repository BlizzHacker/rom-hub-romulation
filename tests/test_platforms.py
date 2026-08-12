"""The mapping must not contain a slug somebody invented.

Same load-bearing check as every other provider in this family: a wrong slug
fails nowhere at runtime, it just files the ROM under another machine.
"""

import pytest

from romulation.platforms import PLATFORMS, platform_for

romarr_platforms = pytest.importorskip(
    "romarr.platforms",
    reason="ROMarr is not importable here; run in ROMarr's venv to check slugs",
)

#: RomuLation's served platforms, from its `/roms/<PLATFORM>` listing pages
#: plus the platform segments seen in live search results (2026-08-12).
#: Pinned so an upstream addition shows up as a failure rather than as
#: silently missing results.
SERVED = {
    "3ds", "dreamcast", "gba", "game_boy_color", "gamecube", "n64", "nds",
    "nes", "ps2", "ps3", "psp", "psx", "snes", "sega_genesis", "sega_saturn",
    "wii", "xbox",
}


@pytest.mark.parametrize("segment,slug", sorted(PLATFORMS.items()))
def test_every_slug_is_one_romarr_actually_has(segment, slug):
    resolved = romarr_platforms.resolve(slug)
    assert resolved is not None, f"{segment} -> {slug!r} is not a ROMarr platform"
    # resolve() answers to names and aliases too, so require the canonical
    # slug rather than merely a hit.
    assert resolved.slug == slug, (
        f"{segment} -> {slug!r} resolves to {resolved.slug!r}, not itself"
    )


def test_every_served_platform_is_mapped():
    # RomuLation is the one provider in this family that skips nothing.
    assert set(PLATFORMS) == SERVED


def test_unknown_platform_returns_nothing_rather_than_a_guess():
    assert platform_for("Amiga") is None
    assert platform_for("Nintendo_Switch") is None
    assert platform_for("") is None
    assert platform_for(None) is None


def test_hyphen_and_underscore_spellings_agree():
    # The nav links /roms/Game-Boy-Color; the detail URLs use
    # /rom/Game_Boy_Color/. Both must resolve to the same platform.
    assert platform_for("Game-Boy-Color") == platform_for("Game_Boy_Color") == "gbc"
    assert platform_for("Sega-Genesis") == platform_for("Sega_Genesis")


def test_lookup_folds_case():
    assert platform_for("nes") == platform_for("NES") == "nes"
