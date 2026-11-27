# SWU integration

This layer adds the project-specific parts on top of the factory core:

- `factory/backlog.json` — the real SWU queue (cleanup, `legality-parity`,
  `suspension-fail-closed`).
- `factory/oracle.py` — the differential runner over `validate_deck` and
  `swu_analyze`.
- `factory/oracle_cases/legality.json` — the adversarial legality cases.
- `factory/tests/test_oracle.py` — tests for the oracle mutations.

The core README and the 101 guide are unchanged. Run the loop from the control
worktree:

```bash
python3 factory/factory.py list
python3 factory/factory.py show legality-parity
python3 factory/factory.py oracle
python3 factory/factory.py packet legality-parity --no-check
```

The current oracle is expected to be **red** on `leader-count-2` and
`secondleader`. That is the product gap `legality-parity` (legacy P0-2)
exposes, not a factory failure.

The expected values are proposals (`frozen_by:
proposed-by-agent-for-human-review`). A human must freeze them before the
oracle becomes a gate.

The oracle uses the Poggle fixture and the real card cache. Do not make it a PR
gate until it uses a synthetic fixture; keep the real-data run in the scheduled
live job.
