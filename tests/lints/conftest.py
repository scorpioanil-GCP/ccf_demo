"""Make `tools.lints` importable from the main suite.

`tools` is a repo-local package (the D-07 lint gate), not an installed
distribution like `ccf`, so tests that exercise the lints from under
`tests/` need the repo root on ``sys.path`` — the same resolution
`tools/lints/tests` gets for free by being a package under the root.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = str(Path(__file__).resolve().parents[2])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
