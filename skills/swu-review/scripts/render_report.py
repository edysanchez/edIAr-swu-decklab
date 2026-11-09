#!/usr/bin/env python3
"""Render ``analysis.json`` as a human-readable Markdown report.

This module is a pure view. It never recomputes a metric: every number in the
report is read from the analysis dict. If a value is wrong, the fix belongs in
``analysis.py``, not here.

Usage (library)::

    from render_report import render_report
    markdown = render_report(analysis_dict)
"""

from collections import Counter


def _fmt(value, places=None):
    if value is None:
        return "—"
    if places is not None:
        return f"{value:.{places}f}"
    return str(value)


def _pct(value):
    return "—" if value is None else f"{value:.1f}%"


def _escape(text):
    return str(text).replace("|", "\\|").replace("\n", " ")


def _table(headers, rows):
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return "\n".join(lines)


def _data_health(analysis):
    limitations = analysis.get("limitations") or []
    counts = Counter(item.get("impact", "info") for item in limitations)
    blocking = [item for item in limitations if item.get("impact") == "blocking"]
    degraded = [item for item in limitations if item.get("impact") == "degraded"]

    if not blocking and not degraded:
        return ""

    parts = [
        f"{counts.get('blocking', 0)} blocking",
        f"{counts.get('degraded', 0)} degraded",
        f"{counts.get('info', 0)} info",
    ]
    if blocking:
        ids = ", ".join(item.get("id", "?") for item in blocking)
        parts.append(f"blocking ids: {ids}")

    return (
        "> **Data health:** " + "; ".join(parts) + ".\n"
        "> Read the affected numbers with the caveats in "
        "[Limitations](#limitations).\n"
    )


def _title(analysis):
    deck = analysis.get("deck") or {}
    leader = deck.get("leader")
    leader_name = leader["name"] if leader else "unknown leader"
    lines = [f"# SWU Review — {leader_name}", ""]

    base = deck.get("base")
    if base:
        base_text = base["name"]
        if base.get("subtitle"):
            base_text += f" — {base['subtitle']}"
        lines.append(f"**Leader:** {leader_name}  ")
        lines.append(f"**Base:** {base_text}")
    else:
        lines.append(f"**Leader:** {leader_name}")
    lines.append("")
    return "\n".join(lines)


def _provenance(analysis):
    db = analysis.get("db") or {}
    source = analysis.get("input") or {}
    lines = ["## Provenance", ""]
    rows = [
        ("Generated at", analysis.get("generated_at")),
        ("Tool version", analysis.get("tool_version")),
        ("Rules version", analysis.get("rules_version")),
        ("Schema version", analysis.get("schema_version")),
        ("Input path", source.get("path")),
        ("Input SHA-256", source.get("sha256")),
        ("Input format", source.get("format")),
        ("Card DB source", db.get("source")),
        ("Card DB snapshot", db.get("data_as_of")),
        ("Card DB sets", ", ".join(db.get("sets") or [])),
        ("Card DB cards", db.get("cards")),
        ("Card DB schema hash", db.get("schema_hash")),
    ]
    lines.append(_table(["Field", "Value"], rows))
    lines.append("")
    return "\n".join(lines)


def _legality(analysis):
    legality = analysis.get("legality") or {}
    lines = ["## Legality", ""]
    if legality.get("ok"):
        lines.append("**Result:** legal according to the local rules version.")
    else:
        lines.append("**Result:** illegal. The errors below block the deck.")
    lines.append("")

    errors = legality.get("errors") or []
    if errors:
        lines.append("### Errors")
        lines.append("")
        for error in errors:
            lines.append(f"- {error}")
        lines.append("")

    warnings = legality.get("warnings") or []
    if warnings:
        lines.append("### Warnings")
        lines.append("")
        for warning in warnings:
            lines.append(f"- {warning}")
        lines.append("")

    checks = legality.get("checks") or []
    if checks:
        lines.append("### Checks")
        lines.append("")
        lines.append(_table(
            ["Check", "Result", "Detail"],
            [
                (
                    check.get("id"),
                    "pass" if check.get("ok") else "fail",
                    _escape(check.get("detail", "")),
                )
                for check in checks
            ],
        ))
        lines.append("")

    penalty = legality.get("aspect_penalty") or {}
    lines.append("### Aspect penalty")
    lines.append("")
    lines.append(
        f"Total penalty: **{penalty.get('total', 0)}**; "
        f"maximum on a single card: **{penalty.get('max', 0)}**."
    )
    lines.append("")
    per_card = penalty.get("per_card") or []
    if per_card:
        lines.append(_table(
            ["Card", "Copies", "Penalty", "Missing aspects"],
            [
                (
                    _escape(item.get("identity", "")),
                    item.get("copies"),
                    item.get("penalty"),
                    ", ".join(item.get("missing_aspects") or []) or "—",
                )
                for item in per_card
            ],
        ))
        lines.append("")
    return "\n".join(lines)


