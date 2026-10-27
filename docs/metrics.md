# Metrics

Definitions for every number this repository reports. A metric without its
parameters is not evidence. If a definition here does not cover a number, the
number must not be reported.

Legality is defined in [`rules.md`](rules.md) and is out of scope here.

## Conventions

- Metrics are computed on the **main deck** only. Leader, base and sideboard
  are excluded unless a section says otherwise. The sideboard is construction
  material, not part of the deck being analysed.
- A **slot** is one physical card: a 3-of occupies 3 slots.
- **Card identity** is the printed name + subtitle, matching the legality
  definition. Two printings of the same card are the same identity.
- Use **printed values**. Ignore in-game modifiers, aspect penalties and
  abilities.
- `N` is the number of cards in the main deck. It is at least 50 but not
  necessarily 50; every percentage must state the `N` it uses.
- Percentages are reported to **one decimal place** and counts as integers.
  Dates use ISO 8601 (`YYYY-MM-DD`). Round only for presentation, never in
  intermediate calculations.

## Reported metrics

Every number a report publishes must appear in this table. If a report needs a
new number, define it here first.

| Metric | Unit | Defined in |
|---|---|---|
| Deck size (`N`) | cards | Conventions |
| Curve | slots per cost | Deck composition |
| Mean cost | resources | Deck composition |
| Type split | slots | Deck composition |
| Arena split | unit slots | Deck composition |
| Distinct cards | count | Deck composition |
| Unique-icon slots | slots | Deck composition |
| Aspect penalty: total and maximum | resources | Deck composition |
| Draw probability | % | Draw odds |
| Expected copies | copies | Draw odds |
| Staple density | % of slots | Meta metrics |
| Off-list slot share | % of slots | Meta metrics |
| Innovation index | % of distinct cards | Meta metrics |
| Core deviation | % of slots | Meta metrics |
| Rogue cards | count | Meta metrics |
| Archetype share | % of decks | Meta metrics |
| Matchup win rate | % of games | Meta metrics |
| Deck price | USD or EUR | Price |
| Price coverage | % of slots | Price |

## Deck composition

### Curve

Number of slots per printed cost, from 0 upwards, plus a separate bucket for
cards without a numeric cost. Report raw counts and percentages of `N`.

### Mean cost

```
mean_cost = sum(cost * copies) / sum(copies)   # only cards with a numeric cost
```

Report the denominator when it differs from `N`, so the reader can see how many
slots were excluded.

### Type split

Slots by card type: unit, event, upgrade. Report counts and percentages of `N`.
A card with two types is counted once per type and the overlap is stated.

### Arena split

Unit slots by arena: ground, space, both.

```
ground_units = slots whose arenas include Ground
space_units  = slots whose arenas include Space
unit_slots   = slots whose type includes Unit
```

A unit with both arenas counts in both, so `ground_units + space_units` can
exceed `unit_slots`. Non-unit cards are excluded from both numbers. Report the
`unit_slots` denominator alongside the split.

### Distinct cards

Number of distinct card identities in the main deck. A 50-card deck with 20
identities reports `distinct_cards = 20`.

### Unique-icon slots

Number of slots whose card has the unique icon. This is not the same as
`distinct_cards` and must not be labelled "unique cards".

### Aspect penalty

For each card identity, compare its aspect icons with the aspects provided by
the leader and base:

```
penalty(card) = 2 * (missing aspect icons)
```

Report:

- `total_penalty`: the sum of `penalty(card) * copies`;
- `max_penalty`: the penalty of the most expensive card.

This is a property of the deck, never a legality failure.

## Draw odds

Draw odds use an exact hypergeometric model under stated goldfish assumptions.
The model is deliberately simple and must be declared in every output.

Assumptions:

- population: `N` main-deck cards;
- opening hand: 6 cards;
- mulligan: optional, once, shuffling the **whole hand** back and drawing 6 new
  cards;
- after each round, during the regroup phase, the player draws **2 cards**;
- no other card draw, no thinning, no opponent interaction.

Given `K` copies of a card or group:

```
P(at least one by n draws) = 1 - C(N-K, n) / C(N, n)
n = 6 + 2 * rounds
with mulligan at the opening hand: P' = 1 - (1 - P(6))^2
expected copies by n draws = n * K / N
```

Report the probability at the opening hand and after each round, and state that
the numbers are a goldfish approximation. Decks with card-draw effects will
exceed the model.

Call the axis **rounds**, not turns: a round contains one action phase for each
player and one regroup phase.

## Meta metrics

All meta metrics are regional and temporal. Every reported value must include:

- the reference list size `N` (for staple density);
- region;
- time window: start and end date;
- sample size: number of decks;
- dataset name and retrieval date.

Values computed with different parameters are not comparable.

### Staple density

Slot-weighted share of the main deck that is played widely in the reference
window.

```
staple_density = slots whose identity is in the top-N usage list / N
```

- Default `N = 50`; the value used must be reported.
- The reference list is built from Premier decks in the stated region and
  window, excluding leaders and bases.
- Usage is the share of decks that include at least one copy of the identity.
- Card identity is name + subtitle.

### Innovation

Innovation is **not** the complement of staple density. `1 - staple_density`
only measures how much of the deck is off-list by slots; it says nothing about
how many different ideas the deck brings.

Report both of:

```
off_list_slot_share = slots outside the top-N list / N
innovation_index    = distinct off-list identities / distinct identities
```

`innovation_index` measures breadth: the share of distinct card choices that
are outside the reference list. Report the absolute count of distinct off-list
cards too.

Neither number is a quality score. An off-meta deck is not a worse deck.

### Core deviation (optional)

When archetype breakdown data is available (core / popular / flex for the
leader+base pair):

```
core_deviation = 1 - (slots in core + popular) / N
```

Report it only next to the archetype sample size. Without enough games for that
archetype, report "not recorded".

### Rogue cards

Number of distinct card identities with recorded usage below a stated threshold
(default: 1% of decks in the window).

Cards absent from the dataset are **not** 0% usage. Report them separately as
"not recorded".

### Archetype share

`metaShare` of the deck's leader+base pair in the stated window. If the pair is
absent from the dataset, report "not recorded", never 0%.

### Matchups

Use only recorded matchup data. Every claim must carry:

- games in the sample;
- the window;
- the archetype names exactly as recorded.

Win rate is `wins / (wins + losses)` over the reported games.

This repository uses **30 games** as the default minimum before discussing a
matchup. Below that, report the number and say the sample is too small. For a
deck that does not appear in the recorded archetypes, report "no recorded
matchup data" and do not substitute a heuristic.

## Price

- **USD:** `MarketPrice` from swu-db for one printing of each card.
- **EUR:** the Cardmarket price guide (bulk JSON, with its `createdAt` date).
- Multiply by the number of copies and sum over the main deck.
- Report currency, source, snapshot date and coverage (`priced_slots / N`).
- Do not mix currencies in one total, and do not compare USD and EUR without a
  stated exchange rate and date.

## Comparability

Two values may be compared only when they share:

- the same card database version;
- the same meta dataset, region and window;
- the same `N` and the same definition.

When any of these differ, report both values with their parameters instead of a
delta.
