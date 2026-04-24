import marimo

__generated_with = "0.20.2"
app = marimo.App(width="full")

with app.setup:
    import io
    import json
    import re

    import marimo as mo
    import pandas as pd


@app.cell
def _():
    mo.md("""
    # Check Results Validity

    Upload a results JSON and the members JSON. All checks run automatically.
    """)
    return


@app.cell
def _():
    results_file = mo.ui.file(label="Upload results JSON", filetypes=[".json"])
    members_file = mo.ui.file(label="Upload members.json", filetypes=[".json"])
    mo.vstack([results_file, members_file])
    return (members_file, results_file)


@app.cell
def _(members_file, results_file):
    mo.stop(
        not results_file.value or not members_file.value,
        mo.callout(mo.md("Upload both files to continue."), kind="warn"),
    )

    data = json.loads(results_file.value[0].contents)
    members = json.loads(members_file.value[0].contents)
    members_by_title = {m["title"]: m for m in members}
    members_by_id = {m["id"]: m for m in members}

    lines = []

    # Check member existence and ID/title consistency
    lines.append("=== Member existence ===")
    existence_ok = True
    for date, date_data in data.items():
        for event, event_data in date_data.items():
            for gender, gender_data in event_data.items():
                for entry in gender_data:
                    title, mid = entry["title"], entry["id"]
                    title_ok = title in members_by_title
                    id_ok = mid in members_by_id
                    id_match = re.search(r".* - (.*)$", title)
                    id_eq = id_match and id_match[1] == mid
                    if not (title_ok and id_ok and id_eq):
                        lines.append(f"  FAIL {date} / {event} / {gender}: {title!r} id={mid!r}")
                        existence_ok = False
    if existence_ok:
        lines.append("  All OK")

    # Check gender correctness
    lines.append("\n=== Gender correctness ===")
    gender_ok = True
    for date, date_data in data.items():
        for event, event_data in date_data.items():
            for gender, gender_data in event_data.items():
                for entry in gender_data:
                    member = members_by_title.get(entry["title"])
                    if member and member["gender"] != gender:
                        lines.append(f"  FAIL {date} / {event}: {entry['title']!r} listed under {gender!r} but is {member['gender']!r}")
                        gender_ok = False
    if gender_ok:
        lines.append("  All OK")

    # Check duplicates
    lines.append("\n=== Duplicates ===")
    dupl_ok = True
    for date, date_data in data.items():
        for event, event_data in date_data.items():
            for gender, gender_data in event_data.items():
                ids = [e["id"] for e in gender_data]
                seen = {}
                for mid in ids:
                    seen[mid] = seen.get(mid, 0) + 1
                for mid, count in seen.items():
                    if count > 1:
                        lines.append(f"  FAIL {date} / {event} / {gender}: id={mid!r} appears {count}x")
                        dupl_ok = False
    if dupl_ok:
        lines.append("  All OK")

    if existence_ok and gender_ok and dupl_ok:
        lines.insert(0, "All checks passed.\n")

    mo.plain_text("\n".join(lines))
    return


if __name__ == "__main__":
    app.run()
