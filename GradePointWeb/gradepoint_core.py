"""Shared grade / GPA logic for GradePoint CLI and web app."""

GRADE_POINTS = {
    "A": 4.0,
    "A-": 3.7,
    "B+": 3.3,
    "B": 3.0,
    "B-": 2.7,
    "C+": 2.3,
    "C": 2.0,
    "C-": 1.7,
    "D+": 1.3,
    "D": 1.0,
    "D-": 0.7,
    "F": 0.0,
}


def letter_minimum_percent(letter):
    letter = letter.strip().upper()
    cutoffs = {
        "A": 93,
        "A-": 90,
        "B+": 87,
        "B": 83,
        "B-": 80,
        "C+": 77,
        "C": 73,
        "C-": 70,
        "D+": 67,
        "D": 63,
        "D-": 60,
        "F": 0,
    }
    return cutoffs.get(letter)


def percent_to_letter(percent):
    if percent >= 93:
        return "A"
    if percent >= 90:
        return "A-"
    if percent >= 87:
        return "B+"
    if percent >= 83:
        return "B"
    if percent >= 80:
        return "B-"
    if percent >= 77:
        return "C+"
    if percent >= 73:
        return "C"
    if percent >= 70:
        return "C-"
    if percent >= 67:
        return "D+"
    if percent >= 63:
        return "D"
    if percent >= 60:
        return "D-"
    return "F"


def grade_from_letter_or_percent(letter, percent):
    """
    letter: str or None (from form)
    percent: float or None
    Returns (letter_grade, error_message). error_message is None if ok.
    """
    if letter and str(letter).strip():
        g = str(letter).strip().upper()
        if g in GRADE_POINTS:
            return g, None
        return None, "Invalid letter grade."
    if percent is not None:
        try:
            p = float(percent)
        except (TypeError, ValueError):
            return None, "Invalid percentage."
        if not 0 <= p <= 100:
            return None, "Percentage must be 0–100."
        return percent_to_letter(p), None
    return None, "Enter a letter grade or a percentage."


def calculate_term_gpa(classes):
    total_units = 0.0
    total_quality_points = 0.0

    for c in classes:
        units = float(c["units"])
        grade = c["grade"]
        points = GRADE_POINTS[grade]
        total_units += units
        total_quality_points += points * units

    if total_units == 0:
        return 0.0, total_units, total_quality_points

    return total_quality_points / total_units, total_units, total_quality_points


def compute_final_needed(current_avg, w_done, w_left, target):
    if not 0 <= current_avg <= 100:
        return {"ok": False, "error": "Average should be between 0 and 100."}
    if w_done <= 0 or w_left <= 0:
        return {"ok": False, "error": "Both weights must be greater than 0."}
    if not 0 <= target <= 100:
        return {"ok": False, "error": "Target should be between 0 and 100."}

    w_sum = w_done + w_left
    if w_sum <= 0:
        return {"ok": False, "error": "Weights must add to something positive."}

    f_done = w_done / w_sum
    f_left = w_left / w_sum
    needed = (target - current_avg * f_done) / f_left

    notes = []
    if needed > 100:
        notes.append("That is above 100% — this target is not reachable with these weights.")
    elif needed < 0:
        notes.append(
            "You can score below 0% on that part and still be at or above the target (in this model)."
        )
    else:
        notes.append(
            f"Rough letter on our scale if that were the whole course: {percent_to_letter(needed)}"
        )

    return {
        "ok": True,
        "needed": needed,
        "w_done": w_done,
        "w_left": w_left,
        "current_avg": current_avg,
        "notes": notes,
    }


def compute_required_term_gpa(prior_units, prior_gpa, term_units, target):
    if prior_units < 0:
        return {"ok": False, "error": "Units cannot be negative."}
    if term_units <= 0:
        return {"ok": False, "error": "This term's units must be greater than 0."}

    total_units = prior_units + term_units
    if total_units <= 0:
        return {"ok": False, "error": "Need positive total units."}

    prior_qp = prior_gpa * prior_units
    required = (target * total_units - prior_qp) / term_units

    notes = []
    if required > 4.0:
        notes.append("That is above a 4.0 scale — not achievable with straight As.")
    elif required < 0:
        notes.append("Your prior GPA already meets or exceeds that cumulative target this term.")
    else:
        notes.append("This is what you need on average across all classes this term (by credit).")

    return {"ok": True, "required_term_gpa": required, "notes": notes}


def compute_projected_cumulative(classes, prior_units, prior_gpa):
    if len(classes) == 0:
        return {"ok": False, "error": "Add at least one class first."}
    if prior_units < 0:
        return {"ok": False, "error": "Units cannot be negative."}

    term_gpa, term_units, term_qp = calculate_term_gpa(classes)
    if term_units <= 0:
        return {"ok": False, "error": "Term has no units."}

    prior_qp = prior_gpa * prior_units
    all_units = prior_units + term_units
    all_qp = prior_qp + term_qp

    if all_units <= 0:
        return {"ok": False, "error": "Total units must be positive."}

    cumulative = all_qp / all_units
    return {
        "ok": True,
        "term_gpa": term_gpa,
        "term_units": term_units,
        "cumulative": cumulative,
        "all_units": all_units,
    }


def compute_what_if(classes, index, new_grade_letter):
    if not (0 <= index < len(classes)):
        return {"ok": False, "error": "Invalid class index."}
    if new_grade_letter not in GRADE_POINTS:
        return {"ok": False, "error": "Invalid letter grade."}

    modified = []
    for i, cl in enumerate(classes):
        if i == index:
            modified.append({**cl, "grade": new_grade_letter})
        else:
            modified.append(dict(cl))

    old_gpa, _, _ = calculate_term_gpa(classes)
    new_gpa, _, _ = calculate_term_gpa(modified)
    return {"ok": True, "old_gpa": old_gpa, "new_gpa": new_gpa}


def compute_cumulative_from_quality_points(old_units, old_quality_points, classes):
    term_gpa, term_units, term_qp = calculate_term_gpa(classes)
    all_units = old_units + term_units
    all_qp = old_quality_points + term_qp
    if all_units <= 0:
        return {"ok": False, "error": "Total units must be positive."}
    return {
        "ok": True,
        "term_gpa": term_gpa,
        "term_units": term_units,
        "cumulative": all_qp / all_units,
        "all_units": all_units,
    }
