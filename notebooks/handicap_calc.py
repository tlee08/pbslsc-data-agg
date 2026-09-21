# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = [
#     "marimo>=0.23.6",
#     "polars==1.38.1",
#     "pydantic==2.13.5",
# ]
# ///

import marimo

__generated_with = "0.24.2"
app = marimo.App(width="full")

with app.setup:
    import json

    import marimo as mo
    import polars as pl

    from data_wrangling.frames import members_to_frame
    from data_wrangling.models import Members, Results

    # Events and genders constants
    events = ["swim", "board", "ski", "run"]
    genders = ["m", "f"]
    # Handicap tuning constants
    hcap_incr = 2
    hcap_max_plus = 20
    hcap_max_minus = 30
    percentile_threshold = 0.67
    round_incr = 5


@app.cell
def _():
    mo.md("""
    # Update Handicaps

    1. Upload the previous handicaps JSON and the latest results JSON.
    2. Select which dates are new this run.
    3. Preview the updated handicaps and download the new `hcaps.json`.
    """)
    return


@app.cell
def _():
    members_file = mo.ui.file(label="Upload members.json", filetypes=[".json"])
    old_hcaps_file = mo.ui.file(label="Upload previous hcaps JSON", filetypes=[".json"])
    results_file = mo.ui.file(label="Upload results JSON", filetypes=[".json"])
    return members_file, old_hcaps_file, results_file


@app.cell
def _(members_file, old_hcaps_file, results_file):
    mo.vstack(
        [
            mo.hstack(
                [
                    members_file,
                    members_file.value[0].name if members_file.value else "",
                ],
            ),
            mo.hstack(
                [
                    old_hcaps_file,
                    old_hcaps_file.value[0].name if old_hcaps_file.value else "",
                ],
            ),
            mo.hstack(
                [
                    results_file,
                    results_file.value[0].name if results_file.value else "",
                ],
            ),
        ],
    )
    return


@app.cell
def _(old_hcaps_file, results_file):
    mo.stop(
        not old_hcaps_file.value or not results_file.value,
        mo.callout(mo.md("Upload both files to continue."), kind="warn"),
    )

    results_data = Results.validate_json(results_file.value[0].contents)
    date_options = {k: k for k in results_data}

    new_dates_select = mo.ui.multiselect(
        options=date_options,
        label="Select new dates to process",
    )
    return new_dates_select, results_data


@app.cell
def _(new_dates_select):
    mo.hstack([new_dates_select, sorted(new_dates_select.value)])
    return


@app.function
def postprocess_hcaps(hcaps):
    """Filter to positive handicaps, sort, and add the rounded column."""
    return (
        hcaps.filter(pl.col("handicap") > 0)
        .with_columns(
            pl.col("handicap").cast(pl.Int64),
            ((pl.col("handicap") / round_incr).round() * round_incr)
            .cast(pl.Int64)
            .alias("handicap_5s"),
        )
        .sort(["event", "gender", "handicap"])
    )


@app.function
def preview_hcaps(hcaps):
    """Project handicaps to the preview columns."""
    return hcaps.select(
        pl.col("event"),
        pl.col("gender"),
        pl.col("member_title").alias("member"),
        pl.col("handicap"),
        pl.col("handicap_5s"),
    )


@app.function
def construct_hcap_csv_download_btn(hcaps, event, gender):
    """Build a download button for one event/gender CSV."""
    subset = hcaps.filter((pl.col("event") == event) & (pl.col("gender") == gender))
    return mo.download(
        data=subset.select("member_title", "handicap", "handicap_5s")
        .write_csv()
        .encode(),
        filename=f"{event}_{gender}.csv",
        label=f"Download {event}_{gender}.csv",
    )


@app.cell
def _(members_file, new_dates_select, old_hcaps_file, results_data):
    mo.stop(
        not new_dates_select.value,
        mo.callout(mo.md("Select at least one new date to continue."), kind="warn"),
    )

    old_hcaps = json.loads(old_hcaps_file.value[0].contents)
    members = Members.validate_json(members_file.value[0].contents)
    new_dates = new_dates_select.value

    members_df = members_to_frame(members)

    # Base frame: one row per (event, member); gender comes from the member
    base = members_df.join(pl.DataFrame({"event": events}), how="cross")

    # Flatten previous handicaps into a long frame (accept "title" or "member_title")
    old_records = [
        {
            "event": _event,
            "gender": _gender,
            "member_title": rec.get("member_title", rec.get("title")),
            "handicap": rec.get("handicap", 0),
        }
        for _event in events
        for _gender in genders
        for rec in old_hcaps.get(_event, {}).get(_gender, [])
    ]
    if old_records:
        old_df = pl.DataFrame(old_records).select(
            "event", "member_title", "handicap",
        )
    else:
        old_df = pl.DataFrame(
            schema={"event": pl.Utf8, "member_title": pl.Utf8, "handicap": pl.Float64},
        )

    base = base.join(old_df, on=["event", "member_title"], how="left").with_columns(
        pl.col("handicap").fill_null(0),
    )

    # Previous handicaps, for the preview
    hcaps_prev = postprocess_hcaps(base)

    # Apply handicap updates for each new date
    hcaps = base
    for _date in new_dates:
        for _event in events:
            for _gender in genders:
                entries = results_data.get(_date, {}).get(_event, {}).get(_gender, [])
                if not entries:
                    continue
                count_total = len(entries)
                count_threshold = round(count_total * percentile_threshold)
                balance_index = count_total - count_threshold
                deltas = [
                    min(hcap_incr * (balance_index - i), hcap_max_plus)
                    for i in range(balance_index)
                ] + [
                    max(-hcap_incr * i, -hcap_max_minus)
                    for i in range(count_threshold)
                ]
                delta_df = pl.DataFrame(
                    {
                        "event": [_event] * count_total,
                        "gender": [_gender] * count_total,
                        "member_title": [entry.title for entry in entries],
                        "delta": deltas,
                    },
                )
                hcaps = hcaps.join(
                    delta_df, on=["event", "gender", "member_title"], how="left",
                ).with_columns(
                    (pl.col("handicap") + pl.col("delta").fill_null(0))
                    .clip(lower_bound=0)
                    .alias("handicap"),
                ).drop("delta")

    hcaps = postprocess_hcaps(hcaps)

    # Build output JSON, keeping the existing {event: {gender: [records]}} shape
    hcaps_json = {
        _event: {
            _gender: json.loads(
                hcaps.filter(
                    (pl.col("event") == _event) & (pl.col("gender") == _gender),
                )
                .select(
                    pl.col("member_title").alias("title"),
                    pl.col("name"),
                    pl.col("dob"),
                    pl.col("gender"),
                    pl.col("club"),
                    pl.col("id"),
                    pl.col("first_name"),
                    pl.col("last_name"),
                    pl.col("handicap"),
                    pl.col("handicap_5s"),
                )
                .write_json(),
            )
            for _gender in genders
        }
        for _event in events
    }

    mo.vstack(
        [
            mo.md("### Old Handicaps"),
            preview_hcaps(hcaps_prev),
            mo.md("### New Handicaps"),
            preview_hcaps(hcaps),
            mo.download(
                data=json.dumps(hcaps_json, indent=2).encode(),
                filename="hcaps.json",
                label="Download hcaps.json",
            ),
            *[
                mo.hstack(
                    [
                        construct_hcap_csv_download_btn(hcaps, _event, _gender)
                        for _event in events
                    ],
                )
                for _gender in genders
            ],
        ],
    )
    return


if __name__ == "__main__":
    app.run()
