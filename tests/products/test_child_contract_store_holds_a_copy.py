# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""The composite's child view is built from contracts the store never held (``D-IMPL-380``, third round, ruling 2 (a)).

Dave, 2026-10-10 09:18 MST (the ``D-IMPL-380`` amendment), verbatim: *"Fix all three the same way. Copy before the
save. [...] The child contracts are built from the copy the writer kept."* And at 09:23 MST: *"Each of the three
writers copies before the save and keeps its own. [...] The parent is built from contracts the store never held."*

``src/ccf/products/resolver.py::GovernedResolver._retain_child_contracts`` files each admitted child's contract by
content address. At ``7d9d2898`` it handed the store the resolver's own contract — the very object in
``resolved.admitted`` from which ``child_contract_view(resolved)``, the parent's view, is then built — and
``ContextProductContract.payload`` validates to a live ``dict`` (Fable seat 3, F3-2; reproduced by the coordinator).
A store that wrote a key into that mapping inside ``put`` and answered the right address had its key reach the
parent's view.

The attacker: a store statically shaped like the composite fixture's store (``isinstance`` against a Protocol reads
``getattr_static``), forwarding everything to it, that writes ``injected_by_store`` into the payload of the admitted
child contract it is handed, files it, and answers the reference of the contract as it was handed. The existing
content-address check is unchanged and passes. The test asserts the served parent's child view carries every child
payload as admitted, with no injected key.

Fixture vocabulary only (CINV-01).
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any

import pytest

import ccf.products.resolver as resolver_module
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.products.composite import ADMITTED_CHILD_CONTRACT_CLASS
from ccf.products.contract import SUBJECT_WITHHOLDING_NEVER
from tests.products.composite_fixture import ask_composite, boot_composite, build_composite

INJECTED = "injected_by_store"


class _Attack:
    def __init__(self) -> None:
        self.as_handed: dict[str, bytes] = {}
        self.address_as_handed: list[str] = []
        self.address_as_altered: list[str] = []


def _altering(inner: Any, attack: _Attack) -> Any:
    """A store statically shaped like ``inner`` that alters each admitted child contract it is handed in ``put``."""
    cls = type(inner)
    namespace: dict[str, Any] = {}
    for name in dir(cls):
        if name.startswith("__") or name == "put":
            continue
        attr = getattr(cls, name)
        if isinstance(attr, property):
            namespace[name] = property(lambda self, n=name: getattr(self._inner, n))
        elif callable(attr):
            namespace[name] = (lambda n: (lambda self, *a, **k: getattr(self._inner, n)(*a, **k)))(name)

    def put(self: Any, authorized: Any, artifact: Any) -> Any:
        if getattr(artifact, "artifact_class", None) != ADMITTED_CHILD_CONTRACT_CLASS:
            return self._inner.put(authorized, artifact)
        contract = artifact.artifact
        handed = content_hash(contract)
        attack.as_handed[handed] = canonical_bytes(contract)
        attack.address_as_handed.append(handed)
        contract.payload[INJECTED] = "laundered"
        altered = content_hash(contract)
        attack.address_as_altered.append(altered)
        filed = self._inner.put(authorized, artifact)
        # The original fingerprint: the reference of the contract as it was handed, naming what was filed.
        return filed.model_copy(update={"content_address": handed, "uri": filed.uri.replace(altered, handed)})

    namespace["put"] = put
    namespace["__getattr__"] = lambda self, n: getattr(self._inner, n)
    wrapped = type(f"Altering{cls.__name__}", (), namespace)()
    wrapped.__dict__.update(inner.__dict__)
    wrapped._inner = inner
    return wrapped


def test_a_store_that_alters_a_child_contract_and_answers_the_right_address_leaves_the_parent_view_as_admitted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    generator = boot_composite(tmp_path, subject_withholding=SUBJECT_WITHHOLDING_NEVER)
    booted = next(generator)
    try:
        attack = _Attack()
        resolver, _children = build_composite(dataclasses.replace(booted, store=_altering(booted.store, attack)))
        views: list[Any] = []
        real_view = resolver_module.child_contract_view

        def recording_view(resolved: Any) -> Any:
            view = real_view(resolved)
            views.append(view)
            return view

        monkeypatch.setattr(resolver_module, "child_contract_view", recording_view)

        ask_composite(resolver)

        assert attack.address_as_handed and all(
            h != a for h, a in zip(attack.address_as_handed, attack.address_as_altered, strict=True)
        ), "the case was not constructed: the store must have filed and altered an admitted child contract"
        assert len(views) == 1, f"the parent's child view was built {len(views)} times, not once"
        (view,) = views
        assert len(view) >= 1, "the parent's child view is empty"
        for product_class, contract in view.items():
            assert INJECTED not in contract.payload, (
                f"the parent's view of child {product_class!r} carries the store's key: {sorted(contract.payload)}"
            )
            address = content_hash(contract)
            assert address in attack.as_handed, (
                f"the parent's view of child {product_class!r} hashes to {address!r}, not to any contract as admitted"
            )
            assert canonical_bytes(contract) == attack.as_handed[address]
    finally:
        generator.close()
