"""The admission gate lets a typed write-401 through by name, never as ``AdmissionNotRecorded`` (decision 10 (b)).

Decision 10 (b), 2026-10-09 16:38 MST (``D-IMPL-378``; the text is Grok's recommendation, which Dave adopted), verbatim:
*"(b) Type a 401 on a write, and rename the type so it covers both."* Once a write's 401 is the typed authentication
refusal, ``ccf.artifacts.protocol.ArtifactStoreUnauthenticated``, it is an ``ArtifactStoreError``, and
``src/ccf/peering/admission.py::PeeringAdmissionGate._persist_admission_record`` catches every
``ArtifactStoreError`` from its ``put`` and raises ``AdmissionNotRecorded`` instead — the class whose own docstring
reads a failure to persist as "a fabric that cannot reach its own substrate", a broken deployment, which is the
outage reading the ruling keeps apart from a refused credential. So the gate lets the typed refusal through by name,
as the read side's consumers do for repair 2.5 (a). SEC-020 stays open: this module measures, it closes nothing.

What is asserted, by type, never by message text:

* **the hole.** A gate whose artifact store is the shipped ``McpArtifactStore``, presenting a bearer token the
  artifact server's verifier does not know, raises the typed authentication refusal at admission — chained from the
  guard's 401 response — never ``AdmissionNotRecorded``, and appends no ``peering_admitted`` verdict;
* **control: the clause is narrow.** A store that declines the write with a plain ``ArtifactStoreError`` is still
  ``AdmissionNotRecorded``, and an outage is still ``McpServerUnreachable``, raised as it was;
* **control: the world admits.** The same gate over the fixture's own store admits the crossing;
* **the nonce, as SP §1.1a states it.** The issuance nonce is spent immediately before the record is filed, so a
  crossing refused at its record write for the credential is not admitted later either: the same envelope, presented
  again to a working store, is refused ``replayed``.

The gate's store is used for the admission record's ``put`` and nothing else, so the 401 here is the write's. The
world is ``tests/peering/test_admission_record.py``'s (its fixtures, by name); the failing stores are
``tests/mcp/test_auth_401_typed_through_the_client.py``'s, declaring the fixture store's write kinds so the record's
capability passes the client's own check and the call reaches the server. Fixture vocabulary only (CINV-01).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import ArtifactRef, ArtifactStoreError
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.mcp.errors import McpServerUnreachable
from ccf.peering.admission import AdmissionNotRecorded, AdmittedProduct, PeeringAdmissionGate
from ccf.peering.identity import DetachedJwsIdentityProvider, JsonWebKey
from ccf.products.contract import RegisteredProductClass
from tests.mcp.test_auth_401_typed_through_the_client import (
    UNKNOWN,
    World,
    assert_the_authentication_refusal,
    store_at_nothing,
    store_over_http,
)
from tests.peering.test_admission_record import (  # noqa: F401 — pytest fixtures, used by name
    _build_gate,
    _consumer_lineage,
    _inbound,
    _now,
    _sign,
    banking_product,
    key_dir,
    product_class,
    provider,
    public_key,
    registry,
    store,
)


def _admitted_events(registry: ControlPlaneRegistry) -> list[Any]:
    return [event for event in registry.audit_events() if event.action == "peering_admitted"]


def _admit(gate: PeeringAdmissionGate, provider: DetachedJwsIdentityProvider) -> Any:
    """Present the fixture product, signed by the fixture peer; the verdict, or the exception raised instead."""
    try:
        return gate.admit(
            inbound=_inbound(_sign(provider, product=banking_product())),
            consumer_lineage=_consumer_lineage(),
            now=_now(),
        )
    except Exception as raised:  # noqa: BLE001 — judged by its type below, never by its text
        return raised


class _Declines:
    """A store that declines every write with a plain ``ArtifactStoreError``: the server answered, and said no."""

    def __init__(self, inner: FileArtifactStore) -> None:
        self._inner = inner

    def put(self, authorized: Any, artifact: Any) -> ArtifactRef:
        raise ArtifactStoreError("the fixture store declines this write")

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


def test_a_write_401_at_the_admission_record_is_the_typed_refusal_never_admission_not_recorded(
    tmp_path: Path,
    provider: DetachedJwsIdentityProvider,
    public_key: JsonWebKey,
    registry: ControlPlaneRegistry,
    product_class: RegisteredProductClass,
    store: FileArtifactStore,
) -> None:
    """The admission record's write meets the guard's 401: the typed refusal, by name, and no verdict appended.

    Measured on the base (``59f6aaaf``): ``McpServerUnreachable``, because the base's ``put`` reported the 401 as an
    outage, which this clause does not catch. With the write typed and nothing else changed, the clause would turn it
    into ``AdmissionNotRecorded``."""
    before = len(_admitted_events(registry))
    with store_over_http(World(tmp_path / "world").server(), UNKNOWN, write_kinds=store.write_kinds) as refused:
        gate = _build_gate(
            provider=provider,
            public_key=public_key,
            registry=registry,
            product_class=product_class,
            artifact_store=refused,
        )
        outcome = _admit(gate, provider)
    assert isinstance(outcome, BaseException), f"the gate admitted over a store whose credential was refused: {outcome!r}"
    assert not isinstance(outcome, AdmissionNotRecorded), (
        "the guard's 401 at the admission record's write was reported as AdmissionNotRecorded, the substrate-failure"
        f" reading: {type(outcome).__name__}: {str(outcome)[:300]}"
    )
    assert_the_authentication_refusal(outcome, what="the admission record's write")
    assert len(_admitted_events(registry)) == before, "a peering_admitted verdict was appended for a refused write"


def test_control_a_declined_write_is_still_admission_not_recorded_and_an_outage_still_an_outage(
    tmp_path: Path,
    provider: DetachedJwsIdentityProvider,
    public_key: JsonWebKey,
    registry: ControlPlaneRegistry,
    product_class: RegisteredProductClass,
    store: FileArtifactStore,
) -> None:
    """The clause that lets the typed refusal through is narrow: every other store failure is answered as before."""
    before = len(_admitted_events(registry))
    declined = _admit(
        _build_gate(
            provider=provider,
            public_key=public_key,
            registry=registry,
            product_class=product_class,
            artifact_store=_Declines(store),
        ),
        provider,
    )
    assert type(declined) is AdmissionNotRecorded, (type(declined).__mro__, str(declined)[:300])
    assert type(declined.__cause__) is ArtifactStoreError, repr(declined.__cause__)
    with store_at_nothing(store.write_kinds) as nothing:
        outage = _admit(
            _build_gate(
                provider=provider,
                public_key=public_key,
                registry=registry,
                product_class=product_class,
                artifact_store=nothing,
            ),
            provider,
        )
    assert type(outage) is McpServerUnreachable, (type(outage).__mro__, str(outage)[:300])
    assert len(_admitted_events(registry)) == before, "a peering_admitted verdict was appended for a failed write"


def test_control_the_same_gate_over_the_fixture_store_admits(
    provider: DetachedJwsIdentityProvider,
    public_key: JsonWebKey,
    registry: ControlPlaneRegistry,
    product_class: RegisteredProductClass,
    store: FileArtifactStore,
) -> None:
    """The world admits when the store writes: the refusals above are the stores', not the crossing's."""
    outcome = _admit(
        _build_gate(
            provider=provider, public_key=public_key, registry=registry, product_class=product_class, artifact_store=store
        ),
        provider,
    )
    assert isinstance(outcome, AdmittedProduct), f"{type(outcome).__name__}: {str(outcome)[:300]}"
    assert len(_admitted_events(registry)) == 1


def test_a_crossing_refused_at_its_record_for_the_credential_has_spent_its_nonce(
    tmp_path: Path,
    provider: DetachedJwsIdentityProvider,
    public_key: JsonWebKey,
    registry: ControlPlaneRegistry,
    product_class: RegisteredProductClass,
    store: FileArtifactStore,
) -> None:
    """The typed refusal at the record write, then the same envelope again over the fixture's own store: ``replayed``.

    What ``public/how-to/security-and-deployment.md`` §1.1a states of a crossing refused at its record, for this third
    way a record write can fail (``tests/peering/test_admission_record_writer_checks_the_returned_reference.py``
    measures the other two)."""
    envelope = _inbound(_sign(provider, product=banking_product()))
    with store_over_http(World(tmp_path / "world").server(), UNKNOWN, write_kinds=store.write_kinds) as refused:
        gate = _build_gate(
            provider=provider, public_key=public_key, registry=registry, product_class=product_class, artifact_store=refused
        )
        first: Any
        try:
            first = gate.admit(inbound=envelope, consumer_lineage=_consumer_lineage(), now=_now())
        except Exception as raised:  # noqa: BLE001 — judged by its type below, never by its text
            first = raised
    assert not isinstance(first, AdmissionNotRecorded), f"{type(first).__name__}: {str(first)[:300]}"
    assert_the_authentication_refusal(first, what="the first presentation's record write")
    working = _build_gate(
        provider=provider, public_key=public_key, registry=registry, product_class=product_class, artifact_store=store
    )
    again = working.admit(inbound=envelope, consumer_lineage=_consumer_lineage(), now=_now())
    assert type(again).__name__ == "IssuanceRefusal" and getattr(again, "failure", None) == "replayed", (
        f"the same envelope presented again was not refused as replayed: {again!r}"[:600]
    )
    assert _admitted_events(registry) == [], "a crossing was reported admitted"
