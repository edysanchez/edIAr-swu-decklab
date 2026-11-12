#!/usr/bin/env python3
"""
validate_deck.py - Validate SWU Premier deck legality
Implements docs/rules.md
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import swu_cards as sc
import constants as C
import suspended_list

PREMIER_SETS = set(C.PREMIER_SETS)


def load_deck(deck_path):
    path = Path(deck_path)
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Try JSON first
    try:
        data = json.loads(content)
        if isinstance(data, list):
            return parse_flat_list(data)
        if isinstance(data, dict):
            # Case format: mainDeck/sideboard with card objects
            if 'mainDeck' in data and isinstance(data['mainDeck'], list):
                return parse_case_format(data)
            if 'deck' in data and isinstance(data['deck'], list):
                if data['deck'] and isinstance(data['deck'][0], dict):
                    if 'id' in data['deck'][0]:
                        return sc.parse_deck_swu_json(data)
                    elif 'key' in data['deck'][0]:
                        return data
                # could be list of dicts without id
                return sc.parse_deck_swu_json(data)
            # maybe top-level leader/base/deck as dicts
            if 'leader' in data or 'base' in data:
                return sc.parse_deck_swu_json(data)
            return sc.parse_deck_swu_json(data)
    except json.JSONDecodeError:
        pass

    # Try text format
    return sc.parse_deck_swu_text(content)


def parse_flat_list(data):
    """Parse flat list format."""
    result = {"leader": None, "base": None, "deck": [], "sideboard": []}
    for e in data:
        if not isinstance(e, dict):
            continue
        t = e.get("type", "Unit")
        if isinstance(t, dict):
            t = t.get("name", "Unit")
        count = int(e.get("count", 1))
        title = e.get("title") or e.get("name") or e.get("cardName") or ""
        subtitle = e.get("subtitle") or ""
        entry = {"name": title, "subtitle": subtitle, "count": count}
        if e.get("code"):
            entry["code"] = e.get("code")
        if t in ("Leader", "leaders"):
            if result["leader"] is None:
                result["leader"] = entry
            continue
        if t in ("Base", "bases"):
            if result["base"] is None:
                result["base"] = entry
            continue
        if t in ("Sideboard",):
            result["sideboard"].append(entry)
            continue
        result["deck"].append(entry)
    return result


def parse_case_format(data):
    """Parse the case study format (mainDeck/sideboard with nested card objects)."""
    result = {"leader": None, "base": None, "deck": [], "sideboard": []}
    
    for card_entry in data.get('mainDeck', []):
        card = card_entry.get('card', {})
        count = card_entry.get('count', 1)
        card_type = card.get('type', {}).get('name', '') if isinstance(card.get('type'), dict) else ''
        code = card.get('expansion', {}).get('code', '') if isinstance(card.get('expansion'), dict) else ''
        number = card.get('cardNumber')
        title = card.get('title', '')
        subtitle = card.get('subtitle', '') or ''
        
        entry = {
            'name': title,
            'subtitle': subtitle,
            'count': count,
            'set': code,
            'number': number
        }
        
        if card_type == 'Leader':
            result['leader'] = entry
        elif card_type == 'Base':
            result['base'] = entry
        else:
            result['deck'].append(entry)
    
    for card_entry in data.get('sideboard', []):
        card = card_entry.get('card', {})
        count = card_entry.get('count', 1)
        code = card.get('expansion', {}).get('code', '') if isinstance(card.get('expansion'), dict) else ''
        number = card.get('cardNumber')
        title = card.get('title', '')
        subtitle = card.get('subtitle', '') or ''
        
        entry = {
            'name': title,
            'subtitle': subtitle,
            'count': count,
            'set': code,
            'number': number
        }
        result['sideboard'].append(entry)
    
    return result


def resolve_card(card_ref, card_db):
    """Resolve a card reference to its identity."""
    if isinstance(card_ref, dict):
        if 'key' in card_ref:
            return card_ref['key']
        if 'name' in card_ref:
            key = sc.card_identity_key(card_ref['name'], card_ref.get('subtitle', ''))
            return key
        if 'id' in card_ref:
            set_code = card_ref.get('set', '')
            number = card_ref.get('number', '')
            for (name, subtitle), card in card_db.items():
                if card.get('set') == set_code and card.get('number') == number:
                    return (name, subtitle)
    return None


def calculate_aspect_penalty(leader_key, base_key, deck_cards, card_db):
    """Calculate aspect penalty (not a legality check)."""
    if not leader_key or not base_key:
        return 0, 0
    
    leader = card_db.get(leader_key)
    base = card_db.get(base_key)
    
    if not leader or not base:
        return 0, 0
    
    provided_aspects = set()
    for aspect in leader.get('aspects', []):
        provided_aspects.add(aspect)
    for aspect in base.get('aspects', []):
        provided_aspects.add(aspect)
    
    total_penalty = 0
    max_penalty = 0
    
    for card_key, count in deck_cards.items():
        card = card_db.get(card_key)
        if not card:
            continue
        
        card_aspects = card.get('aspects', [])
        missing = 0
        for aspect in card_aspects:
            if aspect not in provided_aspects:
                missing += 1
        
        penalty = missing * 2
        total_penalty += penalty * count
        if penalty > max_penalty:
            max_penalty = penalty
    
    return total_penalty, max_penalty


def validate_deck(deck_path, verbose=True):
    errors = []
    warnings = []
    
    try:
        card_db = sc.load_swu_cards()
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    suspended = suspended_list.load(card_db)
    warnings.extend(suspended.warnings)
    
    try:
        deck = load_deck(deck_path)
    except Exception as e:
        print(f"ERROR: Failed to load deck: {e}", file=sys.stderr)
        sys.exit(1)
    
    if verbose:
        print(f"Validating: {deck_path}")
        print("=" * 60)
    
    all_identities = {}
    
    leader_key = resolve_card(deck.get('leader'), card_db)
    if leader_key:
        all_identities[leader_key] = all_identities.get(leader_key, 0) + 1
    else:
        errors.append("No leader found or leader could not be resolved")
    
    base_key = resolve_card(deck.get('base'), card_db)
    if base_key:
        all_identities[base_key] = all_identities.get(base_key, 0) + 1
    else:
        errors.append("No base found or base could not be resolved")
    
    deck_cards = {}
    for card in deck.get('deck', []):
        key = resolve_card(card, card_db)
        if key:
            count = card.get('count', 1) if isinstance(card, dict) else 1
            deck_cards[key] = deck_cards.get(key, 0) + count
            all_identities[key] = all_identities.get(key, 0) + count
        else:
            errors.append(f"Could not resolve card in deck: {card}")
    
    sideboard_cards = {}
    for card in deck.get('sideboard', []):
        key = resolve_card(card, card_db)
        if key:
            count = card.get('count', 1) if isinstance(card, dict) else 1
            if key == leader_key or key == base_key:
                errors.append(f"Leader or base cannot be in sideboard: {key}")
            sideboard_cards[key] = sideboard_cards.get(key, 0) + count
            all_identities[key] = all_identities.get(key, 0) + count
        else:
            errors.append(f"Could not resolve card in sideboard: {card}")
    
    leader_count = 1 if deck.get('leader') else 0
    base_count = 1 if deck.get('base') else 0
    
    if leader_count != 1:
        errors.append(f"Must have exactly 1 leader (found: {leader_count})")
    if base_count != 1:
        errors.append(f"Must have exactly 1 base (found: {base_count})")
    
    deck_size = sum(deck_cards.values())
    if deck_size < 50:
        errors.append(f"Draw deck must be at least 50 cards (found: {deck_size})")
    
    sideboard_size = sum(sideboard_cards.values())
    if sideboard_size > 10:
        errors.append(f"Sideboard must be at most 10 cards (found: {sideboard_size})")
    
    for key, count in all_identities.items():
        if key == leader_key or key == base_key:
            continue
        if count > 3:
            card = card_db.get(key)
            if card:
                name = f"{card['name']} - {card['subtitle']}" if card.get('subtitle') else card['name']
            else:
                name = str(key)
            errors.append(f"Too many copies of {name}: {count} (max 3)")
    
    for key in deck_cards:
        card = card_db.get(key)
        if card and card['set'] not in PREMIER_SETS:
            errors.append(f"Card {card['name']} is from non-Premier set {card['set']}")
    
    for key in sideboard_cards:
        card = card_db.get(key)
        if card and card['set'] not in PREMIER_SETS:
            errors.append(f"Sideboard card {card['name']} is from non-Premier set {card['set']}")
    
    for key in all_identities:
        if key in suspended.identities:
            card = card_db.get(key)
            if card:
                label = f"{card['name']} - {card['subtitle']}" if card.get('subtitle') else card['name']
                errors.append(
                    f"Card {label} ({card['set']} {card['number']}) is suspended in Premier"
                )
            else:
                errors.append(f"Card {key} is suspended in Premier")
    
    total_penalty, max_penalty = calculate_aspect_penalty(leader_key, base_key, deck_cards, card_db)
    
    if verbose:
        print(f"\nDeck structure:")
        if leader_key:
            l = card_db.get(leader_key)
            if l:
                print(f"  Leader: {l['name']} - {l['subtitle']} ({l['set']} {l['number']})")
        if base_key:
            b = card_db.get(base_key)
            if b:
                print(f"  Base: {b['name']} - {b['subtitle']} ({b['set']} {b['number']})")
        print(f"  Draw deck: {deck_size} cards")
        print(f"  Sideboard: {sideboard_size} cards")
        print(f"  Distinct cards (main deck): {len(deck_cards)}")
        
        print(f"\nAspect penalty (not a legality issue):")
        print(f"  Total penalty: {total_penalty}")
        print(f"  Max penalty: {max_penalty}")
        
        print(f"\nValidation:")
        if errors:
            print(f"  ❌ ILLEGAL ({len(errors)} error(s))")
            for err in errors:
                print(f"     - {err}")
        else:
            print(f"  ✅ LEGAL")
        if warnings:
            print(f"\n  ⚠️  WARNINGS ({len(warnings)}):")
            for warning in warnings:
                print(f"     - {warning}")
        print("=" * 60)
    
    return len(errors) == 0, errors, warnings


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Validate SWU Premier deck legality')
    parser.add_argument('deck', help='Path to deck file (SWUDB JSON or text)')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--quiet', action='store_true', help='Only output result')
    args = parser.parse_args()
    
    valid, errors, warnings = validate_deck(args.deck, verbose=not args.quiet)
    
    if args.json:
        result = {"valid": valid, "errors": errors, "warnings": warnings}
        print(json.dumps(result, indent=2))
    
    sys.exit(0 if valid else 1)


if __name__ == '__main__':
    main()
