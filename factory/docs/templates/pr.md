# <ID> — <title>

## What changed

- One paragraph, one question.

## Why

Link the backlog item and the problem it solves.

## Verification

- [ ] `python3 factory/factory.py check --worktree <path>`
- [ ] `python3 factory/factory.py oracle --worktree <path>`
- [ ] Poggle or the relevant live-data case, if the change touches data.
- [ ] No new skips, no tracked card data.

```text
<paste the check table>
```

## Evidence

- Test that fails before the fix:
- Test that passes after the fix:
- Differential cases:
- Oracle rows:

## Risks and limitations

- What this change does not cover.
- Any skip or exclusion, with a reason.

## Council

- Triggered: yes/no
- Lenses:
- Consensus:
- Dissent:
- Open questions:

## Human gates

- [ ] Scope/design approved.
- [ ] Expected values frozen by a human.
- [ ] CI required checks green.
- [ ] Merge by a human; no auto-merge.
