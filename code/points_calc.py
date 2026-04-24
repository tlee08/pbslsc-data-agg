import marimo

__generated_with = "0.20.2"
app = marimo.App(width="full")

with app.setup:
    import io
    import json
    import re

    import marimo as mo
    import numpy as np
    import pandas as pd


@app.cell
def _():
    mo.md("""
    # Calculate Points

    Upload all required files. Points are calculated automatically once all files are provided.
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
    mo.vstack([results_file, members_file, freshers_file, bbb_file, jcc_file])
    return (bbb_file, freshers_file, jcc_file, members_file, results_file)


@app.cell
def _(bbb_file, freshers_file, jcc_file, members_file, results_file):
    mo.stop(
        not all([results_file.value, members_file.value, freshers_file.value, bbb_file.value, jcc_file.value]),
        mo.callout(mo.md("Upload all five files to continue."), kind="warn"),
    )

    results_data = json.loads(results_file.value[0].contents)
    members_df = pd.read_json(io.StringIO(members_file.value[0].contents.decode()))
    fr_raw_df = pd.read_csv(io.StringIO(freshers_file.value[0].contents.decode()))
    fr_df = members_df[members_df["id"].isin(fr_raw_df["id"])]
    bbb_fr_attendance = pd.read_csv(io.StringIO(bbb_file.value[0].contents.decode()))
    jcc_results = pd.read_csv(io.StringIO(jcc_file.value[0].contents.decode()))

    # ── Config ──────────────────────────────────────────────────────────────
    whc_events = ["swim", "board", "ski", "run", "flags"]
    swim_not_required = [
        "mswim", "mboard", "mski", "mrun",
        "cswim", "cboard_rescue", "cboard_mal", "cski_surf", "cski_racing", "crun_90", "cflags",
        "imdl",
    ]
    cchamps_dates = [k for k in results_data if "CChamps" in k]
    cchamps_events = ["cswim", "cboard_rescue", "cboard_mal", "cski_surf", "cski_racing", "crun_90", "cflags"]

    def get_dbhunter_pts(event):
        mapping = {
            "swim": 1, "board": 1, "ski": 1, "run": 1, "flags": 1,
            "mswim": 5, "mboard": 5, "mski": 5, "mrun": 5,
            "cswim": 1, "cboard_rescue": 1, "cboard_mal": 1,
            "cski_surf": 1, "cski_racing": 1, "crun_90": 1, "cflags": 1,
            "imdl": 5,
        }
        return mapping.get(event, 0)

    def get_whc_pts(placing):
        return int(np.maximum(11 - placing, 1)) if placing > 0 else 0

    def get_jcc_pts(event_name):
        if re.search("^individual_", event_name):
            return 25
        if re.search("^team_", event_name):
            return 5
        return 0

    # ── Attendance matrix ────────────────────────────────────────────────────
    attendance_df = pd.DataFrame(
        index=members_df["title"],
        columns=pd.Series(
            [f"{d}__{e}" for d in results_data for e in results_data[d]],
            name="event_identifier",
        ),
    ).fillna(0).astype(int)

    for _date in results_data:
        for _event in results_data[_date]:
            for _gender in results_data[_date][_event]:
                for _place, _member in enumerate(results_data[_date][_event][_gender]):
                    attendance_df.loc[_member["title"], f"{_date}__{_event}"] = _place + 1

    # ── Attendance list (member → list of (date__event, place)) ─────────────
    attendance_ls_vect = attendance_df.apply(
        lambda row: tuple((idx, val) for idx, val in row.items() if val > 0),
        axis=1,
    )
    attendance_ls_vect.name = "attendance_list"

    # ── WHC + DB Hunter points ───────────────────────────────────────────────
    whc_pts_df = pd.DataFrame(
        index=members_df["title"],
        columns=pd.Series(["all_attendance", "dbhunter_pts", "whc_pts"], name="pts"),
    ).fillna(0).astype(int)

    for _member, _att in attendance_ls_vect.items():
        _event_ls = [i[0] for i in _att]
        for _date_event, _place in _att:
            _date, _event = _date_event.split("__")
            whc_pts_df.loc[_member, "all_attendance"] += get_dbhunter_pts(_event)
            if f"{_date}__swim" in _event_ls or _event in swim_not_required:
                whc_pts_df.loc[_member, "dbhunter_pts"] += get_dbhunter_pts(_event)
                if _event in whc_events:
                    whc_pts_df.loc[_member, "whc_pts"] += get_whc_pts(_place)

    # ── Club champs points ───────────────────────────────────────────────────
    cchamps_dict = {m: {e: [] for e in cchamps_events} for m in members_df["title"]}
    for _date in cchamps_dates:
        for _event in cchamps_events:
            col = f"{_date}__{_event}"
            if col not in attendance_df.columns:
                continue
            for _member, _place in attendance_df[col].items():
                ls = cchamps_dict[_member][_event]
                ls.append(get_whc_pts(_place))
                ls.sort(reverse=True)
    for _member in cchamps_dict:
        for _event in cchamps_dict[_member]:
            cchamps_dict[_member][_event] = cchamps_dict[_member][_event][:2]

    cchamps_pts_df = pd.DataFrame(index=members_df["title"], columns=pd.Series(cchamps_events)).fillna(0)
    for _event in cchamps_events:
        for _member in cchamps_dict:
            cchamps_pts_df.loc[_member, _event] = np.sum(cchamps_dict[_member][_event])
    cchamps_pts_df = cchamps_pts_df.assign(cchamps=lambda df: df.sum(axis=1))

    # ── Merge all pts ────────────────────────────────────────────────────────
    all_pts_df = pd.merge(
        whc_pts_df, cchamps_pts_df[["cchamps"]],
        left_index=True, right_index=True, how="left",
    )

    # ── Fresher points ───────────────────────────────────────────────────────
    attendance_ls_fr_df = attendance_ls_vect.loc[fr_df["title"]].copy()
    pts_fr_df = all_pts_df.loc[fr_df["title"]].copy()
    pts_fr_df["fr_whc_pts"] = pts_fr_df["dbhunter_pts"]
    pts_fr_df["fr_bbb_pts"] = 0
    pts_fr_df["fr_jcc_pts"] = 0

    for _idx in attendance_ls_fr_df.index:
        if _idx in bbb_fr_attendance["title"].values:
            attendance_ls_fr_df[_idx] += (["260103_bbb__bbb", 0],)
            pts_fr_df.loc[_idx, "fr_bbb_pts"] = 5
            pts_fr_df.loc[_idx, "fr_whc_pts"] += 5

    for _, _row in jcc_results.iterrows():
        if _row["title"] in pts_fr_df.index:
            attendance_ls_fr_df[_row["title"]] += ([f"260405_JCC__{_row['event']}", _row["place"]],)
            _jcc_pts = get_jcc_pts(_row["event"])
            pts_fr_df.loc[_row["title"], "fr_jcc_pts"] = _jcc_pts
            pts_fr_df.loc[_row["title"], "fr_whc_pts"] += _jcc_pts

    # ── Build download bytes ─────────────────────────────────────────────────
    def to_csv_bytes(df):
        return df.to_csv().encode()

    def to_json_bytes(series):
        return series.to_json().encode()

    mo.vstack([
        mo.md("### All members points"),
        all_pts_df[all_pts_df.sum(axis=1) > 0].reset_index(),
        mo.md("### Fresher points"),
        pts_fr_df.reset_index(),
        mo.hstack([
            mo.download(data=to_csv_bytes(attendance_df), filename="attendance.csv", label="attendance.csv"),
            mo.download(data=to_csv_bytes(all_pts_df), filename="pts.csv", label="pts.csv"),
            mo.download(data=to_csv_bytes(pts_fr_df), filename="pts_fr.csv", label="pts_fr.csv"),
            mo.download(data=to_json_bytes(attendance_ls_vect), filename="attendance_ls.json", label="attendance_ls.json"),
            mo.download(data=to_json_bytes(attendance_ls_fr_df), filename="attendance_ls_fr.json", label="attendance_ls_fr.json"),
            mo.download(
                data=to_csv_bytes(cchamps_pts_df[cchamps_pts_df.sum(axis=1) > 0]),
                filename="cchamps_nonzero_pts.csv",
                label="cchamps_nonzero_pts.csv",
            ),
        ]),
    ])
    return


if __name__ == "__main__":
    app.run()
