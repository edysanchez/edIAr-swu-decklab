# Premier legality rules

Single source of truth for **Star Wars: Unlimited Premier** deck legality in this
repository. Validators, the `swu-review` skill and all documentation must follow
this file. Do not restate these rules elsewhere.

_Last verified: 2026-11-09._

## Sources

- Official Premier format page:
  <https://starwarsunlimited.com/how-to-play?chapter=premier>
- Comprehensive Rules 9.0:
  <https://cdn.starwarsunlimited.com//SWH_Comp_Rules_v9_0_c4aa591948.pdf>
- Comprehensive Event Guide v1.5 (updated 2026-10-09) — deckbuilding rules,
  Premier-legal product list and suspension list:
  <https://cdn.starwarsunlimited.com//Comprehensive_Event_Guide_v1_5_FINAL_8_2e86283787.pdf>

When the official documents disagree, the Comprehensive Event Guide wins for
tournament deckbuilding, and the Comprehensive Rules win for card behaviour.

## Deck structure

A legal Premier deck consists of:

- **exactly one leader**;
- **exactly one base**;
- a **draw deck of at least 50 cards** (units, events and upgrades);
- optionally, a **sideboard of at most 10 cards**.

There is no maximum draw deck size and no maximum total. A deck with 51 or more
cards in the draw deck is legal. Do not require exactly 50.

Leaders and bases cannot be in the sideboard or in the draw deck.

## Copy limit

- No more than **3 copies of any card** across the draw deck **and** sideboard
  combined.
- A "copy" is any card that shares the **printed name and subtitle** with
  another card, regardless of art, foiling, variant or graphic design.
- The limit applies to unique and non-unique cards alike. The unique icon only
  restricts how many copies a player may control in play, not deckbuilding.

## Card pool

Only cards from products designated **Premier-legal** may be used. As of
2026-10-26 the official list is:

| Set | Code |
|---|---|
| Jump to Lightspeed | JTL |
| Legends of the Force | LOF |
| Intro Battle: Hoth | IBH |
| Secrets of Power | SEC |
| A Lawless Time | LAW |
| Ashes of the Empire | ASH |
| Homeworlds | HMW |

Everything else is not Premier-legal, including Spark of Rebellion (SOR),
Shadows of the Galaxy (SHD), Twilight of the Republic (TWI) and 2026 Twin Suns
(TS26).

Legality follows the **card version**: a card reprinted in a Premier-legal
product is legal even if the player uses an older printing. Match by printed
name and subtitle, not by set code alone.

Rotation symbols A and B currently mark the two most recent rotations, and every
product in the table above carries one of them. A rotation symbol alone is
**not** proof of legality: a newly indexed or not-yet-released product can carry
a symbol before it appears on the official Premier-legal list. For example,
Icons 2027 Edition (IC27) is indexed by the card database with a rotation symbol
but is not on the Premier-legal list as of 2026-10-26.

Because the Comprehensive Event Guide is updated periodically, a product
released after its last update is legal from its official release date. The
official release announcement is the tiebreaker; check the Premier page before
accepting a product that is missing from the table.

Cards obtained at a prerelease event are only legal for that event until the set
is officially released.

## Suspended cards

A suspended card is **not legal in any event of that format**, competitive or
casual, while it remains on the list. Suspension is by printed name and
subtitle: other printings of the same name are unaffected.

As of 2026-11-09 the Premier suspended list is:

| Card | Set | No. | Type | Announced |
|---|---|---|---|---|
| Cad Bane, *Still Faster Than You* | ASH | 011 | Leader | 2026-08-24 |
| Chimaera, *A Frightening Reality* | ASH | 052 | Unit | 2026-11-09 |
| Koska Reeves, *Warrior of Mandalore* | ASH | 079 | Unit | 2026-11-09 |
| Neel, *The Cutest Boy* | ASH | 248 | Unit | 2026-11-09 |
| Aggressive Negotiations | SEC | 179 | Event | 2026-11-09 |

Official sources (one announcement per entry, no community lists):

- [Cad Bane Leader Card Suspended](https://starwarsunlimited.com/articles/cad-banned)
  (2026-08-24).
- [Premier Format Update: November 2026](https://starwarsunlimited.com/articles/premier-format-update-november-2026)
  (2026-11-09, effective immediately).

The machine-readable copy lives in `skills/swu-review/scripts/constants.py`
(`SUSPENDED_CARDS`, with a per-card `source`); keep both in sync.

**Caveat:** FFG publishes suspensions as individual articles, not as a
standing list, and the Comprehensive Event Guide can lag behind them. v1.5
(updated 2026-10-09) still states that no Premier cards are suspended, even
though Cad Bane had been announced on 2026-08-24. When the guide and a dated
announcement disagree, the newest announcement wins.

For automation, `fetch_suspended.py` parses the
[SWU Competitive Hub suspended list](https://www.swu-competitivehub.com/suspended-list/)
into `data/swu/suspended.json`. That snapshot is the operational source when
present; `constants.SUSPENDED_CARDS` is the offline fallback and the place where
each card cites its official announcement. Differences between the two are
reported as warnings, never applied silently.

## Errata

Errata change how a card works but do not affect legality. The current errata
list is published on the official rules page. Any tool that quotes card text
must prefer errata over the printed text.

## Aspect penalty

The aspect penalty is **not** a legality rule.

A deck may include cards whose aspects are not provided by its leader or base.
When such a card is played, the player pays **2 additional resources for each
missing aspect icon**.

A validator must never reject a deck for containing off-aspect cards. It should
report the penalty as a property of the deck (for example, the total penalty if
every card were played at full cost).

## Validator checklist

`validate_deck.py` must check, in this order:

1. exactly one leader and exactly one base;
2. draw deck size >= 50;
3. sideboard size <= 10, with no leaders or bases;
4. at most 3 copies per printed name + subtitle, counting draw deck + sideboard;
5. every card, including sideboard cards, is from a Premier-legal product;
6. no suspended cards;
7. reprints are accepted through name + subtitle matching;
8. aspect penalties are reported, never treated as illegal.

Any deck that passes 1-6 is **legal**, even if it has more than 50 cards, more
than one aspect, or an unusual curve.

## Maintenance

Any change to this file must be reflected in:

- `validate_deck.py` and its tests;
- `SKILL.md` and the skill reference material;
- `docs/metrics.md`, if the change affects a reported metric.

Review this file whenever a set is released, a suspension is announced or a new
Comprehensive Event Guide is published.
