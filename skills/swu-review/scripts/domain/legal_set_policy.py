"""Domain policy: is a set legal in Premier on a given date?

Pure logic, no files, no network, no warnings. Taken from `docs/rules.md`:

- the Premier-legal product list is the primary criterion;
- a product whose effective date (its release, or the date the source says it
  becomes legal) is **after** the list was published is legal from that date,
  which is how the guide's lag is resolved;
- a rotation symbol is never proof of legality, so rotation is not modelled.

The date override is deliberately narrow: only the gap between the list's date
and today. A product released long before the list and absent from it was
removed on purpose (rotation), so it must stay illegal. Widening the window to
"any past release" would legalise every rotated set as soon as the list arrives
truncated, which is the worst failure this feature can produce: a silent
"legal" on an illegal deck.
"""

from dataclasses import dataclass
from datetime import date
from typing import Mapping, Optional


@dataclass(frozen=True)
class LegalSetPolicy:
    """Legal set codes, the list's date, and known effective dates."""

    codes: frozenset
    effective_from: Mapping[str, date]
    as_of: Optional[date]

    def is_legal(self, set_code: str, on: date) -> bool:
        """Return whether ``set_code`` may be used in Premier on ``on``."""
        if set_code in self.codes:
            return True

        available = self.effective_from.get(set_code)
        if available is None or self.as_of is None:
            # No list date means no lag window: never infer legality.
            return False

        return self.as_of < available <= on

    def available_but_unlisted(self, on: date):
        """Products that became available after the list and are still missing.

        These are legal per `docs/rules.md` (the date wins over a lagging list)
        and are worth surfacing: they mean the list is behind.
        """
        if self.as_of is None:
            return []

        return sorted(
            code
            for code, available in self.effective_from.items()
            if self.as_of < available <= on and code not in self.codes
        )
