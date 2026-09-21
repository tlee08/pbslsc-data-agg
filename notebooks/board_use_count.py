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
    import marimo as mo
    import polars as pl

    from data_wrangling.frames import results_to_frame
    from data_wrangling.models import Results


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Board & Ski Usage

    Counts how many board and ski events each member attended.
    """)
    return


@app.cell
def _():
    results_file = mo.ui.file(label="Upload results JSON", filetypes=[".json"])
    results_file
    return (results_file,)


@app.cell
def _(results_file):
    mo.stop(
        not results_file.value,
        mo.callout(mo.md("Upload a results JSON to continue."), kind="warn"),
    )

    results_data = Results.validate_json(results_file.value[0].contents)
    results_df = results_to_frame(results_data)

    craft_events = ["board", "cboard_rescue", "mboard", "ski", "cski_surf", "mski"]
    board_events = ["board", "cboard_rescue", "mboard"]
    ski_events = ["ski", "cski_surf", "mski"]

    craft_df = results_df.filter(pl.col("event").is_in(craft_events))

    counts_df = (
        craft_df.group_by("member_title")
        .agg(
            pl.col("event").is_in(board_events).sum().alias("board_usage"),
            pl.col("event").is_in(ski_events).sum().alias("ski_usage"),
        )
        .filter((pl.col("board_usage") + pl.col("ski_usage")) > 0)
        .sort("member_title")
    )
    return counts_df, craft_df


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Craft attendance (long format)
    """)
    return


@app.cell
def _(craft_df):
    craft_df.select("member_title", "date", "event", "gender", "place").sort(
        "member_title",
        "date",
        "event",
    )
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Craft attendance counts
    """)
    return


@app.cell
def _(counts_df):
    counts_df
    return


@app.cell
def _(counts_df, craft_df):
    mo.vstack(
        [
            mo.md("### Downloads"),
            mo.hstack(
                [
                    mo.download(
                        data=craft_df.select(
                            "member_title",
                            "date",
                            "event",
                            "gender",
                            "place",
                        )
                        .write_csv()
                        .encode(),
                        filename="craft_attendance.csv",
                        label="craft_attendance.csv",
                    ),
                    mo.download(
                        data=counts_df.write_csv().encode(),
                        filename="craft_attendance_count.csv",
                        label="craft_attendance_count.csv",
                    ),
                ],
            ),
        ],
    )
    return


if __name__ == "__main__":
    app.run()
