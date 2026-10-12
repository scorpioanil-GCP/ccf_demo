# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""A typed registration over a stored untyped document is refused before any class binding (D-IMPL-381).

``D-IMPL-381`` (recorded 2026-10-10 18:25 MST): register a document's
canonical mapping through ``register``, then ``register_typed`` the typed
artifact under the same key. The content hash is the same, so the typed call
took the idempotent path, bound the class to the key, and left the stored
``dict`` in place: ``resolve`` then served a ``dict`` under a class-bound key.
``register_versioned`` had the same shape. Dave, 2026-10-11 14:51: *"implement
the already-selected refusal before class binding or registration state
changes. No replacement semantics or broader registry redesign."* Test
vocabulary only (CINV-01).
"""

from __future__ import annotations

import json

import pytest

from ccf.contracts.canonical import canonical_bytes
from ccf.controlplane.artifacts import HALF_LIFE_TABLE, HalfLifeTable
from ccf.workflow.definitions import WORKFLOW_DEFINITION
from http_api.composition_authority import register_versioned_at_composition
from tests.controlplane.test_registry_isolation_refusal import _REGISTRATIONS, _cap, _entry, _registry
from tests.workflow.test_factory import _workflow_definition

REFUSAL = "is stored untyped"


def _state(registry: object, key: str) -> tuple[object, ...]:
    """Everything a refused registration must leave untouched."""
    return (
        registry.versions(key),  # type: ignore[attr-defined]
        registry.artifact_class_of(key),  # type: ignore[attr-defined]
        dict(getattr(registry, "_bumps").get(key, {})),
        # registration rows only: the composition root records its own authority first
        [e.action for e in registry.audit_events() if e.action in _REGISTRATIONS],  # type: ignore[attr-defined]
    )


def test_register_typed_over_the_same_document_stored_untyped_is_refused() -> None:
    registry = _registry()
    key = "acme/half-life-table/spreads"
    table = HalfLifeTable(semver="1.0.0", entries={"spread": _entry()})
    stored = registry.register(_cap(key), json.loads(canonical_bytes(table)))
    before = _state(registry, key)
    with pytest.raises(TypeError, match=REFUSAL):
        registry.register_typed(_cap(key), table, HALF_LIFE_TABLE)
    assert _state(registry, key) == before
    assert registry.artifact_class_of(key) is None
    assert registry.versions(key) == (stored,)


def test_register_versioned_over_the_same_document_stored_untyped_is_refused() -> None:
    registry = _registry()
    key = "acme/workflow-definition/release"
    definition = _workflow_definition()
    registry.register(_cap(key), json.loads(canonical_bytes(definition)))
    before = _state(registry, key)
    with pytest.raises(TypeError, match=REFUSAL):
        register_versioned_at_composition(registry, key, definition, WORKFLOW_DEFINITION)
    assert _state(registry, key) == before
    assert registry.artifact_class_of(key) is None


def test_a_typed_idempotent_reregistration_is_still_admitted() -> None:
    """Positive control: the idempotent path itself is unchanged for a typed history."""
    registry = _registry()
    key = "acme/half-life-table/spreads"
    table = HalfLifeTable(semver="1.0.0", entries={"spread": _entry()})
    first = registry.register_typed(_cap(key), table, HALF_LIFE_TABLE)
    assert registry.register_typed(_cap(key), table, HALF_LIFE_TABLE) == first
    assert isinstance(registry.resolve(key, first), HalfLifeTable)
