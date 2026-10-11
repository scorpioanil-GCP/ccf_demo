"""The admission gate points its verdict only at the admission record it wrote (``D-IMPL-378`` decision 5 (a)).

Dave, 2026-10-09 16:38 MST, adopting Grok's recommendation on the "j" batch's decision 5, verbatim: *"(a) Fix
the four writers in one small lane."* Decision 5 (a) itself (06:06 MST, confirmed at 06:21 MST), verbatim:
*"Verify the returned record address against the record actually written."* It was built for
``src/ccf/replay/serve.py::ReplayWriter.write_replay_record``; this module holds its neighbor
``src/ccf/peering/admission.py::PeeringAdmissionGate`` to the same rule.

Before a crossing is reported admitted, the gate files an ``AdmissionRecord`` of what crossed (``D-IMPL-58``
reading (d)) and appends the audit verdict, whose ``key`` and ``version`` are the name and the content address
of the reference the store answered. The gate recorded that answer unchecked. The small lane found it by reading
the code; this module measures it on ``dl-378-integ`` @ ``6cd6023e``: a store that filed the second crossing's
record faithfully and answered with the first crossing's record reference had the second crossing's verdict
point at the first crossing's record.

What the gate knows before the store answers (``D-IMPL-26``): the record's address is the content hash of the
record, its name is the admitted product's content address, the tenant is its capability's, the class is
``ccf.admission-record``, and the URI is ``ccf-artifact://{tenant}/{class}/{name}@{address}``.

What is asserted, by mechanism:

1. **The hole as evidenced.** A store answering another crossing's genuine record reference is refused by name
   (``AdmissionRecordReferenceMismatch``), and no admission verdict is appended for the crossing.
2. **Every field of the reference.** One field of the record's reference answered as another record's (the
   address, the URI, the name) or as another tenant's or class's is refused by name; so is a changed field carried
   in a ``str`` subclass that claims to equal the record's own.
3. **Control.** An honest store's reference is what the verdict points at, and it is the record's own.

The refusal is asserted by its class NAME as a string, so a tree without the check fails each test on its
behavior (the crossing admitted, its verdict naming what the store answered), never on an import. Every domain
value comes from ``tests/fixtures/banking/*.yaml`` through the admission-record harness (CINV-01).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import ArtifactRef, ArtifactStoreError, ArtifactStoreProtocol, artifact_uri
from ccf.contracts.canonical import content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.peering.admission import ADMISSION_RECORD, AdmissionRecord, AdmittedProduct, PeeringAdmissionGate
from ccf.peering.identity import DetachedJwsIdentityProvider, JsonWebKey
from ccf.products.contract import ContextProductContract, RegisteredProductClass
from tests.peering.test_admission_record import (  # noqa: F401 — pytest fixtures, used by name
    TENANT,
    _build_gate,
    _consumer_lineage,
    _inbound,
    _now,
    _record,
    _sign,
    banking_product,
    key_dir,
    product_class,
    provider,
    public_key,
    registry,
    store,
)

#: The refusal this check raises, by name (absent on a tree without the check).
REFUSAL = "AdmissionRecordReferenceMismatch"

#: The one field each lying store changes, and the foreign value it answers with.
#: ``None`` means "the other record's value for that field".
FIELDS: dict[str, str | None] = {
    "content_address": None,
    "uri": None,
    "name": None,
    "tenant_id": "another-tenant",
    "artifact_class": "another-record-class",
}


def _record_ref(*, name: str, address: str) -> ArtifactRef:
    """The reference of the admission record at ``address`` named ``name``, under this fixture's tenant (D-IMPL-26)."""
    return ArtifactRef(
        content_address=address,
        uri=artifact_uri(tenant_id=TENANT, artifact_class=ADMISSION_RECORD.class_id, name=name, artifact_version=address),
        tenant_id=TENANT,
        artifact_class=ADMISSION_RECORD.class_id,
        name=name,
    )


def _another_records_ref() -> ArtifactRef:
    """The reference another admission record would have: the harness's own record, under this tenant."""
    other = _record()
    return _record_ref(name=other.product_content_address, address=content_hash(other))


class _Answers:
    """A store that files every write faithfully through ``inner`` and answers with ``answer(the honest ref)``.

    ``answer`` is ``None`` until a test sets it, so one gate can file an honest crossing first. A buggy or hostile
    artifact server whose bytes are right and whose reference is not; reads delegate unchanged.
    """

    def __init__(self, inner: ArtifactStoreProtocol) -> None:
        self._inner = inner
        self.answer: Callable[[ArtifactRef], ArtifactRef] | None = None
        self.filed: list[ArtifactRef] = []

    def put(self, authorized: Any, artifact: Any) -> ArtifactRef:
        honest = self._inner.put(authorized, artifact)
        self.filed.append(honest)
        return honest if self.answer is None else self.answer(honest)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


class _ClaimsEquality(str):
    """A ``str`` whose equality answers for itself: equal to anything, unequal to nothing."""

    def __eq__(self, other: object) -> bool:
        return True

    def __ne__(self, other: object) -> bool:
        return False

    __hash__ = str.__hash__


