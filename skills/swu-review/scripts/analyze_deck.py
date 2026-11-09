#!/usr/bin/env python3
"""
analyze_deck.py - Analyze SWU Premier deck
Implements docs/metrics.md (composition, aspect penalty, price)
Card database only, no meta.
"""

import json
import sys
from pathlib import Path
from collections import Counter, defaultdict
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent))

import swu_cards as sc
from validate_deck import load_deck, resolve_card, calculate_aspect_penalty


def analyze_deck(deck_path, verbose=True):
    try:
        card_db = sc.load_swu_cards()
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    
    try:
        deck = load_deck(deck_path)
    except Exception as e:
        print(f"ERROR: Failed to load deck: {e}", file=sys.stderr)
        sys.exit(1)
    
    if verbose:
        print(f"Analyzing: {deck_path}")
        print("=" * 60)
    
    leader_key = resolve_card(deck.get('leader'), card_db)
    base_key = resolve_card(deck.get('base'), card_db)
    
    deck_cards = {}
    for card in deck.get('deck', []):
        key = resolve_card(card, card_db)
        if key:
            count = card.get('count', 1) if isinstance(card, dict) else 1
            deck_cards[key] = deck_cards.get(key, 0) + count
    
    N = sum(deck_cards.values())
    
    if verbose:
        print(f"\nDeck: {N} cards")
        if leader_key:
            l = card_db.get(leader_key)
            if l:
                print(f"Leader: {l['name']} - {l['subtitle']} ({l['set']})")
        if base_key:
            b = card_db.get(base_key)
            if b:
                print(f"Base: {b['name']} - {b['subtitle']} ({b['set']})")
    
    # Curve
    curve = Counter()
    no_cost = 0
    total_cost = 0
    cost_count = 0
    for key, count in deck_cards.items():
        card = card_db.get(key)
        if not card:
            continue
        cost = card.get('cost')
        if cost is None or cost == '':
            no_cost += count
        else:
            try:
                c = int(cost)
                curve[c] += count
                total_cost += c * count
                cost_count += count
            except:
                no_cost += count
    
    mean_cost = total_cost / cost_count if cost_count > 0 else 0
    
    if verbose:
        print(f"\nCurve:")
        for cost in sorted(curve.keys()):
            pct = (curve[cost] / N * 100) if N > 0 else 0
            print(f"  {cost}: {curve[cost]} ({pct:.1f}%)")
        if no_cost > 0:
            pct = (no_cost / N * 100) if N > 0 else 0
            print(f"  -: {no_cost} ({pct:.1f}%)")
        print(f"  Mean cost: {mean_cost:.2f} (of {cost_count} cards with cost)")
    
    # Type split
    type_counts = Counter()
    for key, count in deck_cards.items():
        card = card_db.get(key)
        if card:
            t = card.get('type', 'Unknown')
            type_counts[t] += count
    
    if verbose:
        print(f"\nType split:")
        for t in ['Unit', 'Event', 'Upgrade']:
            if type_counts[t] > 0:
                pct = (type_counts[t] / N * 100) if N > 0 else 0
                print(f"  {t}: {type_counts[t]} ({pct:.1f}%)")
    
    # Arena split
    ground = 0
    space = 0
    unit_slots = 0
    for key, count in deck_cards.items():
        card = card_db.get(key)
        if not card:
            continue
        if card.get('type') == 'Unit':
            unit_slots += count
            arenas = card.get('arenas', [])
            if 'Ground' in arenas:
                ground += count
            if 'Space' in arenas:
                space += count
    
    if verbose:
        print(f"\nArena split ({unit_slots} unit slots):")
        g_pct = (ground / unit_slots * 100) if unit_slots > 0 else 0
        s_pct = (space / unit_slots * 100) if unit_slots > 0 else 0
        print(f"  Ground: {ground} ({g_pct:.1f}%)")
        print(f"  Space: {space} ({s_pct:.1f}%)")
    
    # Distinct cards
    distinct = len(deck_cards)
    
    if verbose:
        print(f"\nDistinct cards: {distinct}")
    
    # Unique-icon slots
    unique_slots = 0
    for key, count in deck_cards.items():
        card = card_db.get(key)
        if card and card.get('unique'):
            unique_slots += count
    
    if verbose:
        print(f"Unique-icon slots: {unique_slots}")
    
    # Aspect penalty
    total_penalty, max_penalty = calculate_aspect_penalty(leader_key, base_key, deck_cards, card_db)
    
    if verbose:
        print(f"\nAspect penalty:")
        print(f"  Total: {total_penalty}")
        print(f"  Max: {max_penalty}")
    
    # Price
    total_usd = Decimal('0')
    priced = 0
    for key, count in deck_cards.items():
        card = card_db.get(key)
        if card and card.get('marketPriceUsd'):
            try:
                price = Decimal(str(card['marketPriceUsd']))
                if price > 0:
                    total_usd += price * count
                    priced += count
            except:
                pass
    
    coverage = (priced / N * 100) if N > 0 else 0
    
    if verbose:
        print(f"\nPrice (USD, swu-db):")
        print(f"  Total: ${total_usd:.2f}")
        print(f"  Coverage: {priced}/{N} ({coverage:.1f}%)")
        print("=" * 60)
    
    return {
        "n": N,
        "curve": dict(curve),
        "mean_cost": mean_cost,
        "types": dict(type_counts),
        "ground": ground,
        "space": space,
        "unit_slots": unit_slots,
        "distinct": distinct,
        "unique_slots": unique_slots,
        "total_penalty": total_penalty,
        "max_penalty": max_penalty,
        "total_usd": float(total_usd),
        "priced": priced,
        "coverage": coverage
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Analyze SWU Premier deck')
    parser.add_argument('deck', help='Path to deck file')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    args = parser.parse_args()
    
    result = analyze_deck(args.deck, verbose=not args.json)
    
    if args.json:
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
