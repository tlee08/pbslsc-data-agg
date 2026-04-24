import marimo

__generated_with = "0.20.2"
app = marimo.App(width="full")

with app.setup:
    import json
    import os

    import marimo as mo
    import numpy as np
    import re
    import pandas as pd
    import seaborn as sns


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Points Calculation
    """)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Results DF List
    """)
    return


@app.function
def read_json(fp: str) -> dict:
    with open(fp) as f:
        return json.load(f)


@app.function
def write_json(data: dict | list, fp: str) -> None:
    with open(fp, "w") as f:
        json.dump(data, f, indent=2)


@app.cell
def _():
    genders = ["m", "f"]

    results_data = read_json(os.path.join("results", "whc_results_260329.json"))

    members_df = pd.read_json(os.path.join("members", "members.json"))

    fr_raw_df = pd.read_csv(os.path.join("members", "freshers.csv"))
    fr_df = members_df[members_df["id"].isin(fr_raw_df["id"])]
    return fr_df, members_df, results_data


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Getting participation

    Represented as both:
    * DataFrame of rows (members) and columns (date-event)
    * Series of members and a list of their events participated in & placing
    """)
    return


@app.cell
def _(members_df, results_data):
    # dataframe of `member_title` x `list of events they did as "<date>__<event>"`
    # Where each cell is the member's placing in the given event, or 0 (if event not entered)
    attendance_df = (
        pd.DataFrame(
            index=members_df["title"],
            columns=pd.Series(
                [
                    f"{_date}__{_event}"
                    for _date in results_data
                    for _event in results_data[_date]
                ],
                name="event_identifier",
            ),
        )
        .fillna(0)
        .astype(int)
    )

    # For each date
    for _date in results_data:
        # For each event on the day
        for _event in results_data[_date]:
            # For each gender
            for _gender in results_data[_date][_event]:
                # For each participant in the specific event, add to their list of participated events
                for _place, _member in enumerate(
                    results_data[_date][_event][_gender],
                ):
                    _place = _place + 1  # To make places 1-indexed
                    _member = _member["title"]
                    # Record presence
                    attendance_df.loc[_member, f"{_date}__{_event}"] = _place

    attendance_df
    return (attendance_df,)


@app.cell
def _(attendance_df):
    # Heatmap of all participants for all events
    sns.heatmap(
        attendance_df > 0,
        cbar=False,
        yticklabels=False,
        xticklabels=False,
    )
    return


@app.cell
def _(attendance_df):
    # Convert attendance to a list of events attended per member (and their places in each event)
    attendance_ls_vect = attendance_df.apply(
        lambda _row: tuple(
            (_idx, _val) for _idx, _val in _row.items() if _val > 0
        ),
        axis=1,
    )
    attendance_ls_vect.name = "attendance_list"

    # Show attendance for each person
    attendance_ls_vect[
        attendance_ls_vect.apply(lambda x: len(x) > 0)
    ].reset_index()
    return (attendance_ls_vect,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Points Calculation

    NOTE: for each WHC event, participant MUST have completed the swim to get any points.
    Don't need swim for club champs.
    Marathon event itself is enough (goes without saying).

    * DB Hunter based on points mapping
    * Fresher WHC points are DB Hunter points
    * WHC points are ONLY for WHC and Xmas cup events (no club champs, no marathon)
      * Points are 1st -> 10pts, 2nd -> 9pts, ...., 9 -> 2pts, 10th+ -> 1pt
    * Club champs are:
      * For each competitor's events, their best 2 performances are taken (i.e. most points)
      * Then sum each competitor's points from their counted events
    * BBB points are 5 for freshers only (no WHC pts)
    """)
    return


