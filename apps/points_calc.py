# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "marimo>=0.23.6",
# ]
# ///

import marimo

__generated_with = "0.20.2"
app = marimo.App(width="full")

with app.setup:
    import io
    import re

    import marimo as mo
    import numpy as np
    import pandas as pd

    from core.models import Members, Results


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
                ]
            ),
            mo.hstack(
                [
                    members_file,
                    members_file.value[0].name if members_file.value else "",
                ]
            ),
            mo.hstack(
                [
                    freshers_file,
                    freshers_file.value[0].name if freshers_file.value else "",
                ]
            ),
            mo.hstack(
                [bbb_file, bbb_file.value[0].name if bbb_file.value else ""]
            ),
            mo.hstack(
                [jcc_file, jcc_file.value[0].name if jcc_file.value else ""]
            ),
        ]
    )
    return


@app.cell
def _(fr_df):
    mo.ui.dataframe(fr_df)
    return


@app.cell
def _(members_df):
    mo.ui.dataframe(members_df)
    return


@app.function
def get_dbhunter_pts(event):
    mapping = {
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
        "crun_90": 1,
        "cflags": 1,
        "imdl": 5,
    }
    return mapping.get(event, 0)


@app.function
def get_whc_pts(placing):
    return int(np.maximum(11 - placing, 1)) if placing > 0 else 0


@app.function
def get_jcc_pts(event_name):
    if re.search("^individual_", event_name):
        return 25
    if re.search("^team_", event_name):
        return 5
    return 0


@app.function
def to_csv_bytes(df):
    return df.to_csv().encode()


@app.function
def to_json_bytes(series):
    return series.to_json().encode()


