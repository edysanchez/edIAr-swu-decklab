"""Read the Premier legal-set snapshot written by `fetch_legal_sets.py`.

Infrastructure layer: file access and shape validation only. It knows nothing
about TTLs, registries or warnings — those are policy, and stay in the
application module (`scripts/legal_sets.py`).
"""

import json
from pathlib import Path
from typing import Optional


class SnapshotError(RuntimeError):
    """The snapshot exists but cannot be trusted."""


def read(path) -> Optional[dict]:
    """Return the parsed snapshot, or ``None`` when the file is absent.

    A missing file is normal (the built-in registry takes over). A file that
    exists but is unreadable or misshapen raises: silently degrading a corrupt
    snapshot to the registry would hide exactly the drift this feature exists
    to catch.
    """
    snapshot_path = Path(path)
    if not snapshot_path.exists():
        return None

    try:
        data = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SnapshotError(f"could not read {snapshot_path}: {exc}") from exc

    if not isinstance(data, dict):
        raise SnapshotError(f"{snapshot_path} does not contain an object")

    legal = data.get("legal")
    if not isinstance(legal, list) or not all(isinstance(code, str) for code in legal):
        raise SnapshotError(f"{snapshot_path} has no usable 'legal' list")
    if not legal:
        # No source can legitimately answer "no set is Premier-legal", so an
        # empty list means the parser or the file is broken. Treating it as a
        # real answer would declare every deck illegal.
        raise SnapshotError(f"{snapshot_path} has an empty 'legal' list")

    return data
