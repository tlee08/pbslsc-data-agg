# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = [
#     "marimo>=0.23.6",
#     "polars==1.38.1",
# ]
# ///

import marimo

__generated_with = "0.24.2"
app = marimo.App(width="full")

with app.setup:
    import json

    import marimo as mo

    from data_wrangling.models import Results


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Make `results.json`
    """)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    Example of `meetings.json`:
    ```json
    {
        "genders": {
            "m": { "label": "Male" },
            "f": { "label": "Female" },
            "mixed": { "label": "Mixed" },
            "family": { "label": "Family" }
        },
        "events": {
            "swim": { "label": "Swim", "genders": ["m", "f"] },
            "board": { "label": "Board", "genders": ["m", "f"] },
            "ski": { "label": "Ski", "genders": ["m", "f"] },
            "run": { "label": "Run", "genders": ["m", "f"] },
            "flags": { "label": "Flags", "genders": ["m", "f"] },
            "cswim": { "label": "Swim", "genders": ["m", "f"] },
            "cboard_rescue": { "label": "Board - Rescue", "genders": ["m", "f"] },
            "cboard_mal": { "label": "Board - Mal", "genders": ["m", "f"] },
            "cski_surf": { "label": "Ski - Surf", "genders": ["m", "f"] },
            "cski_racing": { "label": "Ski - Racing", "genders": ["m", "f"] },
            "crun": { "label": "Run", "genders": ["m", "f"] },
            "cflags": { "label": "Flags", "genders": ["m", "f"] },
            "mswim": { "label": "Marathon Swim", "genders": ["m", "f"] },
            "mboard": { "label": "Marathon Board", "genders": ["m", "f"] },
            "mski": { "label": "Marathon Ski", "genders": ["m", "f"] },
            "mrun": { "label": "Marathon Run", "genders": ["m", "f"] },
            "jcc_individual": { "label": "JCC - Individual", "genders": ["m", "f"] },
            "jcc_team": {
            "label": "JCC - Team",
            "genders": ["m", "f", "mixed", "family"]
            },
            "imdl": { "label": "Iron Man - Diamond Lady", "genders": ["m", "f"] }
        },
        "series": {
            "whc": {
            "label": "WHC",
            "events": ["swim", "board", "ski", "run", "flags"]
            },
            "cchamps": {
            "label": "Club Champs",
            "events": [
                "cswim",
                "cboard_rescue",
                "cboard_mal",
                "cski_surf",
                "cski_racing",
                "crun",
                "cflags"
            ]
            },
            "mswim": {
            "label": "Marathon Swim",
            "events": ["mswim"]
            },
            "mboard": {
            "label": "Marathon Board",
            "events": ["mboard"]
            },
            "mski": {
            "label": "Marathon Ski",
            "events": ["mski"]
            },
            "mrun": {
            "label": "Marathon Run",
            "events": ["mrun"]
            },
            "jcc": {
            "label": "Jack Carter Cup",
            "events": ["jcc_individual", "jcc_team"]
            },
            "xmas": {
            "label": "Xmas",
            "events": ["swim", "board", "ski", "run", "flags"]
            },
            "imdl": {
            "label": "Iron Man - Diamond Lady",
            "events": ["imdl"]
            }
        }
    }
    ```

    Example of `lookups.json`:
    ```json
    [
        { "id": "260927_whc", "series": "whc" },
        { "id": "261004_whc", "series": "whc" },
        { "id": "261005_whc", "series": "whc" },
        { "id": "261011_whc", "series": "whc" },
        { "id": "261018_whc", "series": "whc" },
        { "id": "261025_cchamps", "series": "cchamps" },
        { "id": "261101_whc", "series": "whc" },
        { "id": "261108_whc", "series": "whc" },
        { "id": "261115_whc", "series": "whc" },
        { "id": "261122_mrun", "series": "mrun" },
        { "id": "261206_cchamps", "series": "cchamps" },
        { "id": "261213_whc", "series": "whc" },
        { "id": "261220_xmas", "series": "xmas" },
        { "id": "261226_xmas", "series": "xmas" },
        { "id": "261227_whc", "series": "whc" },
        { "id": "261228_whc", "series": "whc" },
        { "id": "270101_whc", "series": "whc" },
        { "id": "270103_mski", "series": "mski" },
        { "id": "270110_jcc", "series": "jcc" },
        { "id": "270117_whc", "series": "whc" },
        { "id": "270124_mboard", "series": "mboard" },
        { "id": "270126_whc", "series": "whc" },
        { "id": "270207_cchamps", "series": "cchamps" },
        { "id": "270214_whc", "series": "whc" },
        { "id": "270221_whc", "series": "whc" },
        { "id": "270228_whc", "series": "whc" },
        { "id": "270326_imdl", "series": "imdl" },
        { "id": "270314_whc", "series": "whc" },
        { "id": "270321_mswim", "series": "mswim" },
        { "id": "270326_whc", "series": "whc" },
        { "id": "270329_whc", "series": "whc" },
        { "id": "270404_whc", "series": "whc" },
        { "id": "270411_whc", "series": "whc" },
        { "id": "270418_whc", "series": "whc" },
        { "id": "270425_whc", "series": "whc" },
        { "id": "270426_whc", "series": "whc" }
    ]
    ```
    """)
    return


@app.cell
def _():
    meetings_file = mo.ui.file(
        label="Upload meetings JSON",
        filetypes=[".json"],
    )
    lookups_file = mo.ui.file(label="Upload lookups JSON", filetypes=[".json"])

    mo.vstack([meetings_file, lookups_file])
    return lookups_file, meetings_file


@app.cell
def _(lookups_file, meetings_file):

    mo.stop(
        not meetings_file.value or not lookups_file.value,
        mo.callout(
            mo.md("Upload a the meetings and lookups JSONs to continue."),
            kind="warn",
        ),
    )
    meetings_dict = json.loads(meetings_file.value[0].contents)
    lookups_dict = json.loads(lookups_file.value[0].contents)

    results_dict = {
        _i["id"]: {
            _event: {
                _gender: [] for _gender in lookups_dict["events"][_event]["genders"]
            }
            for _event in lookups_dict["series"][_i["series"]]["events"]
        }
        for _i in meetings_dict
    }

    _json_bytes = Results.dump_json(
        Results.validate_python(results_dict),
        indent=2,
    )
    mo.vstack(
        [
            mo.accordion({"Results": results_dict}),
            mo.download(
                data=_json_bytes,
                filename="results.json",
                label="Download results.json",
            ),
        ],
    )
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
