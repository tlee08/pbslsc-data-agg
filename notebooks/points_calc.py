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
    import io

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
    freshers_file = mo.ui.file(label="Upload freshers.csv", filetypes=[".csv"])
    bbb_file = mo.ui.file(label="Upload bbb_freshers.csv", filetypes=[".csv"])
    jcc_file = mo.ui.file(label="Upload jcc_results.csv", filetypes=[".csv"])
    return bbb_file, freshers_file, jcc_file, members_file, results_file


@app.cell
def _(bbb_file, freshers_file, jcc_file, members_file, results_file):
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
            mo.hstack(
                [
                    freshers_file,
                    freshers_file.value[0].name if freshers_file.value else "",
                ],
            ),
            mo.hstack([bbb_file, bbb_file.value[0].name if bbb_file.value else ""]),
            mo.hstack([jcc_file, jcc_file.value[0].name if jcc_file.value else ""]),
        ],
    )
    return


@app.cell
def _(members_file, results_file):
    mo.stop(
        not results_file.value or not members_file.value,
        mo.callout(
            mo.md("Upload the results and members files to continue."), kind="warn",
        ),
    )

    results = Results.validate_json(results_file.value[0].contents)
    members = Members.validate_json(members_file.value[0].contents)

    members_df = members_to_frame(members)
    results_df = results_to_frame(results)
    return members_df, results_df


@app.cell
def _(members_df):
    mo.ui.dataframe(members_df)
    return


@app.cell
def _(bbb_file, freshers_file, jcc_file, members_df, results_df):
    mo.stop(
        not all([freshers_file.value, bbb_file.value, jcc_file.value]),
        mo.callout(
            mo.md("Upload the freshers, BBB, and JCC files to continue."), kind="warn",
        ),
    )

    fr_raw = pl.read_csv(
        io.BytesIO(freshers_file.value[0].contents), infer_schema=False,
    )
    bbb_attendance = pl.read_csv(
        io.BytesIO(bbb_file.value[0].contents), infer_schema=False,
    ).rename({"title": "member_title"})
    jcc_results = pl.read_csv(
        io.BytesIO(jcc_file.value[0].contents), infer_schema=False,
    ).rename({"title": "member_title"})

    fr_df = members_df.filter(pl.col("id").is_in(fr_raw["id"].to_list()))

    # ── Config ──────────────────────────────────────────────────────────────
    dbhunter_map = {
        "swim": 1, "board": 1, "ski": 1, "run": 1, "flags": 1,
        "mswim": 5, "mboard": 5, "mski": 5, "mrun": 5,
        "cswim": 1, "cboard_rescue": 1, "cboard_mal": 1,
        "cski_surf": 1, "cski_racing": 1, "crun_90": 1, "cflags": 1,
        "imdl": 5,
    }
    whc_events = ["swim", "board", "ski", "run", "flags"]
    marathon_events = ["mswim", "mboard", "mski", "mrun"]
    swim_not_required = [
        "mswim", "mboard", "mski", "mrun",
        "cswim", "cboard_rescue", "cboard_mal",
        "cski_surf", "cski_racing", "crun_90", "cflags", "imdl",
    ]
    cchamps_events = [
        "cswim", "cboard_rescue", "cboard_mal",
        "cski_surf", "cski_racing", "crun_90", "cflags",
    ]
    xmas_dates = [_k for _k in results_df["date"].unique() if "_Xmas" in _k]
    curlewis_dates = ["250928_WHC", "251005_WHC"]

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
            .select("member_title", "date")
            .unique()
            .with_columns(pl.lit(True).alias("swam")),
            on=["member_title", "date"],
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

    pts_raw = results_enriched.group_by("member_title").agg(
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
        .group_by("member_title", "event")
        .agg(
            pl.col("whc_val").sort(descending=True).head(2).sum().alias("cchamps_pts"),
        )
        .group_by("member_title")
        .agg(pl.col("cchamps_pts").sum().alias("cchamps"))
    )

    pts = (
        members_df.select("member_title", "id", "gender")
        .join(pts_raw, on="member_title", how="left")
        .join(cchamps, on="member_title", how="left")
        .with_columns(pl.col(*tally_cols).fill_null(0))
    )

    # ── Fresher points ──────────────────────────────────────────────────────
    bbb_titles = bbb_attendance["member_title"].to_list()

    jcc_pts = (
        jcc_results.with_columns(
            pl.when(pl.col("event").str.starts_with("individual_"))
            .then(25)
            .when(pl.col("event").str.starts_with("team_"))
            .then(5)
            .otherwise(0)
            .alias("jcc_pts"),
        )
        .group_by("member_title")
        .agg(pl.col("jcc_pts").sum().alias("fr_jcc_pts"))
    )

    pts_fr = (
        pts.join(fr_df.select("member_title"), on="member_title", how="inner")
        .with_columns(
            pl.when(pl.col("member_title").is_in(bbb_titles))
            .then(5)
            .otherwise(0)
            .alias("fr_bbb_pts"),
        )
        .join(jcc_pts, on="member_title", how="left")
        .with_columns(
            pl.col("fr_jcc_pts").fill_null(0),
            (
                pl.col("dbhunter_pts")
                + pl.col("fr_bbb_pts")
                + pl.col("fr_jcc_pts")
            ).alias("fr_whc_pts"),
        )
    )

    # ── Attendance (long) ───────────────────────────────────────────────────
    attendance_long = (
        results_df.filter(pl.col("place") > 0)
        .select("member_title", "date", "event", "place")
        .sort("member_title", "date", "event")
    )

    bbb_rows = pl.DataFrame(
        {
            "member_title": bbb_titles,
            "date": ["260103_bbb"] * len(bbb_titles),
            "event": ["bbb"] * len(bbb_titles),
            "place": [0] * len(bbb_titles),
        },
    )
    jcc_rows = jcc_results.select(
        "member_title",
        pl.lit("260405_JCC").alias("date"),
        "event",
        pl.col("place").cast(pl.Int64),
    )
    attendance_fr_long = pl.concat(
        [
            attendance_long.join(
                fr_df.select("member_title"), on="member_title", how="inner",
            ),
            bbb_rows,
            jcc_rows,
        ],
    ).sort("member_title", "date", "event")

    cchamps_long = (
        results_enriched.filter(
            pl.col("event").is_in(cchamps_events) & (pl.col("place") > 0),
        )
        .select(
            "member_title", "date", "event", pl.col("whc_val").alias("points"),
        )
        .sort("member_title", "date", "event")
    )

    return attendance_fr_long, attendance_long, cchamps_long, fr_df, pts, pts_fr


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


if __name__ == "__main__":
    app.run()
