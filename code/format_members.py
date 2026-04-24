import marimo

__generated_with = "0.20.2"
app = marimo.App(width="full")

with app.setup:
    import json
    import os

    import marimo as mo
    import pandas as pd


@app.cell
def _():
    mo.md(r"""
    # Data Processing
    """)
    return


@app.cell
def _():
    mo.md(r"""
    ## Member df
    """)
    return


@app.cell
def _():
    # Read
    df = pd.read_csv("members/members_25.csv")

    # Wrangling
    df["first_name"] = df["name"].str.split(", ").str[1]
    df["last_name"] = df["name"].str.split(", ").str[0]
    df["gender"] = df["gender"].map({"Male": "m", "Female": "f"})
    df["title"] = df.apply(
        lambda x: f"{x['first_name']} {x['last_name'].upper()} - {x['id']}",
        axis=1,
    )
    df = df.sort_values(by="title", axis=0)

    # Show
    df
    return (df,)


@app.cell
def _(df):
    df.to_json("members/members.json", orient="records")

    mo.accordion({"data as JSON": json.loads(df.to_json(orient="records"))})
    return


@app.cell
def _():
    mo.md(r"""
    ## Checking new members list

    ### Does it have duplicates?
    """)
    return


@app.cell
def _():
    def _():
        df = pd.read_csv(os.path.join("members", "members_25.csv"))
        dupls_df = df["id"].value_counts()
        dupls_df = dupls_df[dupls_df > 1]
        filt_df = df[df["id"].isin(dupls_df.index)]
        return filt_df


    _()
    return


@app.cell
def _():
    mo.md(r"""
    ## Fresher BBB names
    """)
    return


@app.cell
def _(df):
    bbb_attendance_df = pd.read_csv("~/Downloads/bbb_1.csv")
    bbb_attendance_df["Name_formatted"] = bbb_attendance_df["Name"].apply(
        lambda x: f"{x.split(' ')[1]}, {x.split(' ')[0]}"
    )

    pd.merge(
        left=bbb_attendance_df,
        right=df,
        left_on="Name_formatted",
        right_on="name",
        how="left",
    )[["name", "id", "title"]]
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
