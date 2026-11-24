# CI and local checks

The repository uses GitHub Actions. The pipeline is split by failure surface so
that only deterministic, offline checks can become required.

## Workflows

| Workflow | Trigger | Gate | What it does |
|---|---|---|---|
| `tests` | push to `main`, PR to `main` | Required | Data-free `unittest` suite, coverage report, no tracked card data |
| `quality` | push to `main`, PR to `main` | Ruff required; mypy required for `domain/` + `infrastructure/`; mypy on `scripts/` advisory | Lint and type checks |
| `docs` | PR to `main`; weekly schedule; manual | Local links on PR; external links on schedule | Markdown link check |
| `live-data` | Weekly schedule; manual | Never a PR gate | Fetch the real catalogue and run the Poggle contract test |

The scheduled `live-data` job needs network access and writes to the gitignored
`data/swudb/` directory. It is deliberately not part of the PR checks.

## Local commands

Install the dev tools from the single declaration:

```bash
python3 -m pip install ".[dev]"
```

Run the data-free suite and the coverage report:

```bash
python3 -m coverage run -m unittest discover -s skills/swu-review/tests
python3 -m coverage report -m
```

Run the checks that gate a PR:

```bash
python3 -m ruff check .
python3 -m mypy
```

`python3 -m mypy` checks `skills/swu-review/domain/` and
`skills/swu-review/infrastructure/`. The scripts are checked separately and are
advisory while their baseline is reduced:

```bash
python3 -m mypy skills/swu-review/scripts
```

Run the live-data path manually only when you need it:

```bash
python3 skills/swu-review/scripts/fetch_cards.py
python3 -m unittest discover -s skills/swu-review/tests -p 'test_poggle_golden.py' -v
```

## Baselines

At the time this pipeline was added:

- **Tests:** 84 tests, 13 Poggle skips without `data/`.
- **Coverage:** about 53% with the synthetic suite; no threshold is enforced.
- **Ruff:** clean with `E4`, `E7`, `E9` and `F`.
- **mypy:** clean on `domain/` and `infrastructure/`; the scripts still have a
  known error baseline and are advisory.
- **Links:** all tracked Markdown local links resolve.

Do not turn these baselines into thresholds until they have been stable for a
few changes. Coverage is a visibility tool, not a target.

## Required checks

After the pipeline lands on `main`, enable branch protection for `main` and
require the deterministic checks:

- `test`
- `ruff`
- `mypy`
- `local-links` (once it has run green at least once)

Do **not** require `live-data` or `external-links`. They depend on the network
and would make unrelated PRs fail.

## Dependency updates

Dev tools are pinned in `pyproject.toml`. Dependabot opens weekly update PRs for
GitHub Actions and Python dependencies. The workflow files use the current
action majors (`actions/checkout@v7`, `actions/setup-python@v7`).

## Not in the pipeline yet

- `ruff format --check` — needs a dedicated formatting commit first.
- Blocking mypy on `scripts/` — the baseline is not clean yet.
- A coverage threshold — the suite still skips the real-data contract.
- Live data on pull requests — the card API is an external dependency.
- `pre-commit` — optional local convenience after the CI checks are stable.
