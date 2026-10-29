# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = [
#     "marimo>=0.23.6",
#     "polars==1.38.1",
# ]
# ///

import marimo

__generated_with = "0.24.2"
app = marimo.App(width="full")

with app.setup:
    import json

    import marimo as mo
    import polars as pl

    from data_wrangling.handicaps import update_handicaps

    # ── Handicap config — edit these values ─────────────────────────────
    # Handicap = start delay in seconds (metres for flags). Bigger = later start.
    CONFIG = {
        "middle_ratio": 0.5,  # zero-change point as a fraction of the field (0.5 = middle)
        "step": {
            "swim": 3,
            "board": 3,
            "ski": 3,
            "run": 3,
            "flags": 0.25,
        },  # change per place
        "max_change": {
            "swim": 50,
            "board": 50,
            "ski": 50,
            "run": 50,
            "flags": 3,
        },  # ± cap
        "round_to": {
            "swim": 5,
            "board": 5,
            "ski": 5,
            "run": 5,
            "flags": 0.5,
        },  # round up to
    }


@app.cell
def _():
    mo.md(
        """# Update Handicaps

        1. Upload the previous handicaps JSON and the results JSON.
        2. Pick the meeting whose results drive this update.
        3. Review the changes and download the new handicaps JSON.
        """,
    )
    return


@app.cell
def _():
    old_hcaps_file = mo.ui.file(label="Previous handicaps JSON", filetypes=[".json"])
    results_file = mo.ui.file(label="Results JSON", filetypes=[".json"])
    return old_hcaps_file, results_file


@app.cell
def _(old_hcaps_file, results_file):
    mo.vstack([old_hcaps_file, results_file])
    return


@app.cell
def _(old_hcaps_file, results_file):
    mo.stop(
        not old_hcaps_file.value or not results_file.value,
        mo.callout(mo.md("Upload both JSON files to continue."), kind="warn"),
    )
    old_hcaps = json.loads(old_hcaps_file.value[0].contents)
    results = json.loads(results_file.value[0].contents)
    return old_hcaps, results


@app.cell
def _(results):
    populated = [
        k
        for k, v in results.items()
        if any(e for gs in v.values() for e in gs.values())
    ]
    meeting = mo.ui.select(
        options=list(results),
        value=populated[-1] if populated else None,
        label="Meeting to use for this update",
    )
    return (meeting,)


@app.cell
def _(meeting):
    meeting
    return


@app.cell
def _(old_hcaps, results, meeting):
    mo.stop(
        meeting.value is None or meeting.value not in results,
        mo.callout(mo.md("Select a meeting to continue."), kind="warn"),
    )
    new_hcaps = update_handicaps(old_hcaps, results[meeting.value], CONFIG)
    return (new_hcaps,)


@app.cell
def _(new_hcaps, meeting):
    rows = [
        {
            "event": event,
            "gender": gender,
            "name": r.get("name"),
            "number": r.get("number"),
            "previous": r.get("previous", 0),
            "handicap": r.get("handicap", 0),
        }
        for event, genders in new_hcaps.items()
        for gender, records in genders.items()
        for r in records
    ]
    table = pl.DataFrame(rows).with_columns(
        (pl.col("handicap") - pl.col("previous")).alias("change"),
    )
    changed = table.filter(pl.col("change") != 0).sort(
        ["event", "gender", "change"],
        descending=[False, False, True],
    )

    n_inc = table.filter(pl.col("change") > 0).height
    n_dec = table.filter(pl.col("change") < 0).height

    mo.vstack(
        [
            mo.md(
                f"**{meeting.value}**: {table.height} handicaps — "
                f"{n_inc} increased, {n_dec} decreased, "
                f"{table.height - n_inc - n_dec} unchanged.",
            ),
            mo.download(
                data=json.dumps(new_hcaps, indent=2).encode(),
                filename="handicaps.json",
                label="Download handicaps.json",
            ),
            mo.md("### Changed"),
            changed,
            mo.accordion(
                {
                    "All handicaps": table.sort(
                        ["event", "gender", "handicap"],
                        descending=[False, False, True],
                    ),
                },
            ),
        ],
    )
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