def _admitted_events(registry: ControlPlaneRegistry) -> list[Any]:
    return [event for event in registry.audit_events() if event.action == "peering_admitted"]


def _admit(gate: PeeringAdmissionGate, provider: DetachedJwsIdentityProvider, product: ContextProductContract) -> Any:
    """Present ``product``, signed by the fixture peer, and return the verdict or the exception raised instead."""
    try:
        return gate.admit(
            inbound=_inbound(_sign(provider, product=product)), consumer_lineage=_consumer_lineage(), now=_now()
        )
    except Exception as raised:  # noqa: BLE001 — judged by its type's name below, never by its text
        return raised


def _assert_refused_by_name(
    outcome: Any, *, registry: ControlPlaneRegistry, admitted_before: int, own: ArtifactRef, case: str
) -> None:
    """No admission verdict was appended for the crossing, and the refusal is the check's own, by its type's name."""
    if not isinstance(outcome, Exception):
        events = _admitted_events(registry)
        if not isinstance(outcome, AdmittedProduct) or len(events) == admitted_before:
            pytest.fail(f"[{case}] the gate returned {type(outcome).__name__}, not the check's refusal: {outcome!r}"[:600])
        event = events[-1]
        pytest.fail(
            f"[{case}] the gate returned {type(outcome).__name__} and its verdict names key={event.key},"
            f" version={event.version} for the crossing whose record is key={own.name}, version={own.content_address};"
            f" the verdict names the record's own: {(event.key, event.version) == (own.name, own.content_address)}"
        )
    assert any(klass.__name__ == REFUSAL for klass in type(outcome).__mro__), (
        f"[{case}] refused, but not by the returned-reference check ({REFUSAL}): {type(outcome).__name__}: {outcome}"
    )
    assert len(_admitted_events(registry)) == admitted_before, (
        f"[{case}] an admission verdict was appended after the store's answer was refused"
    )


def _gate(
    provider: DetachedJwsIdentityProvider,
    public_key: JsonWebKey,
    registry: ControlPlaneRegistry,
    product_class: RegisteredProductClass,
    store: FileArtifactStore,
) -> tuple[PeeringAdmissionGate, _Answers]:
    answers = _Answers(store)
    gate = _build_gate(
        provider=provider,
        public_key=public_key,
        registry=registry,
        product_class=product_class,
        artifact_store=answers,
    )
    return gate, answers


def _own_ref(store: FileArtifactStore, filed: ArtifactRef) -> ArtifactRef:
    """The record's own reference, from the bytes the store holds — the case's construction check."""
    record = AdmissionRecord.model_validate_json(store.get(content_address=filed.content_address))
    assert content_hash(record) == filed.content_address
    own = _record_ref(name=record.product_content_address, address=content_hash(record))
    assert filed == own, "the case was not constructed: the store must have filed the record under its own reference"
    return own


# --- 1. the hole as evidenced: another crossing's record reference ----------------------------


def test_a_store_answering_another_crossings_record_reference_is_refused_by_name(
    provider: DetachedJwsIdentityProvider,
    public_key: JsonWebKey,
    registry: ControlPlaneRegistry,
    product_class: RegisteredProductClass,
    store: FileArtifactStore,
) -> None:
    """The first crossing is admitted honestly; the second crossing's write is answered with the first's reference.

    Measured on ``6cd6023e``: the second crossing was admitted and its verdict pointed at the first crossing's record.
    """
    gate, answers = _gate(provider, public_key, registry, product_class, store)
    first = _admit(gate, provider, banking_product())
    assert isinstance(first, AdmittedProduct), f"the case was not constructed: the honest crossing must admit: {first}"
    first_ref = answers.filed[-1]
    answers.answer = lambda _honest: first_ref
    second = banking_product().model_copy(update={"payload": {"exposure_state": "a-second-crossing"}})
    before = len(_admitted_events(registry))

    outcome = _admit(gate, provider, second)

    assert len(answers.filed) == 2 and answers.filed[-1].content_address != first_ref.content_address, (
        "the case was not constructed: the store must have filed a second, different record"
    )
    _assert_refused_by_name(
        outcome, registry=registry, admitted_before=before, own=_own_ref(store, answers.filed[-1]),
        case="another crossing's record reference",
    )


# --- 2. every field of the returned reference ------------------------------------------------


def _one_field_changed(field: str, *, foreign: ArtifactRef) -> Callable[[ArtifactRef], ArtifactRef]:
    value = FIELDS[field]
    replacement = getattr(foreign, field) if value is None else value
    return lambda honest: honest.model_copy(update={field: replacement})


@pytest.mark.parametrize("field", sorted(FIELDS))
def test_a_reference_with_any_field_not_the_records_own_is_refused_by_name(
    provider: DetachedJwsIdentityProvider,
    public_key: JsonWebKey,
    registry: ControlPlaneRegistry,
    product_class: RegisteredProductClass,
    store: FileArtifactStore,
    field: str,
) -> None:
    """One field of the record's reference answered as another record's (or another tenant's, or class's)."""
    gate, answers = _gate(provider, public_key, registry, product_class, store)
    answers.answer = _one_field_changed(field, foreign=_another_records_ref())

    outcome = _admit(gate, provider, banking_product())

    assert len(answers.filed) == 1, "the case was not constructed: the store must have filed the record"
    _assert_refused_by_name(
        outcome, registry=registry, admitted_before=0, own=_own_ref(store, answers.filed[0]), case=f"one field, {field}"
    )


