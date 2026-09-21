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

    from data_wrangling.frames import members_to_frame, results_to_frame
    from data_wrangling.models import Members, Results


@app.cell
def _():
    mo.md("""
    # Check Results Validity

    Upload a results JSON and the members JSON. All checks run automatically.
    """)
    return


@app.cell
def _():
    results_file = mo.ui.file(label="Upload results JSON", filetypes=[".json"])
    members_file = mo.ui.file(label="Upload members.json", filetypes=[".json"])
    mo.vstack([results_file, members_file])
    return (members_file, results_file)


@app.cell
def _(members_file, results_file):
    mo.stop(
        not results_file.value or not members_file.value,
        mo.callout(mo.md("Upload both files to continue."), kind="warn"),
    )

    results = Results.validate_json(results_file.value[0].contents)
    members = Members.validate_json(members_file.value[0].contents)

    results_df = results_to_frame(results)
    members_df = members_to_frame(members)
    member_titles = members_df["member_title"].to_list()
    member_ids = members_df["id"].to_list()

    lines = []

    # Check member existence and ID/title consistency
    lines.append("=== Member existence ===")
    bad_existence = results_df.with_columns(
        pl.col("member_title").is_in(member_titles).alias("title_ok"),
        pl.col("member_id").is_in(member_ids).alias("id_ok"),
        (
            pl.col("member_title").str.split(" - ").list.get(-1)
            == pl.col("member_id")
        ).alias("id_eq"),
    ).filter(~(pl.col("title_ok") & pl.col("id_ok") & pl.col("id_eq")))
    lines.extend(
        f"  FAIL {row['date']} / {row['event']} / {row['gender']}: "
        f"{row['member_title']!r} id={row['member_id']!r}"
        for row in bad_existence.iter_rows(named=True)
    )
    if bad_existence.height == 0:
        lines.append("  All OK")

    # Check gender correctness
    lines.append("\n=== Gender correctness ===")
    bad_gender = (
        results_df.join(
            members_df.select(
                pl.col("member_title"), pl.col("gender").alias("member_gender"),
            ),
            on="member_title",
            how="inner",
        ).filter(pl.col("member_gender") != pl.col("gender"))
    )
    lines.extend(
        f"  FAIL {row['date']} / {row['event']}: {row['member_title']!r} listed "
        f"under {row['gender']!r} but is {row['member_gender']!r}"
        for row in bad_gender.iter_rows(named=True)
    )
    if bad_gender.height == 0:
        lines.append("  All OK")

    # Check duplicates
    lines.append("\n=== Duplicates ===")
    dupl = (
        results_df.group_by(["date", "event", "gender", "member_id"])
        .agg(pl.len().alias("count"))
        .filter(pl.col("count") > 1)
    )
    lines.extend(
        f"  FAIL {row['date']} / {row['event']} / {row['gender']}: "
        f"id={row['member_id']!r} appears {row['count']}x"
        for row in dupl.iter_rows(named=True)
    )
    if dupl.height == 0:
        lines.append("  All OK")

    if bad_existence.height == 0 and bad_gender.height == 0 and dupl.height == 0:
        lines.insert(0, "All checks passed.\n")

    mo.plain_text("\n".join(lines))
    return


if __name__ == "__main__":
    app.run()
