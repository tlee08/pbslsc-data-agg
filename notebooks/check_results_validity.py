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

    from data_wrangling.frames import (
        handicaps_to_frame,
        members_to_frame,
        results_to_frame,
    )
    from data_wrangling.models import (
        handicaps_adapter,
        members_adapter,
        results_adapter,
    )


@app.cell
def _():
    results_file = mo.ui.file(label="Upload results.json", filetypes=[".json"])
    members_file = mo.ui.file(label="Upload members.json", filetypes=[".json"])
    handicaps_file = mo.ui.file(
        label="Upload handicaps.json", filetypes=[".json"]
    )
    return handicaps_file, members_file, results_file


@app.cell
def _(handicaps_file, members_file, results_file):
    mo.vstack([results_file, members_file, handicaps_file])
    return


@app.cell
def _():
    mo.md("""
    # Check Results Validity

    Upload a results JSON and the members JSON. All checks run automatically.
    """)
    return


@app.cell
def _(members_file, results_file):
    mo.stop(
        not results_file.value or not members_file.value,
        mo.callout(mo.md("Upload both files to continue."), kind="warn"),
    )

    results = results_adapter.validate_json(results_file.value[0].contents)
    members = members_adapter.validate_json(members_file.value[0].contents)

    results_df = results_to_frame(results)
    members_df = members_to_frame(members)
    titles = members_df.get_column("title").to_list()

    _lines = []

    # Check member existence and ID/title consistency
    _lines.append("=== Member existence ===")
    bad_existence = results_df.with_columns(
        pl.col("title").is_in(titles).alias("title_ok"),
    ).filter(~(pl.col("title_ok")))
    _lines.extend(
        f"  FAIL {row['date']} / {row['event']} / {row['gender']}: {row['title']!r}"
        for row in bad_existence.iter_rows(named=True)
    )
    if bad_existence.height == 0:
        _lines.append("  All OK")

    # Check gender correctness
    _lines.append("\n=== Gender correctness ===")
    bad_gender = results_df.join(
        members_df.select(
            pl.col("title"),
            pl.col("gender").alias("member_gender"),
        ),
        on="title",
        how="inner",
    ).filter(pl.col("member_gender") != pl.col("gender"))
    _lines.extend(
        f"  FAIL {row['date']} / {row['event']}: {row['title']!r} listed "
        f"under {row['gender']!r} but is {row['member_gender']!r}"
        for row in bad_gender.iter_rows(named=True)
    )
    if bad_gender.height == 0:
        _lines.append("  All OK")

    # Check duplicates
    _lines.append("\n=== Duplicates ===")
    dupl = (
        results_df.group_by(["date", "event", "gender", "title"])
        .agg(pl.len().alias("count"))
        .filter(pl.col("count") > 1)
    )
    _lines.extend(
        f"  FAIL {row['date']} / {row['event']} / {row['gender']}: "
        f"id={row['title']!r} appears {row['count']}x"
        for row in dupl.iter_rows(named=True)
    )
    if dupl.height == 0:
        _lines.append("  All OK")

    if (
        bad_existence.height == 0
        and bad_gender.height == 0
        and dupl.height == 0
    ):
        _lines.insert(0, "All checks passed.\n")

    mo.plain_text("\n".join(_lines))
    return (titles,)


@app.cell
def _():
    mo.md("""
    # Check Results Validity

    Upload a results JSON and the members JSON. All checks run automatically.
    """)
    return


@app.cell
def _(handicaps_file, members_file, titles):
    mo.stop(
        not handicaps_file.value or not members_file.value,
        mo.callout(
            mo.md("Upload both handicaps and members JSON files to continue."),
            kind="warn",
        ),
    )

    handicaps = handicaps_adapter.validate_json(
        handicaps_file.value[0].contents
    )

    handicaps_df = handicaps_to_frame(handicaps)
    handicaps_df = handicaps_df.with_columns(
        pl.col("title")
        .str.split(" - ")
        .list.get(1)
        .str.strip_chars()
        .alias("id")
    )

    _lines = []

    # Check member existence
    _lines.append("=== Member existence ===")

    bad_hcap = handicaps_df.with_columns(
        pl.col("title").is_in(titles).alias("title_ok"),
    ).filter(~(pl.col("title_ok")))
    _lines.extend(
        f"  FAIL {row['event']} {row['gender']}: {row['title']!r}"
        for row in bad_hcap.iter_rows(named=True)
    )
    if bad_hcap.height == 0:
        _lines.append("  All OK")

    if bad_hcap.height == 0:
        _lines.insert(0, "All checks passed.\n")

    # Check member numbers don't appear twice in handicaps
    _lines.append("\n=== Member duplication ===")

    double_hcaps = (
        handicaps_df.group_by("event", "gender", "id")
        .agg(pl.len())
        .filter(pl.col("len") > 1)
    )

    _lines.extend(
        f"  FAIL {row['event']} {row['gender']}: {row['title']!r}"
        for row in double_hcaps.iter_rows(named=True)
    )

    if double_hcaps.height == 0:
        _lines.append("  All OK")

    mo.plain_text("\n".join(_lines))
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
