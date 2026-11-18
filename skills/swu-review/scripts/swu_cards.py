#!/usr/bin/env python3
"""
swu_cards.py - Shared helpers for SWU card data.

Loads card data from data/, parses decklists in SWUDB formats,
provides name+subtitle identity lookups.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from decimal import Decimal


def get_data_dir() -> Path:
    """Get the data directory for card/price caches."""
    # Look for data/ relative to script location or cwd
    cwd = Path.cwd()
    if (cwd / "data").exists():
        return cwd / "data"
    # Look relative to this file
    here = Path(__file__).parent
    for p in [here / ".." / ".." / "data", here / ".." / "data"]:
        if p.exists():
            return p.resolve()
    return cwd / "data"


def load_swu_cards(card_db_path: Optional[Path] = None) -> Dict[Tuple[str, str], Dict[str, Any]]:
    """
    Load and normalize card database.
    Returns dict keyed by (name, subtitle) with card data.
    Only includes VariantType == 'Normal' and excludes tokens.
    """
    if card_db_path is None:
        data_dir = get_data_dir()
        card_db_path = data_dir / "swudb" / "cards_normalized.json"
    else:
        card_db_path = Path(card_db_path)

    if not card_db_path.exists():
        raise FileNotFoundError(f"Card database not found: {card_db_path}. Run fetch_cards.py first.")
    
    with open(card_db_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Convert string keys back to tuples
    cards = {}
    for k, v in data.items():
        # Key is stored as "Name|Subtitle" or just "Name"
        if '|' in k:
            name, subtitle = k.split('|', 1)
        else:
            name, subtitle = k, ""
        cards[(name, subtitle)] = v
    
    return cards


def card_printings(card: Dict[str, Any]) -> List[str]:
    """Return every set code a card is known to be printed in.

    `rules.md`: legality follows the card version, so a reprint in a Premier
    legal product legalises the card. The card database keeps one entry per
    identity, with ``printings`` when more than one set is known and ``set``
    otherwise.
    """
    codes = []
    for entry in card.get("printings") or []:
        code = entry.get("set") if isinstance(entry, dict) else entry
        if code and str(code) not in codes:
            codes.append(str(code))
    if codes:
        return codes
    return [card["set"]] if card.get("set") else []


def card_printing_ids(card: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Every ``(set, number)`` the card is known to be printed as.

    A deck may reference any printing, so resolution must accept all of them,
    not just the canonical one kept on the record.
    """
    ids = []
    if card.get("set"):
        ids.append((str(card["set"]), str(card.get("number", "") or "")))

    for entry in card.get("printings") or []:
        if isinstance(entry, dict):
            pair = (str(entry.get("set") or ""), str(entry.get("number", "") or ""))
            if pair[0] and pair not in ids:
                ids.append(pair)
        elif entry:
            pair = (str(entry), "")
            if pair not in ids:
                ids.append(pair)
    return ids


def read_sets_index(sets_dir=None) -> Dict[str, Dict[str, Any]]:
    """Read the per-set completeness index; an absent index is not an error."""
    directory = Path(sets_dir) if sets_dir is not None else get_data_dir() / "swudb"
    path = directory / "sets_index.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def complete_sets(sets_dir=None) -> set:
    """Set codes the catalogue holds in full.

    A set counts only when the index says it is complete **and** its raw payload
    still exists: an index entry without a file is a deleted cache, not data.
    """
    directory = Path(sets_dir) if sets_dir is not None else get_data_dir() / "swudb"
    index = read_sets_index(directory)
    return {
        code
        for code, meta in index.items()
        if (meta or {}).get("complete") is True
        and (directory / f"{code}.json").exists()
    }


def card_db_sets(card_db: Dict[Tuple[str, str], Dict[str, Any]]) -> set:
    """Return every set code the loaded card database has cards from."""
    known = set()
    for card in card_db.values():
        known.update(card_printings(card))
    return known


def card_identity_key(name: str, subtitle: str = "") -> Tuple[str, str]:
    """Get canonical card identity key (name, subtitle)."""
    return (name.strip(), (subtitle or "").strip())


def parse_deck_swu_json(deck_data: Dict) -> Dict[str, Any]:
    """
    Parse SWUDB JSON format.
    Returns dict with leader, base, deck, sideboard (all as identity keys).
    """
    result = {
        "leader": None,
        "base": None,
        "deck": [],
        "sideboard": []
    }
    
    # Leader
    if "leader" in deck_data and deck_data["leader"]:
        leader = deck_data["leader"]
        if isinstance(leader, dict):
            leader_id = leader.get("id", "")
            count = leader.get("count", 1)
            # Parse SET_NUMBER format
            if "_" in leader_id:
                set_code, num = leader_id.split("_", 1)
                result["leader"] = {"set": set_code, "number": num, "id": leader_id}
    
    # Base
    if "base" in deck_data and deck_data["base"]:
        base = deck_data["base"]
        if isinstance(base, dict):
            base_id = base.get("id", "")
            if "_" in base_id:
                set_code, num = base_id.split("_", 1)
                result["base"] = {"set": set_code, "number": num, "id": base_id}
    
    # Deck
    for card in deck_data.get("deck", []):
        if isinstance(card, dict):
            card_id = card.get("id", "")
            count = card.get("count", 1)
            if "_" in card_id:
                set_code, num = card_id.split("_", 1)
                result["deck"].append({
                    "set": set_code, 
                    "number": num, 
                    "id": card_id, 
                    "count": count
                })
    
    # Sideboard
    for card in deck_data.get("sideboard", []):
        if isinstance(card, dict):
            card_id = card.get("id", "")
            count = card.get("count", 1)
            if "_" in card_id:
                set_code, num = card_id.split("_", 1)
                result["sideboard"].append({
                    "set": set_code, 
                    "number": num, 
                    "id": card_id, 
                    "count": count
                })
    
    return result


