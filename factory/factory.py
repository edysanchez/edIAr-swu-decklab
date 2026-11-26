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
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FACTORY_DIR = ROOT / "factory"
ORACLE_CASES = FACTORY_DIR / "oracle_cases" / "legality.json"
DEFAULT_WORKTREES = Path(
    os.environ.get("FACTORY_WORKTREES", "/tmp/opencode/factory-worktrees")
)
RISKS = ("T0", "T1", "T2", "T3", "T4")
STATUSES = ("ready", "doing", "review", "done")
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


def load_backlog() -> dict[str, Any]:
    path = backlog_path()
    if not path.exists():
        raise SystemExit(f"backlog not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("items", [])
    if not isinstance(items, list):
        raise SystemExit(f"{path.name}: 'items' must be a list")
    ids = [item.get("id") for item in items]
    if len(ids) != len(set(ids)):
        raise SystemExit(f"{path.name}: duplicate item ids")
    if data.get("wip_limit", 1) < 1:
        raise SystemExit(f"{path.name}: wip_limit must be >= 1")
    return data


def save_backlog(data: dict[str, Any]) -> None:
    path = backlog_path()
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def find_item(data: dict[str, Any], item_id: str) -> dict[str, Any]:
    for item in data["items"]:
        if item["id"] == item_id:
            return item
    raise SystemExit(f"unknown item: {item_id}")


def wip_items(data: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in data["items"] if item.get("status") == "doing"]


def render_list(data: dict[str, Any]) -> str:
    lines = ["ID           STATUS  RISK  PRIO  TITLE"]
    for item in data["items"]:
        lines.append(
            f"{item['id']:<12} {item.get('status', ''):<7} {item.get('risk', ''):<4} "
            f"{item.get('priority', ''):<5} {item.get('title', '')}"
        )
    wip = wip_items(data)
    lines += ["", f"WIP: {len(wip)}/{data.get('wip_limit', 1)}"]
    return "\n".join(lines)


def render_item(item: dict[str, Any]) -> str:
    lines = [
        f"## {item['id']} — {item['title']}",
        "",
        f"- Status: {item.get('status')}",
        f"- Risk: {item.get('risk')} / Priority: {item.get('priority')}",
        f"- F1: {item.get('f1')}",
        f"- Source: {item.get('source', '—')}",
        "",
        "### Scope",
        "",
        item.get("scope", "—"),
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
        lines += ["", "### Notes", "", item["notes"]]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------


def run(cmd: list[str], cwd: Path = ROOT, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, timeout=timeout)


def git_output(args: list[str], cwd: Path) -> str:
    proc = run(["git", *args], cwd=cwd)
    return proc.stdout.strip() if proc.returncode == 0 else ""


def resolve_worktree(value: str | None) -> Path:
    return Path(value).resolve() if value else ROOT


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
    tracked = proc.stdout.strip()
    return {
        "name": "data-guard",
        "status": "PASS" if not tracked else "FAIL",
        "detail": "no tracked data" if not tracked else "tracked card data found",
        "output": tracked,
    }


def check_links(cwd: Path) -> dict[str, Any]:
    proc = run(["git", "ls-files", "*.md"], cwd=cwd)
    paths = [Path(line) for line in proc.stdout.splitlines() if line.strip()]
    missing: list[str] = []
    for path in paths:
        text = (cwd / path).read_text(encoding="utf-8", errors="replace")
        for raw_target in LINK_RE.findall(text):
            target = raw_target.strip().strip("<>")
            if not target or target.startswith(("#", "http://", "https://", "mailto:", "tel:")):
                continue
            target = target.split('"', 1)[0].strip()
            target = target.split("#", 1)[0].split("?", 1)[0]
            if not target:
                continue
            if not (cwd / path.parent / target).resolve().exists():
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
    else:
        for name in ("mypy-core", "mypy-scripts"):
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


def cmd_list(_: argparse.Namespace) -> int:
    print(render_list(load_backlog()))
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
    if wip and not args.force:
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
    branch = git_output(["branch", "--show-current"], cwd) or "(detached)"
    head = git_output(["rev-parse", "--short", "HEAD"], cwd) or "?"
    behind = git_output(["rev-list", "--count", "HEAD..origin/main"], cwd) or "?"
    dirty = git_output(["status", "--short"], cwd)
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
    print(f"Worktree:  {cwd}")
    print(f"Branch:    {branch} @ {head}")
    print(f"Behind:    {behind} commit(s) behind origin/main")
    print(f"Data:      {'present' if data else 'missing'}")
    print(f"Dirty:     {'yes' if dirty else 'no'}")
    if dirty:
        print(dirty)
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    cwd = resolve_worktree(args.worktree)
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
    cases = Path(os.environ.get("FACTORY_ORACLE_CASES", ORACLE_CASES))
    if not cases.exists():
        print(
            "No oracle integration installed. "
            "Set FACTORY_ORACLE_CASES and add the project-specific runner."
        )
        return 2
    try:
        from oracle import run_oracle_cases
    except ImportError:
        print(
            "No oracle runner installed. "
            "The project integration adds oracle.py and its cases."
        )
        return 2
    cwd = resolve_worktree(args.worktree)
    return run_oracle_cases(cases, cwd, as_json=args.json)


def cmd_packet(args: argparse.Namespace) -> int:
    data = load_backlog()
    item = find_item(data, args.item)
    cwd = resolve_worktree(args.worktree)
    checks = [] if args.no_check else collect_checks(cwd)
    status = git_output(["status", "--short"], cwd)
    diffstat = git_output(["diff", "--stat", "HEAD"], cwd)

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
