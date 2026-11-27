# Factory spike

A deliberately small software factory for `edIAr-swu-decklab`. It is a spike,
not a platform: one tracked backlog, one worktree per item, one verification
bundle, one review packet, and an **optional** project-specific domain oracle.
There is no orchestrator, no LLM call and no auto-merge.

The design follows the 2026-11-26 council: the bottleneck is domain truth and
review, not code generation. The factory starts with the check bundle, then adds
a worktree and a packet; the project integration adds the human-frozen oracle.

Core vs integration:

- **Core:** CLI, worktree, check, packet, templates, tooling tests and an
  example backlog. It is self-contained.
- **Integration:** the real backlog, the oracle runner and the project-specific
  cases. For this repo, the SWU integration adds `backlog.json`, `oracle.py`
  and `oracle_cases/legality.json`.

New to software factories? Read the illustrated introduction:
[Software Factories 101](docs/software-factories-101.md).

## The loop

```text
tracked backlog
  -> short design (human approves)
  -> worktree from origin/main
  -> failing test first
  -> implementation
  -> check bundle
  -> adversarial oracle
  -> review packet
  -> required CI
  -> human merge
  -> one metrics line
```

WIP is one. A council runs only on a trigger: legality, rules, schema,
cross-cutting, scope, or a failing oracle.

## Quick start

From the control worktree (the one containing `factory/`):

```bash
python3 factory/factory.py list
python3 factory/factory.py show example-path-config
python3 factory/factory.py check
python3 factory/factory.py packet example-path-config
# The oracle requires the project integration:
# python3 factory/factory.py oracle
```

Create an item worktree:

```bash
python3 factory/factory.py new example-path-config --base origin/main
```

That command:

- refuses to start unless the item is `ready` and WIP is 0;
- creates branch `factory/example-path-config` from `origin/main`;
- creates a worktree under `/tmp/opencode/factory-worktrees/example-path-config`
  (override with `FACTORY_WORKTREES` or `--worktree-dir`);
- symlinks `data/` from the control worktree so the real-data tests can run
  (`--no-data-link` to skip);
- marks the item `doing` in the resolved backlog
  (`factory/backlog.json`, `factory/backlog.example.json` or
  `FACTORY_BACKLOG`).

The item worktree is a clean checkout; the factory control plane stays in the
control worktree. Run checks against it with `--worktree`:

```bash
python3 factory/factory.py check --worktree /tmp/opencode/factory-worktrees/example-path-config
python3 factory/factory.py packet example-path-config --worktree /tmp/opencode/factory-worktrees/example-path-config
python3 factory/factory.py status --worktree /tmp/opencode/factory-worktrees/example-path-config
# The oracle requires the project integration:
# python3 factory/factory.py oracle --worktree /tmp/opencode/factory-worktrees/example-path-config
```

## Backlog

The resolved backlog is the only queue. The core ships
`factory/backlog.example.json`; the project integration adds
`factory/backlog.json`; `FACTORY_BACKLOG` can point to a private file. Each item
has:

- `id` (a lowercase slug), optional `legacy_id`, `title`, `status`
  (`ready`, `doing`, `review`, `done`);
- `priority`: `now`, `next`, `later`;
- `risk`: `T0`–`T4` (internal process tier; the CLI shows a process label);
- `data_touch`: `true` when the change touches card or snapshot data;
- `milestone`: `functional-core`, `shareable`, `distributable`,
  `optional-extensions`, or `null`;
- `scope`, `acceptance`, `oracle`, `source`, `notes`.

The field set is intentionally small. If an item needs a second question, split
it. The permanent legacy mapping is in [`docs/legacy-map.md`](docs/legacy-map.md).

## Verification bundle

`check` mirrors the deterministic CI jobs as far as the local environment
allows:

| Check | What it runs |
|---|---|
| `tests` | `python3 -m unittest discover -s skills/swu-review/tests` |
| `data-guard` | `git ls-files data` must be empty |
| `tooling-tests` | `python3 -m unittest discover -s factory/tests` when present |
| `ruff` | `python3 -m ruff check .` if available |
| `mypy-core` | `python3 -m mypy` if available |
| `mypy-scripts` | `python3 -m mypy skills/swu-review/scripts` if available |
| `mypy-factory` | `python3 -m mypy factory/factory.py` if available |
| `links` | local Markdown links resolve (offline approximation of lychee) |

If `ruff` or `mypy` is missing, the check is `SKIP`, not `PASS`. Use
`--strict` to make skips fail. Install the declared tools with:

```bash
python3 -m pip install ".[dev]"
```

`check` does not run the live-data Poggle job. A data-touching change needs a
targeted live run, as [`docs/templates/pr.md`](docs/templates/pr.md) says.

The default check commands target this repo. A generic configuration layer
(`.factory.toml`) is a later step; the current split keeps the mechanism here and
the domain data in the integration.

## Domain oracle (integration)

The core exposes `factory.py oracle` as a hook. The SWU integration adds:

- `factory/oracle.py`, the differential runner;
- `factory/oracle_cases/legality.json`, the adversarial cases;
- the Poggle fixture dependency and the real-data expectations.

The core command returns `2` until that integration is installed:

```bash
python3 factory/factory.py oracle
python3 factory/factory.py oracle --json
```

The SWU integration's first run is expected to be **red**: `leader-count-2` and
`secondleader` currently fail. That is not a core bug; it is the product gap the
oracle exposes.

**The expected values are proposals, not frozen truth.** A human must review and
freeze them before the oracle becomes a merge gate. The runner never regenerates
expected values from the implementation; that would turn the bug into the spec.

## Risk tiers and human gates

| Process label | Tier (internal) | Examples |
|---|---|---|
| quick review | T0 / T1 | docs, typos, tests, tooling |
| council + differential tests | T2 | engine behaviour |
| domain sign-off | T3 | rules, legality, data |
| human-led design | T4 | scope, architecture |

`data_touch: true` adds the data guard and the live case to any tier.

Humans approve the design and the merge. Agents implement, run checks and
assemble evidence. **Agents never merge.** There is no separate autonomy scale
in this spike.

## Metrics

Add one line per item:

```text
date | item | risk | lead_time | review_minutes | ci_first_pass | rework_commits | escaped_defects | cost
```

Success for the first three items: the pilot closes with tests, the domain
oracle (when present) agrees, median issue-to-merge ≤ 2 days, ≤ 2 review rounds,
zero factual corrections, zero stale-doc mismatches. Kill the factory if the
product does not move in two weeks or if the overhead exceeds the time saved.

## Limits of this spike

- The repository's `main` is protected. The factory and its oracle are not part
  of the required checks yet.
- It does not call an LLM, open PRs or merge.
- It does not run the full mutation-testing suite.
- The link check is a local approximation, not lychee.
- The backlog is a file, not GitHub Issues. One queue, deliberately.
- The production version should be smaller than this spike after the loop is
  proven; the council cap is roughly 100 LOC and one tracked document.

## Cleanup

```bash
git worktree remove /tmp/opencode/factory-worktrees/example-1
git branch -D factory/example-1
```

If you ran `new`, restore the resolved backlog status (`git checkout --
factory/backlog.json` in the integration, or edit the example in the core).
