"""
Vercel entry when the Git root is this folder (not GradePointWeb).
Loads the Flask app from GradePointWeb/app.py without naming it root app.py.
"""
import importlib.util
import sys
from pathlib import Path

_WEB = Path(__file__).resolve().parent / "GradePointWeb"
sys.path.insert(0, str(_WEB))

_spec = importlib.util.spec_from_file_location(
    "gradepoint_web_impl",
    _WEB / "app.py",
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
app = _mod.app
