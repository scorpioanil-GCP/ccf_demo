"""The memo-grade obligor set for `credit-memo-context`, defined once.

`docs/wave13a-design.md` §5: the set is constrained to obligors carrying an
extracted covenant, because a covenant needs a filed credit agreement to anchor
to and cannot be manufactured. Everything else a memo needs -- facilities,
pledges, exposures, relationship history -- is bank-internal by nature and can
legitimately be generated, so the covenant leg is what fixes membership.

Defined here rather than restated in each loader because at least four modules
need the same answer, and a set that drifts between them produces a five-way
"intersection" that is not one. known-issues.md §9.1 is the same lesson in a
different costume.
"""

from __future__ import annotations

import json
from functools import lru_cache

from ccf.config import REPO_ROOT

SCREEN = REPO_ROOT / "sources" / "screening"


@lru_cache(maxsize=1)
def memo_grade_leis() -> frozenset[str]:
    """LEIs of obligors with at least one covenant extracted from a filing."""
    docs = json.loads((SCREEN / "covenants_extracted.json").read_text())["documents"]
    return frozenset(d["lei"] for d in docs if d.get("covenants") and d.get("lei"))
