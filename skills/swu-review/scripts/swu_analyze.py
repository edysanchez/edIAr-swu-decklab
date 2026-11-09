#!/usr/bin/env python3
"""CLI for the SWU card-analysis pipeline.

Examples::

    # JSON on stdout
    python3 swu_analyze.py deck.json --json

    # Both artefacts on disk
    python3 swu_analyze.py deck.json --json analysis.json --report report.md

    # Custom database and shorter draw horizon
    python3 swu_analyze.py deck.json --card-db data/swudb/cards_normalized.json \
        --max-round 4 --json
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from analysis import build_analysis  # noqa: E402
from render_report import render_report  # noqa: E402
import cardmarket  # noqa: E402

STDOUT = "-"


def _parser():
    parser = argparse.ArgumentParser(
        description="Analyse the card and deck-composition part of a SWU Premier deck.",
    )
    parser.add_argument("deck", help="Path to the deck file.")
    parser.add_argument(
        "--json",
        nargs="?",
        const=STDOUT,
        default=None,
        metavar="PATH",
        help="Write analysis JSON to PATH, or to stdout when PATH is omitted.",
    )
    parser.add_argument(
        "--report",
        nargs="?",
        const=STDOUT,
        default=None,
        metavar="PATH",
        help="Write the Markdown report to PATH, or to stdout when PATH is omitted.",
    )
    parser.add_argument(
        "--card-db",
        default=None,
        metavar="PATH",
        help="Path to cards_normalized.json (defaults to data/swudb/).",
    )
    parser.add_argument(
        "--max-round",
        type=int,
        default=None,
        metavar="N",
        help="Last round to include in draw odds (default: 6).",
    )
    parser.add_argument(
        "--cm-cache",
        default=None,
        metavar="PATH",
        help=(
            "Cardmarket cache directory (defaults to data/cm/). "
            "Added automatically when the files exist."
        ),
    )
    parser.add_argument(
        "--no-eur",
        action="store_true",
        help="Do not add the optional Cardmarket EUR price block.",
    )
    return parser


def _write_json(data, target):
    text = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if target == STDOUT:
        sys.stdout.write(text)
    else:
        Path(target).write_text(text, encoding="utf-8")


def _write_report(data, target):
    text = render_report(data)
    if target == STDOUT:
        sys.stdout.write(text)
    else:
        Path(target).write_text(text, encoding="utf-8")


def main(argv=None):
    parser = _parser()
    args = parser.parse_args(argv)

    json_target = args.json
    report_target = args.report
    if json_target is None and report_target is None:
        json_target = STDOUT

    if json_target == STDOUT and report_target == STDOUT:
        parser.error("cannot send both --json and --report to stdout")

    try:
        cm_index = None
        if not args.no_eur:
            cm_index = cardmarket.load_index(args.cm_cache)
            if cm_index is None and args.cm_cache is not None:
                print(
                    f"ERROR: no Cardmarket cache in {args.cm_cache} "
                    f"(run fetch_prices_cm.py or drop --cm-cache)",
                    file=sys.stderr,
                )
                return 1
        data = build_analysis(
            args.deck,
            card_db_path=args.card_db,
            max_round=args.max_round,
            cm_index=cm_index,
        )
    except FileNotFoundError as exc:
        print(f"ERROR: file not found: {exc.filename or exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - defensive CLI boundary
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if json_target is not None:
        _write_json(data, json_target)
    if report_target is not None:
        _write_report(data, report_target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
