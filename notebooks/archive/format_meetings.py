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
    from pathlib import Path

    import marimo as mo
    import polars as pl
    import io

    from data_wrangling.models import Members, Results


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Make empty `meetings.json`
    """)
    return


@app.cell
def _():
    meetings_dict = json.loads(
        (Path.cwd().parent / "data" / "2026_27" / "meetings.json").read_text(),
    )
    lookups_dict = json.loads(
        (Path.cwd().parent / "data" / "2026_27" / "lookups.json").read_text(),
    )

    results_dict = {
        _i["id"]: {
            _event: {
                _gender: []
                for _gender in lookups_dict["events"][_event]["genders"]
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