def _composition(analysis):
    comp = analysis.get("composition") or {}
    arenas = comp.get("arenas") or {}
    price = comp.get("price") or {}
    price_eur = comp.get("price_eur") or {}
    mean = comp.get("mean_cost") or {}

    rows = [
        ("Main deck", comp.get("n")),
        ("Distinct cards", comp.get("distinct")),
        ("Unique slots", comp.get("unique_slots")),
        (
            "Mean cost",
            f"{_fmt(mean.get('value'), 2)} "
            f"(denominator {mean.get('denominator')})",
        ),
        (
            "Ground units",
            f"{arenas.get('ground')} / {arenas.get('unit_slots')} "
            f"({_pct(arenas.get('ground_pct'))})",
        ),
        (
            "Space units",
            f"{arenas.get('space')} / {arenas.get('unit_slots')} "
            f"({_pct(arenas.get('space_pct'))})",
        ),
        (
            "Both arenas",
            f"{arenas.get('both')} / {arenas.get('unit_slots')}",
        ),
        (
            f"Deck price ({price.get('currency')})",
            f"{_fmt(price.get('total'), 2)} "
            f"({price.get('priced_slots')}/{comp.get('n')} slots, "
            f"{_pct(price.get('coverage_pct'))})",
        ),
    ]
    if price_eur:
        rows.append((
            f"Deck price ({price_eur.get('currency')})",
            f"{_fmt(price_eur.get('total'), 2)} "
            f"({price_eur.get('priced_slots')}/{comp.get('n')} slots, "
            f"{_pct(price_eur.get('coverage_pct'))}; "
            f"{price_eur.get('source')}, {price_eur.get('snapshot')})",
        ))

    lines = ["## Composition snapshot", ""]
    lines.append(_table(
        ["Metric", "Value"],
        rows,
    ))
    lines.append("")

    curve = comp.get("curve") or {}
    curve_pct = comp.get("curve_pct") or {}
    if curve:
        lines.append("### Cost curve")
        lines.append("")
        lines.append(_table(
            ["Cost", "Cards", "% of N"],
            [
                (cost, curve.get(cost), _pct(curve_pct.get(cost)))
                for cost in sorted(curve, key=lambda value: int(value))
            ],
        ))
        lines.append("")

    types = comp.get("types") or {}
    type_pct = comp.get("type_pct") or {}
    if types:
        lines.append("### Types")
        lines.append("")
        lines.append(_table(
            ["Type", "Slots", "% of N"],
            [
                (card_type, types[card_type], _pct(type_pct.get(card_type)))
                for card_type in sorted(types)
            ],
        ))
        lines.append("")

    return "\n".join(lines)


def _card_sheet(card):
    name = card.get("name", "Unknown")
    subtitle = card.get("subtitle") or ""
    heading = f"#### {name}" + (f" — {subtitle}" if subtitle else "")
    lines = [heading, ""]

    facts = [
        ("Code", _fmt(card.get("code"))),
        ("Copies", _fmt(card.get("copies"))),
        ("Type", _fmt(card.get("type"))),
        ("Cost", _fmt(card.get("cost"))),
        ("Power", _fmt(card.get("power"))),
        ("HP", _fmt(card.get("hp"))),
        ("Arenas", ", ".join(card.get("arenas") or []) or "—"),
        ("Aspects", ", ".join(card.get("aspects") or []) or "—"),
        ("Traits", ", ".join(card.get("traits") or []) or "—"),
        ("Keywords", ", ".join(card.get("keywords") or []) or "—"),
        ("Rarity", _fmt(card.get("rarity"))),
        ("Unique", "yes" if card.get("unique") else "no"),
    ]
    lines.append(_table(["Field", "Value"], facts))
    lines.append("")

    text = card.get("text")
    if text is None or card.get("text_status") == "missing":
        lines.append("_Text missing from local database._")
    elif str(text).strip() == "":
        lines.append("_No card text in local database._")
    else:
        lines.append("> " + str(text).replace("\n", "\n> "))
    lines.append("")

    flags = card.get("flags") or {}
    notes = []
    if flags.get("off_aspect"):
        notes.append("off-aspect")
    if flags.get("no_price"):
        notes.append("no price")
    if flags.get("unresolved_text"):
        notes.append("text missing")
    if notes:
        lines.append(f"**Flags:** {', '.join(notes)}")
        lines.append("")

    tags = card.get("derived_tags") or []
    if tags:
        lines.append(f"**Derived tags:** {', '.join(tags)}")
        lines.append("")
    return "\n".join(lines)


def _cards(analysis):
    cards = analysis.get("cards") or []
    lines = ["## Card sheets", ""]
    if not cards:
        lines.append("No card sheets available.")
        lines.append("")
        return "\n".join(lines)

    zones = {"leader": "Leader", "base": "Base", "main": "Main deck"}
    current = None
    for card in cards:
        zone = card.get("zone", "main")
        if zone != current:
            current = zone
            lines.append(f"### {zones.get(zone, zone.title())}")
            lines.append("")
        lines.append(_card_sheet(card))
    return "\n".join(lines)


