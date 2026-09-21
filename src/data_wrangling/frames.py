"""Polars frame builders shared by the notebooks.

These functions convert the validated pydantic models into long-format
DataFrames. The long format is the primary working representation: members are
keyed by ``member_title``, and results are one row per placing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import polars as pl

if TYPE_CHECKING:
    from data_wrangling.models import Member


def members_to_frame(members: list[Member]) -> pl.DataFrame:
    """Convert validated members to a frame keyed by ``member_title``.

    Columns are the Member fields with ``title`` renamed to ``member_title``.
    """
    return pl.DataFrame([m.model_dump() for m in members]).rename(
        {"title": "member_title"},
    )


def results_to_frame(results: dict) -> pl.DataFrame:
    """Flatten validated results into a long frame.

    ``results`` is ``{date: {event: {gender: [ResultEntry, ...]}}}`` where the
    list order encodes placing. Returns one row per placing with columns:
    ``date``, ``event``, ``gender``, ``place`` (1-indexed), ``member_title``,
    ``member_id``.
    """
    records = [
        {
            "date": date,
            "event": event,
            "gender": gender,
            "place": place,
            "member_title": entry.title,
            "member_id": entry.id,
        }
        for date, events in results.items()
        for event, genders in events.items()
        for gender, entries in genders.items()
        for place, entry in enumerate(entries, 1)
    ]
    return pl.DataFrame(records, schema_overrides={"place": pl.Int64})
