from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, TypeAdapter


class Member(BaseModel):
    name: str
    dob: str
    gender: Literal["m", "f"]
    club: str
    id: str
    first_name: str
    last_name: str
    title: str


Members = TypeAdapter(list[Member])


class ResultEntry(BaseModel):
    id: str
    title: str


Results = TypeAdapter(dict[str, dict[str, dict[str, list[ResultEntry]]]])
