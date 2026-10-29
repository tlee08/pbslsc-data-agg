"""Handicap update logic (mirrors the 'Method' sheet in proposed_handicaps_261018_A.xlsx)."""

from __future__ import annotations

import math

EVENTS = ["swim", "board", "ski", "run", "flags"]
GENDERS = ["m", "f"]


def _key(title: str) -> str:
    """Member id from a results entry 'Name - ID', else the bare name."""
    return title.rsplit(" - ", 1)[1] if " - " in title else title


def _rec_key(record: dict) -> str:
    """Match key for an old handicap record: member number, else name."""
    number = record.get("number")
    return record.get("name", "") if number in (None, "", "(none)") else number


def update_handicaps(old: dict, meeting_results: dict, config: dict) -> dict:
    """Return updated handicaps in the same ``{event: {gender: [records]}}`` shape.

    Handicap = start delay (seconds, metres for flags); bigger = later start.
    Per discipline+gender pool: ``change = step * (middle - place)`` where
    ``middle = 1 + ratio * (field - 1)``. The change is capped at
    ``max_change``, the new handicap is floored at 0 and rounded up to the
    nearest ``round_to``. Non-racers carry their old handicap forward.

    ``config`` keys: ``step``, ``max_change``, ``round_to`` (per-event dicts)
    and ``middle_ratio`` (float).
    """
    new: dict = {}
    for event in EVENTS:
        new[event] = {}
        for gender in GENDERS:
            pool = {_rec_key(r): r for r in old.get(event, {}).get(gender, [])}
            entries = meeting_results.get(event, {}).get(gender, [])
            middle = 1 + config["middle_ratio"] * (len(entries) - 1)
            updated: dict = {}
            for place, title in enumerate(entries, 1):
                key = _key(title)
                record = pool.get(key, {})
                old_handicap = record.get("handicap", 0)
                change = config["step"][event] * (middle - place)
                change = max(
                    -config["max_change"][event],
                    min(config["max_change"][event], change),
                )
                raw = max(0.0, old_handicap + change)
                updated[key] = {
                    "name": record.get("name")
                    or (title.rsplit(" - ", 1)[0] if " - " in title else title),
                    "number": record.get("number")
                    or (key if " - " in title else "(none)"),
                    "handicap": math.ceil(raw / config["round_to"][event])
                    * config["round_to"][event],
                    "previous": old_handicap,
                }
            for key, record in pool.items():
                if key not in updated:
                    updated[key] = {**record, "previous": record.get("handicap", 0)}
            kept = [r for r in updated.values() if r["handicap"] > 0]
            kept.sort(key=lambda r: r["handicap"], reverse=True)
            new[event][gender] = kept
    return new