def parse_deck_swu_text(text: str) -> Dict[str, Any]:
    """
    Parse SWUDB text format (Melee/Picklist style).
    Sections: Leader, Base, MainDeck, Sideboard
    Lines like: "3 | Card Name | Subtitle" or "1 | Card Name"
    """
    result = {
        "leader": None,
        "base": None,
        "deck": [],
        "sideboard": []
    }
    
    lines = text.strip().split('\n')
    current_section = None
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        # Check for section headers
        if line.lower() in ['leader', 'leaders']:
            current_section = 'leader'
            continue
        elif line.lower() in ['base', 'bases']:
            current_section = 'base'
            continue
        elif line.lower() in ['maindeck', 'main deck', 'main']:
            current_section = 'deck'
            continue
        elif line.lower() in ['sideboard', 'side board']:
            current_section = 'sideboard'
            continue
        
        # Parse card line
        # Try to split by |
        if '|' in line:
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 2:
                try:
                    count = int(parts[0])
                    name = parts[1]
                    subtitle = parts[2] if len(parts) > 2 else ""
                except ValueError:
                    continue
            else:
                continue
        else:
            # Try to parse "3 Card Name"
            parts = line.split(None, 1)
            if len(parts) == 2:
                try:
                    count = int(parts[0])
                    rest = parts[1]
                    # Could be "Name | Subtitle" or just "Name"
                    if '|' in rest:
                        name_parts = [p.strip() for p in rest.split('|')]
                        name = name_parts[0]
                        subtitle = name_parts[1] if len(name_parts) > 1 else ""
                    else:
                        name = rest
                        subtitle = ""
                except ValueError:
                    continue
            else:
                continue
        
        card_entry = {"name": name, "subtitle": subtitle, "count": count}
        
        if current_section == 'leader':
            if result["leader"] is None:
                result["leader"] = card_entry
            else:
                result["leader"] = card_entry  # last wins; counts come from _zone_counts
        elif current_section == 'base':
            result["base"] = card_entry  # last wins; counts come from _zone_counts
        elif current_section == 'deck':
            result["deck"].append(card_entry)
        elif current_section == 'sideboard':
            result["sideboard"].append(card_entry)
    
    return result


def resolve_deck_to_identities(deck_parsed: Dict, card_db: Dict) -> Dict[str, Any]:
    """
    Resolve parsed deck to card identities using the card database.
    Returns deck with resolved card identities.
    """
    result = {
        "leader": None,
        "base": None,
        "deck": [],
        "sideboard": [],
        "unresolved": []
    }
    
    # Try to resolve by ID first if available
    if deck_parsed.get("leader") and isinstance(deck_parsed["leader"], dict) and "id" in deck_parsed["leader"]:
        # Would need reverse lookup by set/number - for now skip
        pass
    elif deck_parsed.get("leader") and isinstance(deck_parsed["leader"], dict) and "name" in deck_parsed["leader"]:
        key = card_identity_key(deck_parsed["leader"]["name"], deck_parsed["leader"].get("subtitle", ""))
        if key in card_db:
            result["leader"] = key
        else:
            result["unresolved"].append(("leader", key))
    
    if deck_parsed.get("base") and isinstance(deck_parsed["base"], dict) and "name" in deck_parsed["base"]:
        key = card_identity_key(deck_parsed["base"]["name"], deck_parsed["base"].get("subtitle", ""))
        if key in card_db:
            result["base"] = key
        else:
            result["unresolved"].append(("base", key))
    
    for card in deck_parsed.get("deck", []):
        if isinstance(card, dict) and "name" in card:
            key = card_identity_key(card["name"], card.get("subtitle", ""))
            if key in card_db:
                result["deck"].append({"key": key, "count": card["count"]})
            else:
                result["unresolved"].append(("deck", key))
    
    for card in deck_parsed.get("sideboard", []):
        if isinstance(card, dict) and "name" in card:
            key = card_identity_key(card["name"], card.get("subtitle", ""))
            if key in card_db:
                result["sideboard"].append({"key": key, "count": card["count"]})
            else:
                result["unresolved"].append(("sideboard", key))
    
    return result
