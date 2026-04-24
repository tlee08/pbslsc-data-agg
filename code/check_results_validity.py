import marimo

__generated_with = "0.20.2"
app = marimo.App(width="full")

with app.setup:
    import json
    import os
    import re

    import marimo as mo
    import pandas as pd


@app.cell
def _():
    with open(os.path.join("results", "whc_results_260329.json")) as _f:
        data = json.load(_f)
    return (data,)


@app.cell
def _():
    with open(os.path.join("members", "members.json")) as _f:
        members = json.load(_f)

    members_title_dict = {_i["title"]: _i for _i in members}
    members_id_dict = {_i["id"]: _i for _i in members}
    return members, members_id_dict, members_title_dict


@app.cell
def _():
    mo.md(r"""
    ## Checking member duplicates inside members list
    """)
    return


@app.cell
def _(members):
    def _():
        member_df = pd.DataFrame(members).sort_values("id")
        member_dupls_df = member_df["id"].value_counts()
        member_dupls_df = member_dupls_df[member_dupls_df > 1]
        member_filt_df = member_df[member_df["id"].isin(member_dupls_df.index)]
        return member_filt_df

    _()
    return


@app.cell
def _():
    mo.md(r"""
    ## Checking member exists
    """)
    return


@app.cell
def _(data, members_id_dict, members_title_dict):
    def _():
        for date_name, date_data in data.items():
            for event_name, event_data in date_data.items():
                for gender_name, gender_data in event_data.items():
                    id_df = pd.DataFrame(
                        {
                            "id": [_i["id"] for _i in gender_data],
                            "title": [_i["title"] for _i in gender_data],
                        }
                    )
                    id_df["title_exists"] = id_df["title"].apply(
                        lambda x: x in members_title_dict
                    )
                    id_df["id_exists"] = id_df["id"].apply(
                        lambda x: x in members_id_dict
                    )
                    id_df["title_id"] = id_df["title"].apply(
                        lambda x: re.search(".* - (.*)$", x)[1]
                    )
                    id_df["id_equals"] = id_df["title_id"] == id_df["id"]
                    id_df["exists"] = (
                        id_df["title_exists"] & id_df["id_exists"] & id_df["id_equals"]
                    )
                    if not id_df["exists"].all():
                        print(date_name, event_name, gender_name)
                        print(id_df[~id_df["exists"]])
                        print()

    _()
    return


@app.cell
def _():
    mo.md(r"""
    ## Checking genders
    """)
    return


@app.cell
def _(data, members_title_dict):
    def _():
        for date_name, date_data in data.items():
            for event_name, event_data in date_data.items():
                for gender_name, gender_data in event_data.items():
                    id_df = pd.DataFrame(
                        {
                            "id": [_i["id"] for _i in gender_data],
                            "title": [_i["title"] for _i in gender_data],
                        }
                    )
                    id_df["gender"] = id_df["title"].apply(
                        lambda x: members_title_dict[x]["gender"]
                    )
                    if not (id_df["gender"] == gender_name).all():
                        print(date_name, event_name, gender_name)
                        print(id_df[id_df["gender"] != gender_name])
                        print()

    _()
    return


@app.cell
def _():
    mo.md(r"""
    ## Checking duplicates
    """)
    return


@app.cell
def _(data):
    def _():
        for date_name, date_data in data.items():
            for event_name, event_data in date_data.items():
                for gender_name, gender_data in event_data.items():
                    id_ls = [_i["id"] for _i in gender_data]
                    id_vect = pd.Series(id_ls)
                    id_vect_count = id_vect.value_counts()
                    id_vect_count_dupls = id_vect_count[id_vect_count > 1]
                    if len(id_vect_count_dupls) > 0:
                        print(date_name, event_name, gender_name)
                        print(id_vect_count_dupls)
                        print()

    _()
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
