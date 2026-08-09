"""The memory backend's boot wiring, pinned (15.2-06, D-06).

Four facts this module exists to hold:

* **Explicit selection, never inference.** ``boot`` reaches this adapter only
  by being told its name. Since D-IMPL-93 the name is required and carries no
  default, and a connection setting this adapter does not declare is refused
  by its own connection contract — the successor to the exactly-one
  exclusivity check, which the eleven per-database keyword arguments took with
  them.
* **The floor is real.** A fabric boots against the memory backend through
  the real composition root, writes through L2, and answers a ``GraphQuery``
  — zero external dependencies. This is the D-06 must-have, asserted
  end-to-end rather than assumed from the differential suite.
* **Single-writer keys on instance identity.** Two memory fabrics are two
  graphs (per-instance synthetic ``memory://`` identity), so booting twice is
  legal — unlike booting twice over one SQLite path.
* **Timestamps are canonical text.** The store's dict field types declare
  ``str`` for every temporal column — the cross-backend byte-drift trap
  (04-RESEARCH.md Pitfall 3) pinned at the type level, so a ``datetime``
  cannot drift in without failing this test and mypy both.

Writes go through the booted worker only — never a directly constructed
writer — per the conformance discipline (D-IMPL-41;
``tests/conformance/test_graphstore.py``).
"""

from __future__ import annotations

import typing
from collections.abc import Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

from ccf.contracts.canonical import canonical_bytes
from ccf.contracts.claims import EntityClaim, LineageEntry
from ccf.graph.backends.memory import (
    EntityClaimRow,
    EntityNodeRow,
    RelationshipClaimRow,
    RelationshipNodeRow,
)
from ccf.graph.backends.memory_write import REGISTRATION as MEMORY_REGISTRATION
from ccf.graph.protocols import GraphQuery, GraphReader
from ccf.signal.envelope import SourceIdentity

if TYPE_CHECKING:
    from ccf.boot import FabricHandle

#: This module's subject, read off the adapter's own registration record
#: rather than typed here, so the name a manifest uses and the name this
#: module asserts cannot drift apart.
BACKEND_NAME = MEMORY_REGISTRATION.name

TENANT = "tenant-a"
T0 = datetime(2026, 1, 1, tzinfo=UTC)
T1 = datetime(2026, 2, 1, tzinfo=UTC)
T2 = datetime(2026, 3, 1, tzinfo=UTC)


def _entity(*, uri: str = "counterparty://acme", observed_at: datetime = T1) -> EntityClaim:
    return EntityClaim(
        tenant_id=TENANT,
        entity_uri=uri,
        entity_class="counterparty",
        attributes={"legal_name": "Acme Holdings"},
        observed_at=observed_at,
        valid_from=T0,
        lineage=frozenset(
            {
                LineageEntry(
                    source=SourceIdentity(system_id="core-banking"),
                    envelope_id=f"env-{uri}-{observed_at.isoformat()}",
                    observed_at=observed_at,
                )
            }
        ),
    )


def test_boot_refuses_another_substrates_connection_setting() -> None:
    """Naming this adapter and supplying another's setting is still refused.

    The guarantee this test has always carried is *the fabric does not pick a
    winner*. Before D-IMPL-93 it arrived as "exactly one of eleven keyword
    arguments"; the eleven are gone, so the same contradiction now arrives as a
    connection key the named adapter does not declare — and this adapter
    declares none at all, so every key is one. The refusal comes from the
    adapter's own connection contract through the registry's single
    config-validation wrapper, which names the adapter and the key and never
    the value.
    """
    from ccf.boot import boot
    from ccf.controlplane.registry import ControlPlaneRegistry
    from ccf.graph.registry import InvalidBackendConfig

    with pytest.raises(InvalidBackendConfig) as caught:
        boot(
            backend=BACKEND_NAME,
            connection={"database_path": "never-created.sqlite3"},
            registry=ControlPlaneRegistry(),
            resolution_spec_key="never",
            resolution_spec_version="never",
            policy_bundle_key="never",
            policy_bundle_version="never",
        )
    assert BACKEND_NAME in str(caught.value)
    assert "database_path" in str(caught.value)
    # The refusal is the adapter's, not a rebuilt one: the value that was
    # supplied does not travel with it.
    assert "never-created.sqlite3" not in str(caught.value)


