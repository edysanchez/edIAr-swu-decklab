# Vocabulary

The backlog and the CLI use plain-language values. The old codes are **not
aliases**: they were removed from the backlog. This page is only for translating
old notes, historical metrics and documents that still use the old vocabulary.

## Priority

| Old | New | Meaning |
|---|---|---|
| P0 | `now` | Do first; the current blocker |
| P1 | `next` | Important, after the current item |
| P2 | `later` | Can wait; structural debt or polish |

`P0-1`, `P0-2`, `P1-3` in `code-health.md` are **defect IDs**, not backlog
priorities. They remain historical headings.

## Risk / process

| Old | New label | Meaning |
|---|---|---|
| T0 | quick review | Docs or typo; CI + quick human review |
| T1 | quick review | Tests or tooling; CI + human review |
| T2 | council + differential tests | Engine behaviour; TDD, differential tests, council |
| T3 | domain sign-off | Rules, legality or data; frozen oracle + human sign-off |
| T4 | human-led design | Scope or architecture; humans lead |

`data_touch: true` adds the data guard and the live case to any tier.

## Milestones

| Old | New | Meaning |
|---|---|---|
| F1 | `functional-core` | One real review works end to end |
| F2 | `shareable` | A clean clone works; failures are explicit |
| F3 | `distributable` | A stranger can install and use it |
| F4 | `optional-extensions` | Meta, matchups, citation checks |

`null` means the item does not belong to a product milestone.

## Item IDs

Item IDs are lowercase noun slugs: `legality-parity`,
`suspension-fail-closed`, `typing-analysis`, `example-path-config`.

There are no legacy ID aliases. Old IDs remain only in git history, old metrics
lines and historical documents; `factory.py` does not resolve them.
