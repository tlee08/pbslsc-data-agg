import marimo

__generated_with = "0.20.2"
app = marimo.App(width="full")

with app.setup:
    import json
    import os
    import re

    import marimo as mo
    import numpy as np
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
    return members_df, results_data


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
    # Convert attendance to a list of events attended per member (and their places in each event)
    attendance_ls_vect = attendance_df.apply(
        lambda _row: tuple(
            (_idx, _val) for _idx, _val in _row.items() if _val > 0
        ),
        axis=1,
    )
    attendance_ls_vect.name = "attendance_list"

    # Show attendance for each person
    # attendance_ls_vect[attendance_ls_vect.apply(lambda x: len(x) > 0)]
    return (attendance_ls_vect,)


@app.cell
def _(attendance_ls_vect):
    _craft_events_ls = [
        "board",
        "cboard_rescue",
        "mboard",
        "ski",
        "cski_surf",
        "mski",
    ]

    attendance_craft_ls_vect = attendance_ls_vect.apply(
        lambda _row: [
            _i[0] for _i in _row if re.search("|".join(_craft_events_ls), _i[0])
        ]
    )

    attendance_craft_ls_vect[
        attendance_craft_ls_vect.apply(lambda x: len(x) > 0)
    ].reset_index()
    return (attendance_craft_ls_vect,)


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


@app.function
def get_board_use(event: str) -> int:
    if event in ["board", "cboard_rescue", "mboard"]:
        return 1
    return 0


@app.function
def get_ski_use(event: str) -> int:
    if event in ["ski", "cski_surf", "mski"]:
        return 1
    return 0


@app.cell
def _(attendance_craft_ls_vect, members_df):
    attendance_count_df = (
        pd.DataFrame(
            index=members_df["title"],
            columns=pd.Series(
                ["board_usage", "ski_usage"],
                name="pts",
            ),
        )
        .fillna(0)
        .astype(int)
    )

    # Calculating pts
    for _member, _attendance_ls in attendance_craft_ls_vect.items():
        # For each event that the curr member attended
        for _date_event in _attendance_ls:
            # Extract event
            _date, _event = _date_event.split("__")
            # Getting all attendance points (same as DB Hunter but don't need WHC swim)
            attendance_count_df.loc[_member, "board_usage"] += get_board_use(
                _event
            )
            attendance_count_df.loc[_member, "ski_usage"] += get_ski_use(_event)

    attendance_count_df[attendance_count_df.sum(axis=1) > 0]
    return (attendance_count_df,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ### Saving Points Results
    """)
    return


@app.cell
def _(attendance_count_df, attendance_craft_ls_vect):
    attendance_craft_ls_vect.to_json(
        os.path.join("other", "craft_attendance_breakdown.json")
    )
    attendance_count_df.to_csv(os.path.join("other", "craft_attendance_count.csv"))

    return


@app.cell(hide_code=True)
def _():
    return


if __name__ == "__main__":
    app.run()
