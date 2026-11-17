#!/usr/bin/env python3
"""Query the local card catalogue.

The skill cannot read 2,400 cards into context, and grepping the JSON is
unreliable (``cost`` is a string, ``aspects`` is an array, legality depends on
the dated snapshot). This tool answers "which cards match these constraints?"
and returns only the matches.

It does not rank or recommend: judging a card is the reviewer's job.

Examples:

    search_cards.py --legal --type Unit --arena Space --cost-max 3
    search_cards.py --legal --aspect Villainy --text "when played" --json
    search_cards.py --legal --trait JEDI --keyword Sentinel
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

import legal_sets  # noqa: E402
import swu_cards as sc  # noqa: E402


@dataclass(frozen=True)
class Filters:
    """What to look for. Empty fields mean "no constraint"."""

    name: str = ""
    text: str = ""
    aspects: tuple = ()
    types: tuple = ()
    cost_min: int = None
    cost_max: int = None
    arena: str = ""
    traits: tuple = ()
    keywords: tuple = ()
    rarity: str = ""
    unique: bool = False
    sets: tuple = ()
    legal: object = None


def _cost(card):
    value = card.get("cost")
    if value is None or value == "":
        return None
    try:
        return int(str(value).strip())
    except ValueError:
        return None


def _contains(values, wanted):
    """Case-insensitive "any of ``wanted`` is in ``values``"."""
    haystack = {str(value).strip().lower() for value in values or ()}
    return any(needle.lower() in haystack for needle in wanted)


def matches(card, filters):
    """Return whether a card satisfies every active filter."""
    if filters.name and filters.name.lower() not in str(card.get("name", "")).lower():
        return False
    if filters.text and filters.text.lower() not in str(card.get("frontText") or "").lower():
        return False
    if filters.aspects and not _contains(card.get("aspects"), filters.aspects):
        return False
    if filters.types and str(card.get("type", "")).lower() not in {
        value.lower() for value in filters.types
    }:
        return False
    if filters.arena and filters.arena.lower() not in {
        value.lower() for value in card.get("arenas") or ()
    }:
        return False
    if filters.traits and not _contains(card.get("traits"), filters.traits):
        return False
    if filters.keywords and not _contains(card.get("keywords"), filters.keywords):
        return False
    if filters.rarity and str(card.get("rarity", "")).lower() != filters.rarity.lower():
        return False
    if filters.unique and not card.get("unique"):
        return False
    if filters.sets and str(card.get("set", "")).upper() not in {
        value.upper() for value in filters.sets
    }:
        return False
    if filters.cost_min is not None or filters.cost_max is not None:
        cost = _cost(card)
        if cost is None:
            return False
        if filters.cost_min is not None and cost < filters.cost_min:
            return False
        if filters.cost_max is not None and cost > filters.cost_max:
            return False
    if filters.legal is not None and not filters.legal.is_legal_any(
        sc.card_printings(card)
    ):
        return False
    return True


def row(key, card):
    """Shape one match for output."""
    name, subtitle = key
    return {
        "name": name,
        "subtitle": subtitle,
        "identity": f"{name}|{subtitle}" if subtitle else name,
        "set": card.get("set", ""),
        "number": str(card.get("number", "")),
        "type": card.get("type", ""),
        "cost": _cost(card),
        "aspects": list(card.get("aspects") or []),
        "arenas": list(card.get("arenas") or []),
        "traits": list(card.get("traits") or []),
        "keywords": list(card.get("keywords") or []),
        "rarity": card.get("rarity", ""),
        "unique": bool(card.get("unique")),
        "text": card.get("frontText") or "",
    }


def search(card_db, filters):
    """Return the matching cards, cheapest first and then by name."""
    found = [row(key, card) for key, card in card_db.items() if matches(card, filters)]
    found.sort(key=lambda item: (item["cost"] if item["cost"] is not None else 99, item["name"]))
    return found


def _csv(value):
    return tuple(part.strip() for part in str(value or "").split(",") if part.strip())


def _parser():
    parser = argparse.ArgumentParser(
        description="Search the local SWU card catalogue.",
    )
    parser.add_argument("--name", default="", help="substring of the card name")
    parser.add_argument("--text", default="", help="substring of the printed text")
    parser.add_argument("--aspect", default="", help="comma separated aspects")
    parser.add_argument("--type", default="", help="comma separated card types")
    parser.add_argument("--cost-min", type=int, default=None)
    parser.add_argument("--cost-max", type=int, default=None)
    parser.add_argument("--arena", default="", help="Ground or Space")
    parser.add_argument("--trait", default="", help="comma separated traits")
    parser.add_argument("--keyword", default="", help="comma separated keywords")
    parser.add_argument("--rarity", default="")
    parser.add_argument("--unique", action="store_true")
    parser.add_argument("--set", dest="sets", default="", help="comma separated set codes")
    parser.add_argument(
        "--legal",
        action="store_true",
        help="only cards legal in Premier as of the dated legal-set list",
    )
    parser.add_argument("--limit", type=int, default=None, help="keep the first N matches")
    parser.add_argument("--json", action="store_true", help="JSON instead of a table")
    parser.add_argument("--card-db", default=None, help="card database path")
    return parser


def main(argv=None):
    args = _parser().parse_args(argv)

    try:
        card_db = sc.load_swu_cards(args.card_db)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    legal = None
    if args.legal:
        known = sc.complete_sets() or sc.card_db_sets(card_db)
        legal = legal_sets.load(known_sets=known)
        for warning in legal.warnings:
            print(f"WARNING: {warning}", file=sys.stderr)

    filters = Filters(
        name=args.name,
        text=args.text,
        aspects=_csv(args.aspect),
        types=_csv(args.type),
        cost_min=args.cost_min,
        cost_max=args.cost_max,
        arena=args.arena,
        traits=_csv(args.trait),
        keywords=_csv(args.keyword),
        rarity=args.rarity,
        unique=args.unique,
        sets=_csv(args.sets),
        legal=legal,
    )

    results = search(card_db, filters)
    if args.limit is not None:
        results = results[: args.limit]

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return 0

    if not results:
        print("No cards match.")
        return 0

    print(f"{len(results)} card(s)")
    for item in results:
        cost = item["cost"] if item["cost"] is not None else "-"
        aspects = "/".join(item["aspects"]) or "-"
        arenas = "/".join(item["arenas"]) or "-"
        print(
            f"  {item['name']}"
            + (f", {item['subtitle']}" if item["subtitle"] else "")
            + f"  [{item['set']} {item['number']}]"
            + f"  cost {cost}  {item['type']}  {aspects}  {arenas}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
