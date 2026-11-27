#!/usr/bin/env python3
"""Tiny software-factory CLI for edIAr-swu-decklab.

This is a spike. It implements the smallest useful loop:

    tracked backlog -> worktree -> failing test -> verification -> packet -> human merge

There is no orchestrator, no LLM call and no auto-merge. The control plane stays
in the source worktree; item worktrees are clean checkouts for product changes.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
FACTORY_DIR = ROOT / "factory"
ORACLE_CASES = FACTORY_DIR / "oracle_cases" / "legality.json"
DEFAULT_WORKTREES = Path(
    os.environ.get("FACTORY_WORKTREES", "/tmp/opencode/factory-worktrees")
)
RISKS = ("T0", "T1", "T2", "T3", "T4")
STATUSES = ("ready", "doing", "review", "done")
PRIORITIES = {"now": 0, "next": 1, "later": 2}
MILESTONES = {
    "functional-core": "functional core (F1)",
    "shareable": "shareable (F2)",
    "distributable": "distributable (F3)",
    "optional-extensions": "optional extensions (F4)",
}
GATES: dict[str, dict[str, object]] = {
    "T0": {"label": "quick review"},
    "T1": {"label": "quick review"},
    "T2": {"label": "council + differential tests", "council": True},
    "T3": {
        "label": "domain sign-off",
        "council": True,
        "oracle": True,
        "signoff": True,
    },
    "T4": {"label": "human-led design", "council": True, "signoff": True},
}
ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LEGACY_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]*$")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


# ---------------------------------------------------------------------------
# backlog
# ---------------------------------------------------------------------------


def backlog_path() -> Path:
    """Resolve the queue.

    Priority:
    1. FACTORY_BACKLOG, for a private or alternate queue.
    2. factory/backlog.json, the project integration.
    3. factory/backlog.example.json, the public core example.
    """
    env = os.environ.get("FACTORY_BACKLOG")
    if env:
        return Path(env).expanduser()
    local = FACTORY_DIR / "backlog.json"
    if local.exists():
        return local
    return FACTORY_DIR / "backlog.example.json"


def validate_backlog(data: object, name: str = "backlog") -> dict[str, Any]:
    if not isinstance(data, dict):
        raise SystemExit(f"{name}: top-level object required")
    payload = cast(dict[str, Any], data)
    items = payload.get("items")
    if not isinstance(items, list):
        raise SystemExit(f"{name}: 'items' must be a list")
    wip_limit = payload.get("wip_limit", 1)
    if isinstance(wip_limit, bool) or not isinstance(wip_limit, int) or wip_limit < 1:
        raise SystemExit(f"{name}: wip_limit must be an integer >= 1")
    seen: dict[str, str] = {}
    for index, raw_item in enumerate(items):
        if not isinstance(raw_item, dict):
            raise SystemExit(f"{name}: item {index} must be an object")
        item = cast(dict[str, Any], raw_item)
        item_id = item.get("id")
        if not isinstance(item_id, str) or not ID_RE.fullmatch(item_id):
            raise SystemExit(f"{name}: invalid id at item {index}: {item_id!r}")
        legacy_id = item.get("legacy_id")
        if legacy_id is not None:
            if not isinstance(legacy_id, str) or not LEGACY_ID_RE.fullmatch(legacy_id):
                raise SystemExit(
                    f"{name}: invalid legacy_id for {item_id}: {legacy_id!r}"
                )
        for alias in (item_id, legacy_id):
            if not alias:
                continue
            key = alias.lower()
            if key in seen:
                raise SystemExit(
                    f"{name}: duplicate id/alias {alias!r} (also {seen[key]})"
                )
            seen[key] = item_id
        if not isinstance(item.get("title"), str) or not item["title"].strip():
            raise SystemExit(f"{name}: {item_id} needs a non-empty title")
        if item.get("status") not in STATUSES:
            raise SystemExit(
                f"{name}: {item_id} has invalid status {item.get('status')!r}"
            )
        if item.get("priority") not in PRIORITIES:
            raise SystemExit(
                f"{name}: {item_id} has invalid priority {item.get('priority')!r}"
            )
        if item.get("risk") not in RISKS:
            raise SystemExit(f"{name}: {item_id} has invalid risk {item.get('risk')!r}")
        milestone = item.get("milestone")
        if milestone is not None and milestone not in MILESTONES:
            raise SystemExit(
                f"{name}: {item_id} has invalid milestone {milestone!r}"
            )
        data_touch = item.get("data_touch", False)
        if not isinstance(data_touch, bool):
            raise SystemExit(f"{name}: {item_id} data_touch must be a boolean")
        for field in ("acceptance", "oracle"):
            value = item.get(field, [])
            if not isinstance(value, list) or not all(
                isinstance(entry, str) for entry in value
            ):
                raise SystemExit(f"{name}: {item_id} {field} must be a list of strings")
        for field in ("scope", "source", "notes"):
            value = item.get(field)
            if value is not None and not isinstance(value, str):
                raise SystemExit(f"{name}: {item_id} {field} must be a string")
    return payload


def backlog_warnings(data: dict[str, Any]) -> list[str]:
    warnings = []
    for item in data["items"]:
        if (
            item.get("risk") == "T3"
            and item.get("status") == "ready"
            and not item.get("oracle")
        ):
            warnings.append(f"{item['id']}: T3 ready without oracle cases")
    return warnings


def load_backlog() -> dict[str, Any]:
    path = backlog_path()
    if not path.exists():
        raise SystemExit(f"backlog not found: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"{path}: cannot read backlog: {exc}") from exc
    data = validate_backlog(raw, path.name)
    for warning in backlog_warnings(data):
        print(f"warning: {warning}", file=sys.stderr)
    return data


def save_backlog(data: dict[str, Any]) -> None:
    path = backlog_path()
    target = path.resolve() if path.is_symlink() else path
    try:
        mode = target.stat().st_mode & 0o777 if target.exists() else 0o644
        with tempfile.NamedTemporaryFile(
            "w",
            dir=target.parent,
            prefix=f".{target.name}.",
            delete=False,
            encoding="utf-8",
        ) as handle:
            handle.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
            tmp = Path(handle.name)
        os.chmod(tmp, mode)
        os.replace(tmp, target)
    except OSError as exc:
        raise SystemExit(f"{path}: cannot save backlog: {exc}") from exc


def find_item(data: dict[str, Any], item_id: str) -> dict[str, Any]:
    items = data["items"]
    for item in items:
        if item["id"] == item_id or item.get("legacy_id") == item_id:
            return cast(dict[str, Any], item)
    lowered = item_id.lower()
    for item in items:
        if item["id"].lower() == lowered:
            return cast(dict[str, Any], item)
        legacy = item.get("legacy_id")
        if isinstance(legacy, str) and legacy.lower() == lowered:
            return cast(dict[str, Any], item)
    raise SystemExit(f"unknown item: {item_id}")


def wip_items(data: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in data["items"] if item.get("status") == "doing"]


def process_label(item: dict[str, Any]) -> str:
    risk = str(item.get("risk", ""))
    label = str(GATES.get(risk, {}).get("label", "unknown"))
    text = f"{label} ({risk})"
    if item.get("data_touch"):
        text += " + data"
    return text


def milestone_label(item: dict[str, Any]) -> str:
    milestone = item.get("milestone")
    return MILESTONES.get(milestone, "—") if milestone else "—"


def render_list(data: dict[str, Any], show_all: bool = False) -> str:
    items = data["items"]
    if not show_all:
        items = [item for item in items if item.get("status") == "ready"]
    ordered = sorted(
        items,
        key=lambda item: (PRIORITIES.get(item.get("priority"), 99), item["id"]),
    )
    headers = ["ID", "STATUS", "PRIORITY", "PROCESS", "MILESTONE", "TITLE"]
    rows = [
        [
            item["id"],
            str(item.get("status", "")),
            str(item.get("priority", "")),
            process_label(item),
            milestone_label(item),
            str(item.get("title", "")),
        ]
        for item in ordered
    ]
    widths = [
        max([len(headers[column])] + [len(row[column]) for row in rows])
        for column in range(5)
    ]
    lines = [
        "  ".join(headers[column].ljust(widths[column]) for column in range(5))
        + "  "
        + headers[5]
    ]
    for row in rows:
        lines.append(
            "  ".join(row[column].ljust(widths[column]) for column in range(5))
            + "  "
            + row[5]
        )
    wip = wip_items(data)
    lines += ["", f"WIP: {len(wip)}/{data.get('wip_limit', 1)}"]
    return "\n".join(lines)


def render_item(item: dict[str, Any]) -> str:
    lines = [
        f"## {item['id']} — {item['title']}",
        "",
        f"- Status: {item.get('status')}",
        f"- Priority: {item.get('priority')}",
        f"- Process: {process_label(item)}",
        f"- Milestone: {milestone_label(item)}",
    ]
    if item.get("data_touch"):
        lines.append("- Data: yes")
    if item.get("legacy_id"):
        lines.append(f"- Legacy ID: {item['legacy_id']}")
    lines += [
        f"- Source: {item.get('source', '—')}",
        "",
        "### Scope",
        "",
        str(item.get("scope", "—")),
        "",
        "### Acceptance",
        "",
    ]
    for entry in item.get("acceptance", []):
        lines.append(f"- [ ] {entry}")
    oracle = item.get("oracle", [])
    if oracle:
        lines += ["", "### Oracle cases", ""]
        lines += [f"- `{case}`" for case in oracle]
    if item.get("notes"):
        lines += ["", "### Notes", "", str(item["notes"])]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------


def run(cmd: list[str], cwd: Path = ROOT, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, timeout=timeout)


def git_output(args: list[str], cwd: Path) -> str | None:
    proc = run(["git", *args], cwd=cwd)
    return proc.stdout.strip() if proc.returncode == 0 else None


def resolve_worktree(value: str | None) -> Path:
    return Path(value).resolve() if value else ROOT


def require_worktree(cwd: Path) -> None:
    """Fail closed unless cwd is a git worktree root."""
    if not cwd.is_dir():
        raise SystemExit(f"not a directory: {cwd}")
    proc = run(["git", "-C", str(cwd), "rev-parse", "--show-toplevel"], cwd=cwd)
    if proc.returncode != 0:
        raise SystemExit(f"not a git worktree: {cwd}")
    top = Path(proc.stdout.strip()).resolve()
    if top != cwd.resolve():
        raise SystemExit(f"not a worktree root: {cwd} (root: {top})")


def module_available(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except ModuleNotFoundError:
        return False


def run_check(
    name: str, cmd: list[str], cwd: Path, timeout: int = 300
) -> dict[str, Any]:
    try:
        proc = run(cmd, cwd=cwd, timeout=timeout)
    except FileNotFoundError:
        return {"name": name, "status": "SKIP", "detail": "command not found", "output": ""}
    except subprocess.TimeoutExpired:
        return {"name": name, "status": "FAIL", "detail": "timeout", "output": ""}
    output = (proc.stdout + "\n" + proc.stderr).strip()
    return {
        "name": name,
        "status": "PASS" if proc.returncode == 0 else "FAIL",
        "detail": f"exit {proc.returncode}",
        "output": output,
    }


def check_data_guard(cwd: Path) -> dict[str, Any]:
    proc = run(["git", "ls-files", "data"], cwd=cwd)
    if proc.returncode != 0:
        return {
            "name": "data-guard",
            "status": "FAIL",
            "detail": "git ls-files failed",
            "output": proc.stderr.strip(),
        }
    tracked = proc.stdout.strip()
    return {
        "name": "data-guard",
        "status": "PASS" if not tracked else "FAIL",
        "detail": "no tracked data" if not tracked else "tracked card data found",
        "output": tracked,
    }


FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
REFERENCE_RE = re.compile(r"^\s*\[[^\]]+\]:\s*(\S+)", re.MULTILINE)


def markdown_targets(text: str) -> list[str]:
    """Return local link targets, ignoring fenced and inline code."""
    text = FENCE_RE.sub("", text)
    text = INLINE_CODE_RE.sub("", text)
    return LINK_RE.findall(text) + REFERENCE_RE.findall(text)


def check_links(cwd: Path) -> dict[str, Any]:
    proc = run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "*.md"],
        cwd=cwd,
    )
    if proc.returncode != 0:
        return {
            "name": "links",
            "status": "FAIL",
            "detail": "git ls-files failed",
            "output": proc.stderr.strip(),
        }
    paths = [Path(line) for line in proc.stdout.splitlines() if line.strip()]
    missing: list[str] = []
    for path in paths:
        try:
            text = (cwd / path).read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            missing.append(f"{path}: cannot read ({exc})")
            continue
        for raw_target in markdown_targets(text):
            target = raw_target.strip().strip("<>")
            if not target or target.startswith(("#", "http://", "https://", "mailto:", "tel:")):
                continue
            target = target.split('"', 1)[0].strip()
            target = target.split("#", 1)[0].split("?", 1)[0]
            if not target:
                continue
            try:
                exists = (cwd / path.parent / target).resolve().exists()
            except (OSError, RuntimeError):
                exists = False
            if not exists:
                missing.append(f"{path}: {target}")
    return {
        "name": "links",
        "status": "PASS" if not missing else "FAIL",
        "detail": "all local links resolve" if not missing else f"{len(missing)} broken",
        "output": "\n".join(missing),
    }


def collect_checks(cwd: Path) -> list[dict[str, Any]]:
    checks = [
        run_check(
            "tests",
            [sys.executable, "-m", "unittest", "discover", "-s", "skills/swu-review/tests"],
            cwd,
        ),
        check_data_guard(cwd),
    ]
    if (cwd / "factory/tests").is_dir():
        checks.append(
            run_check(
                "tooling-tests",
                [sys.executable, "-m", "unittest", "discover", "-s", "factory/tests"],
                cwd,
            )
        )
    else:
        checks.append(
            {
                "name": "tooling-tests",
                "status": "SKIP",
                "detail": "factory tests not present in this worktree",
                "output": "",
            }
        )
    if module_available("ruff"):
        checks.append(run_check("ruff", [sys.executable, "-m", "ruff", "check", "."], cwd))
    else:
        checks.append(
            {
                "name": "ruff",
                "status": "SKIP",
                "detail": "python -m ruff not available; install .[dev]",
                "output": "",
            }
        )
    if module_available("mypy"):
        checks.append(run_check("mypy-core", [sys.executable, "-m", "mypy"], cwd))
        checks.append(
            run_check(
                "mypy-scripts",
                [sys.executable, "-m", "mypy", "skills/swu-review/scripts"],
                cwd,
            )
        )
        if (cwd / "factory/factory.py").is_file():
            checks.append(
                run_check(
                    "mypy-factory",
                    [sys.executable, "-m", "mypy", "factory/factory.py"],
                    cwd,
                )
            )
        else:
            checks.append(
                {
                    "name": "mypy-factory",
                    "status": "SKIP",
                    "detail": "factory code not present in this worktree",
                    "output": "",
                }
            )
    else:
        for name in ("mypy-core", "mypy-scripts", "mypy-factory"):
            checks.append(
                {
                    "name": name,
                    "status": "SKIP",
                    "detail": "python -m mypy not available; install .[dev]",
                    "output": "",
                }
            )
    checks.append(check_links(cwd))
    return checks


def print_checks(checks: list[dict[str, Any]], show_output: bool = False) -> None:
    print(f"{'CHECK':<14} {'STATUS':<6} DETAIL")
    for check in checks:
        print(f"{check['name']:<14} {check['status']:<6} {check['detail']}")
        if show_output and check["status"] == "FAIL" and check["output"]:
            print()
            print(check["output"])
            print()


def cmd_list(args: argparse.Namespace) -> int:
    print(render_list(load_backlog(), show_all=args.all))
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    print(render_item(find_item(load_backlog(), args.item)))
    return 0


def ignore_data_link(worktree: Path) -> None:
    """Add /data to the local exclude file so a symlink is not dirty.

    The tracked .gitignore uses ``/data/`` (a directory); a symlink to a
    directory is a file to git, so it needs its own local exclude entry.
    """
    proc = run(["git", "rev-parse", "--git-path", "info/exclude"], cwd=worktree)
    if proc.returncode != 0:
        return
    exclude = Path(proc.stdout.strip())
    if not exclude.is_absolute():
        exclude = (worktree / exclude).resolve()
    lines = exclude.read_text(encoding="utf-8").splitlines() if exclude.exists() else []
    if "/data" not in lines:
        exclude.parent.mkdir(parents=True, exist_ok=True)
        with exclude.open("a", encoding="utf-8") as handle:
            handle.write("/data\n")


def cmd_new(args: argparse.Namespace) -> int:
    data = load_backlog()
    item = find_item(data, args.item)
    if item.get("status") != "ready":
        raise SystemExit(f"{item['id']} is {item.get('status')!r}, not 'ready'")
    wip = wip_items(data)
    if len(wip) >= data.get("wip_limit", 1) and not args.force:
        raise SystemExit(
            f"WIP limit reached: {wip[0]['id']} is already 'doing'. "
            "Finish it or pass --force."
        )

    base = args.base
    if args.fetch:
        proc = run(["git", "fetch", "origin"], cwd=ROOT)
        if proc.returncode != 0:
            raise SystemExit(proc.stderr.strip() or "git fetch failed")

    branch = f"factory/{item['id'].lower()}"
    worktree = Path(args.worktree_dir).expanduser().resolve() / item["id"].lower()
    if worktree.exists():
        raise SystemExit(f"worktree already exists: {worktree}")

    proc = run(["git", "worktree", "add", "-b", branch, str(worktree), base], cwd=ROOT)
    if proc.returncode != 0:
        raise SystemExit(proc.stderr.strip() or "git worktree add failed")

    data_source = ROOT / "data"
    data_link = worktree / "data"
    if not args.no_data_link and data_source.exists() and not data_link.exists():
        data_link.symlink_to(data_source, target_is_directory=True)
        ignore_data_link(worktree)

    item["status"] = "doing"
    save_backlog(data)

    print(f"Worktree: {worktree}")
    print(f"Branch:   {branch}")
    print(f"Base:     {base}")
    print()
    print("Next:")
    print(f"  cd {worktree}")
    print(f"  {sys.executable} {ROOT / 'factory' / 'factory.py'} check --worktree {worktree}")
    print(f"  {sys.executable} {ROOT / 'factory' / 'factory.py'} oracle --worktree {worktree}")
    print(f"  {sys.executable} {ROOT / 'factory' / 'factory.py'} packet {item['id']} --worktree {worktree}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    cwd = resolve_worktree(args.worktree)
    require_worktree(cwd)
    branch = git_output(["branch", "--show-current"], cwd) or "(detached)"
    head = git_output(["rev-parse", "--short", "HEAD"], cwd) or "unknown"
    behind_raw = git_output(["rev-list", "--count", "HEAD..origin/main"], cwd)
    behind: int | None = int(behind_raw) if behind_raw and behind_raw.isdigit() else None
    dirty = git_output(["status", "--short"], cwd)
    if dirty is None:
        raise SystemExit(f"git status failed in {cwd}")
    data = (cwd / "data").exists()
    payload = {
        "worktree": str(cwd),
        "branch": branch,
        "head": head,
        "behind_origin_main": behind,
        "dirty": bool(dirty),
        "data": data,
        "status": dirty.splitlines(),
    }
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0
    behind_text = f"{behind} commit(s)" if behind is not None else "unknown"
    print(f"Worktree:  {cwd}")
    print(f"Branch:    {branch} @ {head}")
    print(f"Behind:    {behind_text} behind origin/main")
    print(f"Data:      {'present' if data else 'missing'}")
    print(f"Dirty:     {'yes' if dirty else 'no'}")
    if dirty:
        print(dirty)
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    cwd = resolve_worktree(args.worktree)
    require_worktree(cwd)
    checks = collect_checks(cwd)
    if args.json:
        print(json.dumps(checks, indent=2))
    else:
        print_checks(checks, show_output=args.show_output)
    failed = [check for check in checks if check["status"] == "FAIL"]
    skipped = [check for check in checks if check["status"] == "SKIP"]
    if failed:
        return 1
    if args.strict and skipped:
        return 1
    return 0


def cmd_oracle(args: argparse.Namespace) -> int:
    cwd = resolve_worktree(args.worktree)
    require_worktree(cwd)
    cases = Path(os.environ.get("FACTORY_ORACLE_CASES", ORACLE_CASES))
    if not cases.exists():
        print(
            "No oracle integration installed. "
            "Set FACTORY_ORACLE_CASES and add the project-specific runner."
        )
        return 2
    try:
        from oracle import run_oracle_cases  # type: ignore[import-not-found]
    except ImportError:
        print(
            "No oracle runner installed. "
            "The project integration adds oracle.py and its cases."
        )
        return 2
    return int(run_oracle_cases(cases, cwd, as_json=args.json))


def cmd_packet(args: argparse.Namespace) -> int:
    data = load_backlog()
    item = find_item(data, args.item)
    cwd = resolve_worktree(args.worktree)
    require_worktree(cwd)
    checks = [] if args.no_check else collect_checks(cwd)
    status = git_output(["status", "--short"], cwd)
    diffstat = git_output(["diff", "--stat", "HEAD"], cwd)
    if status is None or diffstat is None:
        raise SystemExit(f"git status/diff failed in {cwd}")

    lines = [
        f"# Review packet — {item['id']}",
        "",
        render_item(item),
        "",
        "## Verification",
        "",
    ]
    if checks:
        lines += ["| Check | Status | Detail |", "|---|---|---|"]
        for check in checks:
            lines.append(f"| `{check['name']}` | {check['status']} | {check['detail']} |")
        failures = [check for check in checks if check["status"] == "FAIL"]
        for check in failures:
            lines += [
                "",
                f"<details><summary>{check['name']} output</summary>",
                "",
                "```text",
                check["output"][-4000:] or "(no output)",
                "```",
                "",
                "</details>",
            ]
    else:
        lines.append("Not run (`--no-check`).")
    lines += [
        "",
        "## Working tree",
        "",
        "```text",
        status or "(clean)",
        "```",
        "",
        "### Diff stat",
        "",
        "```text",
        diffstat or "(no diff against HEAD)",
        "```",
        "",
        "## Human gates",
        "",
        "- [ ] The design and the scope were approved before implementation.",
        "- [ ] Expected values for rules/legality were frozen by a human.",
        "- [ ] `check` is green, or every skip is explained.",
        "- [ ] The council ran if this is a T2/T3/T4 item.",
        "- [ ] A human merges; there is no auto-merge.",
        "",
        "## Council triggers",
        "",
        "- Legality, rules, schema, cross-cutting or scope changes.",
        "- Any failure in the adversarial oracle.",
        "- Any new dependency, public output or data source.",
    ]
    body = "\n".join(lines)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(body + "\n", encoding="utf-8")
        print(out)
    else:
        print(body)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Tiny software-factory CLI (spike)")
    sub = parser.add_subparsers(dest="command", required=True)

    list_cmd = sub.add_parser("list", help="list the tracked backlog")
    list_cmd.add_argument("--all", action="store_true", help="include non-ready items")
    list_cmd.set_defaults(func=cmd_list)

    show = sub.add_parser("show", help="show one backlog item")
    show.add_argument("item")
    show.set_defaults(func=cmd_show)

    new = sub.add_parser("new", help="create a worktree for a ready item")
    new.add_argument("item")
    new.add_argument("--base", default="origin/main", help="git revision to base on")
    new.add_argument(
        "--worktree-dir",
        default=str(DEFAULT_WORKTREES),
        help="parent directory for worktrees (default: %(default)s)",
    )
    new.add_argument("--fetch", action="store_true", help="run git fetch origin first")
    new.add_argument("--no-data-link", action="store_true", help="do not symlink data/")
    new.add_argument("--force", action="store_true", help="ignore the WIP limit")
    new.set_defaults(func=cmd_new)

    status = sub.add_parser("status", help="show worktree state")
    status.add_argument("--worktree")
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=cmd_status)

    check = sub.add_parser("check", help="run the local verification bundle")
    check.add_argument("--worktree")
    check.add_argument("--json", action="store_true")
    check.add_argument("--show-output", action="store_true", help="print failing output")
    check.add_argument("--strict", action="store_true", help="treat SKIP as failure")
    check.set_defaults(func=cmd_check)

    oracle = sub.add_parser("oracle", help="run the adversarial legality oracle")
    oracle.add_argument("--worktree")
    oracle.add_argument("--json", action="store_true")
    oracle.set_defaults(func=cmd_oracle)

    packet = sub.add_parser("packet", help="build a review packet")
    packet.add_argument("item")
    packet.add_argument("--worktree")
    packet.add_argument("--out", help="write the packet to a file")
    packet.add_argument("--no-check", action="store_true", help="skip verification")
    packet.set_defaults(func=cmd_packet)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
