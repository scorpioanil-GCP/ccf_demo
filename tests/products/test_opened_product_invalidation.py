# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""A deployment records an invalidation boundary through the SDK's scoped writer (round 5, item 4).

**SDK-defined** (CLAUDE.md §8.1, §11). Dave, 2026-10-11 20:19 MST: *"Invalidation
must use the existing scoped writer capability."*

The invalidation register is written only under
:class:`~ccf.authz.capability.InvalidationRecordRegister`, which SDK composition
mints per composed tenant for that tenant's invalidation prefix (``D-IMPL-354``,
``D-IMPL-382``). A paved deployment had no way to reach it: every per-question
fabric composes its own sink for the graph writer, and
``ControlPlaneInvalidationSink(registry=...)`` without the minted capability is
refused (``cp-17`` ``MWE-G11``: an external Reg FD disclosure is a boundary the
deployment must record). The supported path now: ``open_product`` composes the
sink once, over the product's ONE Control Plane, under the SAME composition
recipe ``ccf.boot`` uses, for the product's own tenant only, and exposes it as
:attr:`~ccf.products.product.OpenedProduct.invalidation_sink`.

Held here:

* the authorized write lands — a new, audited version of that entity's record,
  read back by the SDK's own resolver;
* an out-of-scope write — another tenant's entity — is refused by name, and
  nothing is written;
* the sink holds exactly the product's tenant and no other.

That the recorded boundary then governs the next question (a determination that
touched the entity before it is refused ``dependency-invalidation``) is the
dependency-invalidation gate's own behavior; cp-17 ``MWE-G11`` exercises it
through this path against the curated estate.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest

from ccf.controlplane.invalidation import InvalidationUnauthorized, record_key, resolve_record
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.contract import SUBJECT_WITHHOLDING_NEVER
from ccf.products.product import open_product

from tests.composition import declare_wide_temporal_boundary, declared_erasure_trust
from tests.products import paved_fixture as fixture

ENTITY = "urn:ccf:fixture:entity:acct-1"
OTHER_TENANT = "someone-elses-tenant"
REASON = "fixture-disclosure"


def _open(tmp_path: Path) -> Any:
    root = fixture.write_tree(
        tmp_path / "deployment",
        config=fixture.producer_config(subject_withholding=SUBJECT_WITHHOLDING_NEVER),
        environment=fixture.producer_environment_text(),
    )
    control_plane = ControlPlaneRegistry()
    declare_wide_temporal_boundary(control_plane, tenant_id=fixture.PRODUCER_TENANT)
    return open_product(
        erasure_trust=declared_erasure_trust(fixture.PRODUCER_TENANT),
        config_root=root,
        scratch=tmp_path / "scratch",
        acquire=fixture.Acquire(),
        project=fixture.plan_factory,
        assess=fixture.assess,
        environ={fixture.CHILD_DSN_VAR: "postgresql://fixture"},
        control_plane=control_plane,
    )


def _sink(opened: Any) -> Any:
    sink = getattr(opened, "invalidation_sink", None)
    assert sink is not None, (
        "an opened product offers no invalidation sink; a deployment cannot record an"
        " invalidation boundary without minting the scoped capability itself (cp-17 MWE-G11)"
    )
    return sink


def test_the_authorized_write_lands_as_an_audited_version(tmp_path: Path) -> None:
    with _open(tmp_path) as opened:
        sink = _sink(opened)
        boundary = fixture.ASKED_AT - timedelta(hours=1)
        before = len(opened.control_plane.audit_log)
        sink.record(tenant_id=opened.tenant_id, entity_uri=ENTITY, invalidated_from=boundary,
                    reason=REASON, source="evt-1")
        record = resolve_record(opened.control_plane, tenant_id=opened.tenant_id, entity_uri=ENTITY)
        assert record is not None, "the boundary did not land"
        assert record.invalidated_from == boundary and record.reason == REASON and record.source == "evt-1"
        assert opened.control_plane.versions(record_key(opened.tenant_id, ENTITY)), "no version was registered"
        registered = [e for e in opened.control_plane.audit_log.events()[before:]
                      if e.key == record_key(opened.tenant_id, ENTITY)]
        assert registered, "the write landed with no audit event"


def test_an_out_of_scope_write_is_refused_and_nothing_lands(tmp_path: Path) -> None:
    with _open(tmp_path) as opened:
        sink = _sink(opened)
        assert sink.tenants == frozenset({opened.tenant_id})
        with pytest.raises(InvalidationUnauthorized, match="holds an invalidation-record capability only for"):
            sink.record(tenant_id=OTHER_TENANT, entity_uri=ENTITY, invalidated_from=fixture.ASKED_AT,
                        reason=REASON, source="evt-2")
        assert resolve_record(opened.control_plane, tenant_id=OTHER_TENANT, entity_uri=ENTITY) is None
        assert not opened.control_plane.versions(record_key(OTHER_TENANT, ENTITY))


def test_a_boundary_that_does_not_move_registers_nothing(tmp_path: Path) -> None:
    with _open(tmp_path) as opened:
        sink = _sink(opened)
        boundary = fixture.ASKED_AT - timedelta(hours=1)
        sink.record(tenant_id=opened.tenant_id, entity_uri=ENTITY, invalidated_from=boundary,
                    reason=REASON, source="evt-1")
        sink.record(tenant_id=opened.tenant_id, entity_uri=ENTITY, invalidated_from=boundary - timedelta(days=1),
                    reason=REASON, source="evt-0")
        assert len(opened.control_plane.versions(record_key(opened.tenant_id, ENTITY))) == 1
