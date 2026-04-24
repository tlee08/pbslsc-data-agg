# Notebook Simplification & Interactive UI Design

**Date:** 2026-04-25
**Scope:** Simplify and make interactive the four marimo notebooks in `code/` so non-technical club admins can operate them without editing Python.

---

## General Principles

Applied across all four notebooks:

- Remove all `mo.md()` section-header cells. Replace with a single title cell describing what the notebook does and what the user needs to do.
- All file inputs use `mo.ui.file()` (upload widget) — no hardcoded paths.
- Notebooks that produce output files use `mo.download()` — the browser/OS handles save location.
- Notebooks with no output (validity check) are read-only — no save/download button.
- Nothing is computed until all required file inputs are provided. Missing inputs show a `mo.callout()` message: "Upload a file to continue."
- Remove intermediate outputs (heatmaps, accordions, debug prints) not useful to non-technical users.
- Prefer minimal cell count and minimal code — maintainability for the coder is a priority.
- Always run via `uv run marimo edit code/<notebook>.py`.

---

## Notebook Designs

### `format_members.py` — Format Members CSV

**Purpose:** At season start, convert the raw members CSV export into a clean `members.json`.

**Inputs:**
- `mo.ui.file()` — members CSV (e.g. `members_25.csv`)

**Flow:**
1. User uploads CSV → wrangle (split name into first/last, map gender M/F → m/f, build `title` as `"Firstname LASTNAME - ID"`) → show preview dataframe
2. `mo.download()` button labelled "Download members.json" → streams wrangled data as JSON

**Removed:** Duplicate-check cell, BBB name-matching cell, JSON accordion preview, hardcoded output path.

**Target cell count:** ~3 cells (title + upload/preview + download)

---

### `check_results_validity.py` — Validate Results

**Purpose:** After entering a new results JSON, verify member IDs/titles are correct, genders match, and no duplicates exist.

**Inputs:**
- `mo.ui.file()` — results JSON (e.g. `whc_results_260406.json`)
- `mo.ui.file()` — `members.json`

**Flow:**
1. Both files uploaded → run three checks automatically:
   - Member existence: every `{id, title}` in results exists in members and ID matches title
   - Gender correctness: members appear under the correct gender key
   - Duplicates: no member appears twice in the same event/gender
2. Output displayed as `mo.plain_text()` — one section per check, listing problems. Prints "All checks passed." if clean.

**No download/save** — read-only notebook.

**Removed:** Member-list self-duplicate check, all `mo.md()` section headers, accordion wrappers.

**Target cell count:** ~3 cells (title + uploads + checks output)

---

### `handicap_calc.py` — Update Handicaps

**Purpose:** After a WHC event, compute updated handicaps and download the new handicaps JSON.

**Inputs:**
1. `mo.ui.file()` — `eventStructure.json` → populates the date multi-select
2. `mo.ui.file()` — previous handicaps JSON (e.g. `hcaps/history/hcaps_260403.json`)
3. `mo.ui.file()` — results JSON (e.g. `whc_results_260406.json`)
4. `mo.ui.multiselect()` — populated from eventStructure.json dates; user picks which date keys are "new" this run

**Flow:**
1. All inputs provided → compute updated handicaps → show summary preview table
2. `mo.download()` button → downloads `hcaps.json`

**Removed:** Per-event/gender CSV exports, heatmap, all debug print statements, `mo.md()` section headers.

**Algorithm unchanged:** Percentile-based adjustment (67th percentile threshold), ±2s increments, capped at +20s/−30s, clipped to ≥0, rounded to nearest 5s for display column.

**Target cell count:** ~4 cells (title + uploads/multiselect + preview + download)

---

### `points_calc.py` — Calculate Points

**Purpose:** Compute season points for all members and freshers, then download results.

**Inputs:**
1. `mo.ui.file()` — results JSON (cumulative season file)
2. `mo.ui.file()` — `members.json`
3. `mo.ui.file()` — `freshers.csv`
4. `mo.ui.file()` — `bbb_freshers.csv`
5. `mo.ui.file()` — `jcc_results.csv`

**Flow:**
1. All inputs provided → compute all points (WHC, DB Hunter, club champs, fresher with BBB/JCC) → show preview table
2. `mo.download()` buttons for each output:
   - `pts.csv`
   - `pts_fr.csv`
   - `attendance.csv`
   - `attendance_ls.json`
   - `attendance_ls_fr.json`
   - `cchamps_nonzero_pts.csv`

**Removed:** Heatmap, `attendance_ls_vect` intermediate display, all `mo.md()` section headers.

**Points rules unchanged** — see CLAUDE.md for summary.

**Target cell count:** ~4 cells (title + uploads + preview + downloads)

---

## Out of Scope

- `board_use_count.py` — not mentioned as a priority; leave unchanged for now.
- Hosting / deployment — design for local `marimo edit` use; hosting decision deferred.
- Shared `utils.py` — not extracting shared logic; each notebook stays self-contained (Option A).
