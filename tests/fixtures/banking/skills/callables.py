"""The fixture local-callable the dispatch suite resolves — /tests only.

The target of the ``covenant-metrics-local`` catalog entry's ``callable_ref``
(``fixtures.banking.skills.callables.covenant_metrics``). A fixture value in
module form: dispatch resolves callables only from entries registered as
Control Plane artifacts under the tenant trust boundary (T-05-18), and this
module is that registered ref's destination for the banking fixtures.

Deterministic and side-effect free, like every fixture the suite drives.
"""

from __future__ import annotations

from collections.abc import Mapping


def covenant_metrics(arguments: Mapping[str, str]) -> dict[str, str]:
    """Return a deterministic mapping derived from the typed arguments."""
    return {"invoked": "covenant-metrics", **arguments}
