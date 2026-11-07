"""Pytest configuration for DringlichAI.

WHY THIS EXISTS: the app modules (`api`, `priority_analyzer_agent`) live at the repo root, but
the tests live in `tests/`. Without putting the repo root on `sys.path` first, pytest's import
mode would only expose the test directory and `import api` would fail.

INTERVIEW TALKING POINT: a one-line conftest that makes the app importable the same way the
running service imports it keeps the tests honest — they exercise the real modules, not a
re-packaged copy.
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