@app.cell
def _():
    # WHC events require a swim to get pts except for these events
    # These events DON'T require a swim (either marathon or cclub events)
    swim_not_required = [
        # Marathon
        "mswim",
        "mboard",
        "mski",
        "mrun",
        # cclubs
        "cswim",
        "cboard_rescue",
        "cboard_mal",
        "cski_surf",
        "cski_racing",
        "crun_90",
        "cflags",
        # IMDL
        "imdl",
        # JCC
    ]

    whc_events = [
        "swim",
        "board",
        "ski",
        "run",
        "flags",
    ]

    cchamps_dates = [
        "251130_CChamps",
        "260208_CChamps",
        "260222_CChamps",
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
    return cchamps_dates, cchamps_events, swim_not_required, whc_events


@app.function
def get_dbhunter_pts(event: str) -> int:
    mapping = {
        # Regular
        "swim": 1,
        "board": 1,
        "ski": 1,
        "run": 1,
        "flags": 1,
        # Marathon
        "mswim": 5,
        "mboard": 5,
        "mski": 5,
        "mrun": 5,
        # cclubs
        "cswim": 1,
        "cboard_rescue": 1,
        "cboard_mal": 1,
        "cski_surf": 1,
        "cski_racing": 1,
        "crun_90": 1,
        "cflags": 1,
        # IMDL
        "imdl": 5,
        # JCC
    }
    return mapping[event]


@app.function
def get_whc_pts(placing: int) -> int:
    if placing <= 0:
        return 0
    return np.maximum(11 - placing, 1)


@app.function
def get_cchamps_pts_step1(placing: int) -> int:
    if placing <= 0:
        return 0
    return np.maximum(11 - placing, 1)


@app.function
def get_jcc_attendance_pts(event_name: str) -> int:
    if re.search("^individual_", event_name):
        return 25
    elif re.search("^team_", event_name):
        return 5
    else:
        raise ValueError(
            "event name must be in form: 'individual_' or 'team_'"
        )


@app.cell
def _(attendance_ls_vect, members_df, swim_not_required, whc_events):
    whc_pts_df = (
        pd.DataFrame(
            index=members_df["title"],
            columns=pd.Series(
                ["all_attendance", "dbhunter_pts", "whc_pts"],
                name="pts",
            ),
        )
        .fillna(0)
        .astype(int)
    )

    # Calculating pts
    for _member, _attendance_ls in attendance_ls_vect.items():
        _attendance_event_ls = [_i[0] for _i in _attendance_ls]
        # For each event that the curr member attended
        for _date_event, _place in _attendance_ls:
            # Extract event
            _date, _event = _date_event.split("__")
            # Getting all attendance points (same as DB Hunter but don't need WHC swim)
            whc_pts_df.loc[_member, "all_attendance"] += get_dbhunter_pts(_event)
            # Make sure that they participated in the swim on the day (to qualify for pts)
            # OR if the event is a cclub event or marathon event
            if (
                f"{_date}__swim" in _attendance_event_ls
                or _event in swim_not_required
            ):
                # Add dbhunter pts based on config map
                whc_pts_df.loc[_member, "dbhunter_pts"] += get_dbhunter_pts(_event)
                # Add whc pts based on placing ONLY for WHC events
                if _event in whc_events:
                    whc_pts_df.loc[_member, "whc_pts"] += get_whc_pts(_place)
    return (whc_pts_df,)


@app.cell
def _(attendance_df, cchamps_dates, cchamps_events, members_df):
    # Calculating club champs points
    # Making dict of: {member: {event: [ordered points]}}
    cchamps_dict = {
        _member: {_event: [] for _event in cchamps_events}
        for _member in members_df["title"]
    }
    for _date in cchamps_dates:
        for _event in cchamps_events:
            for _member, _place in attendance_df[f"{_date}__{_event}"].items():
                _ls = cchamps_dict[_member][_event]
                _ls.append(get_cchamps_pts_step1(_place))
                _ls.sort(reverse=True)
    # Getting only top 2 results for each competitor & each event
    for _member in cchamps_dict:
        for _event in cchamps_dict[_member]:
            cchamps_dict[_member][_event] = cchamps_dict[_member][_event][:2]
    # Summing points for each event
    cchamps_pts_df = pd.DataFrame(
        index=members_df["title"],
        columns=pd.Series(cchamps_events, name="event"),
    ).fillna(0)
    for _event in cchamps_events:
        for _member in cchamps_dict:
            cchamps_pts_df.loc[_member, _event] = np.sum(
                cchamps_dict[_member][_event]
            )
    # Summing overall points
    cchamps_pts_df = cchamps_pts_df.assign(cchamps=(lambda _df: _df.sum(axis=1)))
    return (cchamps_pts_df,)


@app.cell
def _(cchamps_pts_df, whc_pts_df):
    all_pts_df = pd.merge(
        left=whc_pts_df,
        right=cchamps_pts_df[["cchamps"]],
        left_index=True,
        right_index=True,
        how="left",
    )

    # Show points
    all_pts_df[all_pts_df.sum(axis=1) > 0].reset_index()
    return (all_pts_df,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ### Getting points for freshers

    * Noting whether they were there for BBB
    * Including 5pts for BBB attendance to "fresher_whc_points"
    """)
    return


@app.cell
def _(all_pts_df, attendance_ls_vect, fr_df):
    bbb_fr_attendance = pd.read_csv(os.path.join("results", "bbb_freshers.csv"))
    jcc_results = pd.read_csv(os.path.join("results", "jcc_results.csv"))

    # Making attendance and pts dfs for just freshers
    attendance_ls_fr_df = attendance_ls_vect.loc[fr_df["title"]]
    pts_fr_df = all_pts_df.loc[fr_df["title"]]

    # Starting off with DB Hunter pts
    pts_fr_df["fr_whc_pts"] = pts_fr_df["dbhunter_pts"]

    # Adding BBB points
    bbb_pts = 5
    pts_fr_df["fr_bbb_pts"] = 0
    # For each fresher, if they attended BBB, then
    # record this in the attendance list, bbb_pts, and add to fresher_whc_pts
    for _idx in attendance_ls_fr_df.index:
        if _idx in bbb_fr_attendance["title"].values:
            attendance_ls_fr_df[_idx] += (["260103_bbb__bbb", 0],)
            pts_fr_df.loc[_idx, "fr_bbb_pts"] = bbb_pts
            pts_fr_df.loc[_idx, "fr_whc_pts"] += bbb_pts

    # Adding JCC points
    jcc_indiv_pts = 25
    jcc_team_pts = 5
    pts_fr_df["fr_jcc_pts"] = 0
    # For each jcc record, we get (if they're a fresher, i.e. member_id exists):
    # whether event was "individual_..." or "team_..." (informs # of points)
    # (and update the fr attendance and pts dfs with this above info)
    # Placing in event (not used for points, but just a matter of record keeping)
    for _idx, _row in jcc_results.iterrows():
        if _row["title"] in pts_fr_df.index:
            attendance_ls_fr_df[_row["title"]] += (
                [f"260405_JCC__{_row['event']}", _row["place"]],
            )
            _row_jcc_pts = get_jcc_attendance_pts(_row["event"])
            pts_fr_df.loc[_row["title"], "fr_jcc_pts"] = _row_jcc_pts
            pts_fr_df.loc[_row["title"], "fr_whc_pts"] += _row_jcc_pts


    # Show fresher points
    pts_fr_df.reset_index()
    return attendance_ls_fr_df, pts_fr_df


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ### Saving Points Results
    """)
    return


@app.cell
def _(
    all_pts_df,
    attendance_df,
    attendance_ls_fr_df,
    attendance_ls_vect,
    cchamps_pts_df,
    pts_fr_df,
):
    attendance_df.to_csv(os.path.join("points", "attendance.csv"))

    attendance_ls_vect.to_json(os.path.join("points", "attendance_ls.json"))
    all_pts_df.to_csv(os.path.join("points", "pts.csv"))

    pts_fr_df.to_csv(os.path.join("points", "pts_fr.csv"))
    attendance_ls_fr_df.to_json(os.path.join("points", "attendance_ls_fr.json"))

    cchamps_pts_df[cchamps_pts_df.sum(axis=1) > 0].to_csv(
        os.path.join("points", "cchamps_nonzero_pts.csv")
    )
    return


@app.cell(hide_code=True)
def _():
    return


if __name__ == "__main__":
    app.run()
