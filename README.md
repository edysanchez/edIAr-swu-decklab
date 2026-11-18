# edIAr SWU Decklab

An open-source, data-grounded toolkit for **Star Wars: Unlimited (SWU) Premier**
deck analysis and review.

**Status:** early development. See the [roadmap](docs/ROADMAP.md) and the
[documentation index](docs/README.md).

## Goals

Deck reviews that are:

- grounded in the real card database;
- explicit about legality;
- honest about data freshness and time windows;
- reproducible from a decklist.

## Scope

The v0.1 target is the functional core: a Premier analysis tool with one leader,
one base, at least 50 main-deck cards, local data, JSON and Markdown output.
Priority is functionality first, audience second: v0.2 makes it shareable, v1.0
makes it distributable. The detailed scope, non-goals and capability matrix are
kept with the local working records.

## Repository layout

A *skill* is a portable bundle of instructions and scripts that an AI agent
(OpenCode, Claude Code, etc.) can load when the task matches. `swu-review`
holds the review workflow, reference material and generic scripts.

Some paths are planned; files are added as the project grows.

```
skills/swu-review/   # portable AI skill: SKILL.md, scripts, reference, tests
docs/                # rules, metrics, scope, data sources, roadmap
```

Local case studies, generated reports and scratch files live in `.local/`,
`reports/` and `cases/`; all three are gitignored. Card data is cached locally in
`data/` and is not published.

## Principles

Principles 3 and 5 describe the optional meta layer (F4). F1 does not model meta,
matchups or play lines.

1. **No invented cards.** Every card, cost and ability comes from the card
   database.
2. **Legality is pass/fail.** See [`docs/rules.md`](docs/rules.md).
3. **Label the meta window.** Meta data is regional and temporal; an
   unlabelled usage number is not evidence.
4. **Off-meta is not automatically a defect.** A deck is judged by what it is
   trying to do, using staple density and innovation as separate measures, both
   defined in [`docs/metrics.md`](docs/metrics.md).
5. **Matchup claims require recorded data.** A deck that does not appear in the
   recorded archetypes gets "no recorded matchup data"; every claim cites its
   sample size and window.
6. **Reports are reproducible.** Every report states its inputs: card-database
   retrieval date, meta dataset, region, window and sample size.

## Legal

- **Code:** MIT, see [`LICENSE`](LICENSE).
- **Card data, text and images:** © Fantasy Flight Games / Asmodee / Lucasfilm.
  Not included in this repository. The Poggle test fixture still contains card
  text while it is being sanitized; see the known gap in
  [`docs/data-sources.md`](docs/data-sources.md).
- **Unofficial fan project:** not affiliated with, endorsed by, or sponsored by
  Fantasy Flight Games, Asmodee or Lucasfilm.

A personal project by **[edysanchez](https://github.com/edysanchez)**. The
`edIAr-` prefix marks AI-related projects.
