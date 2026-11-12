---
name: swu-review
description: Analyze and validate Star Wars: Unlimited Premier decks using local card data only.
---

# SWU Review

A minimal skill for reviewing Star Wars: Unlimited Premier decks. It uses only local card data from `data/swudb/` (fetched from swu-db) and the rules in [`docs/rules.md`](../../docs/rules.md). No card texts, images, or DB dumps are included in the repo.

## Requirements

- Python 3
- Card database cached via `fetch_cards.py` (stored in `data/swudb/cards_normalized.json`, gitignored)
- Suspended list cached via `fetch_suspended.py` (stored in `data/swu/suspended.json`, gitignored). Without it, the built-in registry in `scripts/constants.py` is used.

## Setup

Fetch Premier cards:

```bash
python3 skills/swu-review/scripts/fetch_cards.py
```

Fetch the Premier suspended list from SWU Competitive Hub:

```bash
python3 skills/swu-review/scripts/fetch_suspended.py
```

The hub page is the operational source: it is one server-rendered page that is
updated the same day FFG announces a suspension, and it also records when a card
leaves the list. The snapshot wins over the built-in registry when present;
every disagreement is reported as a warning so the registry can be updated with
the official announcement link.

Optionally fetch Cardmarket EUR prices (public bulk files, cached in
`data/cm/`):

```bash
python3 skills/swu-review/scripts/fetch_prices_cm.py
```

Without that cache, analysis still runs and only the USD price block is
produced.

## Strategic review protocol

> This protocol is for optional strategic commentary **outside** the analysis
> artefacts. `analysis.json` and `report.md` never contain recommendations,
> cuts/adds, matchups or play lines; those are listed in `out_of_scope[]`.

For deck reviews (not just validation/analysis):

1. **Capture the plan first.** Before recommending cuts/additions, summarize: objective, target line, matchups, and flexible slots. Preserve this context across turns.
2. **Resources model.** A game starts with **2 prepared resources**. Normally **+1 resource per regroup phase** (if resourcing each round). 
   - First action phase: ~2 resources
   - Second: ~3, Third: ~4, Fourth: ~5, Fifth: ~6
   - Do **not** say "1 resource" for the initial round.
   - Distinguish **round / turn / phase / resources available**.
   - Resources are different from the **2 cards drawn per regroup phase** (do not confuse them).
   - Deployment timing (e.g. Poggle needs >= 5 resources) must follow this model.
3. **Evaluate cards in context.** Do not list candidates in isolation. For each candidate, link to a concrete need/matchup and a specific slot to replace. Consider role (aggression/control/value/tech/defensive/engine), sequences enabled, and opportunity cost.
4. **Substitution analysis.** For any proposed cut/addition, explain: slot out, role lost/gained, sequence enabled/lost, matchup relevance, opportunity cost, confidence. Mark uncertainties if text/interaction is not verified.
5. **Local-first data.** Consult `data/swudb/` first (use exact card text from local DB). Prioritize `docs/rules.md`. Only use external sources to fill missing data or resolve discrepancies, and explicitly state what was checked locally vs externally.
6. **Traceability.** Attribute facts to sources. Mark tactical inferences as inferences. If using tier lists/meta, record source/date/scope/sample size or label as orientative.
7. **Transparent council.** If consulting multiple perspectives, list them, state points of consensus and disagreements explicitly.

## Play lines
When analyzing lines of play:
- Show resources at start of relevant phases, costs paid, order of actions, and resources remaining.
- State assumptions clearly.
- Separate "probability to draw" (draw_odds, hypergeometric, +2 per regroup) from "probability to play" (resource-constrained).
- Draw odds must declare: which cards counted, how many seen so far, what is not modeled.

## Accepted deck formats

All tools share the same normalization layer. Supported formats:

| Format | Example | Notes |
|---|---|---|
| SWUDB export with IDs | `{"leader":{"id":"HMW_012","count":1},"base":{"id":"HMW_022","count":1},"deck":[{"id":"ASH_032","count":3}],...}` | Resolved via local card DB by set/number. |
| Case format | `{"mainDeck":[{"count":3,"card":{"title":"...","subtitle":"...","expansion":{"code":"ASH"},"cardNumber":32,"type":{"name":"Unit"},...}}],...}` | Leader/base detected by type. |
| Flat list | `[{"count":3,"title":"Card Name","subtitle":"...","code":"ASH032"},...]` | Leader/Base entries ignored by draw odds. |
| SWUDB text | Sections: `Leader`, `Base`, `MainDeck`, `Sideboard` with `count \| Name \| Subtitle` | Parsed by `swu_cards.py`. |

