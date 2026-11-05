# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = [
#     "marimo>=0.23.6",
# ]
# ///
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, TypeAdapter


class GenderInfo(BaseModel):
    """A gender identifier."""

    model_config = ConfigDict(extra="forbid")

    label: str


class EventInfo(BaseModel):
    """An event identifier."""

    model_config = ConfigDict(extra="forbid")

    label: str
    genders: list[str]


class SeriesInfo(BaseModel):
    """A series identifier."""

    model_config = ConfigDict(extra="forbid")

    label: str
    events: list[str]


class Lookups(BaseModel):
    """Lookup tables for meetings, events and genders."""

    model_config = ConfigDict(extra="forbid")

    genders: dict[str, GenderInfo]
    events: dict[str, EventInfo]
    series: dict[str, SeriesInfo]


class MeetingId(BaseModel):
    """A meeting identifier."""

    model_config = ConfigDict(extra="forbid")

    id: str
    series: str


class Member(BaseModel):
    """A club member."""

    model_config = ConfigDict(extra="ignore")

    name: str
    gender: Literal["m", "f"]
    membership: str
    id: str
    title: str


class HandicapEntry(BaseModel):
    """A single handicap entry for a given event and gender."""

    model_config = ConfigDict(extra="forbid")

    title: str
    handicap: float


Meetings = list[MeetingId]
meetings_adapter = TypeAdapter(Meetings)

Members = list[Member]
members_adapter = TypeAdapter(Members)

Results = dict[str, dict[str, dict[str, list[str]]]]
results_adapter = TypeAdapter(Results)

Handicaps = dict[str, dict[str, list[HandicapEntry]]]
handicaps_adapter = TypeAdapter(Handicaps)
