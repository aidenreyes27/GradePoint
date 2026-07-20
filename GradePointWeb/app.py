"""
GradePoint web app — local:
  pip install -r requirements.txt
  python app.py
  → http://127.0.0.1:5000

Production: gunicorn -c gunicorn.conf.py wsgi:app
"""

import os
from pathlib import Path

from flask import Flask, render_template

_BASE_DIR = Path(__file__).resolve().parent

app = Flask(
    __name__,
    template_folder=str(_BASE_DIR / "templates"),
    static_folder=str(_BASE_DIR / "static"),
)
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


def _page(template, nav):
    return render_template(template, nav=nav, grade_order=GRADE_ORDER)


@app.route("/")
def index():
    return _page("index.html", "term")


@app.route("/plan")
def plan():
    return _page("plan.html", "plan")


@app.route("/trends")
def trends():
    return _page("trends.html", "trends")


@app.route("/goals")
def goals():
    return _page("goals.html", "goals")


@app.route("/transcript")
def transcript():
    return _page("transcript.html", "transcript")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(debug=True, host="0.0.0.0", port=port)
