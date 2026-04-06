"""
Vercel serverless entry: all traffic is rewritten here (see vercel.json).
Loads the Flask app from GradePointWeb/app.py.
"""
import importlib.util
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_WEB = _REPO / "GradePointWeb"
sys.path.insert(0, str(_WEB))

_spec = importlib.util.spec_from_file_location(
    "gradepoint_web_impl",
    _WEB / "app.py",
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
app = _mod.app
