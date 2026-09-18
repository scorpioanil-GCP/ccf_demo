"""D-28 — every shipped refusal crosses the seam without flattening.

Spec ``docs/superpowers/specs/2026-08-15-ccf-client-design.md`` Amendment 1 §A;
CLAUDE.md §7.3. The envelope under test is
:mod:`ccf.products.refusal`.

**What these tests enforce, and why each shape was chosen.**

1. **Per kind, one at a time.** Every one of the twenty-two kinds gets its own
   assertion. Deliberately *not* one parameterized assertion over the mapping
   with an ``any()`` inside: a property asserted in aggregate passes when one
   member survives and licenses the rest, which is this project's recurring
   defect class rather than a hypothetical one.

2. **The vocabulary is closed by set equality against a structural walk of the
   tree**, over all three of the ``…Refusal``, ``…Violation`` and ``…Conflict``
   name families (:data:`NAME_FAMILIES`), partitioned by resolved base. Nothing
   enters the vocabulary by name. A refusal type added to ``src/`` and
   translated nowhere fails the build and demands a ruling — it does not ship
   untranslated with the gate green. The third family joined in ``24.6-L-07``
   rather than exempting one member: see :data:`NAME_FAMILIES` for why.

3. **The walk is import-order independent, and that is its whole design
   constraint.** ``type.__subclasses__`` reports only what the interpreter has
   already executed, so its answer depends on which modules the importer
   happened to touch; a gate built on it returns one verdict under a narrow
   ``pytest`` invocation and another under the full suite. The enumeration is
   therefore an :mod:`ast` walk over a source **root taken as a parameter**,
   reading no imports and executing no module. ``__subclasses__`` appears
   exactly once, inside the cross-check that reconciles the two answers, and a
   test asserts that placement structurally.

4. **The gate has been watched failing.** Six sabotage controls widen or narrow
   a *copy* of the tree in ``tmp_path`` and assert the comparison fails. That
   is why the helper takes a root at all: a check pinned to the real ``src/``
   cannot be sabotaged without editing ``src/``, and a control that edits and
   reverts leaves nothing behind to prove it ever fired.

**What these tests do not enforce.** They do not prove any door emits an
envelope — no door does yet, which is the whole reason the shape is defined
before the doors change. They do not reach a refusal type declared outside
``src/``, nor one produced dynamically by ``type()`` rather than a ``class``
statement, both of which an AST walk cannot see.
"""

from __future__ import annotations

import ast
import builtins
import importlib
import inspect
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from ccf.agents.errors import AssemblyRefusal, AssemblyRefused
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import HASH_TRANSPARENT_KEY, canonical_bytes

from ccf.products.refusal import (
    NON_PRODUCT_REFUSALS,
    NON_VALUE_VIOLATIONS,
    NO_REPLAY_REFERENCE,
    REFUSAL_KINDS,
    RefusalEnvelope,
    RefusalEvidence,
    RequestIdentity,
    ResourceRequestIdentity,
    SubjectUnavailableRefusal,
    envelope_for,
)
from ccf.graph.protocols import NO_STORE_SNAPSHOT_PIN
from ccf.graph.product_source import GATE_PRODUCT_MOUNT, ProductMountRefusal
from ccf.peering.admission import (
    AdmissionRefusal,
    ContractRefusal,
    LineageContinuityRefusal,
    PayloadTooLargeRefusal,
    PolicyBindingRefusal,
    SignatureRefusal,
)
from ccf.products.composite import GATE_CHILD_ADMISSION, ChildAdmissionRefusal
from ccf.products.composition import MixingRefusal
from ccf.products.constraints import ConstraintRefusal, PolicyResolutionConflict
from ccf.products.contract import ProductLineage
from ccf.products.provenance import ParameterBound, ProvenanceSource
from ccf.products.gates import (
    GATE_DECLARED_OBLIGATIONS,
    GATE_EMPTY_OPERATOR,
    GATE_LINEAGE_ATTRIBUTABILITY,
    GATE_LINEAGE_EQUALITY,
    GATE_SOURCE_ATTESTATION,
    GATE_DEPENDENCY_INVALIDATION,
    GATE_TTL_BOUNDS,
    AttestationRefusal,
    DeclaredObligationRefusal,
    EmptyOperatorRefusal,
    GateRefusal,
    LineageAttributionRefusal,
    LineageMismatchRefusal,
    ProductInvariantRefusal,
    ToleranceExceededRefusal,
    DependencyInvalidationRefusal,
    TTLRefusal,
)
from ccf.products.payload import PayloadSchemaViolation
from ccf.products.provenance import ProvenanceSource
from ccf.products.request import AnchorAmbiguityRefusal, ProductRequestViolation

#: The real source root the shipped assertions read. The sabotage controls read
#: a copy of it under ``tmp_path`` instead — never this one.
SRC_ROOT = Path(__file__).resolve().parents[2] / "src"

#: This module's own source, parsed once. Several assertions are about the
#: *shape of this file* rather than about the tree, and reading them from the
#: file is what keeps them true after an edit.
SELF_SOURCE = Path(__file__).read_text(encoding="utf-8")

