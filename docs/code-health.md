# Code health follow-ups

Tracking list for defects and structural debt found while reviewing the
`swu-review` skill. Ordered by risk, not by effort. Each entry records the
symptom, the evidence and what "done" means, so the next session can start
without rebuilding the context.

Last reviewed: 2026-11-16.

## Fixed

### Aspect penalty was always 0 — `e046ff8`

`legality.aspect_penalty` reported `{"total": 0, "max": 0, "per_card": []}` for
every deck, including decks with off-aspect cards.

Four defects, each of which alone would have been enough:

| # | Where | What |
|---|---|---|
| 1 | `analysis.py` `build_analysis` | created `InMemoryCardRepository()` with no cards |
| 2 | `analysis.py` `_aspect_penalty` | read the leader/base key from `card["identity"]`, a field the card dicts do not have |
| 3 | `card_db` ↔ repository | `main_counts` keys are `(name, subtitle)` tuples, the repository was keyed by `"name\|subtitle"` strings, so `get()` missed and returned `[]` |
| 4 | `AspectPenaltyService` | emitted `per_card[].identity` as a tuple, which JSON renders as an array and `analysis.schema.json` forbids |

The regression test is `tests/test_aspect_penalty_integration.py` (one off-aspect
card: Adept ARC-170 under Poggle, 2 per copy). It failed before the fix and
passes after, without changes. The calculation itself now has unit coverage in
`tests/test_aspect_penalty_service.py` (8 tests, in-memory repository, no file
I/O), so the service can be tested in isolation and the adapter/wiring is
covered separately.

Root cause worth remembering: an unknown card and a card without aspects were
indistinguishable, so a wrong repository looked like a legitimate zero.

## In progress

### Dynamic legal-set check (branch `dynamic-legal-set-check`) — medium

The feature now exists in three layers and is tested, but the pipeline still
reads `constants.PREMIER_SETS` directly, so the branch name is not honoured yet.

- Done: `infrastructure/legal_sets_snapshot.py` (read + fail-closed shape
  checks), `domain/legal_set_policy.py` (pure rule, lag window only),
  `scripts/legal_sets.py` (precedence, freshness, warnings) and
  `scripts/fetch_legal_sets.py` (hub page → dated snapshot; 7 legal sets and 11
  products parsed from the live page).
- Done: four freshness/failure rules — 14-day TTL, announced change already due,
  product available but unlisted, and an empty `legal` list is treated as
  corrupt instead of "nothing is legal".
- Done: wired into `analysis._legality` and `validate_deck`; both read the
  snapshot, apply the lag window and surface its warnings.
- Done: `infrastructure/legality_cache.py` deleted; it was superseded and
  never imported.
- Done: warns when the legal list names a set the card database has no cards
  from (the IC27 case), naming the sets and `fetch_cards.py`.
- Pending: the reprint rule (see the identity-collisions item below).

## Open

> Ordered by risk, not by number. Items 8-10 come from the Poggle Blue Endor
> review of 2026-11-16 (see `review-log.md`); their risk is in the heading.

### 1. Card database ingestion: every product — mostly done

`fetch_cards.py` no longer hardcodes seven sets. The list comes from `/sets`,
every payload is checked against `numberCards` before being stored, and the
normalised catalogue is derived from the raw per-set files in a fixed order.

Shipped: base sets by default (`--all` for promos), a short payload refused
instead of half-written, incremental downloads, atomic writes, legacy caches
measured, incomplete sets retried after six hours, CLI repair with `--no-fetch`,
11 of 12 base sets complete (2,445 cards, including rotated SOR/SHD/TWI/TS26),
and fixtures regenerated.

Remaining:

- **Displayed printing.** A card printed in several sets keeps the record of the
  last set in `SET_ORDER`, which is arbitrary for a reader. Keeping the original
  printing would be more useful; either way the rule must be explicit and tested.
- **Promos.** The 39 promo sets are not fetched by default. They add printings
  but no new identities, so this is a choice, not a gap.
