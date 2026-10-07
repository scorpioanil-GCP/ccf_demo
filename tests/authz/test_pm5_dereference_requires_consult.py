"""PM5 (panel C5): ``govern_dereference`` refuses a store that does not consult the erasure index (SEC-009; `D-IMPL-374`).

U12 says the erasure consult is composed ALWAYS, at every store construction
site. ``govern_dereference`` — the public governed evidence read both shipped
evidence doors call — read the consult conditionally
(``store.inner if isinstance(store, ErasureConsultingStore) else store``, and
the same for the caller's tenant view), so an out-of-tree door that called it
over a store it never composed served erased bytes with no refusal at all.
After the repair such a store is refused by name, after the capability check
and before anything is read, recorded or clocked. The shipped callers (the HTTP
artifact and replay routes over ``create_app``'s composed store; the MCP
artifact server over its ``consulted`` store) are unaffected — held by their
own suites.
"""

from __future__ import annotations

import pathlib

import pytest

from ccf.authz.capability import ArtifactRead
from ccf.erasure import compose_erasure_consult
from tests.authz.test_dereference_capability import NOWHERE, PRINCIPAL, TENANT, _World
from tests.composition import declared_erasure_trust, no_erasures
from tests.controlplane.capabilities import capability


def test_pm5_an_uncomposed_store_is_refused_by_name_before_anything_is_read(tmp_path: pathlib.Path) -> None:
    world = _World(tmp_path)
    raw = getattr(world, "raw", world.store)  # the world's own store, never composed here
    composed = compose_erasure_consult(
        raw, index=no_erasures(), audit_log=world.registry.audit_log, clock=lambda: world.source.clock(),
        control_plane=world.registry, erasure_trust=declared_erasure_trust(TENANT),
    )
    world.store = raw
    before = world.addresses()
    with pytest.raises(TypeError) as refused:
        world.dereference(capability(ArtifactRead, tenant=TENANT, resource=NOWHERE, principal=PRINCIPAL))
    assert type(refused.value).__name__ == "UnconsultedDeliveryBoundaryError", repr(refused.value)
    assert "SEC-009" in str(refused.value)
    # Refused before the clock, the store or the recorder.
    assert world.addresses() == before
    assert world.clock_reads == 0
    assert world.read_trail() == []

    # The control: the same read over the same store, composed, is decided.
    world.store = composed
    decided = world.dereference(capability(ArtifactRead, tenant=TENANT, resource=NOWHERE, principal=PRINCIPAL))
    assert type(decided).__name__ == "RefusalEnvelope"
