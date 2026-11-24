"""Normalise raw catalogue rows into the canonical :class:`CardData` shape.

The SWU-DB and Cardmarket payloads are not type-stable: a numeric field may
arrive as a string, a number or ``null``. This module is the infrastructure
boundary that converts those variants once, so the domain and analysis layers
only see canonical values.
"""

from typing import List, Mapping, Optional

from infrastructure.card_repository import CardData


def _as_str(value: object) -> str:
    return "" if value is None else str(value)


def _as_optional_str(value: object) -> Optional[str]:
    return None if value is None else str(value)


def _as_int(value: object) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _as_bool(value: object) -> bool:
    return bool(value)


def _as_str_list(value: object) -> List[str]:
    if not isinstance(value, (list, tuple)):
        return []
    return [str(item) for item in value]


def normalize_card_data(raw: Mapping[str, object]) -> CardData:
    """Convert one raw card row into canonical ``CardData``."""
    return {
        "name": _as_str(raw.get("name")),
        "subtitle": _as_str(raw.get("subtitle")),
        "set": _as_str(raw.get("set")),
        "number": _as_str(raw.get("number")),
        "type": _as_str(raw.get("type")),
        "aspects": _as_str_list(raw.get("aspects")),
        "traits": _as_str_list(raw.get("traits")),
        "arenas": _as_str_list(raw.get("arenas")),
        "cost": _as_int(raw.get("cost")),
        "power": _as_int(raw.get("power")),
        "hp": _as_int(raw.get("hp")),
        "keywords": _as_str_list(raw.get("keywords")),
        "unique": _as_bool(raw.get("unique")),
        "rarity": _as_str(raw.get("rarity")),
        "frontText": _as_optional_str(raw.get("frontText")),
        "epicAction": _as_optional_str(raw.get("epicAction")),
        "doubleSided": _as_bool(raw.get("doubleSided")),
        "marketPriceUsd": _as_optional_str(raw.get("marketPriceUsd")),
        "lowPriceUsd": _as_optional_str(raw.get("lowPriceUsd")),
        "foilPriceUsd": _as_optional_str(raw.get("foilPriceUsd")),
        "tcgplayerId": _as_optional_str(raw.get("tcgplayerId")),
        "cid": _as_optional_str(raw.get("cid")),
        "frontArt": _as_optional_str(raw.get("frontArt")),
        "artist": _as_optional_str(raw.get("artist")),
        "upgradePower": _as_int(raw.get("upgradePower")),
        "upgradeHp": _as_int(raw.get("upgradeHp")),
    }