Example ID-based export:
```json
{
  "metadata": {},
  "leader": {"id": "HMW_012", "count": 1},
  "base": {"id": "HMW_022", "count": 1},
  "deck": [{"id": "ASH_032", "count": 3}],
  "sideboard": []
}
```

## Card analysis (v0.1)

The card-analysis pipeline is the primary review output. It produces two
artefacts from one run:

| Artefact | Purpose |
|---|---|
| `analysis.json` | Machine-readable contract. Every number, finding and limitation is here. |
| `report.md` | Human-readable view rendered from the JSON. It never recomputes a metric. |

```bash
# Both files
python3 skills/swu-review/scripts/swu_analyze.py path/to/deck.json \
  --json analysis.json --report report.md

# JSON on stdout (nothing else is printed to stdout)
python3 skills/swu-review/scripts/swu_analyze.py path/to/deck.json --json

# Options
#   --card-db PATH    explicit cards_normalized.json
#   --max-round N     last round in draw odds (default 6)
#   --cm-cache PATH   Cardmarket cache directory (defaults to data/cm/)
#   --no-eur          omit the optional Cardmarket EUR price block
```

The contract is [`analysis.schema.json`](analysis.schema.json). It covers:

- **provenance** — schema/tool/rules versions, input SHA-256, DB snapshot,
  sets and schema hash;
- **legality** — leader, base, deck size, sideboard size, copy limit, Premier
  sets, suspensions, aspect penalty;
- **composition** — main deck only: curve, mean cost, types, arenas, distinct,
  unique slots, USD price with coverage, and an optional separate EUR
  (`price_eur`) block when the Cardmarket cache is present;
- **cards** — leader, base and one sheet per main-deck identity, with the exact
  local `frontText` or `text: null` / `text_status: "missing"`;
- **draw odds** — declared goldfish model, assumptions, per-card probabilities
  and expected copies;
- **findings** — deterministic, threshold-based observations. Every rule lives
  in [`reference/findings.md`](reference/findings.md). A finding without a
  documented threshold is not emitted;
- **limitations** — what the model and the data cannot see, each with an
  `impact` of `info`, `degraded` or `blocking`;
- **out of scope** — meta, matchups, strategy, cuts/adds, council, subjective
  grades, price speculation.

Scope rules:

- Composition and draw odds use the **main deck only**. Leader and base get
  legality checks and card sheets but no composition slots and no draw pool.
- The sideboard is used for **legality only**.
- Findings are observations, never recommendations. `critical` is reserved for
  `legality.errors[]`.
- Text semantics (draw, removal, ramp) are **not** classified in v0.1. The
  absence of such a finding is not a claim that the deck lacks the effect; see
  the `text-semantics-not-analyzed` limitation.

Definition sources: [`docs/rules.md`](../../docs/rules.md) for legality,
[`docs/metrics.md`](../../docs/metrics.md) for every metric and the draw model.
Do not restate those definitions in the report.

## Commands

### Card analysis and report
See [Card analysis (v0.1)](#card-analysis-v01) above. This is the recommended
path for a deck review.

### Validate deck legality
Checks against [`docs/rules.md`](../../docs/rules.md) (exactly 1 leader/base, >=50 draw deck, <=10 sideboard, max 3 copies by name+subtitle across deck+sideboard, Premier sets only, suspended cards). Aspect penalty is reported but does not block legality.

```bash
python3 skills/swu-review/scripts/validate_deck.py path/to/deck.json
python3 skills/swu-review/scripts/validate_deck.py path/to/deck.json --json
```

### Analyze deck
Reports curve, type split, arena split, distinct cards, unique slots, aspect penalty, and price (from swu-db market prices in local cache). Calculations use the local card DB only.

```bash
python3 skills/swu-review/scripts/analyze_deck.py path/to/deck.json
python3 skills/swu-review/scripts/analyze_deck.py path/to/deck.json --json
```

### Draw odds
Hypergeometric draw odds with **+2 cards per regroup phase** (see [`docs/metrics.md`](../../docs/metrics.md)). Leader and base are excluded from the draw pool (N=50). Copies are grouped by **name + subtitle** identity. Supports mulligan, grouping by `cost`, `arena`, `type`, or name substring.

```bash
python3 skills/swu-review/scripts/draw_odds.py path/to/deck.json --max-turn 6
python3 skills/swu-review/scripts/draw_odds.py path/to/deck.json --group cost:2
python3 skills/swu-review/scripts/draw_odds.py path/to/deck.json --mulligan --json
```

## Notes

- Card identity is `name + subtitle` (deduplicated across reprints).
- Aspect penalty is calculated but never makes a deck illegal.
- Prices come from swu-db cached data; coverage may vary.
- Tokens and non-Normal variants are excluded from the card DB.
- For rule interpretations, suspended cards, or anything not covered by local data, verify against official sources.