_INSTANT = datetime(2026, 8, 15, 12, 0, 0, tzinfo=UTC)
_LATER = datetime(2026, 8, 16, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def request_identity() -> RequestIdentity:
    """A question, as it stood before assembly. Shape only; no domain meaning."""
    return RequestIdentity(
        product_id="test.product",
        product_version="1.0.0",
        parameters={"subject-slot": "s-1"},
        temporal_boundary=_INSTANT,
    )


@pytest.fixture
def partial_lineage() -> ProductLineage:
    """The partial lineage that exists once a candidate contract does."""
    return ProductLineage(
        operators_invoked=frozenset({"op-a"}),
        policy_bundle_versions=frozenset({"bundle-1"}),
        graph_snapshot_at=_INSTANT,
    )


# --- one assertion per kind -------------------------------------------------
#
# One function per kind, each naming its kind. The coverage test below derives
# the expected names from REFUSAL_KINDS and reads the actual ones out of this
# file's own AST, so a kind added to the mapping with no test here fails. The
# count is deliberately not restated here: it would be a second, unchecked copy
# of a number the mapping already holds.


def test_envelope_for_product_request_violation(
    request_identity: RequestIdentity,
) -> None:
    """Pre-assembly: the reason is the violation's own token, lineage is None."""
    refusal = ProductRequestViolation(
        reason="type-mismatch",
        key="amount",
        declared_type="integer",
        presented_type="str",
        declared_keys=frozenset({"amount", "currency"}),
        presented_keys=frozenset({"amount"}),
        detail="the request presented a str where the contract declares integer",
    )
    envelope = envelope_for(refusal, request=request_identity)

    assert envelope.kind == REFUSAL_KINDS[ProductRequestViolation]
    assert envelope.reason == "type-mismatch"
    assert envelope.key == "amount"
    assert envelope.detail == refusal.detail
    # Every typed field survives except the three promoted above. `reason` and
    # `key` were promoted; `detail` was promoted; four conformity members
    # remain, plus the override attempts a refused resolution carries
    # (`D-IMPL-260` P-I) — rendered even when empty, so field presence is one
    # shape for every violation of this kind.
    assert set(envelope.fields) == {
        "declared_type",
        "presented_type",
        "declared_keys",
        "presented_keys",
        "overrides",
    }
    assert envelope.fields["overrides"] == "[]"
    assert envelope.fields["declared_type"] == '"integer"'
    assert envelope.fields["presented_type"] == '"str"'
    assert envelope.fields["declared_keys"] == '["amount","currency"]'
    assert envelope.fields["presented_keys"] == '["amount"]'
    # D-09: refuse_request runs before the graph is touched, so there is no
    # pre-assembly lineage — and the envelope says so rather than omitting it.
    assert envelope.pre_assembly_lineage is None
    assert envelope.request == request_identity


def test_envelope_for_payload_schema_violation(
    request_identity: RequestIdentity, partial_lineage: ProductLineage
) -> None:
    """Post-assembly: a candidate contract exists, so a partial lineage does."""
    refusal = PayloadSchemaViolation(
        reason="undeclared-key",
        key="extras.note",
        declared_type=None,
        presented_type="str",
        declared_keys=frozenset({"total"}),
        presented_keys=frozenset({"total", "note"}),
        detail="the payload presented a key the schema does not declare",
    )
    envelope = envelope_for(
        refusal, request=request_identity, pre_assembly_lineage=partial_lineage
    )

    assert envelope.kind == REFUSAL_KINDS[PayloadSchemaViolation]
    assert envelope.reason == "undeclared-key"
    assert envelope.key == "extras.note"
    assert envelope.detail == refusal.detail
    assert envelope.fields["declared_type"] == "null"
    assert envelope.fields["presented_type"] == '"str"'
    # The distinction D-09 needs, carried rather than flattened.
    assert envelope.pre_assembly_lineage == partial_lineage


def test_envelope_for_gate_refusal(request_identity: RequestIdentity) -> None:
    """The family base: gate becomes the reason, and nothing else is declared."""
    refusal = GateRefusal(gate=GATE_LINEAGE_EQUALITY, detail="declared set differs")
    envelope = envelope_for(refusal, request=request_identity)

    assert envelope.kind == REFUSAL_KINDS[GateRefusal]
    assert envelope.reason == GATE_LINEAGE_EQUALITY
    assert envelope.key is None
    assert envelope.detail == "declared set differs"
    assert envelope.fields == {}


def test_envelope_for_empty_operator_refusal(
    request_identity: RequestIdentity,
) -> None:
    """Gate 1 adds no field of its own, and is still distinguishable by kind."""
    refusal = EmptyOperatorRefusal(
        gate=GATE_EMPTY_OPERATOR, detail="operators_invoked was empty"
    )
    envelope = envelope_for(refusal, request=request_identity)

    assert envelope.kind == REFUSAL_KINDS[EmptyOperatorRefusal]
    assert envelope.kind != REFUSAL_KINDS[GateRefusal]
    assert envelope.reason == GATE_EMPTY_OPERATOR
    assert envelope.fields == {}


def test_envelope_for_lineage_mismatch_refusal(
    request_identity: RequestIdentity,
) -> None:
    """Both sides of the failed comparison survive, and stay distinguishable."""
    refusal = LineageMismatchRefusal(
        gate=GATE_LINEAGE_EQUALITY,
        detail="declared and resolved differ",
        declared=frozenset({"op-a"}),
        resolved=frozenset({"op-b"}),
    )
    envelope = envelope_for(refusal, request=request_identity)

    assert envelope.kind == REFUSAL_KINDS[LineageMismatchRefusal]
    assert set(envelope.fields) == {"declared", "resolved"}
    assert envelope.fields["declared"] == '["op-a"]'
    assert envelope.fields["resolved"] == '["op-b"]'
    # Neither is dropped and neither is collapsed into the other.
    assert envelope.fields["declared"] != envelope.fields["resolved"]


def test_envelope_for_lineage_attribution_refusal(
    request_identity: RequestIdentity,
) -> None:
    """The federated gate's three fields all cross."""
    refusal = LineageAttributionRefusal(
        gate=GATE_LINEAGE_ATTRIBUTABILITY,
        detail="the gated bytes are not the signed bytes",
        declared=frozenset({"op-a"}),
        attested_address="addr-attested",
        candidate_address="addr-candidate",
    )
    envelope = envelope_for(refusal, request=request_identity)

    assert envelope.kind == REFUSAL_KINDS[LineageAttributionRefusal]
    assert set(envelope.fields) == {
        "declared",
        "attested_address",
        "candidate_address",
    }
    assert envelope.fields["attested_address"] == '"addr-attested"'
    assert envelope.fields["candidate_address"] == '"addr-candidate"'


def test_envelope_for_dependency_invalidation_refusal(
    request_identity: RequestIdentity
) -> None:
    """`D-IMPL-334`: the entity, both instants and the cause cross intact.

    All four are FABRIC state — the external statement discloses none of them
    (`PERMITTED_AT_MINIMAL` is empty for this kind) — and this test is about
    the internal form, where a refusal must carry enough for an auditor to
    answer *which* evidence moved.
    """
    refusal = DependencyInvalidationRefusal(
        gate=GATE_DEPENDENCY_INVALIDATION,
        detail="an entity this product touched was superseded after its snapshot",
        entity_uri="entity://fixture-obligor",
        invalidated_from=_LATER,
        graph_snapshot_at=_INSTANT,
        cause="claim-fixture-0001",
    )
    envelope = envelope_for(refusal, request=request_identity)

    assert envelope.kind == REFUSAL_KINDS[DependencyInvalidationRefusal]
    assert envelope.reason == GATE_DEPENDENCY_INVALIDATION
    assert set(envelope.fields) == {
        "entity_uri", "invalidated_from", "graph_snapshot_at", "cause",
    }
    # The two instants render RFC3339 UTC at fixed precision, never a repr,
    # and the boundary is the LATER of the two — which is the whole reason
    # this refusal exists.
    assert envelope.fields["invalidated_from"] == '"2026-08-16T12:00:00.000000Z"'
    assert envelope.fields["graph_snapshot_at"] == '"2026-08-15T12:00:00.000000Z"'
    assert envelope.fields["entity_uri"] == '"entity://fixture-obligor"'
    assert envelope.fields["cause"] == '"claim-fixture-0001"'


def test_envelope_for_composite_child_refusal(
    request_identity: RequestIdentity,
) -> None:
    """`D-IMPL-336`: a child refusal crosses with its cause AND its identity.

    The second half is the ruling Amendment 2 added: **a product produced but
    rejected at admission is not a product that never existed.** Its known
    content address is retained on the refusal, so an audit can tell a
    rejection apart from an absence — which is why `child_content_address` is
    asserted present here rather than merely permitted.
    """
    refusal = ChildAdmissionRefusal(
        gate=GATE_CHILD_ADMISSION,
        detail="child answered as of a different reconstruction instant",
        product_class="CorporateFamilyTree",
        reason="as-of-mismatch",
        reported_content_address="a" * 64,
        verified_content_address="a" * 64,
    )
    envelope = envelope_for(refusal, request=request_identity)

    assert envelope.kind == REFUSAL_KINDS[ChildAdmissionRefusal]
    assert envelope.kind == "composite-child-refusal"
    assert envelope.reason == GATE_CHILD_ADMISSION
    # `D-IMPL-340`: the five producer-relationship members ride on every
    # child refusal — `null` on a leg that has no producer — because a field
    # added to a refusal type appears in the envelope by design
    # (`envelope_for`'s own rule), and a refused `mcp_product` row must name
    # the exact producer it was refused under.
    assert set(envelope.fields) == {
        "product_class",
        "reason",
        "reported_content_address",
        "verified_content_address",
        "producer_id",
        "producer_tenant",
        "producer_registration_address",
        "producer_server",
        "question_address",
        # `D-IMPL-342`: the refusing producer's own evidence and the retained
        # question's reference — rendered like every other member, "null" when
        # the branch had none, so a composite refusal recorded after 342 says
        # what its producer said (and hashes differently from one before it).
        "producer_refusal_kind",
        "producer_refusal_reason",
        "producer_refusal_key",
        "producer_replay_ref",
        "question_ref",
    }
    assert envelope.fields["producer_id"] == "null"
    assert envelope.fields["producer_refusal_reason"] == "null"
    assert envelope.fields["reason"] == '"as-of-mismatch"'
    # F9: the two addresses cross SEPARATELY and labelled. On an
    # address-mismatch they differ, and the record must never present the
    # value the gate disproved as the rejected product's identity.
    assert envelope.fields["reported_content_address"] == f'"{"a" * 64}"'
    assert envelope.fields["verified_content_address"] == f'"{"a" * 64}"'


def test_a_child_that_never_existed_carries_no_invented_address(
    request_identity: RequestIdentity,
) -> None:
    """The other half of the same ruling: absence invents nothing.

    A requirement no granted skill produces has no product and therefore no
    address. The field is **absent**, not a placeholder — a sentinel address
    would be a fact the record does not have, and would make "nothing was
    produced" indistinguishable from "something was produced and rejected".
    """
    refusal = ChildAdmissionRefusal(
        gate=GATE_CHILD_ADMISSION,
        detail="no in-force grant produces this class",
        product_class="PeerBenchmark",
        reason="no-producing-skill",
    )
    envelope = envelope_for(refusal, request=request_identity)

    assert envelope.fields["reported_content_address"] == "null"
    assert envelope.fields["verified_content_address"] == "null"


def test_envelope_for_ttl_refusal(request_identity: RequestIdentity) -> None:
    """Gate 3 carries two instants and a bound; all three cross intact."""
    refusal = TTLRefusal(
        gate=GATE_TTL_BOUNDS,
        detail="expires_at fell outside the permitted window",
        expires_at=_LATER,
        now=_INSTANT,
        max_ttl_seconds=3600,
    )
    envelope = envelope_for(refusal, request=request_identity)

    assert envelope.kind == REFUSAL_KINDS[TTLRefusal]
    assert envelope.reason == GATE_TTL_BOUNDS
    assert set(envelope.fields) == {"expires_at", "now", "max_ttl_seconds"}
    # Instants render RFC3339 UTC at fixed precision, never as a repr.
    assert envelope.fields["expires_at"] == '"2026-08-16T12:00:00.000000Z"'
    assert envelope.fields["now"] == '"2026-08-15T12:00:00.000000Z"'
    assert envelope.fields["max_ttl_seconds"] == "3600"


def test_envelope_for_declared_obligation_refusal(
    request_identity: RequestIdentity,
) -> None:
    """The ONE structural declared-obligations gate names which obligation and both sides.

    ``24.5-L-26`` (``D-IMPL-237``). The gate token is the promoted ``reason``,
    the three fields the kind declares cross intact, and the kind is the one
    the HTTP door maps to ``409``.

    **Re-derived at ``24.6-04``, and it can no longer be written the old way.**
    The obligation was ``debt-ceiling`` here until the debt half retired
    (``D-IMPL-251`` C1=A); ``obligation`` is now a single-member ``Literal``
    and the control below proves it — the retired token is not merely unused,
    it is unconstructible.
    """
    refusal = DeclaredObligationRefusal(
        gate=GATE_DECLARED_OBLIGATIONS,
        detail="a payload member the class obliges is absent",
        obligation="lineage-inputs",
        declared="inputs",
        observed="absent",
    )
    envelope = envelope_for(refusal, request=request_identity)

    assert envelope.kind == REFUSAL_KINDS[DeclaredObligationRefusal]
    assert envelope.kind == "declared-obligation-refusal"
    assert envelope.reason == GATE_DECLARED_OBLIGATIONS == "declared-obligations"
    assert envelope.key is None
    assert set(envelope.fields) == {"obligation", "declared", "observed"}
    assert envelope.fields["obligation"] == '"lineage-inputs"'
    assert envelope.fields["declared"] == '"inputs"'
    assert envelope.fields["observed"] == '"absent"'

    # The retired half, as a control: the token the debt path carried is not
    # a member of the vocabulary any more, so a caller cannot file one.
    with pytest.raises(ValidationError):
        DeclaredObligationRefusal(
            gate=GATE_DECLARED_OBLIGATIONS,
            detail="the retired half",
            obligation="debt-ceiling",  # type: ignore[arg-type]
            declared="0.5",
            observed="0.7",
        )


def test_envelope_for_product_invariant_refusal(
    request_identity: RequestIdentity,
) -> None:
    """The seventh sibling names WHICH gate refused, and at which version.

    ``24.10-02`` / ``R-11``; ``D-IMPL-282`` option 1a with ``D-IMPL-224``.
    The gate a DEPLOYMENT supplied refused, and the two facts an examiner
    needs — which declared invariant, at which declared lane — cross the
    envelope intact: the declared id is promoted as the ``reason`` (the
    ``GateRefusal`` branch prefers ``gate`` over anything else), and the lane
    rides in ``fields``.

    The kind is distinct from every universal gate's, which is the whole point
    of ``D-10``: a runtime product-gate failure is distinguishable in
    replay and audit from the SDK's own three-plus-one-plus-one gates.
    """
    refusal = ProductInvariantRefusal(
        gate="fixture.reconciliation-guard",
        gate_version="1.0.0",
        detail="adjusted committed 9 exceeds gross 8",
    )
    envelope = envelope_for(refusal, request=request_identity)

    assert envelope.kind == REFUSAL_KINDS[ProductInvariantRefusal]
    assert envelope.kind == "product-invariant-refusal"
    assert envelope.reason == "fixture.reconciliation-guard"
    assert envelope.key is None
    assert set(envelope.fields) == {"gate_version"}
    assert envelope.fields["gate_version"] == '"1.0.0"'
    assert envelope.detail == "adjusted committed 9 exceeds gross 8"

    # The kind is its OWN kind, not the family's: a reader dispatching on the
    # token must not receive the base gate's answer for a deployment gate.
    assert envelope.kind != REFUSAL_KINDS[GateRefusal]


def test_envelope_for_tolerance_exceeded(
    request_identity: RequestIdentity,
) -> None:
    """The withheld-fulfillment shell: no gate token, the kind IS the reason.

    ``24.6-L-05``, ``D-IMPL-251`` C2=B, ``D-IMPL-253`` Q10. Three things this
    asserts that no other per-kind test can:

    * the promotion fallback — the type declares neither ``gate`` nor
      ``reason``, so :func:`envelope_for` reports the KIND as the reason, and
      that branch is reached by nothing else in the vocabulary today;
    * the authority survives the crossing, because *"preserve which authority
      established the tolerance"* is the ruling and a shell that lost it would
      be a well-formed envelope carrying the wrong answer;
    * the shell never says the Debt was invalid.
    """
    refusal = ToleranceExceededRefusal(
        authority="caller",
        source=ProvenanceSource(
            kind="request", identity="request-fixture", version=None
        ),
        tolerance=Decimal("0.20"),
        observed=Decimal("0.31"),
        breakdown=None,
        detail=(
            "the product was constructible; fulfillment was withheld because"
            " an applicable declared tolerance (caller) of 0.20 was exceeded"
            " by the observed Context Debt 0.31"
        ),
    )
    envelope = envelope_for(refusal, request=request_identity)

    assert envelope.kind == REFUSAL_KINDS[ToleranceExceededRefusal]
    assert envelope.kind == "tolerance-exceeded"
    # No `gate` and no `reason` on the type: the kind is the most specific
    # true thing that can be said about why, and `envelope_for` says it.
    assert envelope.reason == envelope.kind
    assert not issubclass(ToleranceExceededRefusal, GateRefusal)
    assert envelope.key is None
    assert set(envelope.fields) == {
        "authority",
        "source",
        "tolerance",
        "observed",
        "breakdown",
    }
    assert envelope.fields["authority"] == '"caller"'
    assert envelope.fields["tolerance"] == '"0.20"'
    assert envelope.fields["observed"] == '"0.31"'
    assert "invalid" not in envelope.detail
    assert "fulfillment was withheld" in envelope.detail


def test_envelope_for_attestation_refusal(
    request_identity: RequestIdentity,
) -> None:
    """The additive gate names its failing dimension and both mode sides."""
    refusal = AttestationRefusal(
        gate=GATE_SOURCE_ATTESTATION,
        detail="the source's mode is not accepted on this dimension",
        failing_dimension="lineage",
        source_mode="mode-declared",
        accepted_modes=frozenset({"mode-x", "mode-y"}),
    )
    envelope = envelope_for(refusal, request=request_identity)

    assert envelope.kind == REFUSAL_KINDS[AttestationRefusal]
    assert set(envelope.fields) == {
        "failing_dimension",
        "source_mode",
        "accepted_modes",
    }
    assert envelope.fields["failing_dimension"] == '"lineage"'
    assert envelope.fields["accepted_modes"] == '["mode-x","mode-y"]'


def test_envelope_for_admission_refusal(request_identity: RequestIdentity) -> None:
    """The peering base is in the vocabulary, not folded into its parent."""
    refusal = AdmissionRefusal(
        gate="peering-admission",
        detail="the inbound product was refused",
        tenant_id="t-1",
        peer_id="peer-1",
    )
    envelope = envelope_for(refusal, request=request_identity)

    assert envelope.kind == REFUSAL_KINDS[AdmissionRefusal]
    assert envelope.kind != REFUSAL_KINDS[GateRefusal]
    assert set(envelope.fields) == {"tenant_id", "peer_id"}


def test_envelope_for_payload_too_large_refusal(
    request_identity: RequestIdentity,
) -> None:
    """Check 1 keeps both sides of the ceiling comparison, plus the middle pair."""
    refusal = PayloadTooLargeRefusal(
        gate="peering-admission",
        detail="the payload exceeded the tenant ceiling",
        tenant_id="t-1",
        peer_id="peer-1",
        observed_bytes=2048,
        ceiling_bytes=1024,
    )
    envelope = envelope_for(refusal, request=request_identity)

    assert envelope.kind == REFUSAL_KINDS[PayloadTooLargeRefusal]
    assert set(envelope.fields) == {
        "tenant_id",
        "peer_id",
        "observed_bytes",
        "ceiling_bytes",
    }
    assert envelope.fields["observed_bytes"] == "2048"
    assert envelope.fields["ceiling_bytes"] == "1024"


def test_envelope_for_signature_refusal(request_identity: RequestIdentity) -> None:
    """Three inheritance levels, none collapsed.

    This is the case that proves ``fields`` is built from the whole MRO rather
    than from the leaf class's own annotations: the leaf's three fields, the
    middle ``AdmissionRefusal`` pair, and the ``GateRefusal`` base pair (which
    is promoted to ``reason``/``detail`` rather than dropped) must all be
    accounted for.
    """
    refusal = SignatureRefusal(
        gate="peering-admission",
        detail="the envelope did not verify under this peer's keys",
        tenant_id="t-1",
        peer_id="peer-1",
        declared_key_id="key-declared",
        permitted_key_ids=frozenset({"key-p1", "key-p2"}),
        failure="signature-mismatch",
    )
    envelope = envelope_for(refusal, request=request_identity)

    assert envelope.kind == REFUSAL_KINDS[SignatureRefusal]
    # Leaf level.
    assert envelope.fields["declared_key_id"] == '"key-declared"'
    assert envelope.fields["permitted_key_ids"] == '["key-p1","key-p2"]'
    assert envelope.fields["failure"] == '"signature-mismatch"'
    # Middle level — the level a leaf-annotations-only read would lose.
    assert envelope.fields["tenant_id"] == '"t-1"'
    assert envelope.fields["peer_id"] == '"peer-1"'
    # Base level, promoted rather than dropped.
    assert envelope.reason == "peering-admission"
    assert envelope.detail == refusal.detail
    # Exactly the five unpromoted fields — no more, and nothing invented.
    assert set(envelope.fields) == {
        "tenant_id",
        "peer_id",
        "declared_key_id",
        "permitted_key_ids",
        "failure",
    }


def test_envelope_for_contract_refusal(request_identity: RequestIdentity) -> None:
    """A nullable field crosses as an explicit null, not as an absence."""
    refusal = ContractRefusal(
        gate="peering-admission",
        detail="the bytes are not a product this fabric can accept",
        tenant_id="t-1",
        peer_id="peer-1",
        schema_name=None,
        violation="extra-fields-forbidden",
    )
    envelope = envelope_for(refusal, request=request_identity)

    assert envelope.kind == REFUSAL_KINDS[ContractRefusal]
    assert "schema_name" in envelope.fields
    assert envelope.fields["schema_name"] == "null"
    assert envelope.fields["violation"] == '"extra-fields-forbidden"'


def test_envelope_for_policy_binding_refusal(
    request_identity: RequestIdentity,
) -> None:
    """Both sides of the entitlement comparison survive and stay separable."""
    refusal = PolicyBindingRefusal(
        gate="peering-admission",
        detail="the peer asserted something outside its entitlements",
        tenant_id="t-1",
        peer_id="peer-1",
        assertion="schema",
        asserted=frozenset({"claimed-a"}),
        permitted=frozenset({"allowed-b"}),
    )
    envelope = envelope_for(refusal, request=request_identity)

    assert envelope.kind == REFUSAL_KINDS[PolicyBindingRefusal]
    assert envelope.fields["asserted"] == '["claimed-a"]'
    assert envelope.fields["permitted"] == '["allowed-b"]'
    assert envelope.fields["asserted"] != envelope.fields["permitted"]


def test_envelope_for_lineage_continuity_refusal(
    request_identity: RequestIdentity,
) -> None:
    """Three lineage sets cross, including ``merged``.

    ``merged`` is the field the plan's inventory table omitted; reflection
    carries it anyway, which is the point of reflecting rather than
    transcribing.
    """
    refusal = LineageContinuityRefusal(
        gate="peering-admission",
        detail="the merged lineage lost an entry it must have kept",
        tenant_id="t-1",
        peer_id="peer-1",
        producer=frozenset({"op-p"}),
        consumer=frozenset({"op-c"}),
        merged=frozenset({"op-c"}),
    )
    envelope = envelope_for(refusal, request=request_identity)

    assert envelope.kind == REFUSAL_KINDS[LineageContinuityRefusal]
    assert set(envelope.fields) == {
        "tenant_id",
        "peer_id",
        "producer",
        "consumer",
        "merged",
    }
    assert envelope.fields["producer"] == '["op-p"]'


def test_envelope_for_product_mount_refusal(
    request_identity: RequestIdentity,
) -> None:
    """The mount refusal keeps its own name, and its own ``reason`` field too.

    It is the one kind declaring both a ``gate`` and a ``reason``. The gate
    wins the promotion — that is what makes a mount refusal read like every
    other gate refusal — and its own ``reason`` stays in ``fields`` rather than
    being overwritten, because dropping it would be exactly the flattening the
    envelope exists to prevent.
    """
    refusal = ProductMountRefusal(
        gate=GATE_PRODUCT_MOUNT,
        detail="the admitted product carries no answerable graph state",
        tenant_id="t-1",
        schema_name="test.product",
        reason="missing-key",
    )
    envelope = envelope_for(refusal, request=request_identity)

    assert envelope.kind == REFUSAL_KINDS[ProductMountRefusal]
    # Not a generic gate refusal.
    assert envelope.kind != REFUSAL_KINDS[GateRefusal]
    assert envelope.reason == GATE_PRODUCT_MOUNT
    assert envelope.fields["reason"] == '"missing-key"'
    assert set(envelope.fields) == {"tenant_id", "schema_name", "reason"}


def test_envelope_for_mixing_refusal(request_identity: RequestIdentity) -> None:
    """The assembly-time rule: five own fields, and no gate to promote.

    ``MixingRefusal`` derives from ``CCFContract``, not from ``GateRefusal`` —
    D-IMPL-31's rule is not a fourth gate. It declares no ``gate`` and no
    ``reason``, so ``reason`` falls back to the kind token, which is the third
    promotion rule and the only kind that exercises it.
    """
    refusal = MixingRefusal(
        constituent_id="c-1",
        signal_type="signal-a",
        constituent_expires_at=_LATER,
        evaluated_at=_INSTANT,
        floor_seconds=600,
        detail="a load-bearing constituent breached its declared floor",
    )
    envelope = envelope_for(refusal, request=request_identity)

    assert envelope.kind == REFUSAL_KINDS[MixingRefusal]
    assert envelope.reason == REFUSAL_KINDS[MixingRefusal]
    assert envelope.key is None
    assert set(envelope.fields) == {
        "constituent_id",
        "signal_type",
        "constituent_expires_at",
        "evaluated_at",
        "floor_seconds",
    }
    assert envelope.fields["floor_seconds"] == "600"
    assert envelope.fields["constituent_expires_at"] == '"2026-08-16T12:00:00.000000Z"'


def test_envelope_for_assembly_refusal(request_identity: RequestIdentity) -> None:
    """``24.5-L-11``: the assembler's own refusal, as a value, and as the raise converted.

    Two own fields and both are promoted, so ``fields`` is empty — which is
    asserted as an equality rather than left implied, because an empty
    ``fields`` is the positive statement *nothing was flattened out*, not the
    absence of a check. The second half is the conversion: an assembler that
    caught its own :class:`AssemblyRefused` and returned ``as_refusal()``
    envelopes **identically** to one that returned the value to begin with,
    field for field, so a consumer cannot tell the two routes apart and does
    not need to.
    """
    refusal = AssemblyRefusal(
        reason="assembly-refused",
        detail="this tier does not serve the question as asked",
    )
    envelope = envelope_for(refusal, request=request_identity)

    assert envelope.kind == REFUSAL_KINDS[AssemblyRefusal]
    assert envelope.kind == "assembly-refusal"
    assert envelope.reason == "assembly-refused"
    assert envelope.key is None
    assert envelope.detail == refusal.detail
    assert envelope.fields == {}
    assert envelope.pre_assembly_lineage is None

    converted = AssemblyRefused(
        "this tier does not serve the question as asked"
    ).as_refusal()
    assert isinstance(converted, AssemblyRefusal)
    assert converted == refusal
    assert envelope_for(converted, request=request_identity) == envelope


def test_envelope_for_anchor_ambiguity_refusal(
    request_identity: RequestIdentity, partial_lineage: ProductLineage
) -> None:
    """``24.5-L-16``: an anchor that answered twice, carried by name, pre-assembly.

    No ``reason`` and no ``key`` are declared, so ``reason`` falls back to the
    kind token and ``key`` is ``None``; ``anchor`` and ``candidates`` are the
    promoted-nothing remainder and cross in ``fields`` by name, the candidate
    set rendered sorted. And it is a pre-assembly kind: a lineage offered
    with it is refused exactly as one offered with a
    :class:`ProductRequestViolation` is, with the type named in the message.
    """
    refusal = AnchorAmbiguityRefusal(
        anchor="lei:shared",
        candidates=frozenset({"urn:entity:b", "urn:entity:a"}),
        detail="the anchor resolved to two entities; which one is the product's ruling",
    )
    envelope = envelope_for(refusal, request=request_identity)

    assert envelope.kind == REFUSAL_KINDS[AnchorAmbiguityRefusal]
    assert envelope.kind == "anchor-ambiguity-refusal"
    assert envelope.reason == "anchor-ambiguity-refusal"
    assert envelope.key is None
    assert envelope.detail == refusal.detail
    assert set(envelope.fields) == {"anchor", "candidates"}
    assert envelope.fields["anchor"] == '"lei:shared"'
    assert envelope.fields["candidates"] == '["urn:entity:a","urn:entity:b"]'
    assert envelope.pre_assembly_lineage is None

    with pytest.raises(ValueError) as caught:
        envelope_for(
            refusal, request=request_identity, pre_assembly_lineage=partial_lineage
        )
    assert "AnchorAmbiguityRefusal" in str(caught.value)


def test_envelope_for_subject_unavailable(
    request_identity: RequestIdentity, partial_lineage: ProductLineage
) -> None:
    """``24.6-L-21``: the ONE outcome two different causes share.

    ``D-IMPL-253`` Q27 with amendment 2 (4). The type declares no ``reason``
    and no ``key``, so ``reason`` falls back to the kind token — which is what
    makes the two causes report the same reason on the wire before disclosure
    is even consulted. ``cause`` and ``error_code`` are the promoted-nothing
    remainder and cross in ``fields`` by name; **no ``subject`` field exists**,
    because naming the subject is itself the leak the kind exists to close.

    And it is a pre-assembly kind: an unauthorized principal is settled at the
    delivery boundary before any plan exists, so a lineage offered with it is
    refused with the type named.
    """
    refusal = SubjectUnavailableRefusal(
        cause="nonexistent",
        detail="no entity resolved for the anchor this question named",
    )
    envelope = envelope_for(refusal, request=request_identity)

    assert envelope.kind == REFUSAL_KINDS[SubjectUnavailableRefusal]
    assert envelope.kind == "subject-unavailable"
    assert envelope.reason == "subject-unavailable"
    assert envelope.key is None
    assert envelope.detail == refusal.detail
    assert set(envelope.fields) == {"cause", "error_code"}
    assert envelope.fields["cause"] == '"nonexistent"'
    assert envelope.fields["error_code"] == "null"
    assert envelope.pre_assembly_lineage is None

    # The type cannot name a subject, so a disclosure step never has to
    # remember to blank one.
    assert "subject" not in SubjectUnavailableRefusal.model_fields

    # The unauthorized cause crosses through the SAME translation, reporting
    # the same kind, the same reason and the same field KEYS. What differs is
    # only the two values disclosure governs.
    unauthorized = envelope_for(
        SubjectUnavailableRefusal(
            cause="unauthorized",
            detail="this principal may not receive that class",
            error_code="product_class_unentitled",
        ),
        request=request_identity,
    )
    assert unauthorized.kind == envelope.kind
    assert unauthorized.reason == envelope.reason
    assert set(unauthorized.fields) == set(envelope.fields)

    with pytest.raises(ValueError) as caught:
        envelope_for(
            refusal, request=request_identity, pre_assembly_lineage=partial_lineage
        )
    assert "SubjectUnavailableRefusal" in str(caught.value)


# --- properties of the translation itself -----------------------------------


def test_kind_is_load_bearing_in_equality(
    request_identity: RequestIdentity,
) -> None:
    """Two kinds, everything else identical, still unequal.

    ``GateRefusal`` and ``EmptyOperatorRefusal`` are the sharpest available
    pair: the subclass declares no field of its own, so with the same ``gate``
    and the same ``detail`` every envelope member except ``kind`` is equal.
    If the kind were flattened out these two would be indistinguishable, which
    is the failure D-28(a) names.
    """
    shared = {"gate": GATE_EMPTY_OPERATOR, "detail": "identical prose"}
    base = envelope_for(GateRefusal(**shared), request=request_identity)
    leaf = envelope_for(EmptyOperatorRefusal(**shared), request=request_identity)

    assert base.reason == leaf.reason
    assert base.detail == leaf.detail
    assert base.fields == leaf.fields
    assert base.request == leaf.request
    assert base.kind != leaf.kind
    assert base != leaf


def test_envelope_for_raises_on_a_non_refusal(
    request_identity: RequestIdentity,
) -> None:
    """No best-effort envelope for something the vocabulary does not contain."""
    for candidate in ("a string", 42, None, request_identity):
        with pytest.raises(TypeError) as caught:
            envelope_for(candidate, request=request_identity)
        assert type(candidate).__name__ in str(caught.value)


def test_envelope_for_raises_on_a_refusal_subclass_not_in_the_vocabulary(
    request_identity: RequestIdentity,
) -> None:
    """Dispatch is on the exact type, so a subclass is not silently absorbed.

    An ``isinstance`` chain would translate an unknown subclass as its nearest
    known ancestor and report that ancestor's kind — a flattening that no
    assertion elsewhere here would catch, because the envelope would look
    perfectly well-formed.
    """

    class UnregisteredRefusal(GateRefusal):
        pass

    refusal = UnregisteredRefusal(gate=GATE_TTL_BOUNDS, detail="unknown")
    with pytest.raises(TypeError) as caught:
        envelope_for(refusal, request=request_identity)
    assert "UnregisteredRefusal" in str(caught.value)


def test_envelope_for_constraint_refusal(
    request_identity: RequestIdentity,
) -> None:
    """A technical limit refused BY NAME: the bound crosses with its authority.

    ``24.6-L-07`` (``D-IMPL-253`` Q21). The kind's own ``reason`` is promoted,
    the parameter is promoted as ``key``, and the two remaining declared
    members — the bound and what was actually asked for — cross in ``fields``.
    The bound is what makes the refusal readable: a consumer learns that the
    boundary was the *substrate's* and not a policy's without parsing prose.
    """
    bound = ParameterBound(
        operator="maximum",
        value=Decimal(100),
        authority="technical",
        source=ProvenanceSource(
            kind="capability", identity="test-store", version=None
        ),
    )
    refusal = ConstraintRefusal(
        reason="bound-exceeded",
        key="depth",
        detail="the requested depth exceeds the technical maximum",
        bound=bound,
        requested=101,
    )
    envelope = envelope_for(refusal, request=request_identity)

    assert envelope.kind == REFUSAL_KINDS[ConstraintRefusal]
    assert envelope.kind == "constraint-refusal"
    assert envelope.reason == "bound-exceeded"
    assert envelope.key == "depth"
    # `overrides` rides beside the bound (`D-IMPL-260` P-I), rendered even
    # when nothing was attempted so the shell's shape is one shape.
    assert set(envelope.fields) == {"bound", "requested", "overrides"}
    assert envelope.fields["overrides"] == "[]"
    assert envelope.fields["requested"] == "101"
    assert envelope.fields["bound"] == canonical_bytes(bound).decode("utf-8")
    assert '"authority":"technical"' in envelope.fields["bound"]


def test_a_constraint_refusal_is_offered_no_lineage(
    request_identity: RequestIdentity, partial_lineage: ProductLineage
) -> None:
    """The constraint layer resolves before an operator plan exists.

    Separate from the per-kind test above so neither assertion stands in for
    the other: one is about what crosses, this is about what may not be
    attached.
    """
    refusal = ConstraintRefusal(
        reason="required-absent",
        key="depth",
        detail="an applicable constraint requires this parameter",
        bound=ParameterBound(
            operator="required",
            value=None,
            authority="policy",
            source=ProvenanceSource(
                kind="artifact", identity="constraint-key", version="1.0.0"
            ),
            policy_id="policy-a",
        ),
        requested=None,
    )
    with pytest.raises(ValueError) as caught:
        envelope_for(
            refusal, request=request_identity, pre_assembly_lineage=partial_lineage
        )
    assert "ConstraintRefusal" in str(caught.value)


def test_envelope_for_policy_resolution_conflict(
    request_identity: RequestIdentity,
) -> None:
    """Both sides of an irreconcilable policy set cross, by pin.

    ``24.6-L-07`` (``D-IMPL-253`` Q4: *"If constraints are irreconcilable,
    return a governed shell identifying a policy-resolution conflict"*). The
    shell's whole substance is that neither constraint was dropped, so the
    assertion is on ``conflicting`` carrying both sources with their versions —
    a conflict reporting one side would be priority erasing a hard constraint
    wearing a different name.
    """
    conflicting = (
        ProvenanceSource(kind="artifact", identity="ceiling-key", version="1.0.0"),
        ProvenanceSource(kind="artifact", identity="floor-key", version="2.0.0"),
    )
    refusal = PolicyResolutionConflict(
        key="depth",
        detail="the applicable ceiling lies below the applicable floor",
        conflicting=conflicting,
    )
    envelope = envelope_for(refusal, request=request_identity)

    assert envelope.kind == REFUSAL_KINDS[PolicyResolutionConflict]
    assert envelope.kind == "policy-resolution-conflict"
    assert envelope.reason == "policy-resolution-conflict"
    assert envelope.key == "depth"
    assert set(envelope.fields) == {"conflicting", "overrides"}
    assert envelope.fields["conflicting"] == canonical_bytes(conflicting).decode(
        "utf-8"
    )
    assert '"identity":"ceiling-key"' in envelope.fields["conflicting"]
    assert '"identity":"floor-key"' in envelope.fields["conflicting"]


def test_a_policy_resolution_conflict_is_offered_no_lineage(
    request_identity: RequestIdentity, partial_lineage: ProductLineage
) -> None:
    """A conflict is reached while the effective request is still being built."""
    refusal = PolicyResolutionConflict(
        key="depth",
        detail="the applicable admitted sets share no member",
        conflicting=(
            ProvenanceSource(kind="artifact", identity="a-key", version="1.0.0"),
        ),
    )
    with pytest.raises(ValueError) as caught:
        envelope_for(
            refusal, request=request_identity, pre_assembly_lineage=partial_lineage
        )
    assert "PolicyResolutionConflict" in str(caught.value)


def test_pre_assembly_refusal_rejects_a_lineage(
    request_identity: RequestIdentity, partial_lineage: ProductLineage
) -> None:
    """D-09's split is structural, not conventional.

    A request-conformity verdict is reached before the graph is touched, so a
    lineage offered alongside one is a category error rather than extra
    information — and it is refused instead of being stored and later read as
    evidence that the graph had been consulted.
    """
    refusal = ProductRequestViolation(
        reason="missing-required-parameter",
        key="amount",
        declared_type=None,
        presented_type=None,
        declared_keys=frozenset({"amount"}),
        presented_keys=frozenset(),
        detail="a required parameter was not presented",
    )
    with pytest.raises(ValueError) as caught:
        envelope_for(
            refusal, request=request_identity, pre_assembly_lineage=partial_lineage
        )
    assert "ProductRequestViolation" in str(caught.value)


def test_every_kind_has_its_own_test_function() -> None:
    """Coverage is derived from the mapping, not counted by hand.

    A ``grep -c`` floor over ``def test_`` counts decorators and comments and
    would pass with three kinds untested. This reads ``REFUSAL_KINDS``, derives
    the token each kind's test must name, and collects the actual function
    names out of this file's own AST.

    **The per-kind test is matched by its exact name,
    ``test_envelope_for_<token>``, not by substring** (``24.5-07``, found by
    sabotage). The substring rule this replaced was satisfied for the
    ``assembly-refusal`` kind by :func:`test_pre_assembly_refusal_rejects_a_lineage`
    — a test about a *different* property that happens to carry
    ``assembly_refusal`` inside its name — so a copy of this module with the
    real per-kind test renamed stayed GREEN. The token-vs-token substring
    guard below never looked at the other test names. Every per-kind test in
    this module already followed the exact pattern, so requiring it costs
    nothing and closes the hole structurally.
    """
    tokens = {kind.replace("-", "_") for kind in REFUSAL_KINDS.values()}
    # No token may be a substring of another. With exact-name matching this no
    # longer risks one test covering two kinds; it is kept because it is a
    # property of the wire vocabulary worth holding — two tokens where one
    # contains the other are a consumer's prefix-match bug waiting to happen.
    for token in tokens:
        others = tokens - {token}
        assert not any(token in other for other in others), (
            f"kind token {token!r} is a substring of another token; "
            "a consumer matching on a prefix would conflate them"
        )

    defined = {
        node.name
        for node in ast.walk(ast.parse(SELF_SOURCE))
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    }
    uncovered = sorted(
        token for token in tokens if f"test_envelope_for_{token}" not in defined
    )
    assert not uncovered, (
        f"kinds with no `test_envelope_for_<token>` function: {uncovered}"
    )


def test_no_aggregate_assertion_stands_in_for_a_per_kind_one() -> None:
    """``any()``/``all()`` are absent from every per-kind test in this module.

    An aggregate that passes when one member survives licenses the fifteen that
    do not. The two functions permitted to use them are this one and the
    coverage test, both of which are *about* the module rather than about a
    kind.
    """
    permitted = {
        "test_every_kind_has_its_own_test_function",
        "test_no_aggregate_assertion_stands_in_for_a_per_kind_one",
        "test_subclasses_is_confined_to_the_cross_check",
        "test_nothing_enters_the_vocabulary_by_name",
        "test_the_gate_assertions_are_equalities",
    }
    offenders: list[str] = []
    for node in ast.walk(ast.parse(SELF_SOURCE)):
        if not isinstance(node, ast.FunctionDef):
            continue
        if not node.name.startswith("test_") or node.name in permitted:
            continue
        for inner in ast.walk(node):
            if (
                isinstance(inner, ast.Call)
                and isinstance(inner.func, ast.Name)
                and inner.func.id in {"any", "all"}
            ):
                offenders.append(node.name)
    assert not offenders, f"aggregate assertion inside a per-kind test: {offenders}"


# --- the exhaustiveness gate ------------------------------------------------
#
# Everything below answers one question: does REFUSAL_KINDS still describe the
# tree? It must answer the same thing regardless of what the importer happened
# to touch, which is why the enumeration is an AST walk over a source root
# taken as a parameter rather than a ``__subclasses__()`` reading.


#: The name suffixes the structural walk treats as refusal-shaped.
#:
#: ``Conflict`` joined in ``24.6-L-07`` and it is not cosmetic: the constraint
#: layer's governed shell for two irreconcilable policy constraints is
#: :class:`~ccf.products.constraints.PolicyResolutionConflict`, which is a
#: refusal in every sense but its name — and the two-family walk could not see
#: it, so the vocabulary equality below would have compared a mapping that
#: named it against a tree that did not. Widening the walk keeps the gate's
#: property ("nothing enters the vocabulary by name") rather than exempting one
#: member from it, and it means a future ``…Conflict`` shell cannot ship
#: untranslated either. The cost is that three pre-existing ``…Conflict``
#: classes now have to be placed, which they are, in the two allowlists.
NAME_FAMILIES = ("Refusal", "Violation", "Conflict")


def discover_refusal_types(root: Path) -> dict[str, tuple[str, str]]:
    """Every ``…Refusal``/``…Violation``/``…Conflict`` class under ``root``, by resolved base.

    Reads no imports and executes no module, so it answers the same thing under
    a narrow ``pytest`` invocation as under the full suite.
    ``type.__subclasses__`` cannot: it reports only classes the interpreter has
    already executed, so a gate built on it is green in the narrow run and
    differently-coloured in the wide one.

    Base names are resolved **transitively within the walk**, which is what
    reaches ``PayloadTooLargeRefusal`` — whose immediate base is
    ``AdmissionRefusal``, not ``GateRefusal``. Both family roots are taken from
    the imported classes' own ``__name__`` rather than written as literals, so
    nothing here can drift from the classes it discriminates on, and no member
    of the vocabulary is ever named.

    Args:
        root: A source tree to read. The shipped assertions pass the real
            ``src/``; the sabotage controls pass a widened copy, which is the
            entire reason this is a parameter.

    Returns:
        ``{class name: (family, "path:lineno")}``. Family is ``gate`` when the
        class is or reaches the gate base, ``contract`` when it reaches the
        contract base without passing through the gate base, ``exception``
        when it reaches a built-in exception, and ``unresolved`` when it
        reaches none of the three — a state asserted empty rather than
        ignored, since a class in no family would otherwise fall through every
        comparison below.
    """
    gate_base = GateRefusal.__name__
    contract_base = CCFContract.__name__

    bases_by_name: dict[str, set[str]] = {}
    located: dict[str, str] = {}
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            # A dotted base (``ccf.products.gates.GateRefusal``) contributes
            # its last component. Duplicate class names across modules union
            # their bases rather than overwrite: a resolution then reaches
            # every possible ancestor, which can only place a class in a
            # family, never silently drop it out of one.
            bases_by_name.setdefault(node.name, set()).update(
                ast.unparse(base).rsplit(".", 1)[-1] for base in node.bases
            )
            if node.name.endswith(NAME_FAMILIES):
                located[node.name] = f"{path.relative_to(root)}:{node.lineno}"

    def ancestors_of(name: str) -> set[str]:
        seen: set[str] = set()
        pending = list(bases_by_name.get(name, ()))
        while pending:
            current = pending.pop()
            if current in seen:
                continue
            seen.add(current)
            pending.extend(bases_by_name.get(current, ()))
        return seen

    def family_of(name: str) -> str:
        if name == gate_base:
            return "gate"
        forebears = ancestors_of(name)
        if gate_base in forebears:
            return "gate"
        if contract_base in forebears:
            return "contract"
        # Structural rather than a hand-kept list of exception names: ask the
        # builtins module whether an ancestor really is an exception type.
        for forebear in forebears:
            candidate = getattr(builtins, forebear, None)
            if isinstance(candidate, type) and issubclass(candidate, BaseException):
                return "exception"
        return "unresolved"

    return {name: (family_of(name), where) for name, where in located.items()}


def vocabulary_comparisons(
    discovered: dict[str, tuple[str, str]],
    *,
    kinds: Any,
    non_product: Any,
    non_value: Any,
) -> dict[str, tuple[set[str], set[str]]]:
    """The four closures, each as an ``(actual, expected)`` pair.

    Returned rather than asserted, so the sabotage controls run the very same
    comparisons the shipped gate runs. A control that re-derived the comparison
    would prove only that the control's own copy of the logic fires.

    The vocabulary and both allowlists are parameters for the same reason:
    control 4 narrows ``REFUSAL_KINDS`` to check the other direction — a kind
    declared but no longer shipped — and must do that without editing ``src/``.
    """
    kind_names = {kind.__name__ for kind in kinds}
    by_family = {
        family: {n for n, (f, _) in discovered.items() if f == family}
        for family in ("gate", "contract", "exception", "unresolved")
    }
    return {
        # Nothing may sit outside the partition. Without this, a class whose
        # base the walk could not resolve would appear in no comparison at all
        # and would ship untranslated with the gate green.
        "totality": (by_family["unresolved"], set()),
        # The vocabulary is exactly what the tree declares. Equality, not
        # containment: a kind declared but no longer shipped is as much a
        # defect as a type shipped but untranslated.
        "vocabulary": (
            (by_family["gate"] | by_family["contract"]) - set(non_product),
            kind_names,
        ),
        # The ``*Refusal``-side allowlist is exact. A fourth contract-based
        # class outside the vocabulary fails here and demands a ruling.
        "non-product-allowlist": (
            by_family["contract"] - kind_names,
            set(non_product),
        ),
        # The ``*Violation``-side allowlist is exact. This is the comparison
        # that closes the half a ``*Refusal``-only walk cannot reach.
        "non-value-allowlist": (by_family["exception"], set(non_value)),
    }


def failing_comparisons(
    discovered: dict[str, tuple[str, str]],
    *,
    kinds: Any = REFUSAL_KINDS,
    non_product: Any = NON_PRODUCT_REFUSALS,
    non_value: Any = NON_VALUE_VIOLATIONS,
) -> dict[str, tuple[set[str], set[str]]]:
    """Which comparisons do not hold. Empty means the gate is green."""
    comparisons = vocabulary_comparisons(
        discovered, kinds=kinds, non_product=non_product, non_value=non_value
    )
    return {name: pair for name, pair in comparisons.items() if pair[0] != pair[1]}


def sabotaged_root(tmp_path: Path, addition: str) -> Path:
    """A copy of ``src/`` with one class statement appended, for a control.

    The controls read a copy and never ``src/`` itself. A control that edited
    and reverted the real tree would leave nothing behind to show it had ever
    fired, and an assertion pinned to ``SRC_ROOT`` could not be sabotaged
    without editing ``src/`` — which is why ``discover_refusal_types`` takes a
    root at all.

    The appended text is parsed, never imported, so it need not resolve at run
    time.
    """
    root = tmp_path / "src"
    shutil.copytree(
        SRC_ROOT, root, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
    )
    target = root / "ccf" / "products" / "gates.py"
    target.write_text(target.read_text(encoding="utf-8") + addition, encoding="utf-8")
    return root


def test_the_refusal_vocabulary_is_closed_by_set_equality() -> None:
    """The gate. Four equalities over a structural walk of the real ``src/``."""
    comparisons = vocabulary_comparisons(
        discover_refusal_types(SRC_ROOT),
        kinds=REFUSAL_KINDS,
        non_product=NON_PRODUCT_REFUSALS,
        non_value=NON_VALUE_VIOLATIONS,
    )
    assert comparisons["totality"][0] == comparisons["totality"][1]
    assert comparisons["vocabulary"][0] == comparisons["vocabulary"][1]
    assert (
        comparisons["non-product-allowlist"][0]
        == comparisons["non-product-allowlist"][1]
    )
    assert (
        comparisons["non-value-allowlist"][0] == comparisons["non-value-allowlist"][1]
    )


def test_the_ast_walk_and_the_runtime_hierarchy_agree() -> None:
    """Leg 4 — the cross-check, and the only ``__subclasses__`` read here.

    It catches a class the AST walk mis-parsed, and it is deterministic because
    the module list comes from the walk's own output rather than from whatever
    pytest happened to import: every module the walk found a refusal in is
    imported explicitly, by name, before the hierarchy is read.

    ``__subclasses__`` **excludes the class itself**, so the gate base is added
    back explicitly. That one-line asymmetry silently costs a kind if it is not
    handled.

    The runtime side is scoped to ``ccf.*`` because the AST side reads ``src/``
    alone — and because a ``GateRefusal`` subclass declared inside a test
    function elsewhere in this file would otherwise leak into the answer and
    make the verdict depend on test order, which is exactly the flakiness this
    gate exists to avoid.
    """
    discovered = discover_refusal_types(SRC_ROOT)
    for _, where in discovered.values():
        module_path = where.rsplit(":", 1)[0]
        importlib.import_module(module_path.removesuffix(".py").replace("/", "."))

    seen: set[type[Any]] = set()
    pending = list(GateRefusal.__subclasses__())
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        pending.extend(current.__subclasses__())

    runtime_gate_family = {GateRefusal.__name__} | {
        cls.__name__ for cls in seen if cls.__module__.startswith("ccf.")
    }
    ast_gate_family = {n for n, (f, _) in discovered.items() if f == "gate"}
    assert runtime_gate_family == ast_gate_family


# --- the sabotage controls (D-22) -------------------------------------------
#
# Each widens or narrows a copy of the tree and asserts the gate goes red. A
# guard nobody has watched fail is a guard nobody knows works.


def test_control_1_a_new_direct_gate_subclass_fails_the_gate(tmp_path: Path) -> None:
    """Widen the gate family by one, directly under the base."""
    root = sabotaged_root(tmp_path, "\n\nclass WidgetRefusal(GateRefusal):\n    pass\n")
    discovered = discover_refusal_types(root)

    assert discovered["WidgetRefusal"][0] == "gate"
    failing = failing_comparisons(discovered)
    assert "vocabulary" in failing
    assert "WidgetRefusal" in failing["vocabulary"][0]


def test_control_2_a_two_level_gate_subclass_fails_the_gate(tmp_path: Path) -> None:
    """Widen it two levels down — the control proving transitive resolution.

    ``WidgetRefusal(AdmissionRefusal)`` never names ``GateRefusal``. A walk
    matching a literal ``(GateRefusal)`` base would miss it, exactly as this
    plan's first draft missed the seven types whose immediate base is
    ``AdmissionRefusal``.
    """
    root = sabotaged_root(
        tmp_path, "\n\nclass WidgetRefusal(AdmissionRefusal):\n    pass\n"
    )
    discovered = discover_refusal_types(root)

    assert discovered["WidgetRefusal"][0] == "gate"
    failing = failing_comparisons(discovered)
    assert "vocabulary" in failing
    assert "WidgetRefusal" in failing["vocabulary"][0]


def test_control_3_a_new_contract_refusal_fails_two_comparisons(
    tmp_path: Path,
) -> None:
    """A contract-based ``…Refusal`` trips the vocabulary *and* the allowlist.

    Both fire, and that is the intended shape: the class is claimed as
    vocabulary it is not in, and the ``*Refusal`` allowlist is no longer exact.
    The only two ways to make the gate green again are deliberate acts —
    translate it into ``REFUSAL_KINDS``, or record it in
    ``NON_PRODUCT_REFUSALS`` with its reason. That is what "demands a ruling"
    means operationally.
    """
    root = sabotaged_root(tmp_path, "\n\nclass WidgetRefusal(CCFContract):\n    pass\n")
    discovered = discover_refusal_types(root)

    assert discovered["WidgetRefusal"][0] == "contract"
    failing = failing_comparisons(discovered)
    assert set(failing) == {"vocabulary", "non-product-allowlist"}
    assert "WidgetRefusal" in failing["non-product-allowlist"][0]


def test_control_4_a_declared_but_unshipped_kind_fails_the_gate() -> None:
    """The other direction: a kind in the mapping the tree no longer has.

    Narrows a *copy* of ``REFUSAL_KINDS`` rather than deleting a class from
    ``src/``, which is why ``vocabulary_comparisons`` takes the vocabulary as a
    parameter. Containment would pass here; equality is what catches it.
    """
    narrowed = {
        kind: token for kind, token in REFUSAL_KINDS.items() if kind is not TTLRefusal
    }
    failing = failing_comparisons(discover_refusal_types(SRC_ROOT), kinds=narrowed)

    assert "vocabulary" in failing
    actual, expected = failing["vocabulary"]
    assert "TTLRefusal" in actual - expected


def test_control_5_a_new_contract_violation_fails_the_gate(tmp_path: Path) -> None:
    """The control a hand-enumerated ``*Violation`` list could not have.

    Under a three-names-by-hand design this class is invisible to every
    assertion: neither discovered nor excluded, with the gate staying green
    while it ships untranslated. Because the walk reads both name families and
    partitions by resolved base, it is discovered instead.
    """
    root = sabotaged_root(
        tmp_path, "\n\nclass WidgetViolation(CCFContract):\n    pass\n"
    )
    discovered = discover_refusal_types(root)

    assert discovered["WidgetViolation"][0] == "contract"
    failing = failing_comparisons(discovered)
    assert "vocabulary" in failing
    assert "WidgetViolation" in failing["vocabulary"][0]


def test_control_6_a_new_exception_violation_trips_the_other_allowlist(
    tmp_path: Path,
) -> None:
    """An exception-based ``…Violation`` trips allowlist 3, not the vocabulary.

    The two halves of the ``…Violation`` name family stay distinguishable by
    resolved base rather than by convention: this one lands in ``exception``
    and the vocabulary comparison is untouched.
    """
    root = sabotaged_root(
        tmp_path, "\n\nclass WidgetViolation(LookupError):\n    pass\n"
    )
    discovered = discover_refusal_types(root)

    assert discovered["WidgetViolation"][0] == "exception"
    failing = failing_comparisons(discovered)
    assert set(failing) == {"non-value-allowlist"}
    assert "WidgetViolation" in failing["non-value-allowlist"][0]


def test_control_7_a_refusal_in_no_family_fails_the_totality_check(
    tmp_path: Path,
) -> None:
    """A seventh control, closing a hole the six numbered ones leave open.

    A refusal whose base resolves to none of the three roots sits in no family.
    Without the totality comparison it would appear in no assertion and pass
    silently — the same shape of hole as a hand-enumerated ``*Violation`` half,
    one level further out.
    """
    root = sabotaged_root(
        tmp_path, "\n\nclass WidgetRefusal(SomeForeignBase):\n    pass\n"
    )
    discovered = discover_refusal_types(root)

    assert discovered["WidgetRefusal"][0] == "unresolved"
    failing = failing_comparisons(discovered)
    assert "totality" in failing
    assert "WidgetRefusal" in failing["totality"][0]


def test_no_control_edits_the_real_source_tree() -> None:
    """``src/`` carries none of the controls' marker classes.

    The controls copy; they do not edit and revert. Asserted rather than
    trusted, because an edit-and-revert control that crashed halfway would
    leave the tree modified and this suite green.

    Scoped to the marker name rather than to "is ``src/`` dirty at all". A
    blanket ``git status`` check would go red for a developer with any
    unrelated uncommitted edit under ``src/`` — a guard that fails on correct
    work teaches people to ignore it, and the thing actually worth catching is
    narrower and exactly nameable: every control appends a ``Widget``-prefixed
    class, so a leak is a ``Widget`` in the real tree.
    """
    marker = "Widget"
    leaked = sorted(n for n in discover_refusal_types(SRC_ROOT) if marker in n)
    assert not leaked, f"a control leaked into src/: {leaked}"

    # Second leg, against the diff rather than the parse, so a leak in a file
    # the walk does not reach is still caught. Tolerant of unrelated edits.
    diff = subprocess.run(
        ["git", "diff", "--", "src/"],
        cwd=SRC_ROOT.parent,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    offending = [
        line
        for line in diff.splitlines()
        if line.startswith("+") and marker in line
    ]
    assert not offending, f"a control leaked into the src/ diff: {offending}"


# --- properties of the gate itself ------------------------------------------


def test_subclasses_is_confined_to_the_cross_check() -> None:
    """``__subclasses__`` appears only inside leg 4.

    The enumeration must not acquire an import-order dependency by absorbing a
    second ``__subclasses__`` reading elsewhere in this file. A property, so it
    stays true after an edit rather than only today.
    """
    permitted = "test_the_ast_walk_and_the_runtime_hierarchy_agree"
    sites: list[str] = []
    for node in ast.walk(ast.parse(SELF_SOURCE)):
        if not isinstance(node, ast.FunctionDef) or node.name == permitted:
            continue
        for inner in ast.walk(node):
            if isinstance(inner, ast.Attribute) and inner.attr == "__subclasses__":
                sites.append(node.name)
    assert not sites, f"__subclasses__ read outside the cross-check: {sites}"


def test_nothing_enters_the_vocabulary_by_name() -> None:
    """No kind's class name is a string constant inside the walk.

    A by-name collection is the hole this gate exists to close, and it must be
    structurally impossible rather than merely absent today. Both family roots
    are read from the imported classes' own ``__name__``, so even
    ``GateRefusal`` — which is both a family root and a vocabulary member — is
    never written as a literal.
    """
    walk = next(
        node
        for node in ast.walk(ast.parse(SELF_SOURCE))
        if isinstance(node, ast.FunctionDef) and node.name == "discover_refusal_types"
    )
    kind_names = {kind.__name__ for kind in REFUSAL_KINDS}
    literals = {
        node.value
        for node in ast.walk(walk)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    assert not literals & kind_names, (
        "discover_refusal_types names a vocabulary member as a literal: "
        f"{sorted(literals & kind_names)}"
    )


def test_the_gate_assertions_are_equalities() -> None:
    """Every comparison in the gate and its cross-check is ``==``.

    Checked by AST rather than by grep: ``grep -n "=="`` cannot tell an ``==``
    inside a message string from one in a comparison. Containment would pass
    where equality must not — a kind declared but no longer shipped is a defect
    a ``>=`` reading would wave through.
    """
    gated = {
        "test_the_refusal_vocabulary_is_closed_by_set_equality",
        "test_the_ast_walk_and_the_runtime_hierarchy_agree",
    }
    offenders: list[str] = []
    for node in ast.walk(ast.parse(SELF_SOURCE)):
        if not isinstance(node, ast.FunctionDef) or node.name not in gated:
            continue
        # Scoped to `assert` statements, not to every comparison in the body:
        # a loop's `if current in seen` is control flow and says nothing about
        # how strictly the gate compares. Every assertion these two functions
        # make must still be an equality.
        asserts = [n for n in ast.walk(node) if isinstance(n, ast.Assert)]
        assert asserts, f"{node.name} asserts nothing at all"
        for statement in asserts:
            for inner in ast.walk(statement):
                if isinstance(inner, ast.Compare) and not all(
                    isinstance(op, ast.Eq) for op in inner.ops
                ):
                    offenders.append(node.name)
    assert not offenders, f"a gate assertion is not an equality: {offenders}"


def test_the_cold_and_warm_runs_agree_on_the_enumeration() -> None:
    """The import-order property, checked rather than argued.

    Runs the enumeration in a **cold subprocess** and asserts it reports the
    same families as the in-process run, which by now has had the whole suite
    importing modules around it. A ``__subclasses__``-based enumeration fails
    this; the AST walk cannot.

    It also imports ``ccf.products.refusal`` cold, which is what makes the
    subprocess a genuine first entry into the tree rather than a re-run of an
    already-warm one.

    **This no longer pins an import order.** When it was written it did: a cycle
    through ``ccf.products.payload`` made that module unimportable as the first
    import, so ``refusal`` ordered its two ``ccf.products`` imports around the
    defect and this test held the order in place (``DEF-17-02``). Plan ``17-03b``
    removed the edge that closed the cycle, so the ordering constraint and its
    comment are gone and the two imports sit in their sorted position —
    ``payload`` first, the order that used to fail. What is asserted here is
    unchanged, and the property it depended on is now guarded at the source by
    ``tests/invariants/test_cold_import.py``, which walks every ``ccf.*`` module
    in its own cold subprocess.
    """
    warm = {name: family for name, (family, _) in discover_refusal_types(SRC_ROOT).items()}
    program = (
        "import json, sys\n"
        "sys.path.insert(0, 'tests')\n"
        "import ccf.products.refusal\n"
        "from products.test_refusal_envelope import discover_refusal_types, SRC_ROOT\n"
        "print(json.dumps({k: v[0] for k, v in"
        " discover_refusal_types(SRC_ROOT).items()}, sort_keys=True))\n"
    )
    completed = subprocess.run(
        [sys.executable, "-c", program],
        cwd=SRC_ROOT.parent,
        capture_output=True,
        text=True,
        env={"PYTHONPATH": "src:runtime", "PATH": os.environ.get("PATH", "")},
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == warm


# ---------------------------------------------------------------------------
# 24.6-07 — the six governance members, and the delivery-boundary identity
# ---------------------------------------------------------------------------


#: The envelope's whole declared shape, as a roster in declaration order.
#:
#: A roster and never a count, on the "verify rosters, not counts" discipline:
#: a right count with a wrong member audits clean forever. The first seven are
#: Amendment 1 §A's; the last six joined in ``24.6-07`` (``24.6-L-08``,
#: ``D-IMPL-253`` Q13/Q14 — *"Extend* ``RefusalEnvelope`` *additively"*; the
#: sixth is ``D-IMPL-256`` (1)'s delivery-boundary identity).
THE_ENVELOPE_MEMBERS: tuple[str, ...] = (
    "kind",
    "reason",
    "key",
    "detail",
    "fields",
    "request",
    "pre_assembly_lineage",
    "policy_bindings",
    "replay_reference",
    "evidence",
    "provenance",
    "disclosure",
    "resource",
)

#: Exactly the six that joined in ``24.6-07``. Each must be hash-transparent,
#: which is what keeps a 24.5-shaped shell byte-identical
#: (``tests/contracts/test_hash_transparency.py`` measures the bytes; this
#: names the members).
THE_SIX_ADDED: tuple[str, ...] = THE_ENVELOPE_MEMBERS[7:]


def _identity_value() -> RequestIdentity:
    """The ``request_identity`` fixture's value, callable from a helper.

    The module's fixture is the shape every earlier test uses; these tests
    build their subjects inside helpers, and a fixture cannot be called from
    one — so the value is named once here rather than restated per test.
    """
    return RequestIdentity(
        product_id="test.product",
        product_version="1.0.0",
        parameters={"subject-slot": "s-1"},
        temporal_boundary=_INSTANT,
    )


def _a_violation() -> ProductRequestViolation:
    return ProductRequestViolation(
        reason="missing-required-parameter",
        key="revenue_threshold",
        detail="fixture",
        declared_type="d",
        presented_type="p",
        declared_keys=frozenset({"revenue_threshold"}),
        presented_keys=frozenset(),
    )


def test_the_envelope_declares_the_original_seven_plus_the_six_added() -> None:
    assert tuple(RefusalEnvelope.model_fields) == THE_ENVELOPE_MEMBERS
    assert THE_ENVELOPE_MEMBERS[:7] == (
        "kind",
        "reason",
        "key",
        "detail",
        "fields",
        "request",
        "pre_assembly_lineage",
    )
    assert len(THE_SIX_ADDED) == 6


@pytest.mark.parametrize("member", THE_SIX_ADDED)
def test_every_added_member_is_hash_transparent(member: str) -> None:
    """``D-IMPL-243``: silence at the sentinel equals yesterday, member by
    member. Asserted one at a time rather than in aggregate, because a
    property asserted over a set passes when one member survives and licenses
    the rest."""
    extra = RefusalEnvelope.model_fields[member].json_schema_extra
    assert isinstance(extra, dict)
    assert extra.get(HASH_TRANSPARENT_KEY) is True


@pytest.mark.parametrize("member", THE_SIX_ADDED)
def test_every_added_member_defaults_to_its_positive_sentinel(member: str) -> None:
    """A shell built the 24.5 way asserts each of the six rather than going
    quiet about it — the ``NO_HITL_ACTIONS`` voice, six members over."""
    envelope = envelope_for(_a_violation(), request=_identity_value())
    expected: dict[str, Any] = {
        "policy_bindings": (),
        "replay_reference": NO_REPLAY_REFERENCE,
        "evidence": None,
        "provenance": None,
        "disclosure": None,
        "resource": None,
    }
    assert getattr(envelope, member) == expected[member]


def test_the_added_members_are_envelope_fields_and_not_promoted_fields() -> None:
    """The promoted set is unchanged by ``24.6-07``.

    ``fields`` carries what the *refusal type* declared; the six carry what the
    *envelope* knows about the decision. A member that leaked into ``fields``
    would make a governance fact read as something the refusal itself said.
    """
    envelope = envelope_for(_a_violation(), request=_identity_value())
    assert set(envelope.fields) == {
        "declared_type",
        "presented_type",
        "declared_keys",
        "presented_keys",
        "overrides",
    }
    assert not set(envelope.fields) & set(THE_SIX_ADDED)


def test_envelope_for_carries_the_four_governance_members_it_is_given() -> None:
    """``envelope_for`` passes them through; it computes none of them.

    ``replay_reference`` is deliberately **not** among its arguments: a shell
    learns its own address only from the seam that appended its record, so an
    envelope this function returns always carries the sentinel.
    """
    source = ProvenanceSource(kind="artifact", identity="policy.bundle", version="v1")
    evidence = RefusalEvidence(
        operators_invoked=frozenset({"traversal.neighbors"}),
        plan_id="plan-1",
    )
    resource = ResourceRequestIdentity(
        surface="fixture-surface",
        address="ccf-product://fixture/1.0.0",
        tenant_id="tenant-a",
        determined_at=datetime(2026, 3, 1, tzinfo=UTC),
    )
    envelope = envelope_for(
        _a_violation(),
        request=_identity_value(),
        policy_bindings=(source,),
        evidence=evidence,
        resource=resource,
    )
    assert envelope.policy_bindings == (source,)
    assert envelope.evidence == evidence
    assert envelope.resource == resource
    assert envelope.replay_reference == NO_REPLAY_REFERENCE
    assert "replay_reference" not in inspect.signature(envelope_for).parameters


def test_a_naive_determination_instant_is_refused_by_name() -> None:
    """``D-IMPL-38``: no implicit UTC anywhere in the fabric.

    A determination instant whose offset is the deciding host's local
    configuration is an instant that replays differently on a different host.
    """
    with pytest.raises(ValidationError) as caught:
        ResourceRequestIdentity(
            surface="fixture-surface",
            address="ccf-product://fixture/1.0.0",
            tenant_id="tenant-a",
            determined_at=datetime(2026, 3, 1),
        )
    assert "no UTC offset" in str(caught.value)


def test_an_aware_determination_instant_is_admitted() -> None:
    """The control: the refusal above is about the offset and nothing else."""
    identity = ResourceRequestIdentity(
        surface="fixture-surface",
        address="ccf-product://fixture/1.0.0",
        tenant_id="tenant-a",
        determined_at=datetime(2026, 3, 1, tzinfo=UTC),
    )
    assert identity.determined_at.utcoffset() is not None


def test_the_evidence_bundle_does_not_carry_the_head_its_search_ran_against() -> None:
    """The head moved to replay dimension 1; it did not become optional here.

    This test asserted the converse until ``D-IMPL-309``: ``store_snapshot_pin``
    was required on the bundle so that *"a defaulted pin would let a caller
    build evidence that silently claims the substrate exposed no head when the
    caller merely forgot to say."* That reasoning was right and it is why the
    field could not simply be given a default — but it was answered by moving
    the field rather than by defaulting it. A refusal's canonical bytes are at
    once its address, its stored form and its wire form, so a head sealed here
    made two identical searches two refusals; and the guarantee itself now
    lives where the head is recorded per execution
    (:class:`~ccf.replay.record.ContextFabricSnapshot`), reachable from the
    shell's replay reference.

    So: refused by name, not accepted and dropped.
    """
    bundle = RefusalEvidence(operators_invoked=frozenset({"o"}), plan_id="plan-1")
    assert "store_snapshot_pin" not in type(bundle).model_fields
    with pytest.raises(ValidationError, match="store_snapshot_pin"):
        RefusalEvidence(  # type: ignore[call-arg]
            operators_invoked=frozenset({"o"}),
            plan_id="plan-1",
            store_snapshot_pin=NO_STORE_SNAPSHOT_PIN,
        )
