"""
GradePoint web app — local:
  pip install -r requirements.txt
  python app.py
  → http://127.0.0.1:5000

Production: gunicorn -c gunicorn.conf.py wsgi:app
"""

import os

from flask import Flask, flash, redirect, render_template, request, session, url_for

from gradepoint_core import (
    GRADE_POINTS,
    calculate_term_gpa,
    compute_cumulative_from_quality_points,
    compute_final_needed,
    compute_projected_cumulative,
    compute_required_term_gpa,
    compute_what_if,
    grade_from_letter_or_percent,
    letter_minimum_percent,
)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-key-change-for-production")

GRADE_ORDER = [
    "A",
    "A-",
    "B+",
    "B",
    "B-",
    "C+",
    "C",
    "C-",
    "D+",
    "D",
    "D-",
    "F",
]


def _classes():
    c = session.get("classes")
    if c is None:
        c = []
        session["classes"] = c
    return c


def _parse_grade(form, prefix=""):
    letter_key = f"{prefix}grade_letter"
    pct_key = f"{prefix}grade_percent"
    letter = (form.get(letter_key) or "").strip()
    pct_raw = (form.get(pct_key) or "").strip()
    percent = float(pct_raw) if pct_raw not in ("", None) else None
    if letter == "":
        letter = None
    return grade_from_letter_or_percent(letter, percent)


def _float(form, key, default=None):
    raw = (form.get(key) or "").strip()
    if raw == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return None


@app.route("/")
def index():
    classes = _classes()
    term_gpa, term_units, _ = calculate_term_gpa(classes)
    scenario_display = session.pop("scenario_display", None)
    return render_template(
        "index.html",
        classes=classes,
        grade_order=GRADE_ORDER,
        term_gpa=term_gpa,
        term_units=term_units,
        scenario_display=scenario_display,
    )


@app.post("/add")
def add_class():
    name = (request.form.get("name") or "").strip() or "Untitled Class"
    units = _float(request.form, "units")
    if units is None or units <= 0:
        flash("Units must be a number greater than 0.", "error")
        return redirect(url_for("index"))

    grade, err = _parse_grade(request.form)
    if err:
        flash(err, "error")
        return redirect(url_for("index"))

    classes = _classes()
    classes.append({"name": name, "units": units, "grade": grade})
    session["classes"] = classes
    session.modified = True
    flash("Class added.", "ok")
    return redirect(url_for("index"))


@app.post("/class/<int:i>/delete")
def delete_class(i):
    classes = _classes()
    if 0 <= i < len(classes):
        classes.pop(i)
        session["classes"] = classes
        session.modified = True
        flash("Class removed.", "ok")
    else:
        flash("Invalid class.", "error")
    return redirect(url_for("index"))


@app.post("/class/<int:i>/update")
def update_class(i):
    classes = _classes()
    if not (0 <= i < len(classes)):
        flash("Invalid class.", "error")
        return redirect(url_for("index"))

    name = (request.form.get("name") or "").strip()
    if name:
        classes[i]["name"] = name

    units = _float(request.form, "units")
    if units is not None:
        if units <= 0:
            flash("Units must be greater than 0.", "error")
            return redirect(url_for("index"))
        classes[i]["units"] = units

    letter = (request.form.get("grade_letter") or "").strip()
    pct_raw = (request.form.get("grade_percent") or "").strip()
    if letter or pct_raw:
        grade, err = _parse_grade(request.form)
        if err:
            flash(err, "error")
            return redirect(url_for("index"))
        classes[i]["grade"] = grade

    session["classes"] = classes
    session.modified = True
    flash("Class updated.", "ok")
    return redirect(url_for("index"))


@app.post("/cumulative")
def cumulative():
    classes = _classes()
    old_units = _float(request.form, "old_units")
    old_qp = _float(request.form, "old_quality_points")
    if old_units is None or old_qp is None:
        flash("Enter previous units and quality points.", "error")
        return redirect(url_for("index"))
    result = compute_cumulative_from_quality_points(old_units, old_qp, classes)
    if result["ok"]:
        session["scenario_display"] = {
            "title": "Cumulative GPA",
            "lines": [
                f"This term: {result['term_gpa']:.2f} GPA ({result['term_units']:.1f} units)",
                f"Cumulative GPA: {result['cumulative']:.2f} ({result['all_units']:.1f} total units)",
            ],
        }
    else:
        flash(result["error"], "error")
    return redirect(url_for("index"))


