import marimo

__generated_with = "0.20.2"
app = marimo.App(width="full")

with app.setup:
    import json
    import os

    import copy
    import marimo as mo
    import numpy as np
    import pandas as pd


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Updating Handicaps

    **Method**

    Percentile-Based Adjustment

    * Use a target percentile (e.g. 0.66 is top third) rather than target placing.
    * Improves Option 1 by normalizing for heat size.
    * $\Delta handicap = (percentile - target\_percentile) \times K$
    * K is a tuning constant (e.g. 10 seconds).
    * Pros
        * Accounts for different heat sizes
        * Still simple
        * More statistically fair
    * Cons
        * Slightly harder to explain
        * Still Doesn't consider field strength on the day
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
def write_json(data: dict | list, fp: str):
    with open(fp, "w") as f:
        json.dump(data, f, indent=2)


@app.cell
def _():
    results_dir = "results"
    events = [
        "swim",
        "board",
        "ski",
        "run",
        # "flags",
    ]
    genders = ["m", "f"]

    # Handicap increments
    hcap_incr_plus = 2
    hcap_incr_minus = 2  # This gets flipped to neg

    # Handicap maximum increases from a single event
    hcap_max_plus = 20
    hcap_max_minus = 30  # This gets flipped to neg

    # Above this percentile -> higher handicap
    # Below this percentile -> lower handicap
    # Handicapping top third
    percentile_threshold = 0.67

    # Considering that increments are not in units of 5s
    # we round final handicaps to nearest 5s in a new column
    # BUT keep the original precise handicap value for future calculations
    round_incr = 5
    return (
        events,
        genders,
        hcap_incr_minus,
        hcap_incr_plus,
        hcap_max_minus,
        hcap_max_plus,
        percentile_threshold,
        round_incr,
    )


@app.cell
def _():
    new_dates_for_hcap = ["260406_WHC"]

    results_data = read_json(os.path.join("results", "whc_results_260406.json"))

    old_hcaps = read_json(os.path.join("hcaps", "history", "hcaps_260403.json"))

    members = pd.read_json(os.path.join("members", "members.json"))
    return members, new_dates_for_hcap, old_hcaps, results_data


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Making Handicaps
    """)
    return


@app.cell
def _(
    events,
    genders,
    hcap_incr_minus,
    hcap_incr_plus,
    hcap_max_minus,
    hcap_max_plus,
    members,
    new_dates_for_hcap,
    old_hcaps,
    percentile_threshold,
    results_data,
    round_incr,
):
    # Making handicaps
    hcaps = {
        _event: {
            _gender: pd.DataFrame(
                {"handicap": 0},
                index=pd.Series(members["title"], name="member_title"),
            )
            for _gender in genders
        }
        for _event in events
    }
    # Updating handicaps with existing values
    for _event in events:
        for _gender in genders:
            hcaps[_event][_gender].update(
                pd.DataFrame(old_hcaps[_event][_gender]).set_index("member_title")
            )

    # Only consider specified "new" dates for handicap updates
    for _date in new_dates_for_hcap:
        for _event in events:
            for _gender in genders:
                hcaps_df = hcaps[_event][_gender]
                results_i = results_data[_date][_event][_gender]
                # Getting percentile threshold as # of people
                count_total = len(results_i)
                count_threshold = round(count_total * percentile_threshold)
                balance_index = count_total - count_threshold
                # Handicapping people above the count threshold
                hcap_delta_plus = np.minimum(
                    np.full(balance_index, hcap_max_plus),
                    np.arange(
                        hcap_incr_plus * (balance_index),
                        0,
                        -hcap_incr_plus,
                    ),
                )
                # Un-handicapping people below the count threshold
                hcap_delta_minus = np.maximum(
                    np.full(count_threshold, -hcap_max_minus),
                    np.arange(
                        0, -hcap_incr_minus * count_threshold, -hcap_incr_minus
                    ),
                )
                # This is the full list of handicap changes
                hcap_delta = np.concat([hcap_delta_plus, hcap_delta_minus])
                # Applying handicap changes
                for member_i, hcap_delta_i in zip(results_i, hcap_delta):
                    hcaps_df.loc[member_i["title"], "handicap"] += hcap_delta_i
                # Handicaps never go negative
                hcaps_df["handicap"] = hcaps_df["handicap"].clip(lower=0)
                # Printing for debugging
                # print(_date, _event, count_total, count_threshold, balance_index)
                # print(
                #     pd.DataFrame(
                #         {
                #             "member": [_i["title"] for _i in results_i],
                #             "hcap_delta": hcap_delta,
                #         }
                #     )
                # )

    # Post-processing
    for _event in events:
        for _gender in genders:
            # Get DF
            _hcaps_df = hcaps[_event][_gender]
            # Filter for only non-zero (positive) handicaps
            _hcaps_df.query("handicap > 0", inplace=True)
            # Sort by handicaps (ascending)
            _hcaps_df.sort_values("handicap", inplace=True)
            # Make a new column that rounds handicaps
            _hcaps_df["handicap_5s"] = (
                (_hcaps_df["handicap"] / round_incr).round() * round_incr
            ).astype(int)

    hcaps
    return (hcaps,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Export Handicaps

    JSON and CSV files
    """)
    return


@app.cell
def _(events, genders):
    def hcaps_dfs_to_json(
        hcaps: dict[str, dict[str, pd.DataFrame]], df_dst_dir: str
    ):
        hcaps_json = {
            _event: {_gender: {} for _gender in genders} for _event in events
        }
        # Save handicaps DFs as JSONs
        for _event in events:
            for _gender in genders:
                # Get DF
                _hcaps_df = hcaps[_event][_gender]
                # Exporting as CSV
                _hcaps_df.to_csv(
                    os.path.join(df_dst_dir, f"{_event}_{_gender}.csv")
                )
                # Storing JSON
                hcaps_json[_event][_gender] = json.loads(
                    _hcaps_df.reset_index().to_json(orient="records")
                )
        # Exporting as JSON
        write_json(hcaps_json, os.path.join(df_dst_dir, "hcaps.json"))

    return (hcaps_dfs_to_json,)


@app.cell
def _(hcaps, hcaps_dfs_to_json):
    # Saving to CSV and JSON files
    hcaps_dfs_to_json(hcaps, "hcaps")
    return


if __name__ == "__main__":
    app.run()
