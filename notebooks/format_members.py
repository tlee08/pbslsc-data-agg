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

    import marimo as mo
    import polars as pl


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
    mo.stop(
        not members_file.value,
        mo.callout(mo.md("Upload a members CSV to continue."), kind="warn"),
    )

    df = pl.read_csv(
        io.BytesIO(members_file.value[0].contents), infer_schema=False,
    )
    df = df.with_columns(
        pl.col("name").str.split(", ").list.get(1).alias("first_name"),
        pl.col("name").str.split(", ").list.get(0).alias("last_name"),
        pl.col("gender").replace({"Male": "m", "Female": "f"}),
    )
    df = df.with_columns(
        pl.format(
            "{} {} - {}",
            pl.col("first_name"),
            pl.col("last_name").str.to_uppercase(),
            pl.col("id"),
        ).alias("title"),
    ).sort("title")

    json_bytes = json.dumps(json.loads(df.write_json()), indent=2).encode()
    mo.vstack(
        [
            df,
            mo.download(
                data=json_bytes, filename="members.json", label="Download members.json",
            ),
        ],
    )
    return


if __name__ == "__main__":
    app.run()
