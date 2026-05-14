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
    import copy
    import json

    import marimo as mo
    import numpy as np
    import pandas as pd

    from core.models import Members, Results

    # Events and genders constants
    events = ["swim", "board", "ski", "run"]
    genders = ["m", "f"]
    # Handicap tuning constants
    hcap_incr = 2
    hcap_max_plus = 20
    hcap_max_minus = 30
    percentile_threshold = 0.67
    round_incr = 5


@app.cell
def _():
    mo.md("""
    # Update Handicaps

    1. Upload the previous handicaps JSON and the latest results JSON.
    2. Select which dates are new this run.
    3. Preview the updated handicaps and download the new `hcaps.json`.
    """)
    return


@app.cell
def _():
    members_file = mo.ui.file(label="Upload members.json", filetypes=[".json"])
    old_hcaps_file = mo.ui.file(label="Upload previous hcaps JSON", filetypes=[".json"])
    results_file = mo.ui.file(label="Upload results JSON", filetypes=[".json"])
    return members_file, old_hcaps_file, results_file


@app.cell
def _(members_file, old_hcaps_file, results_file):
    mo.vstack(
        [
            mo.hstack(
                [
                    members_file,
                    members_file.value[0].name if members_file.value else "",
                ]
            ),
            mo.hstack(
                [
                    old_hcaps_file,
                    old_hcaps_file.value[0].name if old_hcaps_file.value else "",
                ]
            ),
            mo.hstack(
                [
                    results_file,
                    results_file.value[0].name if results_file.value else "",
                ]
            ),
        ]
    )
    return


@app.cell
def _(old_hcaps_file, results_file):
    mo.stop(
        not old_hcaps_file.value or not results_file.value,
        mo.callout(mo.md("Upload both files to continue."), kind="warn"),
    )

    results_data = Results.validate_json(results_file.value[0].contents)
    date_options = {k: k for k in results_data}

    new_dates_select = mo.ui.multiselect(
        options=date_options,
        label="Select new dates to process",
    )
    return new_dates_select, results_data


@app.cell
def _(new_dates_select):
    mo.hstack([new_dates_select, sorted(new_dates_select.value)])
    return


@app.function
def preview_hcaps(hcaps):
    # Preview: combined summary of non-zero handicaps
    preview_rows = []
    for _event in events:
        for _gender in genders:
            for _, row in hcaps[_event][_gender].iterrows():
                preview_rows.append(
                    {
                        "event": _event,
                        "gender": _gender,
                        "member": row.name,
                        "handicap": row["handicap"],
                        "handicap_5s": row["handicap_5s"],
                    }
                )
    preview_df = pd.DataFrame(preview_rows)
    return preview_df


@app.function
def postprocess_hcaps(hcaps):
    hcaps = copy.deepcopy(hcaps)
    # Post-process: filter zeros, sort, add rounded column
    for _event in events:
        for _gender in genders:
            _df = hcaps[_event][_gender]
            _df.query("handicap > 0", inplace=True)
            _df.sort_values("handicap", inplace=True)
            _df["handicap_5s"] = (
                (_df["handicap"] / round_incr).round() * round_incr
            ).astype(int)
    return hcaps


@app.function
def construct_hcap_csv_download_btn(hcaps, event, gender):
    return mo.download(
        data=hcaps[event][gender].to_csv().encode(),
        filename=f"{event}_{gender}.csv",
        label=f"Download {event}_{gender}.csv",
    )


@app.cell
def _(members_file, new_dates_select, old_hcaps_file, results_data):
    mo.stop(
        not new_dates_select.value,
        mo.callout(mo.md("Select at least one new date to continue."), kind="warn"),
    )

    old_hcaps = json.loads(old_hcaps_file.value[0].contents)
    members = Members.validate_json(members_file.value[0].contents)
    new_dates = new_dates_select.value

    # Build handicap DataFrames from previous values
    hcaps = {
        _event: {
            _gender: pd.DataFrame(members)
            .set_index("title")
            .query(f"gender == '{_gender}'")
            .merge(
                right=pd.DataFrame(old_hcaps[_event][_gender]).set_index("member_title")
                if "member_title" in pd.DataFrame(old_hcaps[_event][_gender])
                else pd.DataFrame(columns=["handicap", "handicap_5s"]),
                how="left",
                left_index=True,
                right_index=True,
            )
            for _gender in genders
        }
        for _event in events
    }
    for _event in events:
        for _gender in genders:
            hcaps[_event][_gender].update(
                pd.DataFrame(old_hcaps[_event][_gender]).set_index("member_title")
                if "member_title" in pd.DataFrame(old_hcaps[_event][_gender])
                else None
            )

    # Saving previous handicaps to compare against new
    hcaps_prev = copy.deepcopy(hcaps)
    # Post-process: filter zeros, sort, add rounded column
    hcaps_prev = postprocess_hcaps(hcaps_prev)

    # Apply handicap updates for each new date
    for _date in new_dates:
        for _event in events:
            for _gender in genders:
                if _date not in results_data or _event not in results_data[_date]:
                    continue
                hcaps_df = hcaps[_event][_gender]
                results_i = results_data[_date][_event][_gender]
                count_total = len(results_i)
                count_threshold = round(count_total * percentile_threshold)
                balance_index = count_total - count_threshold
                hcap_delta_plus = np.minimum(
                    np.full(balance_index, hcap_max_plus),
                    np.arange(hcap_incr * balance_index, 0, -hcap_incr),
                )
                hcap_delta_minus = np.maximum(
                    np.full(count_threshold, -hcap_max_minus),
                    np.arange(0, -hcap_incr * count_threshold, -hcap_incr),
                )
                hcap_delta = np.concat([hcap_delta_plus, hcap_delta_minus])
                for member_i, hcap_delta_i in zip(results_i, hcap_delta):
                    if member_i.title in hcaps_df.index:
                        hcaps_df.loc[member_i.title, "handicap"] += hcap_delta_i
                hcaps_df["handicap"] = hcaps_df["handicap"].clip(lower=0)

    # Post-process: filter zeros, sort, add rounded column
    hcaps = postprocess_hcaps(hcaps)

    # Build output JSON
    hcaps_json = {
        event: {
            gender: json.loads(
                hcaps[event][gender].reset_index().to_json(orient="records")
            )
            for gender in genders
        }
        for event in events
    }

    # Output
    mo.vstack(
        [
            # Old handicaps
            mo.md("### Old Handicaps"),
            preview_hcaps(hcaps_prev),
            # New handicaps
            mo.md("### New Handicaps"),
            preview_hcaps(hcaps),
            # Download
            mo.download(
                data=json.dumps(hcaps_json, indent=2).encode(),
                filename="hcaps.json",
                label="Download hcaps.json",
            ),
            *[
                mo.hstack(
                    [
                        construct_hcap_csv_download_btn(hcaps, _event, _gender)
                        for _event in events
                    ]
                )
                for _gender in genders
            ],
        ]
    )
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
