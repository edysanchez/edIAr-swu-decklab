# Findings registry

A **finding** is a deterministic observation about the deck that crosses a
documented threshold. It is not a recommendation, a grade, or a meta claim.

Rules:

1. Every finding emitted by `analysis.py` must have a row in this file.
2. Adding a rule requires a written rationale and a regression test.
3. A finding without a threshold is not a finding. Do not add "interesting"
   observations here.
4. Findings are suppressed when the data is incomplete (unresolved cards,
   copies not summing to `N`). Missing data is reported in `limitations[]`,
   never as a finding.
5. Severity is `info` or `warning`. `critical` is reserved for legality errors.

## Registry

| id | metric path | operator | threshold | severity | since | rationale |
|---|---|---|---|---|---|---|
| `arena-imbalance` | `composition.arenas.space_pct` | `<` | `15` (% of unit slots) | `warning` | 0.1.0 | A deck whose unit base is almost entirely Ground has no answer to Space units in the other arena. 15% is the floor used by the Poggle case study; it is a convention, not a rule of the game. |
| `price-coverage` | `composition.price.coverage_pct` | `<` | `100` (% of main-deck slots) | `warning` | 0.1.0 | A total that excludes unpriced cards is not a deck price. Below 100% coverage the total is a lower bound and must be labelled as such. |

## Evidence contract

Every emitted finding carries:

```json
{
  "id": "arena-imbalance",
  "severity": "warning",
  "category": "composition",
  "statement": "Only 2 of 39 unit slots are Space (5.1%).",
  "evidence": {
    "metric_path": "composition.arenas.space",
    "value": 2,
    "denominator": 39,
    "pct": 5.1,
    "threshold": { "op": "<", "value": 15, "unit": "pct_of_unit_slots" },
    "cards": [{ "identity": "…", "copies": 2 }]
  },
  "source": {
    "kind": "threshold",
    "registry": "reference/findings.md#arena-imbalance",
    "version": "1"
  }
}
```

`evidence.cards` is mandatory for any finding that can name the cards involved.
It is what makes the finding auditable: a reader can recompute the number from
the card list.

## Deliberately excluded

These are out of scope until a taxonomy exists:

- "no card draw" and "scarce removal" — they require interpreting card text,
  which is not deterministic with the current data model;
- any overall deck grade or score;
- meta, matchups, cuts/adds, scenarios and play lines.