- **Discovery.** `catalogue.json` is written by `fetch_cards.py` only, so a new
  product enters the picture when that runs. The analysis CLIs repair gaps; they
  do not discover sets. That is deliberate and worth keeping.

### 2. `analysis.py` is still a procedural module — medium

`build_analysis` plays the role of the application service but is a 1,000-line
function that loads the database, resolves cards, runs six steps and shapes the
output. Only the aspect-penalty step goes through the repository pattern;
`_legality`, `_composition`, `_findings`, `_draw_odds` and `_db_meta` all take
the raw `card_db` dict (40 mentions, 14 direct `card_db[key]`).

Half-applying the pattern is worse than not applying it: two access paths to the
same data is how defect 3 above stayed invisible.

**Done means:** `DeckAnalysisService(card_repository)` owns the use case, the
five helpers take `cards: CardRepository` instead of the dict, `_db_meta`
(provenance: `meta.json`, `schema_hash`) moves to the infrastructure layer, and
`swu_analyze.py` is the only place that builds `CardDBRepository(load_swu_cards())`.

**Safety net:** `test_poggle_golden` pins the JSON contract, so the refactor can
be verified byte-for-byte.

### 3. Suspended-list warnings pollute `legality.warnings` — low

`analysis.py` passes `suspended_list.load(card_db).warnings` into
`legality.warnings`, so every report without a local snapshot opens with
"Run fetch_suspended.py to refresh it", even though `constants.SUSPENDED_CARDS`
is the authoritative fallback. Data freshness is not a legality warning.

**Done means:** the missing/old snapshot message is reported as provenance
(`db.suspended`) or only in verbose CLI output; genuine registry/snapshot
disagreements keep their warning.

Related: `SUSPENDED_SNAPSHOT_PATH` is resolved against the current directory, so
running the CLI from anywhere but the repository root silently falls back to the
registry (plus the warning above).

### 4. Dead fixtures and debug scripts — low

- `tests/fixtures/repositories.py` imports `infrastructure.in_memory_repository`,
  a module that does not exist (the real one is `in_memory_card_repository`).
  Nothing imports the fixture, so the suite never notices. It is also redundant
  now: the aspect-penalty unit tests build their own `InMemoryCardRepository`
  inline.
- `scripts/test_import.py` is a debugging script with an absolute
  `/home/edy/...` path; `scripts/test_formats.py` is not a `unittest` module, so
  `unittest discover` never runs it.

**Done means:** the fixture is fixed or removed; debug scripts leave the tree;
anything worth keeping moves to `tests/` as a real test.

### 5. Card database identity collisions — low, needs a check

`fetch_cards.py` keys cards by `name + subtitle`, so raw API rows collapse onto
one entry per identity. Seven identities are printed in more than one set and now
carry `printings` (`Pounce` in LOF and HMW, the Endor base in JTL and HMW, ...).

`CardIndex.by_set_number` and `test_every_suspended_card_is_in_the_card_database`
still assume the surviving `set`/`number` are the ones a deck references.

**Done means:** confirm that none of the five suspended cards is affected, and
decide the displayed printing (see item 1).

### 6. Session notes in the working tree — low

`CODE_ANALYSIS.md`, `CODE_ANALYSIS_SUMMARY.md`, `COUNCIL-analyze-steps.md` and
`git-config-edy-evo14a8.txt` kept appearing as untracked files at the root. They
are session material, not project documentation, so `.gitignore` now covers them
(`CODE_ANALYSIS*.md`, `COUNCIL-*.md`, `git-config-*.txt`): they stay on disk and
never show up in `git status`. This file is the canonical tracking list; if a
note here needs more detail, add it here.

**Done means:** untracked session notes never pollute `git status`, and the
`git config` dump is deleted rather than archived.

### 7. Test directory structure — low

`tests/` is flat: unit, integration and golden tests sit side by side, and the
layer split introduced with the aspect-penalty tests relies on a filename suffix
(`test_aspect_penalty_service.py` vs `test_aspect_penalty_integration.py`).

- `tests/fixtures/` mixes data (`poggle-blue-endor/`, `competitivehub/`) with a
  Python module (`repositories.py`).
