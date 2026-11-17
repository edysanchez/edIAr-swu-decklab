# AGENTS.md

## Autonomy and Confirmations
- When given a task, proceed autonomously through necessary local steps without asking routine confirmation for each individual action.
- External, reversible actions within the explicit scope of the request may be executed without re-prompting.
- Prompt for confirmation only when critical information is missing, an action is irreversible, or system security requires explicit user approval.
- Never attempt to bypass access controls or permission checks; if the harness requests approval, explain briefly what action needs permission.

## Language
- Everything committed to the repository is written in English: documentation (`.md`), code, comments and commit messages. Chat replies follow the user's language.
- Catalan sources that already exist (`data/cardsets/`, `.local/`) are local working files and are gitignored, not project documentation.

## Project
`edIAr-swu-decklab` - Star Wars: Unlimited Premier deck review tools.

## Where to look
- `skills/swu-review/SKILL.md` - the skill: review protocol, commands, flags, snapshots
- `docs/rules.md` - legality rules (source of truth)
- `docs/metrics.md` - metric definitions
- `docs/data-sources.md` - sources, freshness and licensing

## Skill: swu-review
Location: `skills/swu-review/`

For strategic deck reviews, read `skills/swu-review/SKILL.md` first. It holds the
review protocol, the resource model, the accepted deck formats, and every command,
flag and snapshot rule. Do not restate them here: add them there.

### Tests
- Run test suite: `python3 -m unittest discover -s skills/swu-review/tests`

### Notes
- Everything under `data/` is a local cache (gitignored): the card catalogue, the
  suspended list, the legal-set snapshot and prices. The skill works without it,
  falling back to the registries in `scripts/constants.py`; what each snapshot
  means and when it goes stale is documented in `SKILL.md`.
