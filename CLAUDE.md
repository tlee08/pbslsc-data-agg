# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Data wrangling tools for Palmy WHC (surf lifesaving club) — processes member data, race results, handicaps, and points for weekly competitions (WHC = Weekly Handicap Competition).

## Environment

Uses [uv](https://docs.astral.sh/uv/) for Python package management (Python 3.12+).

**Always use `uv run` to execute any Python or marimo command — never call `python`, `marimo`, or `pip` directly.**

```bash
# Install dependencies
uv sync

# Run a marimo notebook interactively
uv run marimo edit code/points_calc.py

# Run a marimo notebook as a script (non-interactive)
uv run marimo run code/points_calc.py

# Run a Python script directly
uv run python code/some_script.py
```

All scripts must be run from the repo root (paths like `results/`, `members/`, `hcaps/` are relative to root).

## Code Architecture

All scripts in `code/` are [marimo](https://marimo.io/) reactive notebooks (`.py` files). They are structured as a DAG of `@app.cell` functions — cells declare their inputs as function parameters and outputs as return values.

### Scripts

All notebooks use `mo.ui.file()` upload widgets — no hardcoded paths. Files that produce output use `mo.download()` so the user saves to wherever they want.

| Script | Purpose | File uploads required | Downloads produced |
|---|---|---|---|
| `format_members.py` | Normalise raw members CSV into members JSON | members CSV | `members.json` |
| `check_results_validity.py` | Validate a results JSON (member existence, genders, duplicates) | results JSON, `members.json` | none (read-only) |
| `handicap_calc.py` | Compute updated handicaps from latest WHC results | `eventStructure.json`, previous `hcaps.json`, results JSON | `hcaps.json` |
| `points_calc.py` | Calculate season points (DB Hunter, WHC, club champs, fresher) | results JSON, `members.json`, `freshers.csv`, `bbb_freshers.csv`, `jcc_results.csv` | `pts.csv`, `pts_fr.csv`, `attendance.csv`, `attendance_ls.json`, `attendance_ls_fr.json`, `cchamps_nonzero_pts.csv` |
| `board_use_count.py` | Count board/ski craft usage per member | (hardcoded paths — not yet updated) | `other/craft_attendance_*.{json,csv}` |

### Key Data Formats

**Members** (`members/members.json`): array of `{id, name, gender, dob, title}`. `title` is the canonical member identifier: `"Firstname LASTNAME - ID"` (e.g. `"John BUCHAN - B042"`).

**Results** (`results/whc_results_YYMMDD.json`): nested dict `{ date_key: { event: { gender: [ {id, title}, ... ] } } }`. Order within the gender array is finishing order (1st = index 0).

Date keys follow `YYMMDD_EventType` pattern (e.g. `260406_WHC`, `251130_CChamps`, `260308_MSwim`).

**Handicaps** (`hcaps/hcaps.json`): `{ event: { gender: [ {member_title, handicap, handicap_5s} ] } }`. Previous snapshots are stored in `hcaps/history/`. The `handicap_5s` column rounds to nearest 5 seconds for display; the raw `handicap` is used for future calculations.

**Event structure** (`results/eventStructure.json`): reference list of all dates/events used by the data-entry frontend.

### Points Rules (encoded in `points_calc.py`)

- WHC points require the member to have completed the swim on the same date (except marathon/cchamps/IMDL events).
- WHC placing: 1st=10pts, 2nd=9pts, ..., 10th+=1pt.
- Club champs: best 2 results per event per member across all cchamps dates, then summed.
- DB Hunter points: 1pt per regular event, 5pts for marathon/IMDL events.
- Freshers additionally receive: 5pts BBB attendance, 25pts JCC individual, 5pts JCC team.

### Handicap Algorithm (`handicap_calc.py`)

Percentile-based adjustment: members finishing above the 67th percentile receive a time penalty, those below receive a reduction. Delta is capped at ±20s/+30s per event. Final handicaps are clipped to ≥0 and rounded to nearest 5s for display.

### Typical Workflow

1. After a new event: add a results JSON to `results/` following the existing format.
2. Open `check_results_validity.py` — upload the results JSON and `members.json`, check output.
3. Open `handicap_calc.py` — upload `eventStructure.json`, previous `hcaps.json`, and the results JSON; select the new date(s); download the updated `hcaps.json`.
4. Open `points_calc.py` — upload all five files; download updated points CSVs/JSONs.
