"""Handicap update logic (mirrors the 'Method' sheet in proposed_handicaps_261018_A.xlsx)."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from .models import HandicapEntry

if TYPE_CHECKING:
    from .models import Handicaps, Results

EVENTS = ["swim", "board", "ski", "run", "flags"]
GENDERS = ["m", "f"]


class HandicapConfig(BaseModel):
    """Handicap update configuration."""

    model_config = ConfigDict(extra="forbid")

    middle_ratio: float
    step: dict[str, float]
    max_change: dict[str, float]
    round_to: dict[str, float]


def update_handicaps(
    old: Handicaps,
    meeting_results: Results,
    config: HandicapConfig,
) -> Handicaps:
    """Return updated handicaps as ``{event: {gender: [HandicapEntry]}}``.

    Handicap = start delay (seconds, metres for flags); bigger = later start.
    Per discipline+gender pool: ``change = step * (middle - place)`` where
    ``middle = 1 + ratio * (field - 1)``, capped at ``max_change``, floored at
    0 and rounded up to ``round_to``. Non-racers carry forward. Records are
    keyed by their ``title``.

    ``config``: ``step``, ``max_change``, ``round_to`` (per-event) and
    ``middle_ratio`` (float).
    """
    new: Handicaps = {}
    for event in EVENTS:
        new[event] = {}
        for gender in GENDERS:
            pool = {r.title: r for r in old.get(event, {}).get(gender, [])}
            entries = meeting_results.get(event, {}).get(gender, [])
            middle = 1 + config.middle_ratio * (len(entries) - 1)
            updated: dict[str, HandicapEntry] = {}
            for place, title in enumerate(entries, 1):
                record = pool.get(
                    title,
                    HandicapEntry(title=title, handicap=0.0),
                )
                change = config.step[event] * (middle - place)
                change = max(
                    -config.max_change[event],
                    min(config.max_change[event], change),
                )
                handicap = max(0.0, record.handicap + change)
                updated[title] = HandicapEntry(
                    title=title,
                    handicap=math.ceil(handicap / config.round_to[event])
                    * config.round_to[event],
                )
            for title, record in pool.items():
                if title not in updated:
                    updated[title] = record
            kept = [r for r in updated.values() if r.handicap > 0]
            kept.sort(key=lambda r: r.handicap, reverse=True)
            new[event][gender] = kept
    return new
