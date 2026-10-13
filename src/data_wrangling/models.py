# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = [
#     "marimo>=0.23.6",
# ]
# ///
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, TypeAdapter


class Member(BaseModel):
    """A club member."""

    name: str
    gender: Literal["m", "f"]
    membership: str
    id: str
    first_name: str
    last_name: str
    title: str


Members = TypeAdapter(list[Member])


Results = TypeAdapter(dict[str, dict[str, dict[str, list[str]]]])
