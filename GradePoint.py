import sys
from pathlib import Path

# Core lives with the web app so one folder can deploy; CLI adds that path.
sys.path.insert(0, str(Path(__file__).resolve().parent / "GradePointWeb"))

from gradepoint_core import (
    GRADE_POINTS,
    calculate_term_gpa,
    compute_cumulative_from_quality_points,
    compute_final_needed,
    compute_projected_cumulative,
    compute_required_term_gpa,
    compute_what_if,
    letter_minimum_percent,
    percent_to_letter,
)


def get_number(prompt, must_be_positive=False):
    """Ask for a number until input is valid."""
    while True:
        text = input(prompt).strip()
        try:
            number = float(text)
            if must_be_positive and number <= 0:
                print("Please enter a number greater than 0.")
                continue
            return number
        except ValueError:
            print("Please enter a valid number.")


def yes_or_no(prompt):
    """Return True for yes, False for no."""
    while True:
        answer = input(prompt).strip().lower()
        if answer in ["y", "yes"]:
            return True
        if answer in ["n", "no"]:
            return False
        print("Please type y or n.")


def choose_grade():
    """Let user enter letter or percentage, then return letter grade."""
    while True:
        mode = input("Enter grade as [L]etter or [P]ercentage: ").strip().upper()

        if mode == "L":
            letter = input("Letter grade (A, A-, B+, ... F): ").strip().upper()
            if letter in GRADE_POINTS:
                return letter
            print("That letter grade is not valid.")

        elif mode == "P":
            percent = get_number("Percentage (0 to 100): ")
            if 0 <= percent <= 100:
                letter = percent_to_letter(percent)
                print(f"Converted {percent:.1f}% to {letter}")
                return letter
            print("Percentage must be between 0 and 100.")

        else:
            print("Please choose L or P.")


def scenario_score_needed_on_final():
    """
    Weighted average: given current average and grade weights, what score is needed
    on the final (or remaining work) to hit a target overall %.
    """
    print("\n— Score needed on final / remaining work —")
    print("Enter how much of the course grade is already determined vs still left.")
    current_avg = get_number("Your current average in the class (%): ")
    if not 0 <= current_avg <= 100:
        print("Average should be between 0 and 100.")
        return

    w_done = get_number("Weight of graded work so far (e.g. 75 for 75% of course): ", True)
    w_left = get_number("Weight of final / remaining (e.g. 25): ", True)
    target = get_number("Target overall grade in the class (%): ")

    result = compute_final_needed(current_avg, w_done, w_left, target)
    if not result["ok"]:
        print(result["error"])
        return

    needed = result["needed"]
    print(
        f"\nYou need {needed:.1f}% on the remaining {result['w_left']:g}-weighted part",
        end="",
    )
    print(f" (with {result['w_done']:g} already in at {result['current_avg']:.1f}%).")
    for note in result["notes"]:
        print(note)


def scenario_term_gpa_for_cumulative_target():
    """What term GPA is required to reach a target cumulative, given prior record."""
    print("\n— Term GPA needed for a cumulative target —")
    prior_units = get_number("Total units completed before this term (not counting this term): ")
    if prior_units < 0:
        print("Units cannot be negative.")
        return

    prior_gpa = get_number("Your cumulative GPA going into this term: ")
    if not 0 <= prior_gpa <= 4.0:
        print("GPA is usually between 0 and 4. Enter what your school uses if different.")

    term_units = get_number("Total units you are taking this term: ", True)
    target = get_number("Cumulative GPA you want after this term: ")
    if target < 0 or target > 4.5:
        print("Unusual target; continuing anyway.")

    result = compute_required_term_gpa(prior_units, prior_gpa, term_units, target)
    if not result["ok"]:
        print(result["error"])
        return

    print(f"\nRequired term GPA (this term): {result['required_term_gpa']:.2f}")
    for note in result["notes"]:
        print(note)


def scenario_project_cumulative(classes):
    """Combine prior cumulative with this term's classes from your list."""
    print("\n— Projected cumulative GPA —")
    if len(classes) == 0:
        print("Add classes to your list first, or use option 2 and enter numbers by hand.")
        return

    prior_units = get_number("Units completed before this term: ")
    prior_gpa = get_number("Cumulative GPA before this term: ")

    result = compute_projected_cumulative(classes, prior_units, prior_gpa)
    if not result["ok"]:
        print(result["error"])
        return

    print(f"\nThis term: {result['term_gpa']:.2f} GPA over {result['term_units']:.1f} units")
    print(
        f"Projected cumulative: {result['cumulative']:.2f} (after {result['all_units']:.1f} total units)"
    )


def scenario_what_if_grade(classes):
    """Swap one class to another grade and see the new term GPA."""
    print("\n— What-if: change one class grade —")
    if len(classes) == 0:
        print("Add at least one class first.")
        return

    show_classes(classes)
    n = int(get_number("Which class number? ", True))
    idx = n - 1
    if idx < 0 or idx >= len(classes):
        print("Invalid class number.")
        return

    c = classes[idx]
    print(f"Current: {c['name']} → {c['grade']}")
    print("Enter the grade to try instead (letter or percent).")
    new_grade = choose_grade()

    result = compute_what_if(classes, idx, new_grade)
    if not result["ok"]:
        print(result["error"])
        return

    print(
        f"\nTerm GPA was {result['old_gpa']:.2f} → would be {result['new_gpa']:.2f} with that change."
    )


