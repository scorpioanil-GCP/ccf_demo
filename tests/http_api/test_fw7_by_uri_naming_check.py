"""FW-7 (whole-branch review M-3): the by-URI naming check reads the caller's tenant view, and an erasure it meets is an erasure (SEC-009; `D-IMPL-374`).

``govern_dereference`` reads the record through the view for the caller's
VERIFIED tenant (fix round 1, I6) — an erasure withholds only within its
tenant. The by-URI naming check after the holds called the TENANTLESS composed
store's ``resolve_uri``, and its ``except (ArtifactStoreError, LookupError)``
turned an ``ErasedContentRefused`` into ``cause="nonexistent"``. Probe X4 measured
the store half: an entry under ANOTHER tenant naming the same address leaves the
caller's tenant view serving while the tenantless ``resolve_uri`` refuses.

The consequence at the door, held here: a holder of an erase capability in
tenant B appends an entry (genuine, or forged and unsupported — the P2 class)
naming tenant A's record address, and tenant A's entitled examiner gets
"absent" on ``/replay/resolutions`` with a refusal record that says
``nonexistent``. After the repair the naming check reads tenant A's view, so
another tenant's entry changes nothing for A; and an erasure the check DOES
meet in the caller's own tenant is decided as the erased reading, not as an
absence.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ccf.authz.capability import ArtifactWrite, ReplayRead
from ccf.erasure import compose_erasure_consult
from ccf.erasure.index import ErasureIndexEntry
from ccf.products.refusal import RefusalEnvelope
from ccf_runtime.authz.delivery_boundary import (
    SURFACE_HTTP_REPLAY_READ,
    DereferenceRequest,
    govern_dereference,
)
from ccf_runtime.authz.product_entitlement import ControlPlaneProductEntitlementSource
from http_api import test_evidence_dereference as ed
from http_api.conftest import Fabric
from tests.composition import declared_erasure_trust
from tests.controlplane.capabilities import capability
from tests.erasure import composed
from tests.erasure.composed import _erase_capability

OTHER = "tenant-fw7-other"


def test_another_tenants_entry_does_not_withhold_a_by_uri_read_in_this_tenant(
    fabric: Fabric, tmp_path: Path
) -> None:
    """Probe X4 at the door: tenant B's entry naming tenant A's record address."""
    governed = ed._governed(fabric, tmp_path)
    address = ed._served_record(governed, principal=ed.A)
    uri = ed._uri_for(governed, address)
    # Positive control: the entitled examiner reads the record by URI.
    assert ed._get_uri(governed, uri, token=ed.A_TOKEN).status_code == 200

    governed.erasure_index.append(
        _erase_capability(OTHER, "customer/r9"),
        ErasureIndexEntry(
            tenant_id=OTHER, content_address=address, erasure_record_address="cd" * 32,
            subject_class="customer", request_id="r9", subject_ref="ef" * 32, approval_ref="01" * 32,
            reason="customer-request", erased_at=datetime(2026, 7, 30, tzinfo=UTC),
            door_signature="x..y", door_key_id="door-1",
        ),
    )

    # The by-address read is tenant A's view, and serves.
    assert ed._get_record(governed, address, token=ed.A_TOKEN).status_code == 200
    # The by-URI read must agree: tenant A erased nothing.
    by_uri = ed._get_uri(governed, uri, token=ed.A_TOKEN)
    assert by_uri.status_code == 200, (
        f"another tenant's entry withheld tenant A's record on the by-URI read:"
        f" {by_uri.status_code} {by_uri.text[:300]}"
    )


class _NamingRedirect:
    """An inner store whose ``resolve_uri`` names a DIFFERENT address for one URI.

    The one way a by-URI read reaches the naming check carrying an address its
    own consult did not already judge — the case the ``except`` clause decides.
    Everything else passes through.
    """

    def __init__(self, inner: Any, *, uri: str, names: str) -> None:
        self._inner = inner
        self._uri = uri
        self._names = names
        self.root = getattr(inner, "root", None)
        self.write_kinds = getattr(inner, "write_kinds", None)

    def put(self, authorized: Any, artifact: object) -> Any:
        return self._inner.put(authorized, artifact)

    def get(self, *, content_address: str) -> bytes:
        return self._inner.get(content_address=content_address)  # type: ignore[no-any-return]

    def exists(self, *, content_address: str) -> bool:
        return self._inner.exists(content_address=content_address)  # type: ignore[no-any-return]

    def resolve_uri(self, *, uri: str) -> str:
        return self._names if uri == self._uri else self._inner.resolve_uri(uri=uri)  # type: ignore[no-any-return]

    def names_at(self, *, content_address: str) -> Any:
        return self._inner.names_at(content_address=content_address)


def test_an_erasure_met_at_the_naming_check_is_the_erased_reading_not_an_absence(
    fabric: Fabric, tmp_path: Path
) -> None:
    governed = ed._governed(fabric, tmp_path)
    address = ed._served_record(governed, principal=ed.A)
    uri = ed._uri_for(governed, address)
    # A client-lane artifact of the same tenant, genuinely erased in that tenant.
    erased = governed.store.put(
        capability(ArtifactWrite, tenant=governed.tenant, resource="fw7/erased"), {"fw7": "erased"}
    )
    composed.erase(
        governed.store, governed.erasure_index, erased.content_address,
        control_plane=governed.registry, tenant=governed.tenant,
    )
    store = compose_erasure_consult(
        _NamingRedirect(governed.store, uri=uri, names=erased.content_address),
        index=governed.erasure_index, audit_log=governed.registry.audit_log,
        clock=lambda: ed.AUDIT_INSTANT, control_plane=governed.registry,
        erasure_trust=declared_erasure_trust(governed.tenant),
    )
    decided = govern_dereference(
        capability(ReplayRead, tenant=governed.tenant, resource=uri, principal=ed.A),
        reference=DereferenceRequest(reference=uri, by_uri=True, wants_bytes=False),
        store=store,
        entitlement_source=ControlPlaneProductEntitlementSource(
            control_plane=governed.registry, clock=lambda: ed.AUDIT_INSTANT
        ),
        refusal_recorder=governed.recorder,
        audit_log=governed.registry.audit_log,
        surface=SURFACE_HTTP_REPLAY_READ,
        address="/replay/resolutions",
    )
    assert isinstance(decided, RefusalEnvelope), decided
    # `A` discloses at full, so the determination crosses whole: an erasure,
    # never the `nonexistent` absence the clause used to record.
    assert decided.kind == "erased-content", (decided.kind, decided.fields)
    internal = governed.internal(decided.replay_reference)
    assert internal.kind == "erased-content", internal.kind
