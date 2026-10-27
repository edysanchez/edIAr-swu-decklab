# Roadmap

The README stays stable; progress lives here.

Ordered by dependency, not by priority: the inputs come first, then the tools
that use them, then the case study and the skill built on top, and polish last.
Anything not listed here is not planned yet.

## Foundations

- [x] Repository scaffold: license, gitignore, version, README
- [x] `docs/rules.md`: Premier legality, verified against the official rules
- [x] `docs/metrics.md`: definitions for every reported number
- [x] `docs/data-sources.md`: sources, freshness and licensing
- [ ] English-only public files: the case notes and the scripts still contain
      Catalan

## Core tools

Deck analysis needs only the card database and the decklist. Meta analysis is a
separate, optional layer: it needs a network fetch and a stated window, and a
report is still valid without it.

All scripts are flat files in one folder and share `swu_cards.py`; there is no
package to install.

- [ ] `fetch_cards.py`: SWUForge -> `data/`, atomic write, max age
- [ ] `swu_cards.py`: shared helpers: card database, deck parsing, name +
      subtitle identity, price lookup
- [ ] `validate_deck.py`: implements `docs/rules.md`
- [ ] `analyze_deck.py`: composition, aspect penalty and price; card database
      only, no meta
- [ ] `draw_odds.py`: English CLI and round-based draw model (2 cards per
      regroup); decklist only
- [ ] `fetch_meta.py`: meta usage with a freshness gate and explicit window
- [ ] `analyze_meta.py`: staple density, innovation, archetype share and
      matchups; consumes `fetch_meta.py` output

## Case study

The Poggle Blue Endor deck needs a sanitized decklist and reports that match the
current definitions. The deck section is always reported; the meta section only
when a window has data.

- [ ] Poggle Blue Endor case study, with a sanitized decklist
- [ ] Regenerate the case reports with the corrected draw model

## Skill

- [ ] `SKILL.md` and the review workflow
- [ ] `reference/`: review rubric, deckbuilding guidance, legality summary
- [ ] `examples/`: example decklists and expected output

## Quality

- [ ] Tests for `swu_cards.py`, `validate_deck.py` and `draw_odds.py`
- [ ] CI: tests, link check and a check that no card data is tracked
- [ ] `install.sh` for OpenCode and Claude Code
- [ ] `pyproject.toml`: project metadata and dev-only test dependencies
      (runtime stays standard library only)

## Later

- [ ] `verify_citations.py`: checks quoted card text against the card database

## Feedback follow-ups

- [ ] **README**: explain how to generate local card data (`data/`) and add a
      short example of a report output
- [ ] **Stale data rule**: define when a meta window is considered stale (e.g.
      warn if the latest window is older than X days) in `docs/data-sources.md`
      or `docs/metrics.md`
- [ ] **Skill skeleton**: create a minimal `skills/swu-review/SKEKYL.md` with
      the review flow, even if partial

## Recurring

- [ ] Re-verify `docs/rules.md` at every set release, suspension or new
      Comprehensive Event Guide
