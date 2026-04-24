import marimo

__generated_with = "0.20.2"
app = marimo.App(width="full")

with app.setup:
    import io
    import json

    import marimo as mo
    import pandas as pd


@app.cell
def _():
    mo.md("""
    # Format Members

    Upload the raw members CSV export. A preview will appear and you can download the formatted `members.json`.
    """)
    return


@app.cell
def _():
    members_file = mo.ui.file(label="Upload members CSV", filetypes=[".csv"])
    members_file
    return (members_file,)


@app.cell
def _(members_file):
    mo.stop(
        not members_file.value,
        mo.callout(mo.md("Upload a members CSV to continue."), kind="warn"),
    )

    raw = io.StringIO(members_file.value[0].contents.decode())
    df = pd.read_csv(raw)
    df["first_name"] = df["name"].str.split(", ").str[1]
    df["last_name"] = df["name"].str.split(", ").str[0]
    df["gender"] = df["gender"].map({"Male": "m", "Female": "f"})
    df["title"] = df.apply(
        lambda x: f"{x['first_name']} {x['last_name'].upper()} - {x['id']}",
        axis=1,
    )
    df = df.sort_values(by="title").reset_index(drop=True)

    json_bytes = json.dumps(json.loads(df.to_json(orient="records")), indent=2).encode()
    mo.vstack(
        [
            df,
            mo.download(
                data=json_bytes, filename="members.json", label="Download members.json"
            ),
        ]
    )
    return


if __name__ == "__main__":
    app.run()
