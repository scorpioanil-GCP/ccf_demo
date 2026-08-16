"""D-28 — every shipped refusal crosses the seam without flattening.

Spec ``docs/superpowers/specs/2026-08-15-ccf-client-design.md`` Amendment 1 §A;
CLAUDE.md §7.3. The envelope under test is
:mod:`ccf.products.refusal`.

**What these tests enforce, and why each shape was chosen.**

1. **Per kind, one at a time.** Every one of the sixteen kinds gets its own
   assertion. Deliberately *not* one parameterized assertion over the mapping
   with an ``any()`` inside: a property asserted in aggregate passes when one
   member survives and licenses the fifteen that do not, which is this
   project's recurring defect class rather than a hypothetical one.

2. **The vocabulary is closed by set equality against a structural walk of the
   tree**, over **both** the ``…Refusal`` and ``…Violation`` name families,
   partitioned by resolved base. Nothing enters the vocabulary by name. A
   refusal type added to ``src/`` and translated nowhere fails the build and
   demands a ruling — it does not ship untranslated with the gate green.

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
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

import pytest

from ccf.products.refusal import (
    NON_PRODUCT_REFUSALS,
    NON_VALUE_VIOLATIONS,
    REFUSAL_KINDS,
    RefusalEnvelope,
    RequestIdentity,
    envelope_for,
)
from ccf.graph.product_source import GATE_PRODUCT_MOUNT, ProductMountRefusal
from ccf.peering.admission import (
    AdmissionRefusal,
    ContractRefusal,
    LineageContinuityRefusal,
    PayloadTooLargeRefusal,
    PolicyBindingRefusal,
    SignatureRefusal,
)
from ccf.products.composition import MixingRefusal
from ccf.products.contract import ProductLineage
from ccf.products.gates import (
    GATE_EMPTY_OPERATOR,
    GATE_LINEAGE_ATTRIBUTABILITY,
    GATE_LINEAGE_EQUALITY,
    GATE_SOURCE_ATTESTATION,
    GATE_TTL_BOUNDS,
    AttestationRefusal,
    EmptyOperatorRefusal,
    GateRefusal,
    LineageAttributionRefusal,
    LineageMismatchRefusal,
    TTLRefusal,
)
from ccf.products.payload import PayloadSchemaViolation
from ccf.products.request import ProductRequestViolation

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
# Sixteen functions, each naming its kind. The coverage test below derives the
# expected names from REFUSAL_KINDS and reads the actual ones out of this
# file's own AST, so a kind added to the mapping with no test here fails.


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
    # `key` were promoted; `detail` was promoted; four remain.
    assert set(envelope.fields) == {
        "declared_type",
        "presented_type",
        "declared_keys",
        "presented_keys",
    }
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
    """
    tokens = {kind.replace("-", "_") for kind in REFUSAL_KINDS.values()}
    # No token may be a substring of another, or one test could silently
    # "cover" two kinds. Asserted rather than assumed, because a kind added
    # later could break it.
    for token in tokens:
        others = tokens - {token}
        assert not any(token in other for other in others), (
            f"kind token {token!r} is a substring of another token; "
            "the coverage rule below would conflate them"
        )

    defined = {
        node.name
        for node in ast.walk(ast.parse(SELF_SOURCE))
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    }
    uncovered = sorted(
        token
        for token in tokens
        if not any(token in name for name in defined)
    )
    assert not uncovered, f"kinds with no test function naming them: {uncovered}"


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
