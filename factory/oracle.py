#!/usr/bin/env python3
"""Adversarial legality oracle for the software-factory spike.

The expected values in ``oracle_cases/legality.json`` are proposals. A human
must freeze them before this becomes a gate. The runner compares both CLIs
against the same input and reports disagreements; it never regenerates the
expected values from the implementation.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

DEFAULT_CASES = Path(__file__).resolve().parent / "oracle_cases" / "legality.json"


def _entry_type(entry: dict[str, Any]) -> str:
    card = entry.get("card", {})
    type_info = card.get("type", {})
    if isinstance(type_info, dict):
        return str(type_info.get("name", ""))
    return str(type_info)


def _find_entry(deck: dict[str, Any], type_name: str) -> dict[str, Any]:
    for entry in deck.get("mainDeck", []):
        if _entry_type(entry) == type_name:
            return entry
    raise ValueError(f"fixture has no {type_name} entry")


def apply_mutation(deck: dict[str, Any], mutation: dict[str, Any]) -> dict[str, Any]:
    kind = mutation["type"]
    if kind == "set_leader_count":
        leader = _find_entry(deck, "Leader")
        leader["count"] = int(mutation["value"])
    elif kind == "unit_in_leader_slot":
        leader = _find_entry(deck, "Leader")
        unit = _find_entry(deck, "Unit")
        leader["card"] = unit["card"]
        leader["count"] = 1
    elif kind == "leader_in_sideboard":
        leader = _find_entry(deck, "Leader")
        deck["mainDeck"].remove(leader)
        deck.setdefault("sideboard", []).append(leader)
    elif kind == "add_secondleader":
        deck["secondleader"] = {"id": mutation.get("value", "ASH_011")}
    else:
        raise ValueError(f"unknown mutation: {kind}")
    return deck


def _run_json(cmd: list[str], cwd: Path) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, timeout=300)
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"non-JSON output from {Path(cmd[1]).name}: "
            f"{proc.stdout[:300]!r} / {proc.stderr[:300]!r}"
        ) from exc


def _actual(deck_path: Path, root: Path) -> dict[str, Any]:
    validate = _run_json(
        [
            sys.executable,
            str(root / "skills/swu-review/scripts/validate_deck.py"),
            str(deck_path),
            "--json",
            "--quiet",
        ],
        root,
    )
    analyze = _run_json(
        [
            sys.executable,
            str(root / "skills/swu-review/scripts/swu_analyze.py"),
            str(deck_path),
            "--json",
            "--no-eur",
        ],
        root,
    )
    return {
        "validate.valid": bool(validate.get("valid")),
        "analyze.legality.ok": bool(analyze.get("legality", {}).get("ok")),
    }


def run_oracle_cases(cases_path: Path, root: Path, as_json: bool = False) -> int:
    if not (root / "data/swudb/cards_normalized.json").exists():
        message = "SKIP: data/swudb/cards_normalized.json is missing"
        if as_json:
            print(json.dumps({"status": "skip", "reason": message}, indent=2))
        else:
            print(message)
        return 2

    payload = json.loads(cases_path.read_text(encoding="utf-8"))
    fixture = root / payload["fixture"]
    results: list[dict[str, Any]] = []
    for case in payload["cases"]:
        deck = json.loads(fixture.read_text(encoding="utf-8"))
        apply_mutation(deck, case["mutation"])
        with tempfile.TemporaryDirectory(prefix="factory-oracle-") as tmp:
            deck_path = Path(tmp) / "deck.json"
            deck_path.write_text(json.dumps(deck), encoding="utf-8")
            try:
                actual = _actual(deck_path, root)
                expected = case["expected"]
                passed = all(actual[key] == expected[key] for key in expected)
                results.append(
                    {
                        "id": case["id"],
                        "description": case["description"],
                        "expected": expected,
                        "actual": actual,
                        "status": "PASS" if passed else "FAIL",
                        "source": case.get("source", ""),
                    }
                )
            except Exception as exc:  # noqa: BLE001 - the oracle reports, never hides
                results.append(
                    {
                        "id": case["id"],
                        "description": case["description"],
                        "expected": case["expected"],
                        "actual": {},
                        "status": "ERROR",
                        "source": case.get("source", ""),
                        "error": str(exc),
                    }
                )

    if as_json:
        print(
            json.dumps(
                {
                    "frozen_by": payload.get("frozen_by"),
                    "results": results,
                },
                indent=2,
            )
        )
    else:
        print(f"Oracle: {cases_path}")
        print(f"Frozen by: {payload.get('frozen_by', 'unknown')}")
        print()
        print(f"{'CASE':<22} {'STATUS':<6} {'VALIDATE':<18} {'ANALYZE':<18} RESULT")
        for result in results:
            expected = result["expected"]
            actual = result["actual"]
            validate = f"{actual.get('validate.valid', '?')} (want {expected.get('validate.valid')})"
            analyze = (
                f"{actual.get('analyze.legality.ok', '?')} "
                f"(want {expected.get('analyze.legality.ok')})"
            )
            print(
                f"{result['id']:<22} {result['status']:<6} {validate:<18} "
                f"{analyze:<18} {result['description']}"
            )
            if result.get("error"):
                print(f"  error: {result['error']}")

    if any(result["status"] == "ERROR" for result in results):
        return 2
    if any(result["status"] == "FAIL" for result in results):
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the adversarial legality oracle")
    parser.add_argument("--cases", default=str(DEFAULT_CASES))
    parser.add_argument("--worktree", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.worktree).resolve() if args.worktree else Path.cwd()
    return run_oracle_cases(Path(args.cases), root, as_json=args.json)


if __name__ == "__main__":
    raise SystemExit(main())
