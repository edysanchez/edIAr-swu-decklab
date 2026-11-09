#!/usr/bin/env python3
"""
draw_odds.py - Draw odds calculator for Star Wars: Unlimited (Premier).

Gives probability of drawing AT LEAST 1 copy of a card (or group of cards)
in the opening hand and after each turn, using exact hypergeometric calculation.

Model (declared goldfish approximation):
  - N = 50 cards in draw deck (leader and base are NOT drawn)
  - Opening hand = 6 cards
  - +2 cards per regroup phase
  - No recursion, no mulligan unless --mulligan specified
  - If --mulligan: discard opening 6 and draw 6 again once
"""

import argparse
import json
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))

import swu_cards as sc
from validate_deck import load_deck as validate_load_deck, resolve_card

DECK_SIZE = 50
OPEN_HAND = 6
DRAW_PER_REGROUP = 2


def p_at_least_one(N, K, n):
    """P(>=1 success) drawing n from N with K successes, hypergeometric."""
    if n <= 0 or K <= 0:
        return 0.0
    n = min(n, N)
    p0 = 1.0
    for i in range(n):
        p0 *= (N - K - i) / (N - i)
    return max(0.0, 1.0 - p0)


def p_with_mulligan(N, K, n_hand=OPEN_HAND):
    """P(>=1) in opening hand with one full redraw of 6."""
    p = p_at_least_one(N, K, n_hand)
    return 1 - (1 - p) ** 2


def load_deck(path, card_db=None):
    """Load deck and return list of dicts with count/name/cost/type/arena/aspects/code.
    Uses shared parsing from validate_deck; groups by name+subtitle identity.
    """
    if card_db is None:
        try:
            card_db = sc.load_swu_cards()
        except Exception:
            card_db = {}

    deck = validate_load_deck(path)

    # Build identity groups (name+subtitle)
    groups = defaultdict(lambda: {"count": 0, "name": "", "subtitle": "", "cost": None, "type": None, "arena": None, "aspects": None, "code": ""})

    # Process main deck only (exclude leader/base)
    for card in deck.get('deck', []):
        key = resolve_card(card, card_db)
        count = card.get('count', 1) if isinstance(card, dict) else 1
        if not key:
            # try to use name/subtitle from card
            if isinstance(card, dict) and 'name' in card:
                name = card['name']
                subtitle = card.get('subtitle', '') or ''
                full = f"{name} - {subtitle}" if subtitle else name
                groups[(name, subtitle)]["count"] += count
                groups[(name, subtitle)]["name"] = name
                groups[(name, subtitle)]["subtitle"] = subtitle
                if full not in [g["name"] for g in groups.values()]:  # keep simple
                    pass
            continue

        name, subtitle = key
        full_name = f"{name} - {subtitle}" if subtitle else name
        groups[key]["count"] += count
        groups[key]["name"] = full_name
        groups[key]["subtitle"] = subtitle

        c = card_db.get(key)
        if c:
            groups[key]["cost"] = c.get('cost')
            groups[key]["type"] = c.get('type')
            arenas = c.get('arenas') or []
            if arenas:
                groups[key]["arena"] = ",".join(arenas)
            aspects = c.get('aspects') or []
            if aspects:
                groups[key]["aspects"] = ",".join(aspects)
            if c.get('set') and c.get('number'):
                groups[key]["code"] = f"{c['set']}{c['number'].zfill(3) if c['number'].isdigit() else c['number']}"

    rows = []
    for key, g in groups.items():
        rows.append({
            "count": int(g["count"]),
            "name": g["name"] or (f"{key[0]} - {key[1]}" if key[1] else key[0]),
            "code": g.get("code", ""),
            "cost": g.get("cost"),
            "type": g.get("type") or "Unit",
            "arena": g.get("arena"),
            "aspects": g.get("aspects")
        })
    return rows


def pct(x):
    return round(x * 100, 1)