def _draw_odds(analysis):
    odds = analysis.get("draw_odds") or {}
    rounds = odds.get("rounds") or []
    per_card = odds.get("per_card") or []

    lines = ["## Draw odds", ""]
    lines.append(
        f"Model: `{odds.get('model')}`. Population {odds.get('n')} cards; "
        f"opening hand {odds.get('hand')}; "
        f"+{odds.get('draw_per_regroup')} per regroup; "
        f"mulligan: {'yes' if odds.get('mulligan') else 'no'}."
    )
    lines.append("")

    assumptions = odds.get("assumptions") or []
    if assumptions:
        lines.append("### Assumptions")
        lines.append("")
        for assumption in assumptions:
            lines.append(f"- {assumption}")
        lines.append("")

    if per_card:
        lines.append("### Probability of seeing at least one copy")
        lines.append("")
        headers = ["Card", "Copies"] + [f"R{round_number}" for round_number in rounds]
        rows = []
        for card in per_card:
            probabilities = card.get("p") or []
            rows.append(
                [_escape(card.get("name", "")), card.get("copies")]
                + [_pct(value) for value in probabilities]
            )
        lines.append(_table(headers, rows))
        lines.append("")

        lines.append("### Expected copies drawn")
        lines.append("")
        rows = []
        for card in per_card:
            expected = card.get("expected_copies") or []
            rows.append(
                [_escape(card.get("name", "")), card.get("copies")]
                + [_fmt(value, 2) for value in expected]
            )
        lines.append(_table(headers, rows))
        lines.append("")
    return "\n".join(lines)


def _findings(analysis):
    findings = analysis.get("findings") or []
    lines = ["## Findings", ""]
    if not findings:
        lines.append("No finding crossed a documented threshold.")
        lines.append("")
        return "\n".join(lines)

    for finding in findings:
        evidence = finding.get("evidence") or {}
        threshold = evidence.get("threshold") or {}
        lines.append(f"### `{finding.get('id')}` ({finding.get('severity')})")
        lines.append("")
        lines.append(finding.get("statement", ""))
        lines.append("")
        lines.append(_table(
            ["Field", "Value"],
            [
                ("Category", finding.get("category")),
                ("Metric", evidence.get("metric_path")),
                ("Value", evidence.get("value")),
                ("Denominator", evidence.get("denominator")),
                ("Percentage", _pct(evidence.get("pct"))),
                (
                    "Threshold",
                    f"{threshold.get('op')} {threshold.get('value')} "
                    f"({threshold.get('unit')})",
                ),
                ("Registry", (finding.get("source") or {}).get("registry")),
                ("Registry version", (finding.get("source") or {}).get("version")),
            ],
        ))
        lines.append("")

        cards = evidence.get("cards") or []
        if cards:
            lines.append(_table(
                ["Card", "Copies"],
                [
                    (_escape(card.get("identity", "")), card.get("copies"))
                    for card in cards
                ],
            ))
            lines.append("")
    return "\n".join(lines)


def _limitations(analysis):
    limitations = analysis.get("limitations") or []
    lines = ["## Limitations", ""]
    if not limitations:
        lines.append("No relevant limitation.")
        lines.append("")
        return "\n".join(lines)

    lines.append(_table(
        ["ID", "Impact", "Category", "Statement"],
        [
            (
                f"`{item.get('id')}`",
                item.get("impact"),
                item.get("category"),
                _escape(item.get("statement", "")),
            )
            for item in limitations
        ],
    ))
    lines.append("")

    for item in limitations:
        affects = item.get("affects") or []
        detail = item.get("detail") or ""
        mitigation = item.get("mitigation") or ""
        if not (affects or detail or mitigation):
            continue
        lines.append(f"- **`{item.get('id')}`**")
        if affects:
            lines.append(f"  - Affects: {', '.join(affects)}")
        if detail:
            lines.append(f"  - Detail: {detail}")
        if mitigation:
            lines.append(f"  - Mitigation: {mitigation}")
    lines.append("")
    return "\n".join(lines)


def _out_of_scope(analysis):
    items = analysis.get("out_of_scope") or []
    lines = ["## Out of scope", ""]
    if not items:
        lines.append("No explicit exclusions recorded.")
        lines.append("")
        return "\n".join(lines)
    lines.append(_table(
        ["ID", "Statement"],
        [
            (f"`{item.get('id')}`", _escape(item.get("statement", "")))
            for item in items
        ],
    ))
    lines.append("")
    return "\n".join(lines)


def render_report(analysis):
    """Render an analysis dict as Markdown. Does not mutate the input."""
    blocks = [
        _title(analysis),
        _data_health(analysis),
        _provenance(analysis),
        _legality(analysis),
        _composition(analysis),
        _cards(analysis),
        _draw_odds(analysis),
        _findings(analysis),
        _limitations(analysis),
        _out_of_scope(analysis),
    ]
    return "\n".join(block for block in blocks if block).rstrip() + "\n"


if __name__ == "__main__":
    import json
    import sys

    with open(sys.argv[1], "r", encoding="utf-8") as handle:
        print(render_report(json.load(handle)), end="")
