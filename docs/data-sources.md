# Data sources

Everything here is fetched at runtime and cached locally under `data/`, which is
not tracked by git. No card text, card image or database dump is redistributed
with this repository.

Every value derived from these sources must carry the parameters described in
[`metrics.md`](metrics.md): region, window, sample size and retrieval date.

## Card database

Three sources are used by this project.

### swu-db (primary)
- Base: <https://api.swu-db.com>
- Endpoint used: `GET https://api.swu-db.com/cards/{SET}`
- Verified: 2026-10-26
- Set coverage: all 51 sets listed on `/sets`. Premier sets are covered by 7
  requests (JTL, LOF, IBH, SEC, LAW, ASH, HMW).
- Provides: printed name and subtitle, type, aspects, traits, arenas, cost,
  power, HP, keywords, unique, rarity, variant flags, FrontText, EpicAction,
  BackArt/BackText, FrontArt, cid, tcgplayerId, `MarketPrice`, `LowPrice`,
  `FoilPrice`, `LowFoilPrice`.
- Shape: `{ "total_cards": <int>, "data": [ ... ] }`. The response contains
  every printing: one row per variant with a different `Number`. Deduplicate by
  printed name + subtitle. Only `VariantType == "Normal"` is used for deck
  analysis and pricing; exclude rows with `Type` starting with `Token` or
  containing `Token` (`Token Unit`, `Token Upgrade`, `Force Token`).
- Local cache: `data/swudb/`
- Freshness: record the retrieval date. Compare `numberCards` from `/sets` with
  the number of distinct non-token identities to detect drift.
- Terms: no public terms of use found as of 2026-10-26. Treat as a community
  source, cache only locally, do not mirror wholesale.

### Official FFG API (authority and audit)
- Endpoint: `https://admin.starwarsunlimited.com/api/cards` (Strapi)
- Verified: 2026-10-26
- Provides: authoritative card attributes, errata-related fields (`text`,
  `textStyled`, `rules`, `rulesStyled`), expansion metadata and
  **`cardCount`** per set (the number of numbered cards). Pagination:
  `pageSize` up to 100; ~103 pages for all cards.
- Use cases: verify `cardCount` against swu-db, cross-check card identity when
  in doubt, and confirm errata.
- Not used for bulk preprocessor runs by default: larger payloads and no public
  rate limits/terms. Use sparingly for audits.
- Terms: `robots.txt` does not block access as written; no public API terms
  found. Use for verification/audit only, not wholesale redistribution.

### SWU Meta Stats (meta, optional)
- Site: <https://swumetastats.com> (verified 2026-10-26)
- API base: `https://swumetastats.com/api`
- Documentation: <https://swumetastats.com/api-docs>,
  <https://swumetastats.com/openapi.json> (OpenAPI 3.1), <https://swumetastats.com/llms.txt>
- No authentication required. Abuse protection is enforced server-side;
  sensitive endpoints may return `429 Too Many Requests`.
- Endpoints used:
  | Endpoint | Parameters | Provides |
  |---|---|---|
  | `/api/meta-boundaries` | none | meta windows with start and end dates |
  | `/api/tierlist` | `mode`, `format`, `startDate`, `topCount` | win rate, meta share, games, conversion, tier |
  | `/api/archetypes` | `startDate`, `placement`, `search` | leader+base archetypes, win rate, meta share, games |
  | `/api/archetypes/{leader}/{base}` | `startDate` | core/popular/flex card breakdown, matchups, recent decklists |
  | `/api/matchups` | `startDate`, `endDate`, `placement`, `minPlayers` | archetype vs archetype wins and losses |
  | `/api/cards` | `type=all`, `includeUsage=true`, `sortBy=usage` | per-card usage and images |
  | `/api/decklists` | `tournamentId`, `take` | decklists with leader, base and cards |
  | `/api/tournaments` | `startDate`, `endDate`, `search`, `take` | tournaments, sourced from Melee.gg |
- Coverage: aggregates tournament results sourced from Melee.gg. Coverage is
  regional and temporal; a window can be empty right after a set release.
- Freshness: cache responses for a short period and always record the retrieval
  time. When the newest window is empty, use the latest populated window and say
  so explicitly. Never present an empty window as zero usage.
- Citation: must be cited as a third-party source with region, window, sample
  size and retrieval date. It is not ground truth.

## Decklist formats
- SWUDB JSON (export): `leader`, `base`, optional `secondleader`, `deck`
  (array of `{id: "SET_NUMBER", count: ...}`), `sideboard`. IDs match
  `Set`+`Number` used by swu-db.
- SWUDB text (Melee/Picklist style): sections `Leader`, `Base`, `MainDeck`,
  `Sideboard`, lines like `3 | Card Name | Subtitle` or similar. The user
  provides these; the parser must not scrape them.
- In-repo format: `cases/*/deck.json` may be used internally, but **must not**
  contain card texts, images or full database dumps.

## Prices

### swu-db (USD)
- Included in the card rows above. Use only `MarketPrice` for a `VariantType ==
  "Normal"` printing of each card identity.
- Local cache: `data/swdb/` (or alongside the card cache)
- Currency: USD, TCGplayer reference.

### Cardmarket (EUR)
- Source: Cardmarket price guide, fetched as a bulk JSON file with `version`
  and `createdAt` fields.
- Local cache: `data/cm/`
- Currency: EUR, European market.
- Prices are snapshots. Always report the `createdAt` date and the share of
  deck slots that could be priced (`priced_slots / N`). Do not mix currencies
  in one total.

## Images
Card images are loaded from official CDN or the sources above. Any report that
embeds images is a local artifact and never part of the repository.

## Licensing and terms

- Card data, card text and card images are © Fantasy Flight Games / Asmodee /
  Lucasfilm. They are not covered by this repository's license.
- **swu-db**: community source with no published terms of use found; cache
  locally only and do not redistribute.
- **Official FFG API**: used for verification/audit. No public terms of use
  found; limit usage to checks, not wholesale mirroring.
- **SWU Forge**: Terms of Service (2026-06-01) explicitly prohibit scraping,
  crawling or otherwise extracting data from the service in bulk without
  permission. For that reason, **SWU Forge is not used as a default provider** in
  this repository. If permission is granted in writing, the provider may be added
  explicitly with attribution and the terms recorded here.
- **SWU Meta Stats**: read-only public API with abuse protection (429).
  Attribution required; cite window, region, sample size and retrieval date.
- **Melee.gg**: not queried directly; tournament data comes via SWU Meta Stats.
- Reports must credit the provider they used.

## Freshness rules

1. Every report states the card database retrieval date.
2. Every meta value states region, window, sample size and retrieval date.
3. Every price states currency, source and snapshot date.
4. A value without its parameters is not reported.
5. For audits, record the official `cardCount` per set and compare against the
   normalized card count.
