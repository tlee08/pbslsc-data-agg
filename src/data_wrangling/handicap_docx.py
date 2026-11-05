"""Build a printable .docx from a handicaps dict.

Matches the layout of ``handicaps_261025.docx``: one bordered table per
event+gender, each starting on a new page, with columns "Name - Member
number" and "Handicap". Handicaps are sorted descending within each table.
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Mm

from data_wrangling.constants import WHC_EVENTS, WHC_GENDERS

if TYPE_CHECKING:
    from .models import Handicaps


_EVENT_TITLE = {
    "swim": "Swim",
    "board": "Board Paddle",
    "ski": "Surf Ski",
    "run": "Run",
    "flags": "Beach Flags",
}
_GENDER_TITLE = {"m": "Men", "f": "Women"}


def _title(event: str, gender: str) -> str:
    label = f"{_EVENT_TITLE[event]} - {_GENDER_TITLE[gender]}"
    return f"{label} (metres)" if event == "flags" else label


def _shade(cell, fill: str) -> None:
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    cell._tc.get_or_add_tcPr().append(shd)


def _write(
    cell,
    text: str,
    *,
    bold: bool = False,
    right: bool = False,
    fill: str | None = None,
) -> None:
    paragraph = cell.paragraphs[0]
    if right:
        paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = paragraph.add_run(text)
    run.bold = bold
    if fill:
        _shade(cell, fill)


def _fmt(handicap: float) -> str:
    """Format a handicap as a whole number where possible (7.0 -> '7', 6.5 -> '6.5')."""
    return f"{handicap:g}"


def build_handicap_docx(handicaps: Handicaps) -> bytes:
    """Return a .docx (bytes) with one table per event+gender, each on a page."""
    doc = Document()
    section = doc.sections[0]
    section.page_width = Mm(210)  # A4 portrait
    section.page_height = Mm(297)

    first = True
    for event in WHC_EVENTS:
        for gender in WHC_GENDERS:
            rows = handicaps.get(event, {}).get(gender, [])
            if not rows:
                continue
            rows = sorted(rows, key=lambda r: r.handicap, reverse=True)

            if not first:
                doc.add_page_break()
            first = False

            table = doc.add_table(rows=0, cols=2)
            table.style = "Table Grid"
            table.autofit = False

            title_cells = table.add_row().cells
            _write(
                title_cells[0].merge(title_cells[1]),
                _title(event, gender),
                bold=True,
                fill="F2F2F2",
            )

            header = table.add_row().cells
            _write(header[0], "Name - Member number", bold=True, fill="DDEBF7")
            _write(header[1], "Handicap", bold=True, right=True, fill="DDEBF7")

            for record in rows:
                cells = table.add_row().cells
                _write(cells[0], record.title)
                _write(cells[1], _fmt(record.handicap), bold=True, right=True)

            table.columns[0].width = Inches(6500 / 1440)
            table.columns[1].width = Inches(2147 / 1440)

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()
