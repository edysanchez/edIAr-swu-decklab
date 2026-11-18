# Roadmap

The README stays stable; progress lives here. Ordered by dependency, not by
priority: the inputs come first, then the tools that use them, then the case
study and the skill built on top, and polish last.

Status as of 2026-11-17. Priority is functionality first, audience second: v0.1
is F1 (functional core, personal), v0.2 is F2 (robust core, shareable), v1.0 is
F3 (distributable, published), and v1.x is F4 (optional meta). Current blockers
are listed below; the detailed scope and the architecture decision are kept with
the local working records.

## Foundations

- [x] Repository scaffold: license, gitignore, version, README
- [x] `docs/rules.md`: Premier legality, verified against the official rules
- [x] `docs/metrics.md`: definitions for every reported number
- [x] `docs/data-sources.md`: sources, freshness and licensing
- [x] English-only public files: documentation and scripts
- [x] Internal legality review (2026-11-17)

## Core tools

Deck analysis needs only the card database and the decklist. Meta analysis is a
separate, optional layer: it needs a network fetch and a stated window, and a
report is still valid without it.

The engine is Python, standard library only. It lives in
`skills/swu-review/scripts/` with `domain/` and `infrastructure/` packages; the
target layout is defined by the architecture decision.

- [x] `fetch_cards.py`: swu-db `/sets` → `data/`, completeness check, atomic
      write, max age, repair before analysis
- [x] `swu_cards.py`: shared helpers: card database, deck parsing, name +
      subtitle identity, printing lookup, price lookup
- [x] `validate_deck.py`: implements `docs/rules.md`
- [x] `analyze_deck.py`: legacy composition surface; prefer `swu_analyze.py`
      for the full contract
- [x] `analysis.py` + `swu_analyze.py`: deterministic JSON and Markdown report
- [x] `draw_odds.py`: English CLI and round-based draw model (2 cards per
      regroup); decklist only
- [x] `fetch_legal_sets.py` + `legal_sets.py`: dated Premier legal-set list,
      release-date override, freshness warnings
- [x] `fetch_suspended.py` + `suspended_list.py`: dated suspended list,
      registry cross-check, fail-closed parsing
- [x] `search_cards.py`: catalogue query tool for agents and humans
- [ ] `fetch_meta.py`: meta usage with a freshness gate and explicit window
- [ ] `analyze_meta.py`: staple density, innovation, archetype share and
      matchups; consumes `fetch_meta.py` output
- [ ] `verify_citations.py`: checks quoted card text against the card database

## Correctness gate

F1 is done when the core analysis works end to end, the two CLIs agree on the
same deck, the aspect penalty is correct, and the synthetic suite passes on a
clean checkout. The atomic snapshot item below is F2a robustness, the
clean-clone suite is F1, and all of them block a published review:

- [ ] Aspect penalty counts every icon, including duplicates
- [ ] One legality policy/resolver shared by `validate_deck` and `analysis`
- [ ] `secondleader`, slot types, leader/base counts and zone checks
- [ ] Empty suspension snapshot fails closed
- [ ] Displayed printing ordered by release date, not `SET_ORDER`
- [ ] Atomic, validated legality snapshots
- [ ] Clean-clone test suite green (currently 13 errors, 106 skips)

## Case study

The Poggle Blue Endor deck needs a sanitized decklist and reports that match the
current definitions. The deck section is always reported; the meta section only
when a window has data.

- [x] Poggle Blue Endor fixture and golden analysis (contains card text;
      sanitization pending)
- [ ] Sanitized decklist without committed card text or image URLs
- [ ] Regenerate the case reports with the corrected draw model and leader back
      side

## Skill

- [x] `SKILL.md` and the review workflow
- [x] `Council.md`: strategic review protocol
- [x] `reference/findings.md`: finding registry
- [ ] `examples/`: example decklists and expected output
- [ ] `SKILL.md` contract test: commands, flags and schema match the engine

## Quality

- [x] Tests for `swu_cards.py`, `validate_deck.py`, `draw_odds.py`, legal sets,
      suspended lists and the analysis pipeline
- [ ] Hermetic fixtures: synthetic catalogue for pipeline tests
- [ ] CI: tests, schema validation, link check and a check that no card data is
      tracked
- [ ] `install.sh` for OpenCode and Claude Code
- [ ] `pyproject.toml`: project metadata and dev-only test dependencies
      (runtime stays standard library only)
- [ ] Package layout and console scripts per the architecture decision
- [ ] `--version` wired to `VERSION`

## Later

- [ ] Meta analysis and matchup datasets with stated windows
- [ ] Card-text taxonomy (removal, ramp, draw) once the v0.1 limitations are
      closed
- [ ] Historical snapshots for reproducible old reviews

## Feedback follow-ups

- [ ] **README**: quick start (fetch → analyse → validate) and a short example
      report
- [x] **AGENTS.md**: card catalogue is required; only the suspension and
      legal-set registries have fallbacks
- [ ] **Stale data rule**: define when a meta window is stale in
      `docs/data-sources.md` or `docs/metrics.md`
- [x] **Council.md**: linked from `SKILL.md`
- [x] **Data sources**: fixed `data/swudb/` typo and the source count

## Recurring

- [ ] Re-verify `docs/rules.md` at every set release, suspension or new
      Comprehensive Event Guide
- [ ] Re-run `fetch_legal_sets.py` and `fetch_suspended.py` before a published
      review