@pytest.mark.parametrize("field", sorted(FIELDS))
def test_a_reference_field_that_only_claims_equality_is_refused_by_name(
    provider: DetachedJwsIdentityProvider,
    public_key: JsonWebKey,
    registry: ControlPlaneRegistry,
    product_class: RegisteredProductClass,
    store: FileArtifactStore,
    field: str,
) -> None:
    """Another record's value in one field, carried in a ``str`` subclass that says it equals the record's own.

    The comparison reads the type first, so the claim is not taken: the field differs, and the gate refuses by name
    rather than appending a verdict.
    """
    gate, answers = _gate(provider, public_key, registry, product_class, store)
    value = FIELDS[field]
    disguised = _ClaimsEquality(getattr(_another_records_ref(), field) if value is None else value)
    answers.answer = lambda honest: honest.model_construct(**{**dict(honest), field: disguised})

    outcome = _admit(gate, provider, banking_product())

    assert disguised == getattr(answers.filed[0], field), "the case was not constructed: the value must claim equality"
    _assert_refused_by_name(
        outcome, registry=registry, admitted_before=0, own=_own_ref(store, answers.filed[0]),
        case=f"claimed equality, {field}",
    )


# --- 3. control -------------------------------------------------------------------------------


def test_control_an_honest_stores_reference_is_what_the_verdict_names_and_is_the_records_own(
    provider: DetachedJwsIdentityProvider,
    public_key: JsonWebKey,
    registry: ControlPlaneRegistry,
    product_class: RegisteredProductClass,
    store: FileArtifactStore,
) -> None:
    """The file store answers exactly the record's own reference, and the verdict's key and version are its own."""
    gate, answers = _gate(provider, public_key, registry, product_class, store)
    outcome = _admit(gate, provider, banking_product())
    assert isinstance(outcome, AdmittedProduct), outcome
    own = _own_ref(store, answers.filed[0])
    (event,) = _admitted_events(registry)
    assert (event.artifact_class, event.key, event.version) == (ADMISSION_RECORD.class_id, own.name, own.content_address)
    assert store.resolve_uri(uri=own.uri) == own.content_address


# --- 4. what a refused record leaves: the issuance nonce is spent -------------------------------


def _store_unreachable(_honest: ArtifactRef) -> ArtifactRef:
    raise ArtifactStoreError("the substrate is unreachable")


#: The two ways a crossing fails at its record, after the replay consult spent the nonce: the store cannot persist the
#: record (raised inside ``put``, so the gate reports ``AdmissionNotRecorded``), or it answers another record's
#: reference (this module's check).
RECORD_FAILURES: dict[str, tuple[Callable[[ArtifactRef], ArtifactRef], str]] = {
    "not persisted": (_store_unreachable, "AdmissionNotRecorded"),
    "another record's reference": (_one_field_changed("uri", foreign=_another_records_ref()), REFUSAL),
}


@pytest.mark.parametrize("failure", sorted(RECORD_FAILURES))
def test_a_crossing_refused_at_its_record_has_spent_its_nonce(
    provider: DetachedJwsIdentityProvider,
    public_key: JsonWebKey,
    registry: ControlPlaneRegistry,
    product_class: RegisteredProductClass,
    store: FileArtifactStore,
    failure: str,
) -> None:
    """The nonce is spent immediately before the record is filed, so a crossing refused at its record is not admitted
    and cannot be admitted later: the same envelope, presented again to a working store, is refused ``replayed``.

    What ``public/how-to/security-and-deployment.md`` §1.1a states. The ``"not persisted"`` case is the gate's behavior
    before decision 5; the other is the refusal it added.
    """
    gate, answers = _gate(provider, public_key, registry, product_class, store)
    envelope = _inbound(_sign(provider, product=banking_product()))
    answer, refusal = RECORD_FAILURES[failure]
    answers.answer = answer

    first: Any
    try:
        first = gate.admit(inbound=envelope, consumer_lineage=_consumer_lineage(), now=_now())
    except Exception as raised:  # noqa: BLE001 — judged by its type's name below, never by its text
        first = raised
    assert any(klass.__name__ == refusal for klass in type(first).__mro__), (
        f"[{failure}] the first presentation was not refused by {refusal}: {type(first).__name__}"
    )
    answers.answer = None
    again = gate.admit(inbound=envelope, consumer_lineage=_consumer_lineage(), now=_now())

    assert type(again).__name__ == "IssuanceRefusal" and getattr(again, "failure", None) == "replayed", (
        f"[{failure}] the same envelope presented again was not refused as replayed: {again!r}"[:600]
    )
    assert _admitted_events(registry) == [], f"[{failure}] a crossing was reported admitted"
