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
    from pathlib import Path

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
    mo.md("""# Calculate Points""")
    return


@app.cell
def _():
    data = Path.cwd().parent / "data" / "2026_27"
    return (data,)


@app.cell
def _(data):
    members = Members.validate_json((data / "members.json").read_text())
    results = Results.validate_json((data / "results.json").read_text())
    lookups = json.loads((data / "lookups.json").read_text())

    members_df = members_to_frame(members)
    results_df = results_to_frame(results)
    return lookups, members_df, results_df


@app.cell
def _(lookups, members_df, results_df):
    # ── Points config — edit values here ────────────────────────────────
    whc_first = 11  # points for 1st place, −1 per place (min 1)
    attendance = {"normal": 1, "marathon": 5}  # attendance points per event kind
    jcc_points = {"jcc_individual": 25, "jcc_team": 5}
    curlewis_dates = ["260927_whc", "261004_whc"]
    # TODO: freshers/bbb — members.json will soon carry membership="Fresher";
    # bbb attendance (5 pts) still needs an external file, not wired yet.

    # Event categories (single source of truth: lookups.json)
    s = lookups["series"]
    whc_events = s["whc"]["events"]
    cchamps_events = s["cchamps"]["events"]
    marathon_events = [e for k in ("mswim", "mboard", "mski", "mrun") for e in s[k]["events"]]
    jcc_events = s["jcc"]["events"]
    imdl_events = s["imdl"]["events"]
    swim_not_required = [*marathon_events, *cchamps_events, *imdl_events]
    xmas_dates = [d for d in results_df["date"].unique() if "_xmas" in d]

    attendance_map = {e: attendance["marathon"] for e in [*marathon_events, *imdl_events]} | {
        e: attendance["normal"] for e in [*whc_events, *cchamps_events]
    }

    fr_df = members_df.filter(pl.col("membership") == "Fresher")

    # ── Points from results ─────────────────────────────────────────────
    results_enriched = (
        results_df.with_columns(
            pl.col("event").replace_strict(attendance_map, default=0).alias("dbhunter_val"),
            pl.when(pl.col("place") > 0)
            .then((whc_first - pl.col("place")).clip(lower_bound=1))
            .otherwise(0)
            .alias("whc_val"),
        )
        .join(
            results_df.filter(pl.col("event") == "swim")
            .select("title", "date")
            .unique()
            .with_columns(pl.lit(True).alias("swam")),
            on=["title", "date"],
            how="left",
        )
        .with_columns(pl.col("swam").fill_null(False))
    )

    eligible = pl.col("swam") | pl.col("event").is_in(swim_not_required)

    def _tally(cond, value_col="whc_val"):
        return pl.when(cond).then(pl.col(value_col)).otherwise(0).sum()

    pts_raw = results_enriched.group_by("title").agg(
        pl.col("dbhunter_val").sum().alias("all_attendance"),
        _tally(eligible, "dbhunter_val").alias("dbhunter_pts"),
        _tally(eligible & pl.col("event").is_in(whc_events)).alias("whc_pts"),
        _tally(eligible & pl.col("date").is_in(xmas_dates)).alias("xmas_pts"),
        _tally(eligible & pl.col("event").is_in(marathon_events)).alias("presidents_pts"),
        _tally(eligible & pl.col("date").is_in(curlewis_dates)).alias("curlewis_pts"),
    )

    cchamps = (
        results_enriched.filter(pl.col("event").is_in(cchamps_events) & (pl.col("place") > 0))
        .group_by("title", "event")
        .agg(pl.col("whc_val").sort(descending=True).head(2).sum().alias("cchamps_pts"))
        .group_by("title")
        .agg(pl.col("cchamps_pts").sum().alias("cchamps"))
    )

    pts = (
        members_df.select("title", "id", "gender")
        .join(pts_raw, on="title", how="left")
        .join(cchamps, on="title", how="left")
        .with_columns(pl.col(*tally_cols).fill_null(0))
    )

    # ── Fresher points ──────────────────────────────────────────────────
    jcc_pts = (
        results_enriched.filter(pl.col("event").is_in(jcc_events))
        .with_columns(pl.col("event").replace_strict(jcc_points, default=0).alias("jcc_val"))
        .group_by("title")
        .agg(pl.col("jcc_val").sum().alias("fr_jcc_pts"))
    )

    pts_fr = (
        pts.join(fr_df.select("title"), on="title", how="inner")
        .join(jcc_pts, on="title", how="left")
        .with_columns(
            pl.col("fr_jcc_pts").fill_null(0),
            (pl.col("dbhunter_pts") + pl.col("fr_jcc_pts")).alias("fr_whc_pts"),
        )
    )

    # ── Long-form outputs ───────────────────────────────────────────────
    attendance_long = (
        results_df.filter(pl.col("place") > 0)
        .select("title", "date", "event", "place")
        .sort("title", "date", "event")
    )
    attendance_fr_long = attendance_long.join(fr_df.select("title"), on="title", how="inner")
    cchamps_long = (
        results_enriched.filter(pl.col("event").is_in(cchamps_events) & (pl.col("place") > 0))
        .select("title", "date", "event", pl.col("whc_val").alias("points"))
        .sort("title", "date", "event")
    )

    return attendance_fr_long, attendance_long, cchamps_long, fr_df, pts, pts_fr


@app.cell
def _(members_df, results_df):
    unknown = sorted(set(results_df["title"].to_list()) - set(members_df["title"].to_list()))
    mo.md(f"⚠️ Results entries with no matching member (dropped): {unknown or 'none'}")
    return


@app.cell
def _(attendance_fr_long, attendance_long, cchamps_long, data, pts, pts_fr):
    pts_nonzero = pts.filter(pl.sum_horizontal(pl.col(tally_cols)) > 0)

    for name, df in [
        ("pts.csv", pts),
        ("pts_fr.csv", pts_fr),
        ("attendance_long.csv", attendance_long),
        ("attendance_fr_long.csv", attendance_fr_long),
        ("cchamps.csv", cchamps_long),
    ]:
        df.write_csv(data / name)

    mo.vstack(
        [
            mo.md("### All members (with points)"),
            pts_nonzero,
            mo.md("### Freshers"),
            pts_fr,
            mo.md(
                f"Saved `pts.csv`, `pts_fr.csv`, `attendance_long.csv`, "
                f"`attendance_fr_long.csv`, `cchamps.csv` to `{data}`"
            ),
        ],
    )
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
