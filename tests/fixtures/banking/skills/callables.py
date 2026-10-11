# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""The fixture local-callable the dispatch suite resolves — /tests only.

What ``tests/conftest.py`` registers into the deployment's
:class:`~ccf.skills.callables.CallableRegistry` under the key the
``covenant-metrics-local`` catalog entry declares as its ``callable_ref``
(D-19 / D-IMPL-54). Nothing imports this module by way of that ref — the key
and the function are bound by an explicit registration call at the test
suite's composition root, which is the whole point of the control: a catalog
entry names a key, and only what a composition root registered is reachable.

Deterministic and side-effect free, like every fixture the suite drives.
"""

from __future__ import annotations

from collections.abc import Mapping


def covenant_metrics(arguments: Mapping[str, str]) -> dict[str, str]:
    """Return a deterministic mapping derived from the typed arguments."""
    return {"invoked": "covenant-metrics", **arguments}
