# Documentation index

Where each document lives and what it is for. The public documentation set is
tracked; local session notes are gitignored and are not linked from public docs.

## Start here

1. [`../README.md`](../README.md) — project entry point and v0.1 scope summary.
2. [`rules.md`](rules.md) — Premier legality, the source of truth.
3. [`metrics.md`](metrics.md) — every reported number and the draw model.
4. [`data-sources.md`](data-sources.md) — sources, freshness and licensing.
5. [`../skills/swu-review/SKILL.md`](../skills/swu-review/SKILL.md) — the
   agent-facing skill and its commands.

## Source-of-truth map

| Question | Authoritative document |
|---|---|
| What is the v0.1 scope summary? | [`../README.md`](../README.md) |
| Is this deck legal? | [`rules.md`](rules.md) |
| What does this metric mean? | [`metrics.md`](metrics.md) |
| Where does the data come from? | [`data-sources.md`](data-sources.md) |
| How does an agent run the skill? | [`../skills/swu-review/SKILL.md`](../skills/swu-review/SKILL.md) |
| What is next? | [`ROADMAP.md`](ROADMAP.md) |

## Public documentation set

This is the set that must stay self-contained: a tracked document may only link
another tracked document.

| Document | Purpose |
|---|---|
| `README.md` | Project entry point |
| `AGENTS.md` | Agent instructions and PR rules |
| `skills/swu-review/SKILL.md` | Agent-facing contract |
| `skills/swu-review/Council.md` | Strategic protocol |
| `skills/swu-review/reference/findings.md` | Finding registry |
| `docs/README.md` | This index |
| `docs/rules.md` | Legality source of truth |
| `docs/metrics.md` | Metric definitions |
| `docs/data-sources.md` | Data provenance and licensing |
| `docs/ROADMAP.md` | Status and planned work |

## Local working notes

Transient handoffs, session logs, scratch protocols, the detailed scope, the
local defect tracker and the architecture decisions are gitignored. They may link
to public documents, but public documents must not link to them. If one becomes
project documentation, move it into the public set and add it here.

## Documentation rules

- One source of truth per question; link to it instead of restating it.
- `docs/rules.md` wins for legality; `docs/metrics.md` wins for numbers; the
  README states the v0.1 scope summary.
- Every factual claim carries a date or a source.
- Public docs are English; local notes may be Catalan.
- A documentation change travels with the feature it describes.
- A tracked document may not link an untracked or gitignored file.
- Run a link check before publishing (planned for F2a).
