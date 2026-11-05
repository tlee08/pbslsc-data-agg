# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = [
#     "marimo>=0.23.6",
#     "polars==1.38.1",
#     "python-docx>=1.1.2",
# ]
# ///

import marimo

__generated_with = "0.24.2"
app = marimo.App(width="full")

with app.setup:
    import marimo as mo

    from data_wrangling.frames import handicaps_to_frame
    from data_wrangling.handicap_docx import build_handicap_docx
    from data_wrangling.models import handicaps_adapter


@app.cell
def _():
    mo.md("""
    # Format handicaps to .docx

    Upload a handicaps JSON and get a printable Word document — one
    bordered table per event and gender, each on its own page.
    """)
    return


@app.cell
def _():
    handicaps_file = mo.ui.file(
        label="Upload handicaps JSON",
        filetypes=[".json"],
    )
    handicaps_file
    return (handicaps_file,)


@app.cell
def _(handicaps_file):
    mo.stop(
        not handicaps_file.value,
        mo.callout(mo.md("Upload a handicaps JSON to continue."), kind="warn"),
    )

    handicaps = handicaps_adapter.validate_json(
        handicaps_file.value[0].contents,
    )

    docx_bytes = build_handicap_docx(handicaps)

    preview = handicaps_to_frame(handicaps)

    mo.vstack(
        [
            mo.md(
                f"**{preview.height}** handicaps across "
                f"**{sum(1 for e in handicaps for g in handicaps[e] if handicaps[e][g])}** "
                f"event/gender tables.",
            ),
            mo.download(
                data=docx_bytes,
                filename="handicaps.docx",
                label="Download handicaps.docx",
            ),
            mo.accordion(
                {
                    "Preview": preview,
                },
                multiple=True,
            ),
        ],
    )
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
