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


@app.cell
def _():
    mo.md("""
    # Add Gender to White Horse Cup members
    """)
    return


@app.function
def gender_label(gender: str) -> str:
    return "Female" if gender.lower().startswith("f") else "Male"


@app.cell
def _():
    data = Path.cwd().parent / "data" / "2026_27" / "raw_members"
    return (data,)


@app.cell
def _(data):
    members = pl.read_csv(
        data / "CTC PC & PBSLSC Members - White Horse Cup.csv"
    ).select("Member No", "Name", "Club")

    members
    return (members,)


@app.cell
def _(data):
    rows = []
    for r in json.loads((data / "members_2025_26.json").read_text()):
        rows.append(
            (
                f"{r['first_name']} {r['last_name']}".lower(),
                gender_label(r["gender"]),
            )
        )
    for r in pl.read_csv(data / "20261008_PBSC_Members.csv").to_dicts():
        last, first = (p.strip() for p in r["Name"].split(",", 1))
        rows.append(
            (f"{first} {last}".lower(), gender_label(r["Gender identity"]))
        )

    gender_lookup = (
        pl.DataFrame(rows, schema=["key", "Gender"], orient="row")
        .unique("key")
        .sort("key")
    )

    gender_lookup
    return (gender_lookup,)


@app.cell
def _(gender_lookup, members):
    merged = (
        members.with_columns(pl.col("Name").str.to_lowercase().alias("key"))
        .join(gender_lookup, on="key", how="left")
        .drop("key")
    )

    merged
    return (merged,)


@app.cell
def _(merged):
    unmatched = merged.filter(pl.col("Gender").is_null())
    mo.vstack(
        [
            mo.md(
                f"Matched **{merged['Gender'].is_not_null().sum()}** of "
                f"**{merged.height}** members; {unmatched.height} unmatched."
            ),
            merged.group_by("Gender")
            .agg(pl.len().alias("count"))
            .sort("count", descending=True),
            mo.accordion(
                {
                    "Unmatched members": unmatched.select(
                        "Member No", "Name", "Club"
                    ),
                }
            ),
        ]
    )
    return


@app.cell
def _(merged):
    # Formatting for export
    merged_formatted = merged.rename(
        {"Member No": "id", "Name": "name", "Club": "membership", "Gender": "gender"}
    ).with_columns(
        pl.concat_str(pl.col("name"), pl.lit(" - "), pl.col("id")).alias("title"),
        pl.col("gender").replace_strict({"Male": "m", "Female": "f"}, default=None).alias("gender")
    )
    merged_formatted

    return (merged_formatted,)


@app.cell
def _(data, merged_formatted):
    # Export for manual labelling missing entries
    merged_formatted.write_csv(data / "members_unfinished_labels.csv")
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
