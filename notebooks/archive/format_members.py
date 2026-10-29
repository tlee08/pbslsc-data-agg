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
    from pathlib import Path

    import marimo as mo
    import polars as pl
    import io

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
    return (members_file,)


@app.cell
def _(members_file):
    my_df = pl.read_csv(
        io.BytesIO(members_file.value[0].contents),
        infer_schema=False,
    )
    my_df
    return


@app.cell
def _(members_file):
    mo.stop(
        not members_file.value,
        mo.callout(mo.md("Upload a members CSV to continue."), kind="warn"),
    )
    df = pl.read_csv(
        io.BytesIO(members_file.value[0].contents),
        infer_schema=False,
    )

    _json_bytes = Members.dump_json(
        Members.validate_python(df.to_dicts()),
        indent=2,
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
    mo.accordion(
        {
            "Duplicate IDs": df.group_by("id")
            .agg(pl.len())
            .filter(pl.col("len") >= 2)
            .sort("len", descending=True),
            "No gender assigned": df.filter(
                ((pl.col("gender") == "") | (pl.col("gender").is_null()))
            ),
            "Duplicate name": df.group_by("name")
            .agg(pl.len())
            .filter(pl.col("len") >= 2)
            .sort("len", descending=True),
        },
        multiple=True,
    )
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
