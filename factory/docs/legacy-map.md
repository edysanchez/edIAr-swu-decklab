# Legacy map

The factory now uses plain-language values in the backlog and the CLI. This
page is the permanent mapping for old IDs, historical metrics and notes that
still use the old vocabulary.

It is a reference, not a second vocabulary: new items use the plain values only.

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

| Old | New |
|---|---|
| `P0-2` | `legality-parity` |
| `P0-3` | `suspension-fail-closed` |
| `CLEAN-B2` | `typing-resolver-cardmarket` |
| `CLEAN-B3A` | `typing-analysis` |
| `CLEAN-B3B` | `typing-render-report` |
| `CLEAN-B3C` | `typing-clis-fetchers` |
| `CLEAN-ANY` | `enable-disallow-any-explicit` |
| `DOC-FACTORY` | `factory-docs` |
| `EXAMPLE-1` | `example-path-config` |

Old IDs resolve through `legacy_id`. Historical metrics lines keep the old ID;
new lines use the new ID.
