# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = [
#     "marimo>=0.23.6",
# ]
# ///
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, TypeAdapter


class Member(BaseModel):
    """A club member."""

    model_config = ConfigDict(extra="ignore")

    name: str
    gender: Literal["m", "f"]
    membership: str
    id: str
    title: str


Members = TypeAdapter(list[Member])


Results = TypeAdapter(dict[str, dict[str, dict[str, list[str]]]])
