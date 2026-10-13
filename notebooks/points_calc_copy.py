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

    tally_cols = [
        "all_attendance",
        "dbhunter_pts",
        "whc_pts",
        "xmas_pts",
        "presidents_pts",
        "curlewis_pts",
        "cchamps",
    ]


@app.cell
def _():
    mo.md("""
    # Calculate Points

    Upload all required files. Points are calculated automatically
    once all files are provided.
    Download individual output files below the preview.
    """)
    return


@app.cell
def _():
    results_file = mo.ui.file(label="Upload results JSON", filetypes=[".json"])
    members_file = mo.ui.file(label="Upload members.json", filetypes=[".json"])
    return members_file, results_file


@app.cell
def _(members_file, results_file):
    mo.vstack(
        [
            mo.hstack(
                [
                    results_file,
                    results_file.value[0].name if results_file.value else "",
                ],
            ),
            mo.hstack(
                [
                    members_file,
                    members_file.value[0].name if members_file.value else "",
                ],
            ),
        ],
    )
    return


@app.cell
def _(members_file, results_file):
    mo.stop(
        not results_file.value or not members_file.value,
        mo.callout(
            mo.md("Upload the results and members files to continue."),
            kind="warn",
        ),
    )

    results = Results.validate_json(results_file.value[0].contents)
    members = Members.validate_json(members_file.value[0].contents)

    members_df = members_to_frame(members)
    results_df = results_to_frame(results).rename({"title": "id"})
    return members_df, results_df


