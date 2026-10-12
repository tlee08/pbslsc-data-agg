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
    import io
    import json
    from pathlib import Path
    import marimo as mo
    import polars as pl
    import json

    from data_wrangling.models import Members, Results


@app.cell
def _():
    mo.md("""
    # Format Members

    Upload the raw members CSV export. A preview will appear and you can
    download the formatted `members.json`.
    """)
    return


@app.cell
def _():
    members_file = mo.ui.file(label="Upload members CSV", filetypes=[".csv"])
    members_file
    return


@app.cell
def _():
    # mo.stop(
    #     not members_file.value,
    #     mo.callout(mo.md("Upload a members CSV to continue."), kind="warn"),
    # )
    # df = pl.read_csv(
    #     io.BytesIO(members_file.value[0].contents),
    #     infer_schema=False,
    # )

    df = pl.read_csv(
        Path.cwd().parent / "data" / "2026_27" / "20261008_PBSC_Members.csv"
    )
    df = df.rename(
        {
            "Name": "name",
            "Gender identity": "gender",
            "Member Number": "id",
            "Status": "membership",
        }
    )

    df = df.with_columns(
        pl.col("name").str.split(", ").list.get(1).alias("first_name"),
        pl.col("name").str.split(", ").list.get(0).alias("last_name"),
        pl.col("gender").replace({"Male": "m", "Female": "f"}),
    )
    df = df.with_columns(
        pl.col("id").fill_null("-"),
        pl.col("membership").fill_null(""),
    )
    df = df.with_columns(
        pl.format(
            "{} {} - {}",
            pl.col("first_name"),
            pl.col("last_name").str.to_uppercase(),
            pl.col("id"),
        ).alias("title"),
    ).sort("title")

    _json_bytes = Members.dump_json(
        Members.validate_python(df.to_dicts()), indent=2
    )
    mo.vstack(
        [
            df,
            mo.download(
                data=_json_bytes,
                filename="members.json",
                label="Download members.json",
            ),
        ],
    )
    return (df,)


@app.cell
def _(df):
    # Checking that members df is valid
    [
        df.group_by("id")
        .agg(pl.count())
        .filter(pl.col("count") >= 2)
        .sort("count", descending=True),
        df.select((pl.col("gender") == "").sum()),
        df.group_by("title")
        .agg(pl.count())
        .filter(pl.col("count") >= 2)
        .sort("count", descending=True),
    ]
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Make `meetings.json`
    """)
    return


@app.cell
def _():
    meetings_dict = json.loads(
        (Path.cwd().parent / "data" / "2026_27" / "meetings.json").read_text()
    )
    lookups_dict = json.loads(
        (Path.cwd().parent / "data" / "2026_27" / "lookups.json").read_text()
    )

    results_dict = {
        _i["id"]: {
            _event: {
                _gender: []
                for _gender in lookups_dict["events"][_event]["genders"]
            }
            for _event in lookups_dict["series"][_i["series"]]["events"]
        }
        for _i in meetings_dict
    }

    _json_bytes = Results.dump_json(
        Results.validate_python(results_dict), indent=2
    )
    mo.vstack(
        [
            mo.accordion({"Results": results_dict}),
            mo.download(
                data=_json_bytes,
                filename="results.json",
                label="Download results.json",
            ),
        ],
    )
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
