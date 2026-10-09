"""Repair 2.5 (a) at the governed evidence read: a 401 is never answered, or recorded, as an absence.

Dave, 2026-10-09 10:54 MST (``D-IMPL-378``), verbatim: *"Return a typed authentication refusal for 401, preserving
its distinction from authorization denial and transport outage."* SEC-020 stays open: this module measures, it closes
nothing.

``ccf_runtime.authz.delivery_boundary.govern_dereference`` answers ONE outcome for a malformed address, nothing
stored, bytes that are not a record and bytes that do not hash to their address: the ``nonexistent`` shell, recorded
(``D-IMPL-345``). It reaches that outcome by catching ``ArtifactStoreError`` at two places — resolving the record, and
the by-URI naming check after the holds. The same ``nonexistent`` shell is what its holds answer an unauthorized
caller, so a 401 folded into it would lose exactly the distinction the ruling keeps, and the deployment's own
credential failure would be written down as the absence of the caller's evidence. On the base (``fe25536c``) the
guard's 401 reached both places as ``McpServerUnreachable``, which neither catches, so it escaped; the typed
authentication refusal is an ``ArtifactStoreError`` and must escape too. Held here:

* resolving the record through a store whose every read the guard answers 401: the typed refusal escapes, and no
  refusal record is filed;
* the by-URI naming check when the guard answers 401 there alone (the credential refused between the reads — the
  only way a request reaches that check with a refused credential): the same.

Each has a positive control through the same world: the entitled examiner reads the record. The store is the shipped
``McpArtifactStore`` over streamable HTTP to the shipped artifact server, presenting a token the server's verifier
does not know. The world is ``tests/http_api/test_evidence_dereference.py``'s, as
``tests/http_api/test_fw7_by_uri_naming_check.py`` uses it. Fixture vocabulary only (CINV-01).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ccf.authz.capability import ReplayRead
from ccf.erasure import compose_erasure_consult
from ccf_runtime.authz.delivery_boundary import (
    SURFACE_HTTP_REPLAY_READ,
    DereferencedEvidence,
    DereferenceRequest,
    govern_dereference,
)
from ccf_runtime.authz.product_entitlement import ControlPlaneProductEntitlementSource
from http_api import test_evidence_dereference as ed
from http_api.conftest import Fabric
from tests.composition import declared_erasure_trust
from tests.controlplane.capabilities import capability
from tests.mcp.test_auth_401_typed_through_the_client import (
    UNKNOWN,
    World,
    assert_the_authentication_refusal,
    raised_by,
    store_over_http,
)


class _NamingRefused:
    """An inner store whose ``resolve_uri`` is answered by ``refusing`` — a store whose credential the guard refuses.

    Every other read is the governed world's own store, so a by-URI read passes every hold and reaches the naming
    check with the credential refused there: the credential revoked between the reads.
    """

    def __init__(self, inner: Any, *, refusing: Any) -> None:
        self._inner = inner
        self._refusing = refusing
        self.root = getattr(inner, "root", None)
        self.write_kinds = getattr(inner, "write_kinds", None)

    def put(self, authorized: Any, artifact: object) -> Any:
        return self._inner.put(authorized, artifact)

    def get(self, *, content_address: str) -> bytes:
        return self._inner.get(content_address=content_address)  # type: ignore[no-any-return]

    def exists(self, *, content_address: str) -> bool:
        return self._inner.exists(content_address=content_address)  # type: ignore[no-any-return]

    def resolve_uri(self, *, uri: str) -> str:
        return self._refusing.resolve_uri(uri=uri)  # type: ignore[no-any-return]

    def names_at(self, *, content_address: str) -> Any:
        return self._inner.names_at(content_address=content_address)


def _decide(governed: ed.Governed, store: Any, reference: str, *, by_uri: bool) -> Any:
    """The governed read the HTTP replay routes make, as the entitled examiner ``A``, over ``store``."""
    return govern_dereference(
        capability(ReplayRead, tenant=governed.tenant, resource=reference, principal=ed.A),
        reference=DereferenceRequest(reference=reference, by_uri=by_uri, wants_bytes=False),
        store=compose_erasure_consult(
            store,
            index=governed.erasure_index,
            audit_log=governed.registry.audit_log,
            clock=lambda: ed.AUDIT_INSTANT,
            control_plane=governed.registry,
            erasure_trust=declared_erasure_trust(governed.tenant),
        ),
        entitlement_source=ControlPlaneProductEntitlementSource(
            control_plane=governed.registry, clock=lambda: ed.AUDIT_INSTANT
        ),
        refusal_recorder=governed.recorder,
        audit_log=governed.registry.audit_log,
        surface=SURFACE_HTTP_REPLAY_READ,
        address="/replay/resolutions" if by_uri else "/replay/decisions",
    )


def test_resolving_the_record_reports_a_401_as_the_authentication_refusal_never_as_a_recorded_absence(
    fabric: Fabric, tmp_path: Path
) -> None:
    governed = ed._governed(fabric, tmp_path)
    address = ed._served_record(governed, principal=ed.A)
    # Positive control: through the world's own store, the entitled examiner reads the record.
    served = _decide(governed, governed.store, address, by_uri=False)
    assert isinstance(served, DereferencedEvidence), served
    records = ed._decision_records(governed)
    with store_over_http(World(tmp_path / "world").server(), UNKNOWN) as refused:
        raised = raised_by(lambda: _decide(governed, refused, address, by_uri=False), what="the record's resolution")
    assert_the_authentication_refusal(raised, what="the governed read, resolving the record")
    # Nothing was recorded: the 401 never became a read refusal of the caller's evidence.
    assert ed._decision_records(governed) == records


def test_the_by_uri_naming_check_reports_a_401_as_the_authentication_refusal_never_as_a_recorded_absence(
    fabric: Fabric, tmp_path: Path
) -> None:
    governed = ed._governed(fabric, tmp_path)
    address = ed._served_record(governed, principal=ed.A)
    uri = ed._uri_for(governed, address)
    # Positive control: through the world's own store, the entitled examiner reads the record by URI.
    served = _decide(governed, governed.store, uri, by_uri=True)
    assert isinstance(served, DereferencedEvidence), served
    records = ed._decision_records(governed)
    with store_over_http(World(tmp_path / "world").server(), UNKNOWN) as refused:
        raised = raised_by(
            lambda: _decide(governed, _NamingRefused(governed.store, refusing=refused), uri, by_uri=True),
            what="the by-URI naming check",
        )
    assert_the_authentication_refusal(raised, what="the governed read's by-URI naming check")
    assert ed._decision_records(governed) == records