@app.cell
def _(members_df, results_df):
    fr_df = members_df.filter(pl.col("membership") == "Fresher")

    # ── Config ──────────────────────────────────────────────────────────────
    # TODO: clean up points mapping
    dbhunter_map = {
        "swim": 1,
        "board": 1,
        "ski": 1,
        "run": 1,
        "flags": 1,
        "mswim": 5,
        "mboard": 5,
        "mski": 5,
        "mrun": 5,
        "cswim": 1,
        "cboard_rescue": 1,
        "cboard_mal": 1,
        "cski_surf": 1,
        "cski_racing": 1,
        "crun": 1,
        "cflags": 1,
        "imdl": 5,
    }
    whc_events = ["swim", "board", "ski", "run", "flags"]
    marathon_events = ["mswim", "mboard", "mski", "mrun"]
    swim_not_required = [
        "mswim",
        "mboard",
        "mski",
        "mrun",
        "cswim",
        "cboard_rescue",
        "cboard_mal",
        "cski_surf",
        "cski_racing",
        "crun",
        "cflags",
        "imdl",
    ]
    cchamps_events = [
        "cswim",
        "cboard_rescue",
        "cboard_mal",
        "cski_surf",
        "cski_racing",
        "crun",
        "cflags",
    ]
    jcc_events = ["jcc_individual", "jcc_team"]
    xmas_dates = [_k for _k in results_df["date"].unique() if "_xmas" in _k]
    curlewis_dates = ["250928_WHC", "251005_WHC"]

    # ── Unknown members ─────────────────────────────────────────────────────
    # TODO: handle members with the same number, but are different people
    known_ids = set(members_df["id"].to_list())
    unknown_ids = [
        _id for _id in results_df["id"].unique().to_list() if _id not in known_ids
    ]
    for _id in unknown_ids:
        print(
            f"ERROR: '{_id}' is in results but not in members.json; "
            "including it and treating it as a non-fresher.",
        )

    # ── Points from results ─────────────────────────────────────────────────
    results_enriched = (
        results_df.with_columns(
            pl.col("event")
            .replace_strict(dbhunter_map, default=0)
            .alias("dbhunter_val"),
            pl.when(pl.col("place") > 0)
            .then((11 - pl.col("place")).clip(lower_bound=1))
            .otherwise(0)
            .alias("whc_val"),
        )
        .join(
            # Members who entered the swim on a given day
            results_df.filter(pl.col("event") == "swim")
            .select("id", "date")
            .unique()
            .with_columns(pl.lit(True).alias("swam")),
            on=["id", "date"],
            how="left",
        )
        .with_columns(pl.col("swam").fill_null(False))
    )

    eligible = (
        pl.col("swam")
        | pl.col("event").is_in(swim_not_required)
        | (pl.col("date") == "260301_WHC")
    )

    def _tally(cond, value_col="whc_val"):
        return pl.when(cond).then(pl.col(value_col)).otherwise(0).sum()

    pts_raw = results_enriched.group_by("id").agg(
        pl.col("dbhunter_val").sum().alias("all_attendance"),
        _tally(eligible, "dbhunter_val").alias("dbhunter_pts"),
        _tally(eligible & pl.col("event").is_in(whc_events)).alias("whc_pts"),
        _tally(eligible & pl.col("date").is_in(xmas_dates)).alias("xmas_pts"),
        _tally(
            eligible & pl.col("event").is_in(marathon_events),
        ).alias("presidents_pts"),
        _tally(eligible & pl.col("date").is_in(curlewis_dates)).alias("curlewis_pts"),
    )

    # Club champs: for each event, take the member's best 2 performances across dates
    cchamps = (
        results_enriched.filter(
            pl.col("event").is_in(cchamps_events) & (pl.col("place") > 0),
        )
        .group_by("id", "event")
        .agg(
            pl.col("whc_val").sort(descending=True).head(2).sum().alias("cchamps_pts"),
        )
        .group_by("id")
        .agg(pl.col("cchamps_pts").sum().alias("cchamps"))
    )

    unknown_frame = pl.DataFrame(
        {
            "title": [None] * len(unknown_ids),
            "id": unknown_ids,
            "gender": [None] * len(unknown_ids),
        },
        schema_overrides={"title": pl.Utf8, "id": pl.Utf8, "gender": pl.Utf8},
    )

    pts = (
        pl.concat(
            [members_df.select("title", "id", "gender"), unknown_frame],
            how="vertical_relaxed",
        )
        .join(pts_raw, on="id", how="left")
        .join(cchamps, on="id", how="left")
        .with_columns(pl.col(*tally_cols).fill_null(0))
    )

    # ── Fresher points ──────────────────────────────────────────────────────
    jcc_pts = (
        results_df.filter(pl.col("event").is_in(jcc_events))
        .with_columns(
            pl.when(pl.col("event") == "jcc_individual")
            .then(25)
            .when(pl.col("event") == "jcc_team")
            .then(5)
            .otherwise(0)
            .alias("jcc_pts"),
        )
        .group_by("id")
        .agg(pl.col("jcc_pts").sum().alias("fr_jcc_pts"))
    )

    pts_fr = (
        pts.join(fr_df.select("id"), on="id", how="inner")
        .join(jcc_pts, on="id", how="left")
        .with_columns(
            pl.col("fr_jcc_pts").fill_null(0),
            (pl.col("dbhunter_pts") + pl.col("fr_jcc_pts")).alias("fr_whc_pts"),
        )
    )

    # ── Attendance (long) ───────────────────────────────────────────────────
    attendance_long = (
        results_df.filter(pl.col("place") > 0)
        .select("id", "date", "event", "place")
        .sort("id", "date", "event")
    )

    attendance_fr_long = attendance_long.join(
        fr_df.select("id"),
        on="id",
        how="inner",
    ).sort("id", "date", "event")

    cchamps_long = (
        results_enriched.filter(
            pl.col("event").is_in(cchamps_events) & (pl.col("place") > 0),
        )
        .select(
            "id",
            "date",
            "event",
            pl.col("whc_val").alias("points"),
        )
        .sort("id", "date", "event")
    )
    return (
        attendance_fr_long,
        attendance_long,
        cchamps_long,
        fr_df,
        pts,
        pts_fr,
    )


@app.cell
def _(fr_df):
    mo.ui.dataframe(fr_df)
    return


@app.cell
def _(attendance_fr_long, attendance_long, cchamps_long, pts, pts_fr):
    pts_nonzero = pts.filter(pl.sum_horizontal(pl.col(tally_cols)) > 0)

    mo.vstack(
        [
            mo.md("### All members points"),
            pts_nonzero,
            mo.md("### Fresher points"),
            pts_fr,
            mo.hstack(
                [
                    mo.download(
                        data=pts.write_csv().encode(),
                        filename="pts.csv",
                        label="pts.csv",
                    ),
                    mo.download(
                        data=pts_fr.write_csv().encode(),
                        filename="pts_fr.csv",
                        label="pts_fr.csv",
                    ),
                    mo.download(
                        data=attendance_long.write_csv().encode(),
                        filename="attendance_long.csv",
                        label="attendance_long.csv",
                    ),
                    mo.download(
                        data=attendance_fr_long.write_csv().encode(),
                        filename="attendance_fr_long.csv",
                        label="attendance_fr_long.csv",
                    ),
                    mo.download(
                        data=cchamps_long.write_csv().encode(),
                        filename="cchamps.csv",
                        label="cchamps.csv",
                    ),
                ],
            ),
        ],
    )
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
