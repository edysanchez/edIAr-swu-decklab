# AGENTS.md

## Autonomy and Confirmations
- When given a task, proceed autonomously through necessary local steps without asking routine confirmation for each individual action.
- External, reversible actions within the explicit scope of the request may be executed without re-prompting.
- Prompt for confirmation only when critical information is missing, an action is irreversible, or system security requires explicit user approval.
- Never attempt to bypass access controls or permission checks; if the harness requests approval, explain briefly what action needs permission.

## Project
`edIAr-swu-decklab` - Star Wars: Unlimited Premier deck review tools.

## Skill: swu-review
Location: `skills/swu-review/`
For strategic deck reviews, always read `skills/swu-review/SKILL.md` first. It contains the full review protocol, resource model, play lines guidance, substitution analysis, and council rules.

### Commands
- Full analysis & report (recommended): `python3 skills/swu-review/scripts/swu_analyze.py <deck> --json out.json --report out.md`
- Fetch card DB: `python3 skills/swu-review/scripts/fetch_cards.py`
- Validate deck (standalone): `python3 skills/swu-review/scripts/validate_deck.py <deck.json|deck.txt>`
- Analyze composition (standalone): `python3 skills/swu-review/scripts/analyze_deck.py <deck.json|deck.txt>`
- Draw odds (standalone): `python3 skills/swu-review/scripts/draw_odds.py <deck.json|deck.txt>`

### Tests
- Run test suite: `python3 -m unittest discover -s skills/swu-review/tests`

### Notes
- Card DB is cached in `data/swudb/` (gitignored). If missing, run `fetch_cards.py` first.
- Rules are in `docs/rules.md` (source of truth).
- Metrics in `docs/metrics.md` (draw model: +2 per regroup, leader/base not drawn).
- Resource model: a game starts with 2 prepared resources (+1 per regroup). First action phase is 2 resources, not 1.
- Supports SWUDB JSON, SWUDB text, case format (`mainDeck`/`sideboard`), and ID-based exports.
- Card identity is `name + subtitle`. Aspect penalty is reported but never blocks legality.
