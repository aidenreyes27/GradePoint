"""
Vercel / local entry when the Git root is this folder.
Loads the real Flask app from GradePointWeb/app.py (do not remove that file).
"""
import importlib.util
import os
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(debug=True, host="0.0.0.0", port=port)
