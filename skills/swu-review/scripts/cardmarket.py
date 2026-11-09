#!/usr/bin/env python3
"""Cardmarket (EUR) price source for SWU cards.

Cardmarket publishes bulk product catalogs and price guides that anyone may
import into their own application. We use only those downloads; the website
itself blocks crawlers and is never scraped.

Two files drive everything:

* ``products_singles_21.json`` - product catalog (identity -> metacard/product)
* ``price_guide_21.json`` - latest price guide (product -> trend/low)

The catalog has one entry per printing (Normal, Hyperspace, Foil, ...) but does
not label the variant. A single card identity can therefore have several
products with the same name. To answer "what does this card cost?", we take the
cheapest **non-foil** ``trend`` among the products of its metacards. That is the
price a buyer would realistically pay, but it is not strictly the Normal
printing; the result carries ``basis`` to make that explicit. The price guide
has no language or seller-country dimension: each quote aggregates all print
languages, seller countries and conditions, and the catalog uses the English
canonical card name.

Bases are sold as ``"<base> // <token>"`` (one product per token variant) or by
their plain name, so they are matched by the name prefix before ``" // "`` and
then by the bare base name.

Everything here is pure data manipulation: :func:`load_index` is the only
function that touches the local cache.
"""

import json
import re
import unicodedata
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import constants as C
import swu_cards as sc

GAME_ID = C.CARDMARKET_GAME_ID
SET_EXPANSIONS = {
    set_code: tuple(expansions)
    for set_code, expansions in C.CARDMARKET_SET_EXPANSIONS.items()
}


def normalize(text):
    """Fold a card name to a comparison key.

    Accents are stripped, the text is lower-cased and everything that is not a
    letter or a digit becomes a single space. ``"Yoda’s – Édition"`` and
    ``"yodas edition"`` therefore compare equal.
    """
    folded = unicodedata.normalize("NFKD", str(text or ""))
    folded = folded.encode("ascii", "ignore").decode("ascii").lower()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", folded).split())


def _positive(value):
    """Return ``value`` as a positive float, or ``None`` when it is not a price."""
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _snapshot_date(prices):
    """Extract the ``YYYY-MM-DD`` date from a price guide ``createdAt`` field."""
    raw = str((prices or {}).get("createdAt") or "")
    match = re.match(r"^(\d{4}-\d{2}-\d{2})", raw)
    return match.group(1) if match else "unknown"


class CardmarketIndex:
    """In-memory index from SWU card identity to a Cardmarket quote."""

    def __init__(self, catalog, prices, set_expansions=None):
        self.set_expansions = {
            set_code: tuple(exps)
            for set_code, exps in (set_expansions or SET_EXPANSIONS).items()
        }
        self.snapshot = _snapshot_date(prices)

        self._prices = {
            row.get("idProduct"): row
            for row in (prices or {}).get("priceGuides") or []
            if row.get("idProduct") is not None
        }

        # (set, idMetacard) -> [idProduct], (set, name) -> {idMetacard},
        # (set, base name) -> {idMetacard}.
        self._products = {}
        self._by_name = {}
        self._by_base_prefix = {}

        for product in (catalog or {}).get("products") or []:
            expansion = product.get("idExpansion")
            metacard = product.get("idMetacard")
            product_id = product.get("idProduct")
            if not metacard or product_id is None:
                continue
            name = str(product.get("name") or "")
            for set_code, expansions in self.set_expansions.items():
                if expansion not in expansions:
                    continue
                self._products.setdefault((set_code, metacard), []).append(product_id)
                self._by_name.setdefault((set_code, normalize(name)), set()).add(metacard)
                if "//" in name:
                    prefix = normalize(name.split("//", 1)[0])
                    self._by_base_prefix.setdefault((set_code, prefix), set()).add(metacard)

    def quote(self, set_code, name, subtitle="", card_type=""):
        """Return the cheapest non-foil quote for a card identity.

        The result is ``{"trend", "low", "id_product"}`` or ``None`` when the
        card is unknown or has no usable non-foil price.
        """
        identity = normalize(f"{name} {subtitle}".strip())
        metacards = self._by_name.get((set_code, identity))

        if not metacards and str(card_type or "").strip().lower() == "base":
            base_name = normalize(name)
            metacards = self._by_base_prefix.get((set_code, base_name))
            if not metacards:
                metacards = self._by_name.get((set_code, base_name))

        if not metacards:
            return None

        best = None
        for metacard in metacards:
            for product_id in self._products.get((set_code, metacard), []):
                row = self._prices.get(product_id) or {}
                trend = _positive(row.get("trend"))
                if trend is None:
                    continue
                if best is None or trend < best[0]:
                    best = (trend, _positive(row.get("low")), product_id)

        if best is None:
            return None
        return {"trend": best[0], "low": best[1], "id_product": best[2]}

    def price_deck(self, main_counts, card_db):
        """Price a main deck keyed by ``(name, subtitle)``.

        ``card_db`` maps the same keys to cards carrying ``set`` and ``type``.
        Returns the EUR block used by ``composition.price_eur``.
        """
        n = sum(main_counts.values())
        total = Decimal("0")
        priced = 0

        for key, copies in main_counts.items():
            card = card_db.get(key) or {}
            quote = self.quote(
                card.get("set", ""),
                key[0],
                key[1] if len(key) > 1 else "",
                card.get("type", ""),
            )
            if quote is None:
                continue
            total += Decimal(str(quote["trend"])) * copies
            priced += copies

        amount = total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return {
            "currency": C.CARDMARKET_PRICE_CURRENCY,
            "total": float(amount),
            "priced_slots": priced,
            "coverage_pct": round(priced / n * 100, 1) if n else 0.0,
            "source": C.CARDMARKET_PRICE_SOURCE,
            "snapshot": self.snapshot,
            "basis": C.CARDMARKET_PRICE_BASIS,
        }


def default_cache_dir():
    """Default cache location: ``data/cm/``."""
    return sc.get_data_dir() / C.CARDMARKET_CACHE_DIR


def load_index(cache_dir=None):
    """Load a :class:`CardmarketIndex` from the local cache.

    Returns ``None`` when either bulk file is missing, so callers can run
    without the optional EUR source.
    """
    cache_dir = Path(cache_dir) if cache_dir is not None else default_cache_dir()
    catalog_path = cache_dir / C.CARDMARKET_CATALOG_FILE
    prices_path = cache_dir / C.CARDMARKET_PRICE_FILE

    if not catalog_path.exists() or not prices_path.exists():
        return None

    with open(catalog_path, "r", encoding="utf-8") as f:
        catalog = json.load(f)
    with open(prices_path, "r", encoding="utf-8") as f:
        prices = json.load(f)

    return CardmarketIndex(catalog, prices, SET_EXPANSIONS)
