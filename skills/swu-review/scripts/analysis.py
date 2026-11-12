#!/usr/bin/env python3
"""Build the deterministic card-analysis JSON for a SWU Premier deck.

The output is the contract described by ``analysis.schema.json``. It covers
legality, main-deck composition, card sheets (leader, base and main deck),
draw odds, findings and limitations. Meta, matchups, strategy and recommendations
are deliberately out of scope.

Usage (library):

    from analysis import build_analysis
    data = build_analysis("deck.json")

The CLI lives in ``swu_analyze.py``.
"""

import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
# Add parent directory to path so infrastructure subpackage is findable
sys.path.insert(0, str(Path(__file__).parent.parent))

import constants as C
import suspended_list
import swu_cards as sc
from card_resolver import CardIndex, UnresolvedCard
from draw_odds import p_at_least_one
from validate_deck import load_deck
from domain.services.aspect_penalty_service import AspectPenaltyService
from infrastructure.card_repository import CardRepository


ZONE_ORDER = {"leader": 0, "base": 1, "main": 2}
TYPE_ORDER = {"Unit": 0, "Event": 1, "Upgrade": 2}


def _round1(value):
    return float(Decimal(str(value)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def _round2(value):
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _to_int(value):
    if value is None or value == "":
        return None
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _identity(key):
    name, subtitle = key
    return f"{name}|{subtitle}" if subtitle else name


def _display_name(card):
    name = card.get("name", "")
    subtitle = card.get("subtitle", "") or ""
    return f"{name} - {subtitle}" if subtitle else name


def _code(card):
    return f"{card.get('set', '')}{card.get('number', '')}"


def _detect_format(content):
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return "text"
    if isinstance(data, list):
        return "flat"
    if isinstance(data, dict):
        if isinstance(data.get("mainDeck"), list):
            return "case"
        if isinstance(data.get("deck"), list):
            return "swudb_json"
    return "json"


def _db_meta(card_db_path, card_db):
    meta_path = card_db_path.parent / "meta.json"
    if meta_path.exists():
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        data_as_of = str(meta.get("fetched_at", ""))[:10] or "unknown"
        source = meta.get("source", "unknown")
        sets = meta.get("sets") or sorted({c.get("set", "") for c in card_db.values()})
    else:
        data_as_of = "unknown"
        source = "unknown"
        sets = sorted({c.get("set", "") for c in card_db.values() if c.get("set")})

    canonical = json.dumps(
        [[list(key), card] for key, card in sorted(card_db.items())],
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return {
        "source": source,
        "data_as_of": data_as_of,
        "sets": list(sets),
        "schema_hash": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "cards": len(card_db),
    }


def _resolve_ref(index, ref, zone, unresolved):
    try:
        return index.resolve(ref)
    except UnresolvedCard as exc:
        safe_ref = ref if isinstance(ref, dict) else {"value": ref}
        unresolved.append({"zone": zone, "ref": safe_ref, "reason": exc.reason})
        return None


def _entry_count(entry):
    if not isinstance(entry, dict):
        return 1
    try:
        return int(entry.get("count", 1))
    except (TypeError, ValueError):
        return 1


def _zone_counts(content, deck_format):
    """Count leader/base entries from the raw input.

    ``validate_deck.load_deck`` keeps only the last leader/base entry and loses
    its count, so the analysis layer re-reads the raw JSON to enforce
    "exactly one leader, exactly one base". Text input returns ``None`` and
    falls back to the presence check.
    """
    if deck_format == "text":
        # Parse text format to extract leaders and bases
        leaders = []
        bases = []
        lines = content.strip().split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.lower() in ['leader', 'leaders']:
                current_section = 'leader'
                continue
            elif line.lower() in ['base', 'bases']:
                current_section = 'base'
                continue
            elif line.lower() in ['maindeck', 'main deck', 'main']:
                current_section = 'done'
                continue
            elif line.lower() in ['sideboard', 'side board']:
                current_section = 'done'
                continue
            
            # Parse card line
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
                parts = line.split(None, 1)
                if len(parts) == 2:
                    try:
                        count = int(parts[0])
                        rest = parts[1]
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
                leaders.append(card_entry)
            elif current_section == 'base' and current_section != 'done':
                bases.append(card_entry)
        
        return leaders, bases
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return None

    if deck_format == "case" and isinstance(data, dict):
        leaders = []
        bases = []
        for entry in data.get("mainDeck") or []:
            if not isinstance(entry, dict):
                continue
            card = entry.get("card") or {}
            type_field = card.get("type")
            type_name = type_field.get("name") if isinstance(type_field, dict) else type_field
            if type_name == "Leader":
                leaders.append(_entry_count(entry))
            elif type_name == "Base":
                bases.append(_entry_count(entry))
        return leaders, bases

    if deck_format == "flat" and isinstance(data, list):
        leaders = []
        bases = []
        for entry in data:
            if not isinstance(entry, dict):
                continue
            type_field = entry.get("type")
            type_name = type_field.get("name") if isinstance(type_field, dict) else type_field
            if type_name in ("Leader", "leaders"):
                leaders.append(_entry_count(entry))
            elif type_name in ("Base", "bases"):
                bases.append(_entry_count(entry))
        return leaders, bases

    if isinstance(data, dict):
        leaders = [_entry_count(data["leader"])] if isinstance(data.get("leader"), dict) else []
        bases = [_entry_count(data["base"])] if isinstance(data.get("base"), dict) else []
        return leaders, bases

    return None


def _card_ref(resolved, count=1):
    if resolved is None:
        return None
    key, card = resolved.key, resolved.card
    return {
        "identity": _identity(key),
        "name": key[0],
        "subtitle": key[1],
        "set": card.get("set", ""),
        "number": str(card.get("number", "")),
        "code": _code(card),
        "count": max(1, count),
        "resolved_by": resolved.resolved_by,
    }


def _deck_entry(key, card, copies):
    return {
        "identity": _identity(key),
        "name": key[0],
        "subtitle": key[1],
        "copies": copies,
    }


def _sheet(key, card, zone, copies, provided_aspects):
    text = card.get("frontText")
    text = None if text is None else str(text)

    arenas = list(card.get("arenas") or [])
    aspects = list(card.get("aspects") or [])
    traits = list(card.get("traits") or [])
    keywords = list(card.get("keywords") or [])

    tags = []
    tags.append(f"type:{card.get('type', 'Unknown')}")
    tags.extend(f"arena:{a}" for a in arenas)
    tags.extend(f"aspect:{a}" for a in aspects)
    tags.extend(f"trait:{t}" for t in traits)
    tags.extend(f"keyword:{k}" for k in keywords)
    if card.get("unique"):
        tags.append("unique")

    price = card.get("marketPriceUsd")
    try:
        has_price = price is not None and Decimal(str(price)) > 0
    except Exception:
        has_price = False

    return {
        "identity": _identity(key),
        "name": key[0],
        "subtitle": key[1],
        "set": card.get("set", ""),
        "number": str(card.get("number", "")),
        "code": _code(card),
        "copies": copies,
        "zone": zone,
        "type": card.get("type", "Unknown"),
        "cost": _to_int(card.get("cost")),
        "power": _to_int(card.get("power")),
        "hp": _to_int(card.get("hp")),
        "upgrade_power": _to_int(card.get("upgradePower")),
        "upgrade_hp": _to_int(card.get("upgradeHp")),
        "arenas": arenas,
        "aspects": aspects,
        "traits": traits,
        "keywords": keywords,
        "unique": bool(card.get("unique")),
        "rarity": card.get("rarity", ""),
        "text": text,
        "text_status": "present" if text is not None else "missing",
        "derived_tags": sorted(set(tags)),
        "epic_action": card.get("epicAction"),
        "double_sided": bool(card.get("doubleSided")),
        "flags": {
            "off_aspect": any(a not in provided_aspects for a in aspects),
            "no_price": not has_price,
            "unresolved_text": text is None,
        },
    }


def _zone_check(zone, resolved, counts):
    """Return (ok, detail) for "exactly one leader/base, count 1"."""
    if counts is None:
        if resolved is None:
            return False, f"No {zone} found or {zone} could not be resolved"
        return True, f"Exactly one {zone}"

    if not counts:
        return False, f"No {zone} found or {zone} could not be resolved"
    if len(counts) > 1:
        return False, f"Exactly one {zone} required (found {len(counts)} entries)"
    if counts[0] != 1:
        return False, f"Exactly one {zone} required (found count {counts[0]})"
    if resolved is None:
        return False, f"{zone.capitalize()} could not be resolved"
    return True, f"Exactly one {zone}"


def _legality(leader, base, main_counts, side_counts, unresolved, card_db, zone_counts, suspended=None):
    errors = []
    warnings = []
    checks = []

    suspended_keys = suspended.identities if suspended is not None else frozenset(C.SUSPENDED)
    if suspended is not None:
        warnings.extend(suspended.warnings)

    def check(check_id, ok, detail):
        checks.append({"id": check_id, "ok": ok, "detail": detail})
        if not ok:
            errors.append(detail)

    check(
        "unresolved",
        not unresolved,
        f"{len(unresolved)} unresolved card reference(s)" if unresolved else "All card references resolved",
    )

    leader_counts = zone_counts[0] if zone_counts is not None else None
    base_counts = zone_counts[1] if zone_counts is not None else None
    leader_ok, leader_detail = _zone_check("leader", leader, leader_counts)
    base_ok, base_detail = _zone_check("base", base, base_counts)
    check("leader", leader_ok, leader_detail)
    check("base", base_ok, base_detail)
    check(
        "leader_type",
        leader is None or leader.card.get("type") == "Leader",
        "Leader slot contains a Leader" if leader is None or leader.card.get("type") == "Leader"
        else "Leader slot does not contain a Leader",
    )
    check(
        "base_type",
        base is None or base.card.get("type") == "Base",
        "Base slot contains a Base" if base is None or base.card.get("type") == "Base"
        else "Base slot does not contain a Base",
    )

    bad_main = [key for key in main_counts if card_db[key].get("type") in ("Leader", "Base")]
    check(
        "main_zone",
        not bad_main,
        "Draw deck contains no leader or base" if not bad_main
        else f"Leader or base in draw deck: {', '.join(_identity(k) for k in bad_main)}",
    )

    bad_side = [key for key in side_counts if card_db[key].get("type") in ("Leader", "Base")]
    check(
        "sideboard_zone",
        not bad_side,
        "Sideboard contains no leader or base" if not bad_side
        else f"Leader or base in sideboard: {', '.join(_identity(k) for k in bad_side)}",
    )

    n = sum(main_counts.values())
    side_n = sum(side_counts.values())
    check("deck_size", n >= 50, f"Draw deck must be at least 50 cards (found: {n})")
    check("sideboard_size", side_n <= 10, f"Sideboard must be at most 10 cards (found: {side_n})")

    leader_key = leader.key if leader else None
    base_key = base.key if base else None
    combined = Counter(main_counts)
    combined.update(side_counts)
    over = [
        (key, count) for key, count in combined.items()
        if key not in (leader_key, base_key) and count > 3
    ]
    check(
        "copy_limit",
        not over,
        "All identities within 3 copies" if not over
        else "; ".join(f"{_identity(k)} has {c} copies (max 3)" for k, c in sorted(over)),
    )

    bad_sets = [
        key for key in combined
        if card_db[key].get("set") not in C.PREMIER_SETS
    ]
    check(
        "premier_sets",
        not bad_sets,
        "All cards from Premier sets" if not bad_sets
        else f"Non-Premier cards: {', '.join(_identity(k) for k in bad_sets)}",
    )

    suspended_cards = []
    for key in (leader_key, base_key, *combined):
        if key and key in suspended_keys and key not in suspended_cards:
            suspended_cards.append(key)
    check(
        "suspended",
        not suspended_cards,
        "No suspended cards" if not suspended_cards
        else f"Suspended cards: {', '.join(_identity(k) for k in suspended_cards)}",
    )

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "checks": checks,
    }


def _aspect_penalty(
    leader, base, main_counts: dict, card_repository: CardRepository
) -> dict:
    """Calculate aspect penalty using the domain service.

    Args:
        leader: Resolved leader card entity or None
        base: Resolved base card entity or None
        main_counts: Dictionary mapping card identities to copy counts
        card_repository: CardRepository implementation for data access

    Returns:
        Dictionary with aspect penalty information
    """
    # Create the domain service with injected repository
    penalty_service = AspectPenaltyService(card_repository)

    # Extract keys from leader and base entities
    leader_key = None
    base_key = None

    if leader is not None:
        # Get the key from the leader card entity
        # leader is a Resolved object; card is a dict
        leader_key = leader.card.get("identity", "") if leader.card else None

    if base is not None:
        # Get the key from the base card entity
        # base is a Resolved object; card is a dict
        base_key = base.card.get("identity", "") if base.card else None

    # Calculate penalty using the domain service
    return penalty_service.calculate_penalty(
        leader_key=leader_key,
        base_key=base_key,
        main_counts=main_counts
    )


def _composition(main_counts, card_db, data_as_of, cm_index=None):
    n = sum(main_counts.values())
    curve = Counter()
    no_cost = 0
    total_cost = 0
    cost_count = 0

    for key, copies in main_counts.items():
        cost = _to_int(card_db[key].get("cost"))
        if cost is None:
            no_cost += copies
        else:
            curve[cost] += copies
            total_cost += cost * copies
            cost_count += copies

    type_counts = Counter()
    for key, copies in main_counts.items():
        type_counts[card_db[key].get("type", "Unknown")] += copies

    ground = 0
    space = 0
    both = 0
    unit_slots = 0
    for key, copies in main_counts.items():
        card = card_db[key]
        if card.get("type") != "Unit":
            continue
        unit_slots += copies
        arenas = card.get("arenas") or []
        is_ground = "Ground" in arenas
        is_space = "Space" in arenas
        if is_ground:
            ground += copies
        if is_space:
            space += copies
        if is_ground and is_space:
            both += copies

    unique_slots = sum(
        copies for key, copies in main_counts.items() if card_db[key].get("unique")
    )

    total_usd = Decimal("0")
    priced = 0
    for key, copies in main_counts.items():
        price = card_db[key].get("marketPriceUsd")
        if price is None:
            continue
        try:
            value = Decimal(str(price))
        except Exception:
            continue
        if value > 0:
            total_usd += value * copies
            priced += copies

    composition = {
        "n": n,
        "curve": {str(cost): curve[cost] for cost in sorted(curve)},
        "curve_pct": {
            str(cost): _round1(curve[cost] / n * 100) if n else 0.0
            for cost in sorted(curve)
        },
        "mean_cost": {
            "value": _round2(total_cost / cost_count) if cost_count else 0.0,
            "denominator": cost_count,
        },
        "types": dict(sorted(type_counts.items())),
        "type_pct": {
            key: _round1(count / n * 100) if n else 0.0
            for key, count in sorted(type_counts.items())
        },
        "arenas": {
            "ground": ground,
            "space": space,
            "both": both,
            "unit_slots": unit_slots,
            "ground_pct": _round1(ground / unit_slots * 100) if unit_slots else 0.0,
            "space_pct": _round1(space / unit_slots * 100) if unit_slots else 0.0,
        },
        "distinct": len(main_counts),
        "unique_slots": unique_slots,
        "price": {
            "currency": C.PRICE_CURRENCY,
            "total": _round2(total_usd),
            "priced_slots": priced,
            "coverage_pct": _round1(priced / n * 100) if n else 0.0,
            "source": C.PRICE_SOURCE,
            "snapshot": data_as_of,
        },
        "no_cost_slots": no_cost,
    }

    # Optional Cardmarket EUR block. Kept separate from the USD total: the two
    # currencies are never summed or compared in the output.
    if cm_index is not None:
        composition["price_eur"] = cm_index.price_deck(main_counts, card_db)

    return composition


def _findings(composition, main_counts, card_db, unresolved):
    findings = []
    if unresolved or composition["n"] == 0:
        return findings

    arenas = composition["arenas"]
    if arenas["unit_slots"] > 0 and arenas["space_pct"] < 15.0:
        space_cards = [
            {"identity": _identity(key), "copies": copies}
            for key, copies in sorted(main_counts.items())
            if "Space" in (card_db[key].get("arenas") or [])
        ]
        verb = "is" if arenas["space"] == 1 else "are"
        findings.append({
            "id": "arena-imbalance",
            "severity": "warning",
            "category": "composition",
            "statement": (
                f"Only {arenas['space']} of {arenas['unit_slots']} unit slots "
                f"{verb} Space ({arenas['space_pct']}%)."
            ),
            "evidence": {
                "metric_path": "composition.arenas.space",
                "value": arenas["space"],
                "denominator": arenas["unit_slots"],
                "pct": arenas["space_pct"],
                "threshold": {"op": "<", "value": 15, "unit": "pct_of_unit_slots"},
                "cards": space_cards,
            },
            "source": {
                "kind": "threshold",
                "registry": "reference/findings.md#arena-imbalance",
                "version": "1",
            },
        })

    price = composition["price"]
    if price["coverage_pct"] < 100.0:
        unpriced = [
            {"identity": _identity(key), "copies": copies}
            for key, copies in sorted(main_counts.items())
            if card_db[key].get("marketPriceUsd") in (None, "", "0", "0.00")
        ]
        findings.append({
            "id": "price-coverage",
            "severity": "warning",
            "category": "composition",
            "statement": (
                f"{price['priced_slots']} of {composition['n']} main-deck slots "
                f"have a market price ({price['coverage_pct']}%)."
            ),
            "evidence": {
                "metric_path": "composition.price.coverage_pct",
                "value": price["priced_slots"],
                "denominator": composition["n"],
                "pct": price["coverage_pct"],
                "threshold": {"op": "<", "value": 100, "unit": "pct_of_main_deck_slots"},
                "cards": unpriced,
            },
            "source": {
                "kind": "threshold",
                "registry": "reference/findings.md#price-coverage",
                "version": "1",
            },
        })

    return sorted(findings, key=lambda f: f["id"])


def _limitations(db, composition, unresolved, findings):
    n = composition["n"]
    price = composition["price"]
    items = [
        {
            "id": "data-snapshot",
            "category": "data",
            "impact": "info",
            "statement": (
                f"Card data snapshot: {db['data_as_of']} from {db['source']} "
                f"({len(db['sets'])} sets, {db['cards']} cards)."
            ),
            "affects": ["legality", "composition", "cards", "draw_odds"],
            "detail": "Any set released after the snapshot is invisible to this analysis.",
            "mitigation": "Re-run fetch_cards.py and check db.data_as_of.",
        },
        {
            "id": "premier-only-db",
            "category": "data",
            "impact": "degraded",
            "statement": "Only Premier sets are fetched; older printings are not in the local DB.",
            "affects": ["legality", "cards"],
            "detail": (
                "Reprint legality by card version cannot be verified. An old printing "
                "may be reported as unresolved even when a Premier reprint exists."
            ),
            "mitigation": "Resolve by name+subtitle or add non-Premier printings to the DB.",
        },
    ]

    if unresolved:
        items.append({
            "id": "unresolved-identity",
            "category": "data",
            "impact": "blocking",
            "statement": f"{len(unresolved)} card reference(s) could not be resolved.",
            "affects": ["legality", "composition", "cards", "draw_odds"],
            "detail": (
                "Unresolved cards are excluded from composition and draw odds. "
                "Totals may not sum to N and composition findings are suppressed."
            ),
            "mitigation": "Fix the deck reference or refresh the card database.",
        })

    items.extend([
        {
            "id": "price-snapshot",
            "category": "data",
            "impact": "info" if price["coverage_pct"] == 100.0 else "degraded",
            "statement": (
                f"Prices are market {price['currency']} from {price['source']}, "
                f"snapshot {price['snapshot']}, coverage {price['coverage_pct']}%."
            ),
            "affects": ["composition.price"],
            "detail": "No foil, EUR, shipping or seller variation. Not an appraisal.",
            "mitigation": "Read the total as an estimate with the stated coverage.",
        },
        {
            "id": "draw-goldfish",
            "category": "model",
            "impact": "degraded",
            "statement": "Draw odds use a goldfish model.",
            "affects": ["draw_odds"],
            "detail": (
                "Opening hand 6, +2 per regroup, no mulligan, no other draw, "
                "no thinning, no recursion, no opponent interaction."
            ),
            "mitigation": "Read as an upper bound on seeing a card, not on playing it.",
        },
        {
            "id": "no-rules-engine",
            "category": "model",
            "impact": "info",
            "statement": "Card text is reproduced from the DB, not interpreted.",
            "affects": ["cards", "findings"],
            "detail": "Keywords are listed, not simulated. Draw, removal and ramp are not classified.",
            "mitigation": "Use the card sheets for manual reading.",
        },
        {
            "id": "rules-version",
            "category": "rules",
            "impact": "info",
            "statement": f"Legality follows the local rules verified on {C.RULES_VERSION}.",
            "affects": ["legality"],
            "detail": "Errata, suspensions or event-specific rules after that date are not included.",
            "mitigation": "Check the official Comprehensive Event Guide.",
        },
        {
            "id": "sideboard-legal-only",
            "category": "scope",
            "impact": "info",
            "statement": "The sideboard is used for legality only.",
            "affects": ["composition", "cards", "draw_odds"],
            "detail": "Sideboard cards get no composition slots, no card sheets and no draw odds.",
            "mitigation": "Analyse the sideboard separately if needed.",
        },
        {
            "id": "heuristic-thresholds",
            "category": "heuristic",
            "impact": "degraded" if findings else "info",
            "statement": "Findings use versioned heuristic thresholds, not rules of the game.",
            "affects": ["findings"],
            "detail": "A threshold crossing is an observation, not a verdict.",
            "mitigation": "Read reference/findings.md for the rationale.",
        },
        {
            "id": "text-semantics-not-analyzed",
            "category": "scope",
            "impact": "degraded",
            "statement": "Draw, removal and ramp are not classified in this version.",
            "affects": ["findings", "cards"],
            "detail": (
                "The absence of a finding is not a claim that the deck lacks an effect. "
                "A curated taxonomy is planned for v0.2."
            ),
            "mitigation": "Read card text manually.",
        },
    ])

    eur = composition.get("price_eur")
    if eur:
        items.append({
            "id": "price-eur-snapshot",
            "category": "data",
            "impact": "info" if eur["coverage_pct"] == 100.0 else "degraded",
            "statement": (
                f"EUR prices come from {eur['source']}, snapshot "
                f"{eur['snapshot']}, coverage {eur['coverage_pct']}% "
                f"({eur['basis']})."
            ),
            "affects": ["composition.price_eur"],
            "detail": (
                "One cheapest non-foil quote per card identity; foil, shipping, "
                "seller variation and currency conversion are not included. "
                "Never mix this total with the USD total."
            ),
            "mitigation": "Read the total as an estimate with the stated coverage.",
        })

    return items


def _out_of_scope():
    return [
        {"id": "meta", "statement": "Meta share, staple density and archetype data."},
        {"id": "matchups", "statement": "Matchup win rates and sideboard plans."},
        {"id": "strategy", "statement": "Play lines, target lines and scenarios."},
        {"id": "cuts_adds", "statement": "Recommended cuts or additions."},
        {"id": "council", "statement": "Multi-perspective council review."},
        {"id": "subjective_grades", "statement": "Card or deck quality scores without a rubric."},
        {"id": "price_speculation", "statement": "Price forecasts or investment advice."},
    ]


def _draw_odds(main_counts, card_db, n, max_round):
    rounds = list(range(0, max_round + 1))
    per_card = []
    for key, copies in sorted(main_counts.items()):
        probabilities = []
        expected = []
        for round_number in rounds:
            drawn = C.DRAW_HAND + round_number * C.DRAW_PER_REGROUP
            probabilities.append(_round1(p_at_least_one(n, copies, drawn) * 100))
            expected.append(_round2(drawn * copies / n) if n else 0.0)
        per_card.append({
            "identity": _identity(key),
            "name": _display_name(card_db[key]),
            "copies": copies,
            "p": probabilities,
            "expected_copies": expected,
        })

    return {
        "model": "hypergeometric_goldfish",
        "assumptions": [
            f"Population: {n} main-deck cards; leader and base are not drawn.",
            f"Opening hand: {C.DRAW_HAND} cards.",
            f"After each round, during the regroup phase, the player draws {C.DRAW_PER_REGROUP} cards.",
            "No mulligan, no other card draw, no thinning, no recursion, no opponent interaction.",
            "P(at least one by n draws) = 1 - C(N-K, n) / C(N, n).",
            "Expected copies by n draws = n * K / N.",
            "P(see) is not P(play): resources and playability are not modelled.",
        ],
        "n": n,
        "hand": C.DRAW_HAND,
        "draw_per_regroup": C.DRAW_PER_REGROUP,
        "mulligan": False,
        "rounds": rounds,
        "per_card": per_card,
    }


def build_analysis(deck_path, card_db_path=None, generated_at=None, max_round=None, cm_index=None, card_repository=None):
    """Build the full analysis dict for a deck file.

    ``cm_index`` is an optional :class:`cardmarket.CardmarketIndex`. When given,
    ``composition.price_eur`` is added next to the USD block; when omitted, the
    output is unchanged.

    Args:
        deck_path: Path to the deck file.
        card_db_path: Path to the card database JSON file.
        generated_at: ISO format timestamp when the analysis was generated.
        max_round: Maximum number of draws for draw odds calculation.
        cm_index: Optional Cardmarket index for price data.
        card_repository: CardRepository implementation for card data access.
            If not provided, an InMemoryCardRepository is used.
    """
    deck_path = Path(deck_path)
    content = deck_path.read_text(encoding="utf-8")
    input_sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
    deck_format = _detect_format(content)

    if card_db_path is None:
        card_db_path = C.CARD_DB_PATH
    card_db_path = Path(card_db_path)
    card_db = sc.load_swu_cards(card_db_path)
    index = CardIndex(card_db)

    deck = load_deck(deck_path)
    unresolved = []

    leader = _resolve_ref(index, deck.get("leader"), "leader", unresolved)
    base = _resolve_ref(index, deck.get("base"), "base", unresolved)

    main_counts = Counter()
    for entry in deck.get("deck", []):
        count = max(1, _entry_count(entry))
        resolved = _resolve_ref(index, entry, "main", unresolved)
        if resolved:
            main_counts[resolved.key] += count

    side_counts = Counter()
    for entry in deck.get("sideboard", []):
        count = max(1, _entry_count(entry))
        resolved = _resolve_ref(index, entry, "sideboard", unresolved)
        if resolved:
            side_counts[resolved.key] += count

    n = sum(main_counts.values())
    db = _db_meta(card_db_path, card_db)
    zone_counts = _zone_counts(content, deck_format)

    # Use provided card_repository or default to InMemoryCardRepository
    if card_repository is None:
        from infrastructure.in_memory_card_repository import InMemoryCardRepository
        card_repository = InMemoryCardRepository()

    legality = _legality(
        leader, base, main_counts, side_counts, unresolved, card_db, zone_counts,
        suspended=suspended_list.load(card_db),
    )
    legality["aspect_penalty"] = _aspect_penalty(leader, base, main_counts, card_repository)
    composition = _composition(main_counts, card_db, db["data_as_of"], cm_index)
    findings = _findings(composition, main_counts, card_db, unresolved)
    limitations = _limitations(db, composition, unresolved, findings)

    provided_aspects = set()
    if leader:
        provided_aspects.update(leader.card.get("aspects") or [])
    if base:
        provided_aspects.update(base.card.get("aspects") or [])

    cards = []
    if leader:
        cards.append(_sheet(
            leader.key, leader.card, "leader",
            max(1, _entry_count(deck.get("leader"))), provided_aspects,
        ))
    if base:
        cards.append(_sheet(
            base.key, base.card, "base",
            max(1, _entry_count(deck.get("base"))), provided_aspects,
        ))
    for key, copies in main_counts.items():
        cards.append(_sheet(key, card_db[key], "main", copies, provided_aspects))
    cards.sort(key=lambda c: (
        ZONE_ORDER.get(c["zone"], 9),
        TYPE_ORDER.get(c["type"], 9),
        c["cost"] if c["cost"] is not None else 999,
        c["name"],
        c["subtitle"],
    ))

    if generated_at is None:
        generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    if max_round is None:
        max_round = C.DRAW_MAX_ROUND

    return {
        "schema_version": C.SCHEMA_VERSION,
        "generated_at": generated_at,
        "tool_version": C.TOOL_VERSION,
        "rules_version": C.RULES_VERSION,
        "db": db,
        "input": {
            "path": str(deck_path),
            "sha256": input_sha256,
            "format": deck_format,
            "n": n,
        },
        "deck": {
            "leader": _card_ref(leader, _entry_count(deck.get("leader"))),
            "base": _card_ref(base, _entry_count(deck.get("base"))),
            "main_deck": [
                _deck_entry(key, card_db[key], copies)
                for key, copies in sorted(main_counts.items())
            ],
            "sideboard": [
                _deck_entry(key, card_db[key], copies)
                for key, copies in sorted(side_counts.items())
            ],
            "unresolved": unresolved,
        },
        "legality": legality,
        "composition": composition,
        "cards": cards,
        "draw_odds": _draw_odds(main_counts, card_db, n, max_round),
        "findings": findings,
        "limitations": limitations,
        "out_of_scope": _out_of_scope(),
    }