def main():
    ap = argparse.ArgumentParser(description="Draw odds for SWU Premier (hypergeometric)")
    ap.add_argument("deck", help="Deck JSON file")
    ap.add_argument("--copies", type=int, help="Only calculate for cards with this many copies (use with --group)")
    ap.add_argument("--group", help="Filter: 'cost:2', 'arena:Space', 'type:Event', or substring of card name")
    ap.add_argument("--hand", type=int, default=OPEN_HAND, help="Opening hand size (default: 6)")
    ap.add_argument("--max-turn", type=int, default=6, help="Turns to calculate (default: 6)")
    ap.add_argument("--mulligan", action="store_true", help="Include one full redraw of opening hand")
    ap.add_argument("--json", action="store_true", help="JSON output")
    args = ap.parse_args()

    try:
        rows = load_deck(args.deck)
    except Exception as ex:
        print(json.dumps({"error": str(ex)}), file=sys.stderr)
        return 2

    N = sum(r["count"] for r in rows) or DECK_SIZE

    sel = rows
    label = "full deck"
    if args.group:
        g = args.group
        if g.startswith("cost:"):
            cv = int(g.split(":", 1)[1])
            sel = [r for r in rows if r.get("cost") is not None and int(float(r["cost"])) == cv]
            label = f"cost {cv}"
        elif g.startswith("arena:"):
            av = g.split(":", 1)[1].lower()
            sel = [r for r in rows if (r.get("arena") or "").lower().startswith(av[:3])]
            label = f"arena {av}"
        elif g.startswith("type:"):
            tv = g.split(":", 1)[1].lower()
            sel = [r for r in rows if (r.get("type") or "").lower() == tv]
            label = f"type {tv}"
        else:
            sel = [r for r in rows if g.lower() in r["name"].lower()]
            label = f"name ~ {g}"

    turns = list(range(0, args.max_turn + 1))  # 0 = opening hand
    out = {
        "deck": args.deck,
        "N": N,
        "hand": args.hand,
        "draw_per_regroup": DRAW_PER_REGROUP,
        "mulligan": args.mulligan,
        "group": label,
        "cards": []
    }

    def prob(K, t):
        # Draw 2 cards per regroup phase
        n = args.hand + (t * DRAW_PER_REGROUP)
        if args.mulligan and t == 0:
            return p_with_mulligan(N, K, args.hand)
        return p_at_least_one(N, K, n)

    for r in sel:
        K = r["count"]
        if args.copies is not None and K != args.copies:
            continue
        probs = [prob(K, t) for t in turns]
        out["cards"].append({
            "name": r["name"],
            "code": r.get("code"),
            "copies": K,
            "p": [pct(p) for p in probs],
            "expected_by_turn": [round(K * (args.hand + t * DRAW_PER_REGROUP) / N, 2) for t in turns],
        })

    if args.group:
        Kg = sum(r["count"] for r in sel)
        out["group_total"] = {
            "copies": Kg,
            "p": [pct(prob(Kg, t)) for t in turns],
            "expected_by_turn": [round(Kg * (args.hand + t * DRAW_PER_REGROUP) / N, 2) for t in turns],
        }

    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    turn_hdr = "  ".join((f"hand" if t == 0 else f"+{t}R").rjust(6) for t in turns)
    print(f"Draw odds - {args.deck} (N={N}, hand={args.hand}, +{DRAW_PER_REGROUP}/regroup{', with mulligan' if args.mulligan else ''})")
    if args.group:
        print(f"Group: {label} ({len(sel)} cards)")
    print(f"{'copy':>4}  {'card':<44} {turn_hdr}")
    for c in out["cards"]:
        probs = "  ".join(f"{v:5.1f}%" for v in c["p"])
        print(f"{c['copies']:>4}  {c['name'][:44]:<44} {probs}")
    if args.group:
        gt = out["group_total"]
        probs = "  ".join(f"{v:5.1f}%" for v in gt["p"])
        print(f"{gt['copies']:>4}  {'= TOTAL ('+label+')':<44} {probs}")
        print("      expected copies:       " + "  ".join(f"{v:5.2f} " for v in gt["expected_by_turn"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