def scenario_min_percent_for_letter():
    """Show cutoff % for a letter on this app's scale."""
    print("\n— Minimum course % for a letter grade —")
    letter = input("Letter grade (A, A-, B+, … F): ").strip().upper()
    if letter not in GRADE_POINTS:
        print("Not a valid letter grade here.")
        return

    low = letter_minimum_percent(letter)
    if letter == "F":
        print("F: below 60% on this scale (anything under D-).")
    else:
        print(f"{letter}: at least {low}% in the class (on this app's scale).")


def grade_scenarios_menu(classes):
    while True:
        print("\n--- Grade scenarios ---")
        print("1) Score needed on final (weighted %)")
        print("2) Term GPA needed to hit a cumulative target")
        print("3) Project cumulative GPA (uses your class list + prior record)")
        print("4) What-if: change one class's grade")
        print("5) Minimum % for a letter (this app's scale)")
        print("6) Back to main menu")

        sub = input("Choose 1-6: ").strip()
        if sub == "1":
            scenario_score_needed_on_final()
        elif sub == "2":
            scenario_term_gpa_for_cumulative_target()
        elif sub == "3":
            scenario_project_cumulative(classes)
        elif sub == "4":
            scenario_what_if_grade(classes)
        elif sub == "5":
            scenario_min_percent_for_letter()
        elif sub == "6":
            break
        else:
            print("Please choose a valid option.")


def show_classes(classes):
    if len(classes) == 0:
        print("No classes yet.")
        return

    print("\nYour classes:")
    for i in range(len(classes)):
        c = classes[i]
        print(f"{i + 1}. {c['name']} | {c['units']} units | {c['grade']}")


def add_class(classes):
    print("\nAdd Class")
    name = input("Class name: ").strip()
    if name == "":
        name = "Untitled Class"

    units = get_number("Units: ", must_be_positive=True)
    grade = choose_grade()

    classes.append({"name": name, "units": units, "grade": grade})
    print("Class added.")


def edit_class(classes):
    if len(classes) == 0:
        print("No classes to edit.")
        return

    show_classes(classes)
    class_number = int(get_number("Which class number do you want to edit? ", True))
    index = class_number - 1

    if index < 0 or index >= len(classes):
        print("Invalid class number.")
        return

    selected = classes[index]
    print(f"\nEditing: {selected['name']}")

    new_name = input("New name (press Enter to keep current): ").strip()
    if new_name != "":
        selected["name"] = new_name

    if yes_or_no("Change units? (y/n): "):
        selected["units"] = get_number("New units: ", must_be_positive=True)

    if yes_or_no("Change grade? (y/n): "):
        selected["grade"] = choose_grade()

    print("Class updated.")


def remove_class(classes):
    if len(classes) == 0:
        print("No classes to remove.")
        return

    show_classes(classes)
    class_number = int(get_number("Which class number do you want to remove? ", True))
    index = class_number - 1

    if index < 0 or index >= len(classes):
        print("Invalid class number.")
        return

    removed = classes.pop(index)
    print(f"Removed: {removed['name']}")


def show_gpa(classes):
    if len(classes) == 0:
        print("No classes entered yet.")
        return

    term_gpa, term_units, _ = calculate_term_gpa(classes)
    print(f"\nTerm GPA: {term_gpa:.2f}")
    print(f"Term units: {term_units:.1f}")

    if yes_or_no("Do you want cumulative GPA too? (y/n): "):
        old_units = get_number("Previous total units: ")
        old_quality_points = get_number("Previous total quality points: ")

        result = compute_cumulative_from_quality_points(
            old_units, old_quality_points, classes
        )
        if result["ok"]:
            print(f"Cumulative GPA: {result['cumulative']:.2f}")
        else:
            print(result["error"])


def print_menu():
    print("\n--- GradePoint ---")
    print("1) Add class")
    print("2) Edit class")
    print("3) Remove class")
    print("4) List classes")
    print("5) Show GPA")
    print("6) Grade scenarios (final needed, targets, what-if…)")
    print("7) Exit")


def main():
    classes = []

    while True:
        print_menu()
        choice = input("Choose 1-7: ").strip()

        if choice == "1":
            add_class(classes)
            if len(classes) > 0:
                term_gpa, _, _ = calculate_term_gpa(classes)
                print(f"Updated term GPA: {term_gpa:.2f}")

        elif choice == "2":
            edit_class(classes)
            if len(classes) > 0:
                term_gpa, _, _ = calculate_term_gpa(classes)
                print(f"Updated term GPA: {term_gpa:.2f}")

        elif choice == "3":
            remove_class(classes)
            if len(classes) > 0:
                term_gpa, _, _ = calculate_term_gpa(classes)
                print(f"Updated term GPA: {term_gpa:.2f}")

        elif choice == "4":
            show_classes(classes)

        elif choice == "5":
            show_gpa(classes)

        elif choice == "6":
            grade_scenarios_menu(classes)

        elif choice == "7":
            print("Good luck this semester.")
            break

        else:
            print("Please choose a valid option.")


if __name__ == "__main__":
    main()