@app.cell
def _(bbb_file, freshers_file, jcc_file, members_file, results_file):
    mo.stop(
        not all(
            [
                results_file.value,
                members_file.value,
                freshers_file.value,
                bbb_file.value,
                jcc_file.value,
            ]
        ),
        mo.callout(mo.md("Upload all five files to continue."), kind="warn"),
    )

    results = Results.validate_json(results_file.value[0].contents)
    members = Members.validate_json(members_file.value[0].contents)
    members_df = pd.DataFrame(Members.dump_python(members)).set_index("title")
    fr_raw_df = pd.read_csv(io.StringIO(freshers_file.value[0].contents.decode()))
    fr_df = members_df[members_df["id"].isin(fr_raw_df["id"])]
    bbb_fr_attendance = pd.read_csv(
        io.StringIO(bbb_file.value[0].contents.decode())
    ).set_index("title")
    jcc_results = pd.read_csv(
        io.StringIO(jcc_file.value[0].contents.decode())
    ).set_index("title")

    # ── Config ──────────────────────────────────────────────────────────────
    whc_events = [
        "swim",
        "board",
        "ski",
        "run",
        "flags",
    ]
    marathon_events = [
        "mswim",
        "mboard",
        "mski",
        "mrun",
    ]
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
        "crun_90",
        "cflags",
        "imdl",
    ]
    cchamps_events = [
        "cswim",
        "cboard_rescue",
        "cboard_mal",
        "cski_surf",
        "cski_racing",
        "crun_90",
        "cflags",
    ]
    cchamps_dates = [_k for _k in results if "_CChamps" in _k]
    xmas_dates = [_k for _k in results if "_Xmas" in _k]
    curlewis_dates = [
        "250928_WHC",
        "251005_WHC",
    ]

    # ── Attendance matrix ────────────────────────────────────────────────────
    attendance_df = (
        pd.DataFrame(
            index=members_df.index,
            columns=pd.Series(
                [
                    f"{_date}__{_event}"
                    for _date in results
                    for _event in results[_date]
                ],
                name="date_event",
            ),
        )
        .fillna(0)
        .astype(int)
    )

    for _date, _date_data in results.items():
        for _event, _event_data in _date_data.items():
            for _gender, _gender_data in _event_data.items():
                for _place, _entry in enumerate(_gender_data, 1):
                    attendance_df.loc[_entry.title, f"{_date}__{_event}"] = _place

    # ── WHC + DB Hunter + Xmas cup points ────────────────────────────────────
    # Make initial df with members as rows, include gender, and all points tallies
    pts_df = members_df[["id", "gender"]].assign(
        all_attendance=0,
        dbhunter_pts=0,
        whc_pts=0,
        xmas_pts=0,
        presidents_pts=0,
        curlewis_pts=0,
    )

    for _entry, _row in attendance_df.iterrows():
        for _date_event_idx, _place in _row.items():
            if _place == 0:
                continue
            _date, _event = _date_event_idx.split("__")
            # All attendance record
            pts_df.loc[_entry, "all_attendance"] += get_dbhunter_pts(_event)
            if (
                (
                    _row.get(f"{_date}__swim", 0) > 0
                )  # Entered swim on day (if swim)
                or (_event in swim_not_required)  # Or swim not required
                or _date == "260301_WHC"  # TODO: remove nxt sns no water events
            ):
                # DB Hunter pts
                pts_df.loc[_entry, "dbhunter_pts"] += get_dbhunter_pts(_event)
                # WHC pts
                if _event in whc_events:
                    pts_df.loc[_entry, "whc_pts"] += get_whc_pts(_place)
                # Xmas cup pts
                if _date in xmas_dates:
                    pts_df.loc[_entry, "xmas_pts"] += get_whc_pts(_place)
                # President's cup (marathon events)
                if _event in marathon_events:
                    pts_df.loc[_entry, "presidents_pts"] += get_whc_pts(_place)
                # Curlewis cup (first two WHCs, no hcaps)
                if _date in curlewis_dates:
                    pts_df.loc[_entry, "curlewis_pts"] += get_whc_pts(_place)

    # ── Club champs points ───────────────────────────────────────────────────
    # For each CChamps event,
    # take the best 2 placing for each member and sum their points.
    cchamps_cols = [
        _col
        for _col in attendance_df.columns
        if _col.split("__")[1] in cchamps_events
    ]
    cchamps_pts_df = (
        attendance_df[cchamps_cols]
        .map(lambda _x: get_whc_pts(_x) if _x > 0 else 0)
        .melt(ignore_index=False)
        .assign(event=lambda df: df["date_event"].str.extract(r"__(.+)$"))
        .query("value > 0")
        .groupby(["title", "date_event"])["value"]
        .apply(lambda _x: _x.nlargest(2).sum())
        .unstack()
        .fillna(0)
    )
    cchamps_pts_df["cchamps"] = cchamps_pts_df.sum(axis=1)

    # ── Merge all pts ────────────────────────────────────────────────────────
    pts_df = pts_df.merge(
        cchamps_pts_df[["cchamps"]],
        left_index=True,
        right_index=True,
        how="left",
    ).fillna(0)

    # ── Fresher points ───────────────────────────────────────────────────────
    pts_fr_df = pts_df.loc[fr_df.index].copy()
    pts_fr_df["fr_whc_pts"] = pts_fr_df["dbhunter_pts"]

    pts_fr_df["fr_bbb_pts"] = 0
    bbb_members = pts_fr_df.index.intersection(bbb_fr_attendance.index)
    pts_fr_df.loc[bbb_members, "fr_bbb_pts"] = 5
    pts_fr_df.loc[bbb_members, "fr_whc_pts"] += 5

    pts_fr_df["fr_jcc_pts"] = 0
    jcc_fr = jcc_results[jcc_results.index.isin(fr_df.index)]
    jcc_pts_by_member = jcc_fr["event"].map(get_jcc_pts)
    pts_fr_df.loc[jcc_pts_by_member.index, "fr_jcc_pts"] = jcc_pts_by_member
    pts_fr_df.loc[jcc_pts_by_member.index, "fr_whc_pts"] += jcc_pts_by_member

    # ── Attendance list (member → list of (date__event, place)) ─────────────
    attendance_ls_vect = attendance_df.apply(
        lambda _row: tuple(
            (_date_event_idx, _place)
            for _date_event_idx, _place in _row.items()
            if _place > 0
        ),
        axis=1,
    )
    attendance_ls_vect.name = "attendance_list"

    attendance_ls_fr_vect = attendance_ls_vect.loc[fr_df.index].copy()
    for m in bbb_members:
        attendance_ls_fr_vect[m] += (("260103_bbb__bbb", 0),)
    for _, row in jcc_fr.iterrows():
        attendance_ls_fr_vect[row.name] += (
            (f"260405_JCC__{row['event']}", row["place"]),
        )

    # ── Build download bytes ─────────────────────────────────────────────────

    mo.vstack(
        [
            mo.md("### All members points"),
            pts_df[
                pts_df.select_dtypes(include="number").sum(axis=1) > 0
            ].reset_index(),
            mo.md("### Fresher points"),
            pts_fr_df.reset_index(),
            mo.hstack(
                [
                    mo.download(
                        data=to_csv_bytes(attendance_df),
                        filename="attendance.csv",
                        label="attendance.csv",
                    ),
                    mo.download(
                        data=to_csv_bytes(pts_df),
                        filename="pts.csv",
                        label="pts.csv",
                    ),
                    mo.download(
                        data=to_csv_bytes(pts_fr_df),
                        filename="pts_fr.csv",
                        label="pts_fr.csv",
                    ),
                    mo.download(
                        data=to_json_bytes(attendance_ls_vect),
                        filename="attendance_ls.json",
                        label="attendance_ls.json",
                    ),
                    mo.download(
                        data=to_json_bytes(attendance_ls_fr_vect),
                        filename="attendance_ls_fr.json",
                        label="attendance_ls_fr.json",
                    ),
                    mo.download(
                        data=to_csv_bytes(
                            cchamps_pts_df[cchamps_pts_df.sum(axis=1) > 0]
                        ),
                        filename="cchamps_nonzero_pts.csv",
                        label="cchamps_nonzero_pts.csv",
                    ),
                ]
            ),
        ]
    )
    return fr_df, members_df


if __name__ == "__main__":
    app.run()