- No `__init__.py` anywhere: test modules are top-level, so imports and
  discovery depend on how the suite is invoked.
- Most test files repeat the same `sys.path.insert` block; the ones that need
  `infrastructure/` and `domain/` insert a second path.
- `scripts/test_formats.py` and `scripts/test_import.py` live outside `tests/`.

**Done means:** unit and integration tests are separated by location or marker,
`tests/fixtures/` holds data only, one shared helper sets the import path once,
and `python3 -m unittest discover -s skills/swu-review/tests` still finds every
test.

### 8. Card sheets hide the leader's unit side — **high, P0**

`fetch_cards.py::normalize_cards()` copies `FrontText` only, so
`cards_normalized.json` has no `backText`. `analysis.schema.json` knows
`double_sided` but has no field for the other face, and
`render_report.py::_card_sheet()` renders a single text block.

Evidence: Poggle the Lesser (HMW012) prints `Action [1 resource, Exhaust]: ready
a friendly Creature unit and deal 1 damage to it` on the leader side, and
`When Deployed: create a Beast token` / `On Attack: you may ready a friendly
Creature unit and deal 1 damage to it` on the unit side. The report for the
Poggle Blue Endor case study shows only the first, and a full strategic review
was built on the wrong engine as a result.

The text is not lost upstream: `data/swudb/HMW.json` carries `BackText`.

**Done means:** `normalize_cards()` stores `backText`; `$defs.card` in the
schema gains `back_text` and `back_text_status`; `analysis.py::_sheet()` emits
them for `double_sided` cards; `render_report.py::_card_sheet()` prints a
`Back side` heading with the same missing-text treatment;
`tests/fixtures/poggle-blue-endor/{analysis.json,report.md}` are regenerated;
and a test asserts `back_text` is non-empty for a known double-sided leader and
`null` for a single-sided card.

### 9. The report is under-informative for a strategic review — medium

The pipeline answers legality and composition well, but three omissions force a
reviewer to rebuild data by hand. None of them is a wrong number; all of them are
missing ones.

- **No trait split.** Nothing says how many slots carry `CREATURE`, so abilities
  that read "friendly Creature unit" — ready, sacrifice, damage — cannot be
  sized without opening every card sheet. In the case study 30 of 50 slots are
  Creatures and 9 are units that are not (EWOK, UNDERWORLD, TROOPER).
- **No round legend.** Draw odds are tabulated as `R0..R6` and the report never
  states that `R0` is the opening hand, nor that round *n* starts with *n+1*
  resources and *6 + 2(n-1)* cards seen. Play lines indexed off by one round
  followed from that.
- **No missing-text summary.** `Filthy Dianoga` (HMW155) and the base (HMW022)
  have an empty `FrontText` upstream. The card sheet says so per card, but the
  data-health line at the top does not, which hid a 3-of.

Two of the requests that came out of the same review are **design decisions, not
defects**, and are not recorded here: sideboard card sheets (the pipeline
declares `sideboard-legal-only` on purpose) and a leader-engine block (text
semantics are out of scope for v0.1). Both belong in `docs/ROADMAP.md`.

**Done means:** `docs/metrics.md` defines the trait metric before it is reported;
`composition.traits` and `composition.creature_slots` exist; the report prints a
`Creature n/N` row and a round / resources / cards-seen legend above the draw-odds
tables; the data-health line lists the identities with `text_status: "missing"`.

### 10. Duplicated aspect icons may be undercharged — low, needs a check

`AspectPenaltyService.calculate_penalty()` compares aspects with a `set`
(`provided: Set[str]`), so a card printed with two icons of the same aspect pays
0 when the leader or base provides that aspect once.

Example: `Dume — Redeem the Future` prints `Vigilance, Vigilance`, and the local
tool reports penalty 0.

This is **not verified against the Comprehensive Rules**. The set-based behaviour
may be exactly right; do not change it before checking.

**Done means:** `docs/rules.md` states how duplicated icons are matched, a test
encodes that rule, and — only if icons are matched one-to-one — the service
switches to a multiset comparison and the affected fixture is regenerated.