@app.post("/scenario/final")
def scenario_final():
    current = _float(request.form, "current_avg")
    w_done = _float(request.form, "w_done")
    w_left = _float(request.form, "w_left")
    target = _float(request.form, "target_pct")
    if None in (current, w_done, w_left, target):
        flash("Fill in all fields with numbers.", "error")
        return redirect(url_for("index"))

    result = compute_final_needed(current, w_done, w_left, target)
    if not result["ok"]:
        flash(result["error"], "error")
        return redirect(url_for("index"))

    lines = [
        f"You need {result['needed']:.1f}% on the remaining ({result['w_left']:g}-weighted) part.",
        f"(So far: {result['w_done']:g} at {result['current_avg']:.1f}%.)",
        *result["notes"],
    ]
    session["scenario_display"] = {"title": "Score needed on final", "lines": lines}
    return redirect(url_for("index"))


@app.post("/scenario/term-target")
def scenario_term_target():
    prior_u = _float(request.form, "prior_units")
    prior_gpa = _float(request.form, "prior_gpa")
    term_u = _float(request.form, "term_units")
    target = _float(request.form, "target_cumulative")
    if None in (prior_u, prior_gpa, term_u, target):
        flash("Fill in all fields.", "error")
        return redirect(url_for("index"))

    result = compute_required_term_gpa(prior_u, prior_gpa, term_u, target)
    if not result["ok"]:
        flash(result["error"], "error")
        return redirect(url_for("index"))

    lines = [f"Required term GPA: {result['required_term_gpa']:.2f}", *result["notes"]]
    session["scenario_display"] = {"title": "Term GPA for cumulative target", "lines": lines}
    return redirect(url_for("index"))


@app.post("/scenario/projected")
def scenario_projected():
    classes = _classes()
    prior_u = _float(request.form, "proj_prior_units")
    prior_gpa = _float(request.form, "proj_prior_gpa")
    if prior_u is None or prior_gpa is None:
        flash("Enter prior units and prior cumulative GPA.", "error")
        return redirect(url_for("index"))

    result = compute_projected_cumulative(classes, prior_u, prior_gpa)
    if not result["ok"]:
        flash(result["error"], "error")
        return redirect(url_for("index"))

    lines = [
        f"This term: {result['term_gpa']:.2f} GPA over {result['term_units']:.1f} units",
        f"Projected cumulative: {result['cumulative']:.2f} ({result['all_units']:.1f} total units)",
    ]
    session["scenario_display"] = {"title": "Projected cumulative", "lines": lines}
    return redirect(url_for("index"))


@app.post("/scenario/whatif")
def scenario_whatif():
    classes = _classes()
    idx = _float(request.form, "whatif_index")
    if idx is None:
        flash("Choose a class number.", "error")
        return redirect(url_for("index"))
    idx = int(idx) - 1
    letter = (request.form.get("whatif_letter") or "").strip().upper()
    if not letter:
        flash("Choose a letter grade for the what-if.", "error")
        return redirect(url_for("index"))

    result = compute_what_if(classes, idx, letter)
    if not result["ok"]:
        flash(result["error"], "error")
        return redirect(url_for("index"))

    lines = [
        f"Term GPA would go from {result['old_gpa']:.2f} to {result['new_gpa']:.2f}.",
    ]
    session["scenario_display"] = {"title": "What-if grade", "lines": lines}
    return redirect(url_for("index"))


@app.post("/scenario/min-pct")
def scenario_min_pct():
    letter = (request.form.get("min_letter") or "").strip().upper()
    if letter not in GRADE_POINTS:
        flash("Pick a valid letter grade.", "error")
        return redirect(url_for("index"))

    low = letter_minimum_percent(letter)
    if letter == "F":
        lines = ["F: below 60% on this scale (under D-)."]
    else:
        lines = [f"{letter}: at least {low}% in the class (this app’s scale)."]
    session["scenario_display"] = {"title": "Minimum % for letter", "lines": lines}
    return redirect(url_for("index"))


@app.post("/reset")
def reset():
    session["classes"] = []
    session.modified = True
    flash("All classes cleared.", "ok")
    return redirect(url_for("index"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(debug=True, host="0.0.0.0", port=port)
