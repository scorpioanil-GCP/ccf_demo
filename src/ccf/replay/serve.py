"""Serving a product *is* appending its replay record, then delivering.

Whitepaper §7.10 (replay enforced at every Context Product boundary, never
bolted on — INV-CH7-79); CLAUDE.md §11; 04-RESEARCH.md Pattern 5.

The shape of this module is the invariant. Rather than

    write_replay_record(record)
    deliver(product)          # two statements, one of them skippable

the successful append *returns* the capability to deliver:

    ReplayWriter.write_replay_record(record) -> DeliveryCapability
    DeliveryCapability.deliver(product)      -> ServedProduct

A caller with no capability has nothing to deliver with, and the only way to
obtain one is an append that succeeded. Should the store fail, the exception
propagates out of the append and there is no branch — none, not even a
mistaken one — that reaches delivery. That closes the repudiation threat
(T-04-10) structurally instead of by review.

:class:`DeliveryCapability` takes a module-private token, exactly as
:class:`~ccf.products.gates.ServableProduct` does, so the capability cannot be
fabricated. The honest claim is DESIGN.md §9's: no unforced path exists, and
every forced path fails at construction.

Note what :meth:`DeliveryCapability.deliver` accepts: a ``ServableProduct``,
never a bare contract. The two structural gates therefore compose — a delivered
product has passed all three validation gates *and* has a replay record, and
neither guarantee is reachable without the other.

Where Context Debt travels on this seam
---------------------------------------
It travels **inside** :attr:`ServedProduct.product`, not beside it. The
:class:`~ccf.halflife.assessment.DebtAssessment` in force is a field of
:class:`~ccf.products.contract.ContextProductContract` under D-IMPL-100, so it
crosses this seam as part of the vessel's own bytes and needs nothing from
``serve()``.

That placement was ruled against the alternative of a third field on
:class:`ServedProduct`, and the reason is measured rather than aesthetic: all
three shipped delivery paths serialize ``servable.product`` and **none** of them
reads ``servable.replay_ref``, so debt hung beside the product would have
reached an in-process caller and no wire consumer at any door. See
:mod:`ccf.products.contract` for the per-door table.

**``serve()`` gains no branch for it.** The whole invariant of this module is
that the successful append *returns* the delivery capability and no branch
reaches delivery; debt travels with the capability's payload or with the record,
and it never becomes a condition. A ``serve()`` that inspected debt would be a
second place a delivery could be refused, and the first one — the append — would
stop being the only one.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from ccf.artifacts.protocol import (
    ArtifactRef,
    ArtifactStoreError,
    ArtifactStoreProtocol,
    DerivedWrite,
    artifact_uri,
)
from ccf.authz.capability import Authorized, ReplayMint, verify
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import content_hash
from ccf.graph.protocols import GraphQuery
from ccf.products.contract import ContextProductContract
from ccf.products.gates import ServableProduct, verify_gate_provenance
from ccf.replay.record import DecisionReplayRecord

__ccf_mode__ = "algorithmic"

__all__ = [
    "CapabilityForgeryError",
    "DeliveryCapability",
    "ProductRecordMismatch",
    "ReplayReferenceMismatch",
    "ReplayTenantMismatch",
    "QueryPinMismatch",
    "QueryPinReferenceMismatch",
    "QueryPinWriter",
    "ReplayWriter",
    "ServedProduct",
    "record_refusal",
    "serve",
]


class CapabilityForgeryError(TypeError):
    """A delivery capability was constructed outside a successful append."""


class ProductRecordMismatch(ValueError):
    """The replay record and the product about to be delivered describe different products.

    SDK-defined per CLAUDE.md §11; the ruling of record is ``D-IMPL-279``
    (Dave, 2026-09-08), narrowing ``D-IMPL-278`` row 1: *"The fabric must
    establish correspondence between the candidate product, the governed
    execution record, and the replay record before delivery."* And on where:
    *"I would not put the primary enforcement in MCP. MCP is transport. The
    canonical enforcement point should be in the governed fulfillment spine,
    before transport encoding."*

    **The sibling of** :class:`QueryPinMismatch`, deliberately. That refusal
    holds the record's pinned query sequence to the bytes the seam was handed;
    this one holds the record's
    :attr:`~ccf.replay.record.ContentGenerationPath.product_content_address`
    to the vessel the seam is about to deliver. Same seam, same moment —
    before anything is persisted — and the same reason: a record that does not
    describe what left is an audit trail an examiner cannot use, and refusing
    at the seam is what keeps that unrepresentable on the governed path.

    **What this closes, measured.** Until this refusal existed,
    :func:`~ccf.products.door.served_answer` proved only that *a* record was
    appended — the shape proof ``D-IMPL-260`` P-A requires — and no layer
    compared its contents against the payload. A ``ServedProduct`` whose
    payload claimed 9,999 members, wrapping a record whose dimension 1
    observed 77, crossed the delivery boundary unremarked
    (``CP-SPEC-005`` §D.10 question 1). Both operands were already in
    :func:`serve`'s hand; only the comparison was missing.

    **Not a governed refusal.** A resolver that hands the seam a record for
    one product and a vessel for another has mis-wired its own spine; that is
    a defect in the deployment's code and never a decision the fabric made
    about a caller's question. It therefore raises, exactly as
    :class:`QueryPinMismatch` does, rather than returning a
    :class:`~ccf.products.refusal.RefusalEnvelope` a caller could mistake for
    an answer.
    """


class ReplayTenantMismatch(ValueError):
    """The record (or query) names a tenant other than the writer's capability's (D-IMPL-353 §1.3).

    A :class:`ReplayWriter` files under ``authorized.tenant`` and nothing else
    may name a tenant. A record whose ``tenant_id`` differs was built by a
    resolver wired to the wrong writer — a deployment defect, raised before
    anything is persisted, exactly as :class:`ProductRecordMismatch` is.
    """


class QueryPinMismatch(ValueError):
    """The record's pinned query sequence and the serve seam's queries disagree.

    Raised by :func:`serve` before anything is persisted: a record appended
    beside query bytes it does not pin — or pinning bytes nobody handed the
    seam — is a pin an auditor can never resolve (T-15.2-28), and refusing at
    the seam is what keeps that unrepresentable on the governed path.
    """


class ReplayReferenceMismatch(ArtifactStoreError):
    """The store answered a record's append with a reference that is not that record's own.

    SDK-defined per CLAUDE.md §11; the ruling of record is ``D-IMPL-378``
    decision 5 (a) (Dave, 2026-10-09 06:06 MST, confirmed at 06:21 MST):
    *"Verify the returned record address against the record actually
    written."* The resolver holds the store's answer for an admitted child
    contract to that contract's own address
    (``src/ccf/products/resolver.py::GovernedResolver._retain_child_contracts``);
    :meth:`ReplayWriter.write_replay_record` now holds the store's answer for
    a record the same way.

    **What the writer knows before the store answers.** Under ``D-IMPL-26``
    and Q11 the whole reference of a record it files is fixed by the record
    and the writer's capability: the content address is
    :func:`~ccf.contracts.canonical.content_hash` of the record, the name is
    that address, the tenant and class are the capability's, and the versioned
    URI is ``ccf-artifact://{tenant}/{class}/{address}@{address}``. Every field
    of the store's answer is held to that, not the address alone, because the
    refusal path hands its caller the URI
    (``src/ccf/products/resolver.py::ReplayRefusalRecorder`` copies it into the
    shell's ``replay_reference``). Measured before this check, on
    ``dl-378-integ`` @ ``a539c215``: a store that filed record A faithfully and
    answered record B's reference had B's reference handed out for A, and one
    field of A's reference answered as another record's was handed out the same
    way (``tests/replay/test_replay_writer_checks_the_returned_reference.py``).

    **Raised after the store's ``put`` returns, so nothing is delivered and no
    reference leaves**: no :class:`DeliveryCapability` is minted on the served
    path, and :func:`record_refusal` returns nothing on the refusal path. The
    store may already hold the bytes; a failure to record is a failure to
    serve. An :class:`~ccf.artifacts.protocol.ArtifactStoreError`, because the
    store's answer is what failed. The text names the fields that differ and
    no value the store answered.

    **What it does not check:** the bytes the store holds. It reads the store's
    answer, not the store; a store that answers the record's own reference
    while holding other bytes under it is found by the readers, which re-hash
    what they read before using it
    (``tests/replay/test_record_content_address_integrity.py``).

    Attributes:
        fields: The names of the reference's fields that differ from the
            record's own, in :class:`~ccf.artifacts.protocol.ArtifactRef`'s
            field order.
    """

    def __init__(self, *, fields: tuple[str, ...]) -> None:
        self.fields = fields
        super().__init__(
            f"the artifact store answered this replay record's append with a"
            f" reference whose {', '.join(fields)} are not the record's own;"
            " the record writer hands out only the reference of the record it"
            " wrote, so nothing is delivered (D-IMPL-378 decision 5 (a))"
        )


class QueryPinReferenceMismatch(ArtifactStoreError):
    """The store answered a pinned query's write with a reference that is not that query's own.

    SDK-defined per CLAUDE.md §11; the ruling of record is ``D-IMPL-378``
    decision 5 (Dave, 2026-10-09 16:38 MST, adopting Grok's recommendation):
    *"(a) Fix the four writers in one small lane."* It extends decision 5 (a)
    (06:21 MST), *"Verify the returned record address against the record
    actually written."*, from :meth:`ReplayWriter.write_replay_record` (whose
    refusal is :class:`ReplayReferenceMismatch`) to
    :meth:`QueryPinWriter.write_query_bytes`.

    **What the writer knows before the store answers.** Under ``D-IMPL-26``
    the whole reference of a query it files is fixed by the query and the
    writer's capability: the content address is
    :func:`~ccf.contracts.canonical.content_hash` of the query, the name is
    that address, the tenant and class are the capability's, and the versioned
    URI is ``ccf-artifact://{tenant}/{class}/{address}@{address}``. Every field
    of the store's answer is held to that as an exact string. Measured before
    this check, on ``dl-378-integ`` @ ``6cd6023e``: a store that filed every
    query faithfully and answered every write with the first query's reference
    had the writer return query 1's reference for query 2, and one field of a
    query's reference answered as another query's (or another tenant's, or
    class's) was returned the same way
    (``tests/replay/test_query_pin_writer_checks_the_returned_reference.py``).

    **Raised after the store's ``put`` returns for that query, so no reference
    leaves the writer.** Queries filed before it in the same call stay filed.
    :func:`serve` persists the pins before it appends the record, so a serve
    whose pin store answers this way appends no record and delivers nothing.
    Before this check :func:`serve` discarded these references, so none of
    them ever left a serve; a caller of :meth:`QueryPinWriter.write_query_bytes`
    itself received the store's answer. An
    :class:`~ccf.artifacts.protocol.ArtifactStoreError`, because the store's
    answer is what failed. The text names the fields that differ and no value
    the store answered.

    **What it does not check:** the bytes the store holds. It reads the store's
    answer, not the store; a store that answers the query's own reference while
    holding other bytes under it is found by a reader that re-hashes what it
    fetches before using it, such as
    :func:`~ccf.replay.engine.resolve_artifact`
    (``tests/replay/test_query_sequence_pin.py::test_the_auditor_resolves_every_pin_to_the_literal_query_bytes``).

    Attributes:
        fields: The names of the reference's fields that differ from the
            query's own, in :class:`~ccf.artifacts.protocol.ArtifactRef`'s
            field order.
    """

    def __init__(self, *, fields: tuple[str, ...]) -> None:
        self.fields = fields
        super().__init__(
            f"the artifact store answered a pinned query's write with a"
            f" reference whose {', '.join(fields)} are not the query's own; the"
            " query-pin writer hands out only the reference of the query bytes"
            " it wrote, so no reference is returned (D-IMPL-378 decision 5 (a))"
        )


class ServedProduct(CCFContract):
    """What a caller receives: the product, and where its record landed.

    The reference travels with the product deliberately. A consumer holding a
    Context Product can name the decision record that authorizes it, which is
    what makes the audit trail usable from the consuming side rather than only
    from the fabric's.
    """

    product: ContextProductContract
    replay_ref: ArtifactRef


_DELIVERY_TOKEN = object()


class DeliveryCapability:
    """The right to deliver one product, granted by a completed replay append."""

    def __init__(self, replay_ref: ArtifactRef, token: object) -> None:
        if token is not _DELIVERY_TOKEN:
            raise CapabilityForgeryError(
                "DeliveryCapability is minted only by "
                "ReplayWriter.write_replay_record; delivery is unreachable "
                "without a completed replay append (whitepaper §7.10, "
                "CLAUDE.md §11)"
            )
        self._replay_ref = replay_ref

    @property
    def replay_ref(self) -> ArtifactRef:
        """Reference to the record whose append granted this capability."""
        return self._replay_ref

    def deliver(self, product: ServableProduct) -> ServedProduct:
        """Release ``product`` to the caller, paired with its replay reference.

        **A governed boundary** (`D-IMPL-337`). Separately reachable from
        :func:`serve`, so it establishes gate provenance itself rather than
        assuming its caller did — this is the entry the measured exploit used.
        """
        product = verify_gate_provenance(product)
        return ServedProduct(product=product.product, replay_ref=self._replay_ref)


def _same_string(answered: object, own: str) -> bool:
    """Whether ``answered`` is exactly the string ``own``: a plain ``str``, character for character.

    The type is read first, so a ``str`` subclass that answers equality for
    itself is a different value here (``D-IMPL-378`` decision 5 (a)).
    """
    return type(answered) is str and answered == own


class ReplayWriter:
    """Appends replay records to the ArtifactStore and grants delivery.

    **Holds the one capability no door can mint (D-IMPL-353 §2 P3).** The
    composition root obtains ``Authorized[ReplayMint]`` through
    :func:`~ccf.authz.capability.mint_at_composition` — its statement, made
    once at boot and audited under the capability's ``decision_id``, that this
    process may mint governed records for one tenant under one record class —
    and hands it here. The record class IS the capability's resource; the
    tenant IS the capability's tenant; there is no ``artifact_class`` parameter
    and no second source for either. Each record is filed as a
    :class:`~ccf.artifacts.protocol.DerivedWrite` — the decision that minted the
    capability could not name a record that did not yet exist, so this writer
    names it (by its content address) and the store verifies the capability against
    the kinds the deployment declared for the class. A store whose declaration
    does not name the class under ``ReplayMint`` refuses at the first write:
    wrong kind, loudly, at boot's first serve.

    One writer per tenant, by construction: the capability is minted for one.

    Args:
        authorized: The composition-minted ``ReplayMint`` capability. Verified
            here at construction so a mis-wired root fails before any request,
            and verified again by the store at every write.
        store: The artifact substrate (CLAUDE.md §7.4). Any conforming
            implementation, and the store is never a second writer to the
            graph: this module holds no graph handle and imports no reader and
            no writer (its one :mod:`ccf.graph` import is the frozen
            :class:`GraphQuery` *value* contract the pin surface persists).
    """

    def __init__(
        self, *, authorized: Authorized[ReplayMint], store: ArtifactStoreProtocol
    ) -> None:
        verify(authorized, kind=ReplayMint, resource=getattr(authorized, "resource", ""))
        self._authorized = authorized
        self._store = store

    @property
    def tenant_id(self) -> str:
        """The one tenant this writer files under — the capability's."""
        return self._authorized.tenant

    @property
    def artifact_class(self) -> str:
        """The record class this writer files under — the capability's resource."""
        return self._authorized.resource

    def write_replay_record(
        self, *, record: DecisionReplayRecord
    ) -> DeliveryCapability:
        """Append ``record``; return the capability its success grants.

        The record is addressed by its content hash and NAMED by it too (Dave's
        Q11, 2026-10-07; ``D-IMPL-378``): *"Equal public references must not
        identify different immutable record contents."* The reference a caller
        is handed — ``ccf-artifact://{tenant}/{class}/{name}@{version}`` — then
        names exactly one immutable content in both its segments. The name used
        to be dimension 1's ``graph_snapshot_id``, which hashes only what the
        decision read, so different records shared a name and a withheld
        subject's answer was named by a read it must not show. A governed
        answer's record carries a per-answer
        :attr:`~ccf.replay.record.ContentGenerationPath.issuance`, so its
        address is unique per answer and computable by nobody who does not hold
        the record. Two appends of byte-identical content still converge on one
        artifact. Records filed before this rule keep the names they were filed
        under; replay resolves by content address and never reads a name.

        **The store's answer is held to the record written** (``D-IMPL-378``
        decision 5 (a)): every field of the reference ``put`` returns must be
        the record's own — its content address, the URI naming it under this
        writer's tenant and class with that address as name and version, and
        the tenant, class and name — or nothing is handed out. The reference
        handed out is the one the writer derived from the record, which the
        store's answer equals field for field.

        Raises:
            ReplayTenantMismatch: the record's ``tenant_id`` is not the
                capability's tenant. Raised before the store is touched.
            ReplayReferenceMismatch: the store's answer is not the record's
                own reference. Raised after the store returns and before any
                capability exists.
            Exception: whatever the store raises. Deliberately not caught: a
                failure to record is a failure to serve, and translating it
                into a softer outcome here would be the exact hole this design
                exists to close.
        """
        if record.tenant_id != self._authorized.tenant:
            raise ReplayTenantMismatch(
                f"the replay record names tenant {record.tenant_id!r} but this"
                f" writer's capability is for {self._authorized.tenant!r}; a"
                " record is filed under the capability's tenant and nothing"
                " else may name one (D-IMPL-353 §1.3)"
            )
        # Q11 (`D-IMPL-378`): the record's own content address — the store's
        # identity of these bytes — so one name, one content.
        address = content_hash(record)
        answered = self._store.put(
            self._authorized,
            DerivedWrite(artifact_class=self._authorized.resource, name=address, artifact=record),
        )
        # Decision 5 (a) (`D-IMPL-378`): the reference of the record actually
        # written, derived here (`D-IMPL-26`: the version IS the address), and
        # the store's answer held to it field for field. Compared as exact
        # strings, so a value that only claims equality does not pass.
        own = ArtifactRef(
            content_address=address,
            uri=artifact_uri(
                tenant_id=self._authorized.tenant,
                artifact_class=self._authorized.resource,
                name=address,
                artifact_version=address,
            ),
            tenant_id=self._authorized.tenant,
            artifact_class=self._authorized.resource,
            name=address,
        )
        differing = tuple(
            field
            for field in ArtifactRef.model_fields
            if not _same_string(getattr(answered, field, None), getattr(own, field))
        )
        if differing:
            raise ReplayReferenceMismatch(fields=differing)
        return DeliveryCapability(own, _DELIVERY_TOKEN)


class QueryPinWriter:
    """Persists executed queries' canonical bytes, content-addressed (D-11).

    The :class:`ReplayWriter` precedent applied to the query pins of 15.2-08:
    the record carries the ordered ``content_hash`` tuple (dimension 5,
    ``graph_query_sequence``); this writer lands the **full canonical bytes**
    of each pinned :class:`~ccf.graph.protocols.GraphQuery` in the
    ArtifactStore, keyed by that hash — so an auditor holding a pin resolves
    the literal question from the store without re-running anything, and a
    replay that recomputes the sequence can quote what disagreed. Two
    executions issuing the same question converge on one artifact, because
    the store's addressing is content addressing.

    The store is reached at the serve seam, never from inside the projection
    engine: the engine stays free of persistence collaborators, exactly as it
    holds no replay writer.

    Holds its own ``Authorized[ReplayMint]`` for the query-pin class, minted at
    composition beside the replay writer's (D-IMPL-353 §2 P3): one capability,
    one class, one tenant. There is no ``artifact_class`` and no ``tenant_id``
    parameter anywhere on this type.

    Args:
        authorized: The composition-minted ``ReplayMint`` capability whose
            resource is the query-pin class.
        store: The artifact substrate (CLAUDE.md §7.4) — ordinarily the same
            store the deployment's :class:`ReplayWriter` appends to.
    """

    def __init__(
        self, *, authorized: Authorized[ReplayMint], store: ArtifactStoreProtocol
    ) -> None:
        verify(authorized, kind=ReplayMint, resource=getattr(authorized, "resource", ""))
        self._authorized = authorized
        self._store = store

    @property
    def tenant_id(self) -> str:
        """The one tenant this writer files under — the capability's."""
        return self._authorized.tenant

    @property
    def artifact_class(self) -> str:
        """The query-pin class this writer files under — the capability's resource."""
        return self._authorized.resource

    def write_query_bytes(
        self, *, queries: tuple[GraphQuery, ...]
    ) -> tuple[ArtifactRef, ...]:
        """Persist every query's canonical bytes; return the refs, in order.

        Each query is named by its own ``content_hash`` — the same value the
        record pins — and the store's derived content address equals that
        hash (both are ``sha256(canonical_bytes(...))``), so either the name
        lane or the address lane resolves a pin to its bytes.

        **The store's answer is held to the query written** (``D-IMPL-378``
        decision 5, extending 5 (a)): every field of the reference ``put``
        returns for a query must be the query's own — its content address,
        the URI naming it under this writer's tenant and class with that
        address as name and version, and the tenant, class and name — or no
        reference is returned. Each reference returned is the one the writer
        derived from its query, which the store's answer equals field for
        field. What is not checked: the bytes the store holds (see
        :class:`QueryPinReferenceMismatch`).

        Raises:
            ReplayTenantMismatch: a query names a tenant other than the
                capability's. Raised before the store is touched.
            QueryPinReferenceMismatch: the store's answer for a query is not
                that query's own reference. Raised after the store returns for
                that query and before any reference is returned.
            Exception: whatever the store raises, deliberately uncaught — the
                :meth:`ReplayWriter.write_replay_record` posture: a failure to
                persist a pinned question must fail the serve, because a
                record whose pins cannot be resolved is the T-15.2-28
                repudiation threat made durable.
        """
        for query in queries:
            if query.tenant_id != self._authorized.tenant:
                raise ReplayTenantMismatch(
                    f"a pinned query names tenant {query.tenant_id!r} but this"
                    f" writer's capability is for {self._authorized.tenant!r}"
                    " (D-IMPL-353 §1.3)"
                )
        written: list[ArtifactRef] = []
        for query in queries:
            address = content_hash(query)
            answered = self._store.put(
                self._authorized,
                DerivedWrite(
                    artifact_class=self._authorized.resource,
                    name=address,
                    artifact=query,
                ),
            )
            # Decision 5 (a) (`D-IMPL-378`), at this writer by decision 5: the
            # reference of the query actually written, derived here (`D-IMPL-26`:
            # the version IS the address), and the store's answer held to it
            # field for field, as exact strings.
            own = ArtifactRef(
                content_address=address,
                uri=artifact_uri(
                    tenant_id=self._authorized.tenant,
                    artifact_class=self._authorized.resource,
                    name=address,
                    artifact_version=address,
                ),
                tenant_id=self._authorized.tenant,
                artifact_class=self._authorized.resource,
                name=address,
            )
            differing = tuple(
                field
                for field in ArtifactRef.model_fields
                if not _same_string(getattr(answered, field, None), getattr(own, field))
            )
            if differing:
                raise QueryPinReferenceMismatch(fields=differing)
            written.append(own)
        return tuple(written)


def serve(
    *,
    product: ServableProduct,
    record: DecisionReplayRecord,
    replay_writer: ReplayWriter,
    query_pin_writer: QueryPinWriter | None = None,
    executed_queries: tuple[GraphQuery, ...] = (),
) -> ServedProduct:
    """Record the decision, then deliver the product — in that order, always.

    **A refusal is recorded by the same writer, through**
    :func:`record_refusal`, **and delivered as a shell by the resolver rather
    than as a product** (``24.6-07``, ``D-IMPL-253`` Q13). The ordering
    sentence above is the whole seam and it does not weaken for a governed
    "no": the append happens first there too, and a shell that left the
    resolver before its record was appended would be a decision with no audit.
    What differs is only that there is nothing to deliver — so that path calls
    the writer directly and never reaches
    :meth:`DeliveryCapability.deliver`, which is typed to a
    :class:`~ccf.products.gates.ServableProduct` a refusal does not have.

    **The 15.2-08 pin ordering** (D-11, T-15.2-28): when the seam is handed
    the executed queries, their canonical bytes are persisted **before** the
    replay-record append, so no moment exists at which an appended record
    pins bytes the store does not hold — a recorded pin never dangles. The
    consistency of the two is checked first: the record's
    ``graph_query_sequence`` must equal the ``content_hash`` tuple of the
    queries handed in, in order, or nothing is persisted at all.

    The two new parameters default to the pre-15.2-08 posture — no pin
    writer, no queries — so every existing call site is byte-for-byte
    unchanged. A deployment on the governed path passes
    ``execution.executed_queries`` and a :class:`QueryPinWriter` constructed
    beside its :class:`ReplayWriter`.

    Raises:
        ProductRecordMismatch: the record's
            ``product_content_address`` and the ``content_hash`` of the
            product handed in disagree — the record does not describe what is
            about to leave (``D-IMPL-279``). Checked FIRST and raised before
            any store write.
        QueryPinMismatch: the record's pinned sequence and the handed-in
            queries disagree, or queries were handed in with no writer to
            persist them, or a configured writer was given a record that pins
            queries nobody handed in. Raised before any store write.
    """
    # `D-IMPL-337`. A governed boundary: `product` is externally substitutable
    # and everything below relies on the authority that only the gates
    # establish. Verified BEFORE the record is appended — a record written for
    # a value with no gate provenance would be an audit trail for a decision
    # the fabric never made.
    product = verify_gate_provenance(product)

    # R-01 (`D-IMPL-279`): the record must be ABOUT the product being served.
    # First, because a mis-wired resolver is a defect and there is no reason to
    # check anything else about a record that does not describe what is
    # leaving. Both operands are already here; only the comparison was missing.
    recorded_address = record.content_generation_path.product_content_address
    served_address = content_hash(product.product)
    if recorded_address != served_address:
        raise ProductRecordMismatch(
            f"the replay record describes the product at {recorded_address!r}"
            f" but the serve seam was handed the product at {served_address!r};"
            " a record that does not describe what left is an audit trail an"
            " examiner cannot use, so the two must agree before anything is"
            " persisted (`D-IMPL-279`, narrowing `D-IMPL-278` row 1)"
        )
    derived_pins = tuple(content_hash(query) for query in executed_queries)
    pinned = record.content_generation_path.graph_query_sequence
    if executed_queries and query_pin_writer is None:
        raise QueryPinMismatch(
            f"{len(executed_queries)} executed quer(y/ies) were handed to the "
            "serve seam with no QueryPinWriter to persist them; a record "
            "appended without its query bytes is a pin an auditor cannot "
            "resolve (D-11, T-15.2-28)"
        )
    if query_pin_writer is not None and derived_pins != pinned:
        raise QueryPinMismatch(
            f"the record pins {list(pinned)!r} but the serve seam was handed "
            f"queries hashing to {list(derived_pins)!r}; the pinned sequence "
            "records what ran, so the two must agree element-for-element "
            "(D-11, `GQ-20`)"
        )
    if query_pin_writer is not None and executed_queries:
        # Bytes first, record second: the append below must never publish a
        # pin the store cannot already resolve (T-15.2-28).
        query_pin_writer.write_query_bytes(queries=executed_queries)
    return replay_writer.write_replay_record(record=record).deliver(product)


def record_refusal(
    *, record: DecisionReplayRecord, replay_writer: ReplayWriter
) -> ArtifactRef:
    """Append a refusal's decision record; return where it landed (24.6-07).

    **SDK-defined** (CLAUDE.md §11); the ruling of record is ``D-IMPL-253``
    Q13 (Dave: *"Refusal is itself a decision and deserves the same
    five-dimensional replay model. Do not create second-class replay."*) with
    ``D-IMPL-256``'s invariant: *"Every governed determination that crosses a
    CCF delivery boundary — fulfilled or refused, tool or resource, authorized
    or denied — must reach the replay writer before the response is
    released."*

    :func:`serve`'s half for a determination that produced no product. It is
    the **same** :class:`ReplayWriter`, over the same artifact store, appending
    the same :class:`~ccf.replay.record.DecisionReplayRecord` — which is the
    substance of *"do not create second-class replay"*: a second writer, or a
    second record shape, would be exactly that.

    **Why this returns an** :class:`~ccf.artifacts.protocol.ArtifactRef`
    **rather than a** :class:`DeliveryCapability`. The capability exists
    because a served product must be unreachable without a completed append,
    and it is typed to a :class:`~ccf.products.gates.ServableProduct` for that
    reason. A refusal has none, so there is nothing for a capability to
    authorize; what the caller needs is the **address**, because
    :attr:`~ccf.products.refusal.RefusalEnvelope.replay_reference` is where it
    goes. Minting a capability nobody could spend, in order to look
    symmetrical, would be ceremony — and the ordering property is preserved by
    the same mechanism either way: this function appends, and a store failure
    propagates out of it with no branch reaching a returned shell.

    Args:
        record: The five-dimension record of the refusal, built by
            :func:`~ccf.replay.record.build_replay_record` with the refusal as
            its outcome.
        replay_writer: The deployment's own writer — the same one its served
            path uses, over the same store.

    Returns:
        The reference the append produced. Its
        :attr:`~ccf.artifacts.protocol.ArtifactRef.uri` is what the returned
        shell carries; the **recorded** shell inside the record carries the
        sentinel, because a record cannot contain its own address.

    Raises:
        Exception: whatever the store raises, deliberately uncaught — the
            :meth:`ReplayWriter.write_replay_record` posture: a failure to
            record is a failure to respond, and a governed "no" released
            without its record is the repudiation this module exists to close.
    """
    return replay_writer.write_replay_record(record=record).replay_ref
