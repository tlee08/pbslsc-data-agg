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
    import marimo as mo
    import polars as pl

    from data_wrangling.handicaps import (
        HandicapConfig,
        update_handicaps,
    )
    from data_wrangling.models import handicaps_adapter, results_adapter


@app.cell
def _():
    # ── Handicap config — edit these values ─────────────────────────────
    # Handicap = start delay in seconds (metres for flags). Bigger = later start.
    config = {
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
    config = HandicapConfig.model_validate(config)
    return (config,)


@app.cell
def _():
    mo.md("""
    # Update Handicaps

    1. Upload the previous handicaps JSON and the results JSON.
    2. Pick the meeting whose results drive this update.
    3. Review the changes and download the new handicaps JSON.
    """)
    return


@app.cell
def _():
    old_hcaps_file = mo.ui.file(
        label="Previous handicaps JSON",
        filetypes=[".json"],
    )
    results_file = mo.ui.file(label="Results JSON", filetypes=[".json"])
    return old_hcaps_file, results_file


@app.cell
def _(old_hcaps_file, results_file):
    mo.vstack(
        [
            mo.hstack(
                [
                    old_hcaps_file,
                    mo.md(
                        f"Has value: {[_i.name for _i in old_hcaps_file.value]}",
                    ),
                ],
            ),
            mo.hstack(
                [
                    results_file,
                    mo.md(
                        f"Has value: {[_i.name for _i in results_file.value]}",
                    ),
                ],
            ),
        ],
    )
    return


@app.cell
def _(old_hcaps_file, results_file):
    mo.stop(
        not old_hcaps_file.value or not results_file.value,
        mo.callout(mo.md("Upload both JSON files to continue."), kind="warn"),
    )

    old_hcaps = handicaps_adapter.validate_json(
        old_hcaps_file.value[0].contents,
    )
    results = results_adapter.validate_json(
        results_file.value[0].contents,
    )
    return old_hcaps, results


@app.cell
def _(results):
    populated = [
        k
        for k, v in results.items()
        if any(e for gs in v.values() for e in gs.values())
    ]
    meeting = mo.ui.multiselect(
        options=populated,  # list(results)
        value=[populated[-1]] if populated else None,
        label="Meeting to use for this update",
    )
    return (meeting,)


@app.cell
def _(meeting):
    mo.hstack([meeting, mo.md(f"Has value: {meeting.value}")])
    return


@app.cell
def _(config, meeting, old_hcaps, results):
    mo.stop(
        meeting.value is None,
        mo.callout(mo.md("Select a meeting to continue."), kind="warn"),
    )

    new_hcaps = old_hcaps
    for _meeting_i in meeting.value:
        new_hcaps = update_handicaps(new_hcaps, results[_meeting_i], config)
    return (new_hcaps,)


@app.cell
def _(meeting, new_hcaps, old_hcaps):
    prev = {
        r.title: r.handicap
        for genders in old_hcaps.values()
        for records in genders.values()
        for r in records
    }
    rows = [
        {
            "event": event,
            "gender": gender,
            "title": r.title,
            "previous": prev.get(r.title, 0.0),
            "handicap": r.handicap,
        }
        for event, genders in new_hcaps.items()
        for gender, records in genders.items()
        for r in records
    ]
    new_hcaps_df = pl.DataFrame(rows).with_columns(
        (pl.col("handicap") - pl.col("previous")).alias("change"),
    )
    changed = new_hcaps_df.filter(pl.col("change") != 0).sort(
        ["event", "gender", "change"],
        descending=[False, False, True],
    )

    n_inc = new_hcaps_df.filter(pl.col("change") > 0).height
    n_dec = new_hcaps_df.filter(pl.col("change") < 0).height

    mo.vstack(
        [
            mo.md(
                f"**{meeting.value}**: {new_hcaps_df.height} handicaps — "
                f"{n_inc} increased, {n_dec} decreased, "
                f"{new_hcaps_df.height - n_inc - n_dec} unchanged.",
            ),
            mo.download(
                data=handicaps_adapter.dump_json(new_hcaps, indent=2),
                filename="handicaps.json",
                label="Download handicaps.json",
            ),
            mo.accordion(
                {
                    "All handicaps": new_hcaps_df.sort(
                        ["event", "gender", "handicap"],
                        descending=[False, False, True],
                    ),
                },
            ),
            mo.accordion({"Changed": changed}),
        ],
    )
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