def test_boot_refuses_to_infer_a_substrate() -> None:
    """There is no default substrate — not this one, not any other.

    `backend` is required and carries no default, so omitting it is refused by
    the signature itself rather than by a check that could be relaxed. That is
    the successor to the old "naming no substrate is refused" case, and it is
    the stronger form: a fabric that could infer its substrate could boot
    against a development store in production and still pass every test.
    """
    import inspect

    from ccf.boot import boot
    from ccf.controlplane.registry import ControlPlaneRegistry

    assert (
        inspect.signature(boot).parameters["backend"].default
        is inspect.Parameter.empty
    )
    with pytest.raises(TypeError, match="backend"):
        boot(  # type: ignore[call-arg]
            registry=ControlPlaneRegistry(),
            resolution_spec_key="never",
            resolution_spec_version="never",
            policy_bundle_key="never",
            policy_bundle_version="never",
        )


def test_memory_fabric_boots_writes_through_l2_and_answers_queries(
    fabric_boot: Callable[..., "FabricHandle"],
) -> None:
    """The D-06 floor, end-to-end: real composition root, L2 write, query answer.

    The reader satisfies the runtime-checkable ``GraphReader`` Protocol; the
    degenerate query and ``as_of`` answer identical canonical bytes (`GQ-21`
    at docs/GRAPH_QUERY_SEMANTICS.md:446 — the D-07 derivation holds on the
    memory reader exactly as on the SQL readers).
    """
    handle = fabric_boot(backend="memory")
    assert isinstance(handle.reader, GraphReader)

    result = handle.worker.admit_entity_claim(tenant_id=TENANT, claim=_entity())
    assert result.claim_created is True

    view = handle.reader.query(GraphQuery(tenant_id=TENANT, as_of=T2))
    assert [record.claim.entity_uri for record in view.entities] == [
        "counterparty://acme"
    ]
    assert canonical_bytes(view) == canonical_bytes(
        handle.reader.as_of(tenant_id=TENANT, at=T2)
    )

    # Idempotent re-arrival: the rowcount-zero contract, through the dict txn.
    again = handle.worker.admit_entity_claim(tenant_id=TENANT, claim=_entity())
    assert again.claim_created is False
    assert again.lineage_added == 0


def test_two_memory_fabrics_are_two_graphs(
    fabric_boot: Callable[..., "FabricHandle"],
) -> None:
    """Per-instance identity: two memory boots coexist, and state never crosses.

    Two writers over one store instance would be the single-writer violation;
    two instances are two fabrics — the graph_identity docstring's claim,
    held here.
    """
    first = fabric_boot(backend="memory")
    second = fabric_boot(backend="memory")

    first.worker.admit_entity_claim(tenant_id=TENANT, claim=_entity())

    assert second.reader.as_of(tenant_id=TENANT, at=T2).entities == ()
    assert first.reader.as_of(tenant_id=TENANT, at=T2).entities != ()


def test_memory_store_timestamps_are_declared_canonical_text() -> None:
    """Every temporal column in the dict tables is ``str`` — canonical RFC3339 text.

    Pinned at the type level: a ``datetime`` slipping into a stored row would
    change cross-substrate canonical bytes (04-RESEARCH.md Pitfall 3), so the
    row types must keep saying ``str`` for every temporal field.
    """
    for row_type, fields in (
        (EntityClaimRow, ("observed_at",)),
        (RelationshipClaimRow, ("observed_at",)),
        (EntityNodeRow, ("first_observed_at", "last_observed_at")),
        (RelationshipNodeRow, ("first_observed_at", "last_observed_at")),
    ):
        hints = typing.get_type_hints(row_type)
        for field in fields:
            assert hints[field] is str, f"{row_type.__name__}.{field} must be str"
    # The supersession pair is nullable text, never a datetime.
    for row_type in (EntityClaimRow, RelationshipClaimRow):
        hints = typing.get_type_hints(row_type)
        assert hints["superseded_at"] == (str | None)
        assert hints["superseded_by"] == (str | None)
