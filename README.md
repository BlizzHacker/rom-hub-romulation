# RomuLation provider for ROM Hub / ROMarr

An RPP v1 provider that searches [RomuLation](https://www.romulation.org).

| Capability | Status |
|---|---|
| `search` | Implemented — the site's own `GET /roms/search` endpoint |
| `importer` | **Deliberately absent** — forbidden by the site's own robots.txt |
| `stream` | **Deliberately absent** — RomuLation hosts no player |

Modelled on the Retrostic provider, which is the reference for this family.

## What it gives you

RomuLation's results page is the richest of the sites surveyed: each row
carries a region, a `[PLATFORM] Title` link and a **real file size**. So this
is the one provider in the family that reports `size_bytes` as a measured
value rather than as unknown.

A query costs the site exactly **one page render** — `GET /roms/search?query=…`
is what its own search box submits, and the results are a single page with no
pagination.

## Why there is no importer

RomuLation's own `robots.txt`:

```
Disallow: /roms/images
Disallow: /roms/download
Disallow: /roms/newdownload
Disallow: /roms/archive
```

Its live download control on a detail page is
`/roms/newdownload/guest/7015/<encrypted token>` — i.e. **under a path the site
explicitly asks crawlers not to touch**. Honouring robots.txt is not optional
here, so an importer cannot exist.

Two further gates point the same way, either of which would be enough alone:

* the token is a per-render encrypted payload (Laravel `iv`/`value`/`mac`), and
* the download column on every search row links to **`/buy/premium`** — the
  files are behind a paid account.

So `importer` is not declared in `manifest.toml` at all, rather than declared
and refusing at runtime. Every result carries `downloadable: "false"`.

## Why there is no stream

There is no player to point at. RomuLation is a download site; the only action
its pages offer is the paywalled download above. Every result carries
`playable: "false"`.

## Platforms

**All 17 platforms map** — this is the one provider in the family that skips
nothing. Every slug was checked with `romarr.platforms.resolve()` and
`tests/test_platforms.py` re-runs that check whenever ROMarr is importable.

`3ds dc gba gbc genesis-slash-megadrive n64 nds nes ngc ps2 ps3 psp psx
saturn snes wii xbox`

The site spells one platform two ways — `/roms/Game-Boy-Color` in navigation,
`/rom/Game_Boy_Color/…` in detail URLs — so lookups fold a hyphen to an
underscore instead of the table carrying both spellings.

### The sitemap is not the catalogue

Worth knowing before anyone tries to build a mirror from it: `sitemap.xml`
lists 12,243 detail URLs across only **13** platforms, and every `lastmod` in
it is 2022. But a live search returns `/rom/NES/Contra` and
`/rom/Game_Boy_Color/Contra-J`, and the site publishes `/roms/NES` and
`/roms/SNES` listing pages.

So **four served platforms — NES, SNES, Game Boy Color and Sega Genesis — are
absent from the sitemap entirely.** A mirror built from that file would be
missing them and would look complete while doing it. That is why this provider
searches live, and why the ROM counts in `platforms.py` are labelled as a
measured floor rather than a catalogue size.

## Install

```sh
rom-hub plugin install https://git.moveweight.com/BlizzHacker/romarr-plugin-romulation --ref v0.1.0
rom-hub search "contra" --platform nes
```

The `source_id` is the detail path, `<PLATFORM>/<slug>`. There is **no numeric
id** on this site — the slug is the id — and the paths are **case-sensitive**
(`/rom/nes/contra` is a 404), so unlike the Retrostic provider this one
preserves case rather than folding it.

To list it in ROMarr's **Hub → Plugins** catalogue:

```sh
rom-hub catalog add moveweight-romulation \
  https://git.moveweight.com/BlizzHacker/romarr-plugin-romulation/raw/tag/v0.1.0/catalog/plugins.json
rom-hub catalog refresh
```

## Config

| Key | Default | Meaning |
|---|---|---|
| `collection` | `RomuLation` | RomM collection name |

A non-200 — 403, 429, 503 — returns no results and is **not retried**.

## Test

```sh
ROM_HUB_SRC=/opt/rom-hub/src PYTHONPATH=/opt/romarr pytest tests/ -q
```

70 passing. `PYTHONPATH` to ROMarr is what makes the platform-slug checks run
rather than skip.

## Terms

RomuLation hosts mixed game content. This provider indexes metadata the site
publishes on its own search page; it downloads nothing, and it does not touch
the paths the site's robots.txt disallows. It grants no redistribution rights.
Operators are responsible for using it in accordance with applicable law and
the source's terms.

## License

MIT — see `LICENSE`.
