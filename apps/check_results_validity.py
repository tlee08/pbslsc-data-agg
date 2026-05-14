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
    import re

    import marimo as mo

    from core.models import Members, Results


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

    results = Results.validate_json(results_file.value[0].contents)
    members = Members.validate_json(members_file.value[0].contents)
    members_by_title = {m.title: m for m in members}
    members_by_id = {m.id: m for m in members}

    lines = []
    # Check member existence and ID/title consistency
    lines.append("=== Member existence ===")
    existence_ok = True
    for _date, _date_data in results.items():
        for _event, _event_data in _date_data.items():
            for _gender, _gender_data in _event_data.items():
                for entry in _gender_data:
                    title, mid = entry.title, entry.id
                    # Check member title exists
                    title_ok = title in members_by_title
                    # Check member ID exists
                    id_ok = mid in members_by_id
                    # Check member ID matches title
                    id_match = re.search(r".* - (.*)$", title)
                    id_eq = id_match and id_match[1] == mid
                    if not (title_ok and id_ok and id_eq):
                        lines.append(
                            f"  FAIL {_date} / {_event} / {_gender}: {title!r} id={mid!r}"
                        )
                        existence_ok = False
    if existence_ok:
        lines.append("  All OK")

    # Check gender correctness
    lines.append("\n=== Gender correctness ===")
    gender_ok = True
    for _date, _date_data in results.items():
        for _event, _event_data in _date_data.items():
            for _gender, _gender_data in _event_data.items():
                for entry in _gender_data:
                    member = members_by_title.get(entry.title)
                    if member and member.gender != _gender:
                        lines.append(
                            f"  FAIL {_date} / {_event}: {entry.title!r} listed "
                            f"under {_gender!r} but is {member.gender!r}"
                        )
                        gender_ok = False
    if gender_ok:
        lines.append("  All OK")

    # Check duplicates
    lines.append("\n=== Duplicates ===")
    dupl_ok = True
    for _date, _date_data in results.items():
        for _event, _event_data in _date_data.items():
            for _gender, _gender_data in _event_data.items():
                seen = {}
                for entry in _gender_data:
                    mid = entry.id
                    seen[mid] = seen.get(mid, 0) + 1
                for mid, count in seen.items():
                    if count > 1:
                        lines.append(
                            f"  FAIL {_date} / {_event} / {_gender}: "
                            f"id={mid!r} appears {count}x"
                        )
                        dupl_ok = False
    if dupl_ok:
        lines.append("  All OK")

    if existence_ok and gender_ok and dupl_ok:
        lines.insert(0, "All checks passed.\n")

    mo.plain_text("\n".join(lines))
    return


if __name__ == "__main__":
    app.run()
