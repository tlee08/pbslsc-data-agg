import marimo

__generated_with = "0.20.2"
app = marimo.App(width="full")

with app.setup:
    import io
    import json

    import marimo as mo
    import numpy as np
    import pandas as pd


@app.cell
def _():
    mo.md("""
    # Update Handicaps

    1. Upload `eventStructure.json`, the previous handicaps JSON, and the latest results JSON.
    2. Select which dates are new this run.
    3. Preview the updated handicaps and download the new `hcaps.json`.
    """)
    return


@app.cell
def _():
    event_structure_file = mo.ui.file(label="Upload eventStructure.json", filetypes=[".json"])
    old_hcaps_file = mo.ui.file(label="Upload previous hcaps JSON", filetypes=[".json"])
    results_file = mo.ui.file(label="Upload results JSON", filetypes=[".json"])
    mo.vstack([event_structure_file, old_hcaps_file, results_file])
    return (event_structure_file, old_hcaps_file, results_file)


@app.cell
def _(event_structure_file, old_hcaps_file, results_file):
    mo.stop(
        not event_structure_file.value or not old_hcaps_file.value or not results_file.value,
        mo.callout(mo.md("Upload all three files to continue."), kind="warn"),
    )

    event_structure = json.loads(event_structure_file.value[0].contents)
    date_options = {d["label"]: d["value"] for d in event_structure["dates"]}

    new_dates_select = mo.ui.multiselect(
        options=date_options,
        label="Select new dates to process",
    )
    new_dates_select
    return (date_options, event_structure, new_dates_select, old_hcaps_file, results_file)


@app.cell
def _(new_dates_select, old_hcaps_file, results_file):
    mo.stop(
        not new_dates_select.value,
        mo.callout(mo.md("Select at least one new date to continue."), kind="warn"),
    )

    results_data = json.loads(results_file.value[0].contents)
    old_hcaps = json.loads(old_hcaps_file.value[0].contents)
    new_dates = new_dates_select.value

    events = ["swim", "board", "ski", "run"]
    genders = ["m", "f"]

    # Handicap tuning constants
    hcap_incr = 2
    hcap_max_plus = 20
    hcap_max_minus = 30
    percentile_threshold = 0.67
    round_incr = 5

    members = pd.read_json(io.StringIO(json.dumps(old_hcaps[events[0]][genders[0]])))["member_title"].tolist()

    # Build handicap DataFrames from previous values
    hcaps = {
        event: {
            gender: pd.DataFrame({"handicap": 0}, index=pd.Series(members, name="member_title"))
            for gender in genders
        }
        for event in events
    }
    for _event in events:
        for _gender in genders:
            hcaps[_event][_gender].update(
                pd.DataFrame(old_hcaps[_event][_gender]).set_index("member_title")
            )

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
                    if member_i["title"] in hcaps_df.index:
                        hcaps_df.loc[member_i["title"], "handicap"] += hcap_delta_i
                hcaps_df["handicap"] = hcaps_df["handicap"].clip(lower=0)

    # Post-process: filter zeros, sort, add rounded column
    for _event in events:
        for _gender in genders:
            _df = hcaps[_event][_gender]
            _df.query("handicap > 0", inplace=True)
            _df.sort_values("handicap", inplace=True)
            _df["handicap_5s"] = ((_df["handicap"] / round_incr).round() * round_incr).astype(int)

    # Build output JSON
    hcaps_json = {
        event: {
            gender: json.loads(hcaps[event][gender].reset_index().to_json(orient="records"))
            for gender in genders
        }
        for event in events
    }

    # Preview: combined summary of non-zero handicaps
    preview_rows = []
    for _event in events:
        for _gender in genders:
            for _, row in hcaps[_event][_gender].iterrows():
                preview_rows.append({
                    "event": _event,
                    "gender": _gender,
                    "member": row.name,
                    "handicap": row["handicap"],
                    "handicap_5s": row["handicap_5s"],
                })
    preview_df = pd.DataFrame(preview_rows)

    mo.vstack([
        preview_df,
        mo.download(
            data=json.dumps(hcaps_json, indent=2).encode(),
            filename="hcaps.json",
            label="Download hcaps.json",
        ),
    ])
    return


if __name__ == "__main__":
    app.run()
