# SWU Review — Poggle the Lesser

**Leader:** Poggle the Lesser  
**Base:** Shield Generator Complex — Endor

> **Data health:** 0 blocking; 4 degraded; 5 info.
> Read the affected numbers with the caveats in [Limitations](#limitations).

## Provenance

| Field | Value |
|---|---|
| Generated at | 2026-11-03T09:36:34Z |
| Tool version | 0.1.0-dev |
| Rules version | 2026-10-26 |
| Schema version | 0.1.0 |
| Input path | cases/poggle-blue-endor/deck.json |
| Input SHA-256 | 9cb743aa588f6d42655d8755cc50334f168cd76994cb2da275ca8edeeb1afb8a |
| Input format | case |
| Card DB source | api.swu-db.com |
| Card DB snapshot | 2026-10-27 |
| Card DB sets | JTL, LOF, IBH, SEC, LAW, ASH, HMW |
| Card DB cards | 1634 |
| Card DB schema hash | 66aa15bcd22bff0933eb4d38b45435cde0f747a217f96dd4f19af38f826095c0 |

## Legality

**Result:** legal according to the local rules version.

### Checks

| Check | Result | Detail |
|---|---|---|
| unresolved | pass | All card references resolved |
| leader | pass | Exactly one leader |
| base | pass | Exactly one base |
| leader_type | pass | Leader slot contains a Leader |
| base_type | pass | Base slot contains a Base |
| main_zone | pass | Draw deck contains no leader or base |
| sideboard_zone | pass | Sideboard contains no leader or base |
| deck_size | pass | Draw deck must be at least 50 cards (found: 50) |
| sideboard_size | pass | Sideboard must be at most 10 cards (found: 10) |
| copy_limit | pass | All identities within 3 copies |
| premier_sets | pass | All cards from Premier sets |
| suspended | pass | No suspended cards |

### Aspect penalty

Total penalty: **0**; maximum on a single card: **0**.

## Composition snapshot

| Metric | Value |
|---|---|
| Main deck | 50 |
| Distinct cards | 18 |
| Unique slots | 20 |
| Mean cost | 3.24 (denominator 50) |
| Ground units | 37 / 39 (94.9%) |
| Space units | 2 / 39 (5.1%) |
| Both arenas | 0 / 39 |
| Deck price (USD) | 28.19 (50/50 slots, 100.0%) |

### Cost curve

| Cost | Cards | % of N |
|---|---|---|
| 1 | 2 | 4.0% |
| 2 | 18 | 36.0% |
| 3 | 12 | 24.0% |
| 4 | 8 | 16.0% |
| 5 | 6 | 12.0% |
| 6 | 2 | 4.0% |
| 7 | 2 | 4.0% |

### Types

| Type | Slots | % of N |
|---|---|---|
| Event | 9 | 18.0% |
| Unit | 39 | 78.0% |
| Upgrade | 2 | 4.0% |

## Card sheets

### Leader

#### Poggle the Lesser — Let the Executions Begin

| Field | Value |
|---|---|
| Code | HMW012 |
| Copies | 1 |
| Type | Leader |
| Cost | 5 |
| Power | 1 |
| HP | 6 |
| Arenas | Ground |
| Aspects | Aggression, Villainy |
| Traits | SEPARATIST, OFFICIAL |
| Keywords | — |
| Rarity | Common |
| Unique | yes |

> Action [C=1, Exhaust]: Ready a friendly Creature unit and deal 1 damage to it.

**Derived tags:** arena:Ground, aspect:Aggression, aspect:Villainy, trait:OFFICIAL, trait:SEPARATIST, type:Leader, unique

### Base

#### Shield Generator Complex — Endor

| Field | Value |
|---|---|
| Code | HMW022 |
| Copies | 1 |
| Type | Base |
| Cost | — |
| Power | — |
| HP | 30 |
| Arenas | — |
| Aspects | Vigilance |
| Traits | ENDOR |
| Keywords | — |
| Rarity | Common |
| Unique | no |

_No card text in local database._

**Flags:** no price

**Derived tags:** aspect:Vigilance, trait:ENDOR, type:Base

### Main deck

#### Adamant Ewoks

| Field | Value |
|---|---|
| Code | HMW177 |
| Copies | 3 |
| Type | Unit |
| Cost | 2 |
| Power | 3 |
| HP | 2 |
| Arenas | Ground |
| Aspects | Aggression |
| Traits | EWOK |
| Keywords | — |
| Rarity | Common |
| Unique | no |

> When Played: If you control another Ewok unit or an Endor base, you may deal 1 damage to a base and 1 damage to an enemy unit.

**Derived tags:** arena:Ground, aspect:Aggression, trait:EWOK, type:Unit

#### Batcher — Loyal Hound

| Field | Value |
|---|---|
| Code | HMW083 |
| Copies | 3 |
| Type | Unit |
| Cost | 2 |
| Power | 2 |
| HP | 3 |
| Arenas | Ground |
| Aspects | Vigilance |
| Traits | CREATURE |
| Keywords | Restore |
| Rarity | Uncommon |
| Unique | yes |

> Restore 1 (When this unit attacks, heal 1 damage from your base.) 
> This unit gets +1/+0 while defending.

**Derived tags:** arena:Ground, aspect:Vigilance, keyword:Restore, trait:CREATURE, type:Unit, unique

#### Feisty Blurrg

| Field | Value |
|---|---|
| Code | HMW179 |
| Copies | 3 |
| Type | Unit |
| Cost | 2 |
| Power | 1 |
| HP | 4 |
| Arenas | Ground |
| Aspects | Aggression |
| Traits | CREATURE |
| Keywords | Grit |
| Rarity | Common |
| Unique | no |

> Grit (This unit gets +1/+0 for each damage on it.)

**Derived tags:** arena:Ground, aspect:Aggression, keyword:Grit, trait:CREATURE, type:Unit

#### Rancor Keeper

| Field | Value |
|---|---|
| Code | ASH032 |
| Copies | 3 |
| Type | Unit |
| Cost | 2 |
| Power | 2 |
| HP | 4 |
| Arenas | Ground |
| Aspects | Vigilance, Aggression |
| Traits | UNDERWORLD |
| Keywords | — |
| Rarity | Uncommon |
| Unique | no |

> When a friendly unit is dealt damage and survives: Deal 1 damage to any number of bases. Use this ability only once each round.

**Derived tags:** arena:Ground, aspect:Aggression, aspect:Vigilance, trait:UNDERWORLD, type:Unit

#### Oggdo Bogdo — Bogano Brute

| Field | Value |
|---|---|
| Code | LOF063 |
| Copies | 3 |
| Type | Unit |
| Cost | 3 |
| Power | 5 |
| HP | 5 |
| Arenas | Ground |
| Aspects | Vigilance |
| Traits | CREATURE |
| Keywords | — |
| Rarity | Rare |
| Unique | yes |

> This unit can't attack unless it's damaged. 
> When this unit attacks and defeats a unit: Heal 2 damage from this unit.

**Derived tags:** arena:Ground, aspect:Vigilance, trait:CREATURE, type:Unit, unique

#### Scorch — Imperial Commando

| Field | Value |
|---|---|
| Code | HMW064 |
| Copies | 3 |
| Type | Unit |
| Cost | 3 |
| Power | 3 |
| HP | 5 |
| Arenas | Ground |
| Aspects | Vigilance, Villainy |
| Traits | IMPERIAL, CLONE, TROOPER |
| Keywords | — |
| Rarity | Uncommon |
| Unique | yes |

> On Attack: You may deal 1 damage to an upgraded unit.

**Derived tags:** arena:Ground, aspect:Vigilance, aspect:Villainy, trait:CLONE, trait:IMPERIAL, trait:TROOPER, type:Unit, unique

#### Venomous Wyyyshokk

| Field | Value |
|---|---|
| Code | HMW087 |
| Copies | 3 |
| Type | Unit |
| Cost | 3 |
| Power | 3 |
| HP | 4 |
| Arenas | Ground |
| Aspects | Vigilance |
| Traits | CREATURE |
| Keywords | — |
| Rarity | Common |
| Unique | no |

> When Defeated: You may give a Weakness token to a damaged unit.

**Derived tags:** arena:Ground, aspect:Vigilance, trait:CREATURE, type:Unit

#### Arena Nexu — Starved for Prey

| Field | Value |
|---|---|
| Code | HMW182 |
| Copies | 3 |
| Type | Unit |
| Cost | 4 |
| Power | 2 |
| HP | 6 |
| Arenas | Ground |
| Aspects | Aggression |
| Traits | CREATURE |
| Keywords | Grit |
| Rarity | Rare |
| Unique | yes |

> Grit 
> On Attack: You may deal 3 damage to a friendly Creature unit (including this one) and ready this unit. Use this ability only once each round.

**Derived tags:** arena:Ground, aspect:Aggression, keyword:Grit, trait:CREATURE, type:Unit, unique

#### Clone of the Zillo Beast — Emperor's Experiment

| Field | Value |
|---|---|
| Code | HMW065 |
| Copies | 2 |
| Type | Unit |
| Cost | 4 |
| Power | 6 |
| HP | 6 |
| Arenas | Ground |
| Aspects | Vigilance, Villainy |
| Traits | CLONE, CREATURE |
| Keywords | — |
| Rarity | Rare |
| Unique | yes |

> Other friendly units get -2/-2. 
> On Attack: You may give a Weakness token to a unit.

**Derived tags:** arena:Ground, aspect:Vigilance, aspect:Villainy, trait:CLONE, trait:CREATURE, type:Unit, unique

#### Filthy Dianoga

| Field | Value |
|---|---|
| Code | HMW155 |
| Copies | 3 |
| Type | Unit |
| Cost | 4 |
| Power | 5 |
| HP | 5 |
| Arenas | Ground |
| Aspects | Aggression, Villainy |
| Traits | CREATURE |
| Keywords | — |
| Rarity | Common |
| Unique | no |

_No card text in local database._

**Derived tags:** arena:Ground, aspect:Aggression, aspect:Villainy, trait:CREATURE, type:Unit

#### Arena Acklay — Screaming Predator

| Field | Value |
|---|---|
| Code | HMW156 |
| Copies | 3 |
| Type | Unit |
| Cost | 5 |
| Power | 5 |
| HP | 6 |
| Arenas | Ground |
| Aspects | Aggression, Villainy |
| Traits | CREATURE |
| Keywords | — |
| Rarity | Uncommon |
| Unique | yes |

> When this unit is dealt damage and survives: Deal 2 damage to each enemy base.

**Derived tags:** arena:Ground, aspect:Aggression, aspect:Villainy, trait:CREATURE, type:Unit, unique

#### The Great Progenitor — First of the Drengir

| Field | Value |
|---|---|
| Code | HMW067 |
| Copies | 3 |
| Type | Unit |
| Cost | 5 |
| Power | 4 |
| HP | 7 |
| Arenas | Ground |
| Aspects | Vigilance, Villainy |
| Traits | CREATURE |
| Keywords | — |
| Rarity | Legendary |
| Unique | yes |

> When Attack Ends: You may give a Weakness token to this unit. If you do, create a Beast token for each Weakness token on this unit.

**Derived tags:** arena:Ground, aspect:Vigilance, aspect:Villainy, trait:CREATURE, type:Unit, unique

#### Starlit Purrgil

| Field | Value |
|---|---|
| Code | HMW092 |
| Copies | 2 |
| Type | Unit |
| Cost | 6 |
| Power | 4 |
| HP | 5 |
| Arenas | Space |
| Aspects | Vigilance |
| Traits | CREATURE |
| Keywords | Restore |
| Rarity | Common |
| Unique | no |

> Restore 2 (When this unit attacks, heal 2 damage from your base.)
> When Played: You may exhaust a unit.

**Derived tags:** arena:Space, aspect:Vigilance, keyword:Restore, trait:CREATURE, type:Unit

#### Giant Gorax

| Field | Value |
|---|---|
| Code | HMW188 |
| Copies | 2 |
| Type | Unit |
| Cost | 7 |
| Power | 7 |
| HP | 7 |
| Arenas | Ground |
| Aspects | Aggression |
| Traits | CREATURE |
| Keywords | Overwhelm |
| Rarity | Legendary |
| Unique | no |

> Overwhelm
> On Attack/When Defeated: If you control an Endor base, each opponent chooses one:
> You deal 3 damage to a unit or base they control.
> They discard a card from their hand and defeat a resource they control.

**Derived tags:** arena:Ground, aspect:Aggression, keyword:Overwhelm, trait:CREATURE, type:Unit

#### Always a Bigger Fish

| Field | Value |
|---|---|
| Code | HMW099 |
| Copies | 3 |
| Type | Event |
| Cost | 2 |
| Power | — |
| HP | — |
| Arenas | — |
| Aspects | Vigilance |
| Traits | INNATE |
| Keywords | — |
| Rarity | Rare |
| Unique | no |

> Defeat a friendly Creature unit. If you do, play a Creature unit that costs up to 3 more than the defeated unit from your hand for free.

**Derived tags:** aspect:Vigilance, trait:INNATE, type:Event

#### Nightfall

| Field | Value |
|---|---|
| Code | HMW193 |
| Copies | 3 |
| Type | Event |
| Cost | 2 |
| Power | — |
| HP | — |
| Arenas | — |
| Aspects | Aggression |
| Traits | DISASTER |
| Keywords | — |
| Rarity | Common |
| Unique | no |

> Deal 1 damage to an enemy unit. 
> If you control an Endor base, you may attack with a unit. It gets +2/+0 for this attack.

**Derived tags:** aspect:Aggression, trait:DISASTER, type:Event

#### Run Amok

| Field | Value |
|---|---|
| Code | HMW194 |
| Copies | 3 |
| Type | Event |
| Cost | 3 |
| Power | — |
| HP | — |
| Arenas | — |
| Aspects | Aggression |
| Traits | DISASTER |
| Keywords | — |
| Rarity | Common |
| Unique | no |

> Create a Beast token.
> Deal 1 damage to a friendly ground unit and 1 damage to an enemy ground unit.

**Derived tags:** aspect:Aggression, trait:DISASTER, type:Event

#### Nimble Prowess

| Field | Value |
|---|---|
| Code | SEC069 |
| Copies | 2 |
| Type | Upgrade |
| Cost | 1 |
| Power | 1 |
| HP | 1 |
| Arenas | — |
| Aspects | Vigilance |
| Traits | INNATE |
| Keywords | — |
| Rarity | Common |
| Unique | no |

> Attach to a friendly unit.
> When Played: You may exhaust a unit in attached unit's arena.

**Derived tags:** aspect:Vigilance, trait:INNATE, type:Upgrade

## Draw odds

Model: `hypergeometric_goldfish`. Population 50 cards; opening hand 6; +2 per regroup; mulligan: no.

### Assumptions

- Population: 50 main-deck cards; leader and base are not drawn.
- Opening hand: 6 cards.
- After each round, during the regroup phase, the player draws 2 cards.
- No mulligan, no other card draw, no thinning, no recursion, no opponent interaction.
- P(at least one by n draws) = 1 - C(N-K, n) / C(N, n).
- Expected copies by n draws = n * K / N.
- P(see) is not P(play): resources and playability are not modelled.

### Probability of seeing at least one copy

| Card | Copies | R0 | R1 | R2 | R3 | R4 | R5 | R6 |
|---|---|---|---|---|---|---|---|---|
| Adamant Ewoks | 3 | 32.4% | 41.4% | 49.6% | 57.0% | 63.6% | 69.5% | 74.7% |
| Always a Bigger Fish | 3 | 32.4% | 41.4% | 49.6% | 57.0% | 63.6% | 69.5% | 74.7% |
| Arena Acklay - Screaming Predator | 3 | 32.4% | 41.4% | 49.6% | 57.0% | 63.6% | 69.5% | 74.7% |
| Arena Nexu - Starved for Prey | 3 | 32.4% | 41.4% | 49.6% | 57.0% | 63.6% | 69.5% | 74.7% |
| Batcher - Loyal Hound | 3 | 32.4% | 41.4% | 49.6% | 57.0% | 63.6% | 69.5% | 74.7% |
| Clone of the Zillo Beast - Emperor's Experiment | 2 | 22.8% | 29.7% | 36.3% | 42.6% | 48.6% | 54.2% | 59.5% |
| Feisty Blurrg | 3 | 32.4% | 41.4% | 49.6% | 57.0% | 63.6% | 69.5% | 74.7% |
| Filthy Dianoga | 3 | 32.4% | 41.4% | 49.6% | 57.0% | 63.6% | 69.5% | 74.7% |
| Giant Gorax | 2 | 22.8% | 29.7% | 36.3% | 42.6% | 48.6% | 54.2% | 59.5% |
| Nightfall | 3 | 32.4% | 41.4% | 49.6% | 57.0% | 63.6% | 69.5% | 74.7% |
| Nimble Prowess | 2 | 22.8% | 29.7% | 36.3% | 42.6% | 48.6% | 54.2% | 59.5% |
| Oggdo Bogdo - Bogano Brute | 3 | 32.4% | 41.4% | 49.6% | 57.0% | 63.6% | 69.5% | 74.7% |
| Rancor Keeper | 3 | 32.4% | 41.4% | 49.6% | 57.0% | 63.6% | 69.5% | 74.7% |
| Run Amok | 3 | 32.4% | 41.4% | 49.6% | 57.0% | 63.6% | 69.5% | 74.7% |
| Scorch - Imperial Commando | 3 | 32.4% | 41.4% | 49.6% | 57.0% | 63.6% | 69.5% | 74.7% |
| Starlit Purrgil | 2 | 22.8% | 29.7% | 36.3% | 42.6% | 48.6% | 54.2% | 59.5% |
| The Great Progenitor - First of the Drengir | 3 | 32.4% | 41.4% | 49.6% | 57.0% | 63.6% | 69.5% | 74.7% |
| Venomous Wyyyshokk | 3 | 32.4% | 41.4% | 49.6% | 57.0% | 63.6% | 69.5% | 74.7% |

### Expected copies drawn

| Card | Copies | R0 | R1 | R2 | R3 | R4 | R5 | R6 |
|---|---|---|---|---|---|---|---|---|
| Adamant Ewoks | 3 | 0.36 | 0.48 | 0.60 | 0.72 | 0.84 | 0.96 | 1.08 |
| Always a Bigger Fish | 3 | 0.36 | 0.48 | 0.60 | 0.72 | 0.84 | 0.96 | 1.08 |
| Arena Acklay - Screaming Predator | 3 | 0.36 | 0.48 | 0.60 | 0.72 | 0.84 | 0.96 | 1.08 |
| Arena Nexu - Starved for Prey | 3 | 0.36 | 0.48 | 0.60 | 0.72 | 0.84 | 0.96 | 1.08 |
| Batcher - Loyal Hound | 3 | 0.36 | 0.48 | 0.60 | 0.72 | 0.84 | 0.96 | 1.08 |
| Clone of the Zillo Beast - Emperor's Experiment | 2 | 0.24 | 0.32 | 0.40 | 0.48 | 0.56 | 0.64 | 0.72 |
| Feisty Blurrg | 3 | 0.36 | 0.48 | 0.60 | 0.72 | 0.84 | 0.96 | 1.08 |
| Filthy Dianoga | 3 | 0.36 | 0.48 | 0.60 | 0.72 | 0.84 | 0.96 | 1.08 |
| Giant Gorax | 2 | 0.24 | 0.32 | 0.40 | 0.48 | 0.56 | 0.64 | 0.72 |
| Nightfall | 3 | 0.36 | 0.48 | 0.60 | 0.72 | 0.84 | 0.96 | 1.08 |
| Nimble Prowess | 2 | 0.24 | 0.32 | 0.40 | 0.48 | 0.56 | 0.64 | 0.72 |
| Oggdo Bogdo - Bogano Brute | 3 | 0.36 | 0.48 | 0.60 | 0.72 | 0.84 | 0.96 | 1.08 |
| Rancor Keeper | 3 | 0.36 | 0.48 | 0.60 | 0.72 | 0.84 | 0.96 | 1.08 |
| Run Amok | 3 | 0.36 | 0.48 | 0.60 | 0.72 | 0.84 | 0.96 | 1.08 |
| Scorch - Imperial Commando | 3 | 0.36 | 0.48 | 0.60 | 0.72 | 0.84 | 0.96 | 1.08 |
| Starlit Purrgil | 2 | 0.24 | 0.32 | 0.40 | 0.48 | 0.56 | 0.64 | 0.72 |
| The Great Progenitor - First of the Drengir | 3 | 0.36 | 0.48 | 0.60 | 0.72 | 0.84 | 0.96 | 1.08 |
| Venomous Wyyyshokk | 3 | 0.36 | 0.48 | 0.60 | 0.72 | 0.84 | 0.96 | 1.08 |

## Findings

### `arena-imbalance` (warning)

Only 2 of 39 unit slots are Space (5.1%).

| Field | Value |
|---|---|
| Category | composition |
| Metric | composition.arenas.space |
| Value | 2 |
| Denominator | 39 |
| Percentage | 5.1% |
| Threshold | < 15 (pct_of_unit_slots) |
| Registry | reference/findings.md#arena-imbalance |
| Registry version | 1 |

| Card | Copies |
|---|---|
| Starlit Purrgil | 2 |

## Limitations

| ID | Impact | Category | Statement |
|---|---|---|---|
| `data-snapshot` | info | data | Card data snapshot: 2026-10-27 from api.swu-db.com (7 sets, 1634 cards). |
| `premier-only-db` | degraded | data | Only Premier sets are fetched; older printings are not in the local DB. |
| `price-snapshot` | info | data | Prices are market USD from swu-db, snapshot 2026-10-27, coverage 100.0%. |
| `draw-goldfish` | degraded | model | Draw odds use a goldfish model. |
| `no-rules-engine` | info | model | Card text is reproduced from the DB, not interpreted. |
| `rules-version` | info | rules | Legality follows the local rules verified on 2026-10-26. |
| `sideboard-legal-only` | info | scope | The sideboard is used for legality only. |
| `heuristic-thresholds` | degraded | heuristic | Findings use versioned heuristic thresholds, not rules of the game. |
| `text-semantics-not-analyzed` | degraded | scope | Draw, removal and ramp are not classified in this version. |

- **`data-snapshot`**
  - Affects: legality, composition, cards, draw_odds
  - Detail: Any set released after the snapshot is invisible to this analysis.
  - Mitigation: Re-run fetch_cards.py and check db.data_as_of.
- **`premier-only-db`**
  - Affects: legality, cards
  - Detail: Reprint legality by card version cannot be verified. An old printing may be reported as unresolved even when a Premier reprint exists.
  - Mitigation: Resolve by name+subtitle or add non-Premier printings to the DB.
- **`price-snapshot`**
  - Affects: composition.price
  - Detail: No foil, EUR, shipping or seller variation. Not an appraisal.
  - Mitigation: Read the total as an estimate with the stated coverage.
- **`draw-goldfish`**
  - Affects: draw_odds
  - Detail: Opening hand 6, +2 per regroup, no mulligan, no other draw, no thinning, no recursion, no opponent interaction.
  - Mitigation: Read as an upper bound on seeing a card, not on playing it.
- **`no-rules-engine`**
  - Affects: cards, findings
  - Detail: Keywords are listed, not simulated. Draw, removal and ramp are not classified.
  - Mitigation: Use the card sheets for manual reading.
- **`rules-version`**
  - Affects: legality
  - Detail: Errata, suspensions or event-specific rules after that date are not included.
  - Mitigation: Check the official Comprehensive Event Guide.
- **`sideboard-legal-only`**
  - Affects: composition, cards, draw_odds
  - Detail: Sideboard cards get no composition slots, no card sheets and no draw odds.
  - Mitigation: Analyse the sideboard separately if needed.
- **`heuristic-thresholds`**
  - Affects: findings
  - Detail: A threshold crossing is an observation, not a verdict.
  - Mitigation: Read reference/findings.md for the rationale.
- **`text-semantics-not-analyzed`**
  - Affects: findings, cards
  - Detail: The absence of a finding is not a claim that the deck lacks an effect. A curated taxonomy is planned for v0.2.
  - Mitigation: Read card text manually.

## Out of scope

| ID | Statement |
|---|---|
| `meta` | Meta share, staple density and archetype data. |
| `matchups` | Matchup win rates and sideboard plans. |
| `strategy` | Play lines, target lines and scenarios. |
| `cuts_adds` | Recommended cuts or additions. |
| `council` | Multi-perspective council review. |
| `subjective_grades` | Card or deck quality scores without a rubric. |
| `price_speculation` | Price forecasts or investment advice. |
