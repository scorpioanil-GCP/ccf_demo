"""PM9 (panel C9): an empty declared product reach is refused at construction (SEC-017; `D-IMPL-374`).

``ProductReach.__post_init__`` promises "no empty statement", but checked
emptiness only for ``argument``, ``undeclared`` and ``unknown``. A
``ProductReach(declared=frozenset())`` constructed, and the roster hold then
passed every call — even an empty roster's — because a call that reaches no
class has nothing outside any roster. No shipped registration builds one
(``products_declared`` always wraps one class), but an adopter registration that
derives its classes from configuration and gets an empty set would be silently
roster-unbound.
"""

from __future__ import annotations

import pytest


def test_pm9_an_empty_declared_reach_is_refused_by_name() -> None:
    from ccf_runtime.mcp.tenancy import ProductReach

    with pytest.raises(ValueError) as refused:
        ProductReach(declared=frozenset())
    assert "SEC-017" in str(refused.value) and "declared" in str(refused.value)


def test_pm9_control_a_declared_reach_naming_a_class_constructs() -> None:
    from ccf_runtime.mcp.tenancy import ProductReach

    assert ProductReach(declared=frozenset({"a-class"})).declared == frozenset({"a-class"})
