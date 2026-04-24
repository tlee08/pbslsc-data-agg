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

| Script | Purpose | Reads | Writes |
|---|---|---|---|
| `format_members.py` | Normalise raw member CSV into members JSON | `members/members_25.csv` | `members/members.json` |
| `check_results_validity.py` | Validate a results JSON (member existence, genders, duplicates) | `results/whc_results_*.json`, `members/members.json` | (none) |
| `handicap_calc.py` | Compute updated handicaps from latest WHC results | `results/whc_results_*.json`, `hcaps/history/hcaps_*.json`, `members/members.json` | `hcaps/*.csv`, `hcaps/hcaps.json` |
| `points_calc.py` | Calculate season points (DB Hunter, WHC, club champs, fresher) | `results/whc_results_*.json`, `members/members.json`, `members/freshers.csv`, `results/bbb_freshers.csv`, `results/jcc_results.csv` | `points/*.csv`, `points/*.json` |
| `board_use_count.py` | Count board/ski craft usage per member | `results/whc_results_*.json`, `members/members.json`, `members/freshers.csv` | `other/craft_attendance_*.{json,csv}` |

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
2. Run `check_results_validity.py` to confirm member IDs/titles are correct.
3. Run `handicap_calc.py` (updating `new_dates_for_hcap` and file paths at the top of the cell) to produce new handicap files.
4. Run `points_calc.py` (updating the results file path) to regenerate season points.
