"""The Disclosure layer — what a policy permits to cross the consumer boundary.

``24.6-08``, ledger rows ``24.6-L-16`` and ``24.6-L-21``. The rulings of record
are ``D-IMPL-253`` Q17 and Q27 with amendment 2 (4), inside ``D-IMPL-254``'s
four layers — Determination → Authority → Disclosure → Delivery.

The two properties this module holds, and neither implies the other:

1. **What is withheld is withheld.** The reason prose, the search behind the
   refusal, the authority resolution and the pre-assembly lineage do not cross
   at ``minimal``, and the fields that do cross are exactly
   :data:`~ccf.products.disclosure.PERMITTED_AT_MINIMAL`.
2. **What is withheld is INDISTINGUISHABLE.** Field presence never differs, and
   the two causes a nonexistent subject and an unauthorized principal share
   disclose to byte-identical shells at every level below ``full``.

Property 1 without property 2 is a shell that says nothing and still tells a
caller which internal cause it hit — through its shape, which is the harder
channel to notice. So both are asserted, per kind, over the whole vocabulary.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import types
from datetime import UTC, datetime
from typing import Any

import pytest

from ccf.contracts.canonical import canonical_bytes
from ccf.products.contract import ProductLineage
from ccf.products.disclosure import (
    DISCLOSURE_LEVELS,
    DISCLOSURE_MINIMAL,
    EXTERNAL_STATEMENTS,
    INDISTINGUISHABLE_BELOW_FULL,
    PERMITTED_AT_MINIMAL,
    SUPPRESSED_BELOW_FULL,
    WITHHELD,
    DisclosureDecision,
    disclose,
)
from ccf.products.constraints import ConstraintRefusal
from ccf.products.provenance import (
    EffectiveParameter,
    EffectiveRequest,
    ParameterBound,
    ProvenanceSource,
)
from ccf.graph.protocols import NO_STORE_SNAPSHOT_PIN
from ccf.products.refusal import (
    REFUSAL_KINDS,
    RefusalEnvelope,
    RefusalEvidence,
    RequestIdentity,
    ResourceRequestIdentity,
    SubjectUnavailableRefusal,
    envelope_for,
)

# The refusal synthesizer, imported rather than restated. It is driven by the
# annotation rather than by a per-type table, so it already covers every kind
# in `REFUSAL_KINDS` and a kind that grows a field needs no edit here — and a
# second copy would be a second thing to keep in step (the
# `test_refusal_replay_record.py` precedent, `24.6-07` deviation 7).
from tests.client.test_codec import _sample_value

DISCLOSURE_PATH = (
    pathlib.Path(__file__).parent.parent.parent / "src/ccf/products/disclosure.py"
)
DISCLOSURE_SOURCE = DISCLOSURE_PATH.read_bytes()

#: The line the leak sabotage replaces. Asserted present, and asserted to
#: appear exactly once, before any mutation.
MARKER = "        # D-17: detail withheld at minimal\n"
PASS_THROUGH = "        update[\"detail\"] = envelope.detail  # SABOTAGE\n"
REAL_LINE = "        update[\"detail\"] = EXTERNAL_STATEMENTS[kind]\n"

_INSTANT = datetime(2026, 3, 2, 9, 30, tzinfo=UTC)

TOKENS = sorted(REFUSAL_KINDS.values())
BY_TOKEN = {token: kind for kind, token in REFUSAL_KINDS.items()}


def _request_identity() -> RequestIdentity:
    return RequestIdentity(
        product_id="ccf.test-product",
        product_version="1.0.0",
        parameters={"revenue_threshold": 1000000},
        temporal_boundary=_INSTANT,
    )


def _evidence() -> RefusalEvidence:
    return RefusalEvidence(
        operators_invoked=frozenset({"op.a"}),
        plan_id="plan-1",
        store_snapshot_pin=NO_STORE_SNAPSHOT_PIN,
    )


def _provenance() -> EffectiveRequest:
    return EffectiveRequest(
        asked_at=_INSTANT,
        parameters=(
            EffectiveParameter(
                name="revenue_threshold",
                value=7,
                authority="caller",
                source=ProvenanceSource(
                    kind="request", identity="the-question", version=None
                ),
                bound=None,
            ),
        ),
        applied=(),
        overrides=(),
        guidance=(),
    )


def _internal(token: str) -> RefusalEnvelope:
    """One INTERNAL envelope per kind, as rich as the kind admits.

    Rich on purpose: an envelope whose evidence, provenance and lineage were
    already ``None`` would let a disclosure step that withheld nothing pass the
    ``minimal`` assertions. The lineage is offered and dropped for the
    pre-assembly kinds, which refuse one by construction — so the factory
    measures that boundary rather than encoding a second copy of it.
    """
    refusal_type = BY_TOKEN[token]
    refusal = refusal_type(
        **{
            name: _sample_value(field.annotation)
            for name, field in refusal_type.model_fields.items()
        }
    )
    common: dict[str, Any] = {
        "request": _request_identity(),
        "evidence": _evidence(),
        "provenance": _provenance(),
        "policy_bindings": (
            ProvenanceSource(
                kind="artifact", identity="ccf.policy-bundle/t", version="1.0.0"
            ),
        ),
    }
    try:
        return envelope_for(
            refusal,
            pre_assembly_lineage=ProductLineage(
                operators_invoked=frozenset({"op.a"}),
                source_addresses=("a" * 64,),
                plan_id="plan-1",
            ),
            **common,
        )
    except ValueError:
        return envelope_for(refusal, **common)


def _expected_below_full(token: str, name: str, internal_value: str) -> str:
    """What one PERMITTED field's rendering is below ``full``.

    The internal rendering with the sub-members
    :data:`SUPPRESSED_BELOW_FULL` names for it removed — measured by
    re-rendering the projected object, so the assertion is on the table's
    meaning rather than on a second copy of the step.
    """
    members = SUPPRESSED_BELOW_FULL.get(token, {}).get(name)
    if not members:
        return internal_value
    document = json.loads(internal_value)
    return canonical_bytes(
        {key: value for key, value in document.items() if key not in members}
    ).decode("utf-8")


_POLICY_BOUND = ParameterBound(
    operator="maximum",
    value=6,
    authority="policy",
    source=ProvenanceSource(
        kind="artifact", identity="ccf.policy-constraint/depth", version="1.0.0"
    ),
    policy_id="depth-ceiling",
    reason="Reg. X §1 — traversal beyond six hops is not a reportable family",
)
_TECHNICAL_BOUND = ParameterBound(
    operator="maximum",
    value=100,
    authority="technical",
    source=ProvenanceSource(kind="capability", identity="fluree/fibo-v2", version=None),
)


def _constraint_refusal(bound: ParameterBound) -> RefusalEnvelope:
    return envelope_for(
        ConstraintRefusal(
            reason="bound-exceeded",
            key="max_depth",
            detail=f"max_depth: 101 exceeds {bound.value}",
            bound=bound,
            requested=101,
        ),
        request=_request_identity(),
    )


# --- (1) the two tables are closed over the vocabulary -----------------------


def test_the_level_vocabulary_is_closed_by_equality() -> None:
    """Three postures, and the constant is the same set the ``Literal`` is."""
    assert DISCLOSURE_LEVELS == frozenset({"minimal", "reasoned", "full"})
    assert DISCLOSURE_MINIMAL in DISCLOSURE_LEVELS
    assert DISCLOSURE_MINIMAL == "minimal"


def test_both_tables_cover_the_whole_refusal_vocabulary() -> None:
    """Closed by set equality, so a new kind with no statement is a red build.

    Two mappings and one denominator. A kind added to
    :data:`~ccf.products.refusal.REFUSAL_KINDS` without an external sentence
    would produce a shell with nothing permitted to say; one added without a
    permitted set would have no rule for its own fields.
    """
    assert set(EXTERNAL_STATEMENTS) == set(REFUSAL_KINDS.values())
    assert set(PERMITTED_AT_MINIMAL) == set(REFUSAL_KINDS.values())
    # And every table is keyed by a token no other token contains — the wire
    # vocabulary's own property, re-read here because these two mappings are
    # looked up by that token.
    assert len(set(REFUSAL_KINDS.values())) == len(REFUSAL_KINDS)


@pytest.mark.parametrize("token", TOKENS)
def test_every_permitted_field_is_a_field_the_type_declares(token: str) -> None:
    """A rename in a refusal type turns the table red rather than silently wrong.

    Without this, a permitted set naming a field that no longer exists would
    withhold everything for that kind and pass every other test in this module
    — a table quietly stricter than it reads.
    """
    declared = set(_internal(token).fields)
    permitted = PERMITTED_AT_MINIMAL[token]
    assert permitted <= declared, (
        f"{token} permits {sorted(permitted - declared)}, which its refusal"
        " type does not declare"
    )


# --- (2) the per-level behaviour, over every kind ----------------------------


@pytest.mark.parametrize("token", TOKENS)
def test_minimal_withholds_everything_outside_the_permitted_set(
    token: str,
) -> None:
    """``minimal`` is the safe default, per kind, with presence preserved."""
    internal = _internal(token)
    shell, decision = disclose(internal, level="minimal", policy=None)

    assert shell.detail == EXTERNAL_STATEMENTS[token]
    # Field PRESENCE is identical (`D-IMPL-253` amendment 2 (4)): keys are
    # kept and only values are replaced, so a consumer counting keys learns
    # nothing about which internal cause it hit.
    assert set(shell.fields) == set(internal.fields)
    rendering = canonical_bytes(WITHHELD).decode("utf-8")
    for name, value in shell.fields.items():
        if name in PERMITTED_AT_MINIMAL[token] and name not in (
            INDISTINGUISHABLE_BELOW_FULL.get(token, frozenset())
        ):
            assert value == _expected_below_full(token, name, internal.fields[name]), name
        else:
            assert value == rendering, name
    assert shell.evidence is None
    assert shell.provenance is None
    assert shell.pre_assembly_lineage is None
    assert shell.disclosure == "minimal"
    assert decision.level == "minimal"
    assert decision.internal_kind == decision.external_kind == token
    # The kind, the reason and the question always cross: a consumer that
    # cannot name the kind cannot audit the refusal at all.
    assert shell.kind == internal.kind
    assert shell.reason == internal.reason
    assert shell.request == internal.request


@pytest.mark.parametrize("token", TOKENS)
def test_reasoned_keeps_the_fabrics_own_account(token: str) -> None:
    """``reasoned`` crosses everything except what Q27 makes indistinguishable."""
    internal = _internal(token)
    shell, decision = disclose(internal, level="reasoned", policy=None)

    indistinguishable = INDISTINGUISHABLE_BELOW_FULL.get(token, frozenset())
    if "detail" in indistinguishable:
        assert shell.detail == EXTERNAL_STATEMENTS[token]
    else:
        assert shell.detail == internal.detail
    assert set(shell.fields) == set(internal.fields)
    for name, value in shell.fields.items():
        if name in indistinguishable:
            assert value == canonical_bytes(WITHHELD).decode("utf-8"), name
        else:
            assert value == _expected_below_full(token, name, internal.fields[name]), name
    assert shell.evidence == internal.evidence
    assert shell.provenance == internal.provenance
    assert shell.pre_assembly_lineage == internal.pre_assembly_lineage
    assert shell.disclosure == "reasoned"
    assert decision.level == "reasoned"


@pytest.mark.parametrize("token", TOKENS)
def test_full_is_the_internal_form_with_its_level_stated(token: str) -> None:
    """``full`` withholds nothing — and says so, which is itself a decision.

    Byte-identical to the internal envelope except ``disclosure``. A shell that
    said nothing at ``full`` would be indistinguishable from one nothing had
    decided about, which is the sentinel discipline this codebase holds
    everywhere else.
    """
    internal = _internal(token)
    shell, decision = disclose(internal, level="full", policy=None)

    assert decision.withheld == ()
    assert shell.disclosure == "full"
    assert canonical_bytes(shell) == canonical_bytes(
        internal.model_copy(update={"disclosure": "full"})
    )


# --- (3) the two causes are one outcome --------------------------------------


def _cause(
    cause: str,
    *,
    detail: str,
    error_code: str | None,
    resource: ResourceRequestIdentity | None = None,
) -> RefusalEnvelope:
    return envelope_for(
        SubjectUnavailableRefusal(
            cause=cause, detail=detail, error_code=error_code
        ),
        request=_request_identity(),
        evidence=_evidence(),
        provenance=_provenance(),
        resource=resource,
    )


#: The identity a DELIVERY-BOUNDARY denial carries and an assembler's
#: nonexistent-subject determination does not (`D-IMPL-256` (1)) — the member
#: whose presence alone told the two apart before `D-IMPL-260` P-J.
_BOUNDARY_RESOURCE = ResourceRequestIdentity(
    surface="mcp-tool",
    address="ccf-product://tenant-a/ccf.test-product/1.0.0",
    tenant_id="tenant-a",
    determined_at=_INSTANT,
)


NONEXISTENT = {
    "cause": "nonexistent",
    "detail": "no entity resolved for the anchor this question named",
    "error_code": None,
}
UNAUTHORIZED = {
    "cause": "unauthorized",
    "detail": "this principal is not entitled to receive that product class",
    "error_code": "product_class_unentitled",
}


@pytest.mark.parametrize("level", ["minimal", "reasoned"])
def test_the_two_subject_causes_are_byte_identical_below_full(level: str) -> None:
    """``24.6-L-21``. ``D-IMPL-253`` Q27's whole substance, measured.

    Dave: *"a canonical externally observable refusal outcome that both
    nonexistent and unauthorized anchors can share ... while the consumer-visible
    shell remains indistinguishable."*

    The request identity is held equal, because amendment 2 (4) says the
    equivalence is **semantic/observable** and not accidental byte equality:
    *"I would not require byte identity, because request identity, timestamps,
    replay IDs, etc. may legitimately differ."* Everything that legitimately
    differs is held constant here so that anything left differing is a leak.
    """
    absent, _ = disclose(_cause(**NONEXISTENT), level=level, policy=None)
    refused, decision = disclose(
        _cause(**UNAUTHORIZED, resource=_BOUNDARY_RESOURCE), level=level, policy=None
    )

    assert canonical_bytes(absent) == canonical_bytes(refused)
    assert absent.detail == EXTERNAL_STATEMENTS["subject-unavailable"]
    assert absent.fields["cause"] == canonical_bytes(WITHHELD).decode("utf-8")
    assert absent.fields["error_code"] == canonical_bytes(WITHHELD).decode("utf-8")
    # `D-IMPL-260` P-J: the boundary denial's resource identity is normalized
    # to the member's own `None` below `full`, so neither shell renders the
    # key and presence says nothing. The decision names the withholding.
    assert refused.resource is None and absent.resource is None
    assert "resource" not in canonical_bytes(refused).decode("utf-8")
    assert "resource" in decision.withheld


def test_at_full_the_two_causes_differ_and_the_internal_truth_survives() -> None:
    """The other half: policy MAY permit the cause, and then it crosses.

    Without this the equality above would pass against a disclosure step that
    blanked the cause at every level — which would destroy the audit truth
    ``D-IMPL-253`` Q27 says to keep.
    """
    absent, _ = disclose(_cause(**NONEXISTENT), level="full", policy=None)
    refused, _ = disclose(
        _cause(**UNAUTHORIZED, resource=_BOUNDARY_RESOURCE), level="full", policy=None
    )

    assert canonical_bytes(absent) != canonical_bytes(refused)
    assert absent.fields["cause"] == '"nonexistent"'
    assert refused.fields["cause"] == '"unauthorized"'
    assert refused.fields["error_code"] == '"product_class_unentitled"'
    assert refused.resource == _BOUNDARY_RESOURCE


# --- (2b) sub-member suppression — the constraint refusal's bound -----------


@pytest.mark.parametrize("token", TOKENS)
def test_every_suppressed_member_is_a_member_the_field_renders(token: str) -> None:
    """The sub-member table names real keys of real object-valued fields.

    A renamed member on :class:`ParameterBound` would otherwise leave the table
    suppressing nothing while reading as if it suppressed three things.
    """
    for name, members in SUPPRESSED_BELOW_FULL.get(token, {}).items():
        internal = _internal(token)
        assert name in internal.fields, (token, name)
        document = json.loads(internal.fields[name])
        assert isinstance(document, dict), (token, name)
        rendered_type = BY_TOKEN[token].model_fields[name].annotation
        declared = set(rendered_type.model_fields)
        assert members <= declared, (
            f"{token}.{name} suppresses {sorted(members - declared)}, which"
            f" {rendered_type.__name__} does not declare"
        )
        assert name in PERMITTED_AT_MINIMAL[token], (
            f"{token}.{name} is suppressed member-wise but withheld whole at"
            " minimal; the table would be dead there"
        )


@pytest.mark.parametrize("level", sorted(DISCLOSURE_LEVELS - {"full"}))
def test_the_bound_crosses_below_full_without_its_source_policy_and_reason(
    level: str,
) -> None:
    """``D-IMPL-260`` P-F / P-G: the actionable bound crosses, its provenance does not.

    The key ``bound`` stays and its ``operator``, ``value`` and ``authority``
    cross unchanged; ``source``, ``policy_id`` and ``reason`` are removed from
    the rendering. The decision records exactly the members that were present
    — the technical bound had no policy and no reason to withhold.
    """
    internal = _constraint_refusal(_POLICY_BOUND)
    shell, decision = disclose(internal, level=level, policy=None)

    crossed = json.loads(shell.fields["bound"])
    assert set(crossed) == {"authority", "operator", "value"}, crossed
    assert crossed == {"authority": "policy", "operator": "maximum", "value": 6}
    assert "bound.policy_id" in decision.withheld
    assert "bound.reason" in decision.withheld
    assert "bound.source" in decision.withheld
    assert _POLICY_BOUND.reason not in canonical_bytes(shell).decode("utf-8")
    assert _POLICY_BOUND.source.identity not in canonical_bytes(shell).decode("utf-8")
    # The internal envelope keeps every member — replay reads it from there.
    kept = json.loads(internal.fields["bound"])
    assert kept["reason"] == _POLICY_BOUND.reason
    assert kept["policy_id"] == _POLICY_BOUND.policy_id
    assert kept["source"]["identity"] == _POLICY_BOUND.source.identity

    technical_shell, technical_decision = disclose(
        _constraint_refusal(_TECHNICAL_BOUND), level=level, policy=None
    )
    technical = json.loads(technical_shell.fields["bound"])
    assert set(technical) == set(crossed), (
        "a bound with a policy behind it and a bound read off a substrate"
        " render with different keys below full — presence says which"
        f" authority answered: {sorted(technical)} vs {sorted(crossed)}"
    )
    assert technical["authority"] == "technical"
    assert set(technical_decision.withheld) & {
        "bound.source",
        "bound.policy_id",
        "bound.reason",
    } == {"bound.source"}, technical_decision.withheld


def test_at_full_the_bound_crosses_whole() -> None:
    internal = _constraint_refusal(_POLICY_BOUND)
    shell, decision = disclose(internal, level="full", policy=None)
    assert shell.fields["bound"] == internal.fields["bound"]
    assert json.loads(shell.fields["bound"])["reason"] == _POLICY_BOUND.reason
    assert decision.withheld == ()


def test_the_internal_envelope_is_never_mutated() -> None:
    """``disclose`` returns copies; the determination it was handed is intact."""
    internal = _cause(**UNAUTHORIZED)
    before = canonical_bytes(internal)
    disclose(internal, level="minimal", policy=None)
    disclose(internal, level="reasoned", policy=None)
    assert canonical_bytes(internal) == before
    assert internal.fields["cause"] == '"unauthorized"'


# --- (4) the decision round-trips --------------------------------------------


def test_the_decision_round_trips_through_canonical_bytes() -> None:
    """It is recorded on dimension 5 as bytes, so it has to survive them."""
    policy = ProvenanceSource(
        kind="artifact",
        identity="ccf.product-entitlement-policy/tenant-a",
        version="1.0.0",
    )
    _, decision = disclose(_cause(**UNAUTHORIZED), level="minimal", policy=policy)

    assert decision.internal_kind == "subject-unavailable"
    assert decision.external_kind == "subject-unavailable"
    assert decision.policy == policy
    assert "detail" in decision.withheld
    assert "cause" in decision.withheld
    assert "evidence" in decision.withheld
    assert "provenance" in decision.withheld
    # Sorted, so two disclosures of one determination are byte-identical.
    assert list(decision.withheld) == sorted(decision.withheld)

    rehydrated = DisclosureDecision.model_validate_json(
        canonical_bytes(decision)
    )
    assert rehydrated == decision


def test_an_unknown_level_is_refused_rather_than_defaulted() -> None:
    """A level nobody declared is a deployment defect, not a safe default.

    Answering it with ``minimal`` would hide the defect behind correct-looking
    behaviour, which is the failure mode this codebase refuses everywhere.
    """
    with pytest.raises(ValueError) as caught:
        disclose(_cause(**NONEXISTENT), level="verbose", policy=None)  # type: ignore[arg-type]
    assert "verbose" in str(caught.value)
    assert "minimal" in str(caught.value)


# --- (5) the leak sabotage ---------------------------------------------------


def _scratch_disclosure(tmp_path: pathlib.Path) -> types.ModuleType:
    """A copy of ``disclosure.py`` that passes ``detail`` through at ``minimal``.

    ``D-IMPL-254``'s second sabotage, criterion 21: *leak the internal cause
    into a shell under minimal disclosure, and the suite must go RED*. The
    marker line is asserted to appear exactly once before it is replaced, so a
    reflow makes this control fail loudly rather than mutate nothing.
    """
    source = DISCLOSURE_SOURCE.decode("utf-8")
    assert source.count(MARKER + REAL_LINE) == 1, (
        "the withholding step is not where the sabotage looks"
    )
    mutated = source.replace(MARKER + REAL_LINE, PASS_THROUGH, 1)
    assert mutated != source

    path = tmp_path / "disclosure_leaking_the_cause.py"
    path.write_text(mutated, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(
        "disclosure_leaking_the_cause", path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["disclosure_leaking_the_cause"] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:  # pragma: no cover - a broken scratch is a red test
        sys.modules.pop("disclosure_leaking_the_cause", None)
        raise
    return module


def test_leaking_the_internal_cause_at_minimal_is_red_sabotage(
    tmp_path: pathlib.Path,
) -> None:
    """Pass ``detail`` through and the indistinguishability predicate fails.

    The predicate is the one above — *the two causes are byte-identical at
    minimal* — and it fails because the two internal details differ. That is
    the whole leak: a caller reading the shell's prose learns whether the
    subject exists.
    """
    scratch = _scratch_disclosure(tmp_path)

    absent, _ = scratch.disclose(
        _cause(**NONEXISTENT), level="minimal", policy=None
    )
    refused, _ = scratch.disclose(
        _cause(**UNAUTHORIZED), level="minimal", policy=None
    )
    assert canonical_bytes(absent) != canonical_bytes(refused), (
        "the sabotage did not leak anything, so it is not a control"
    )
    assert NONEXISTENT["detail"] == absent.detail
    assert UNAUTHORIZED["detail"] == refused.detail

    # And the REAL module is indistinguishable for the same two inputs.
    real_absent, _ = disclose(_cause(**NONEXISTENT), level="minimal", policy=None)
    real_refused, _ = disclose(
        _cause(**UNAUTHORIZED), level="minimal", policy=None
    )
    assert canonical_bytes(real_absent) == canonical_bytes(real_refused)


def test_no_sabotage_edits_the_real_source_tree() -> None:
    """The control above mutates a copy under ``tmp_path``.

    ``disclosure.py`` on disk is byte-identical, it holds the withholding step,
    and it does **not** hold the pass-through — the positive half, so "the
    sabotage adds something" is measured rather than assumed.
    """
    assert DISCLOSURE_PATH.read_bytes() == DISCLOSURE_SOURCE
    source = DISCLOSURE_SOURCE.decode("utf-8")
    assert MARKER + REAL_LINE in source
    assert PASS_THROUGH not in source


# --- (6) the allowed set crosses only where `detail` crosses (24.7-01) -------
#
# `D-IMPL-264` D-05 (Dave): *"The presented value can be named; disclosure
# controls whether the allowed set is exposed."* The set travels ONLY in
# `detail`, so `PERMITTED_AT_MINIMAL` decides its exposure without a new
# member; advertisement of the set is the other channel (D-02) and is not a
# refusal shell's business. Criterion 6.

_ENUMERATED_MEMBERS = ("alpha", "beta")
_ENUMERATED_PARAMETER = "kind"


def _not_in_domain() -> RefusalEnvelope:
    """A REAL `not-in-domain` verdict from `refuse_request`, enveloped."""
    from datetime import datetime as _dt

    from ccf.products.request import (
        ArgumentDomain,
        ProductRequest,
        ProductRequestContract,
        refuse_request,
    )
    from ccf.skills.catalog import SkillArgumentProperty, SkillArgumentSchema

    declared = ProductRequestContract(
        semver="1.0.0",
        schema_name="ccf.test-product",
        schema_version="1.0.0",
        arguments=SkillArgumentSchema(
            properties={
                _ENUMERATED_PARAMETER: SkillArgumentProperty(
                    type="string", description="an enumerated parameter"
                )
            },
            required=(_ENUMERATED_PARAMETER,),
        ),
        argument_domains={
            _ENUMERATED_PARAMETER: ArgumentDomain(members=_ENUMERATED_MEMBERS)
        },
    )
    verdict = refuse_request(
        request=ProductRequest(
            schema_name="ccf.test-product",
            schema_version="1.0.0",
            subject="fixture:subject/one",
            intent="fixture-intent",
            freshness="fixture-freshness",
            asked_at=_dt(2026, 3, 2, 9, 30, tzinfo=UTC),
            parameters={_ENUMERATED_PARAMETER: "gamma"},
        ),
        declared=declared,
    )
    assert verdict is not None and verdict.reason == "not-in-domain"
    return envelope_for(
        verdict,
        request=RequestIdentity(
            product_id="ccf.test-product",
            product_version="1.0.0",
            parameters={_ENUMERATED_PARAMETER: "gamma"},
            temporal_boundary=_INSTANT,
        ),
    )


@pytest.mark.parametrize("level", sorted(DISCLOSURE_LEVELS))
def test_the_allowed_set_crosses_only_where_detail_crosses(level: str) -> None:
    """Absent at ``minimal``, present at ``reasoned`` and at ``full``.

    The `fields` roster is the one `test_refusal_envelope.py` pins — no
    member was added to carry the set, so `PERMITTED_AT_MINIMAL` needs no
    row and the observational-equivalence controls at both doors stand.
    """
    internal = _not_in_domain()
    shell, decision = disclose(internal, level=level, policy=None)
    rendered = canonical_bytes(shell).decode("utf-8")

    assert set(shell.fields) == {
        "declared_type",
        "presented_type",
        "declared_keys",
        "presented_keys",
        "overrides",
    }
    assert shell.reason == "not-in-domain"
    assert shell.key == _ENUMERATED_PARAMETER
    if level == "minimal":
        assert shell.detail == EXTERNAL_STATEMENTS["product-request-violation"]
        for member in _ENUMERATED_MEMBERS:
            assert member not in rendered, (member, rendered)
        assert "detail" in decision.withheld
    else:
        assert shell.detail == internal.detail
        for member in _ENUMERATED_MEMBERS:
            assert member in shell.detail
    # The caller's own value crosses at every level — it is the caller's.
    assert "gamma" in rendered


# --- (7) the declared intent set crosses only where `detail` crosses (24.7-07)
#
# `D-IMPL-264` amendment 3 A-8 a (Dave): *"The intent set is always
# advertisable through the canonical contract/discovery representation, but a
# refusal shell reveals it only according to the disclosure level."* The set
# travels ONLY in `detail` — the channel the enumerated argument domain uses
# in (6) — never in `declared_type`, which `PERMITTED_AT_MINIMAL` lets cross.
# Criterion 10.

_DECLARED_INTENTS = ("credit-screening", "onboarding-review")
_PRESENTED_INTENT = "other-intent"


def _intent_refusal() -> RefusalEnvelope:
    """A REAL intent verdict from `refuse_intent`, enveloped."""
    from ccf.products.contract import ProductDiscovery
    from ccf.products.request import ProductRequest, refuse_intent

    verdict = refuse_intent(
        request=ProductRequest(
            schema_name="ccf.test-product",
            schema_version="1.0.0",
            subject="fixture:subject/one",
            intent=_PRESENTED_INTENT,
            freshness="fixture-freshness",
            asked_at=_INSTANT,
            parameters={},
        ),
        discovery=ProductDiscovery(
            domain="fixture-domain",
            intents=frozenset(_DECLARED_INTENTS),
            capabilities=frozenset(),
        ),
    )
    assert verdict is not None and verdict.key == "intent"
    return envelope_for(verdict, request=_request_identity())


@pytest.mark.parametrize("level", sorted(DISCLOSURE_LEVELS))
def test_the_declared_intent_set_crosses_only_where_detail_crosses(
    level: str,
) -> None:
    """Absent at ``minimal``, present at ``reasoned`` and at ``full``.

    Same `fields` roster as (6): no member was added to carry the set, so
    `PERMITTED_AT_MINIMAL` needs no row. Sabotage (recorded in the plan
    SUMMARY): carry the set in `declared_type` and the `minimal` case reds.
    """
    internal = _intent_refusal()
    shell, decision = disclose(internal, level=level, policy=None)
    rendered = canonical_bytes(shell).decode("utf-8")

    assert set(shell.fields) == {
        "declared_type",
        "presented_type",
        "declared_keys",
        "presented_keys",
        "overrides",
    }
    assert shell.reason == "class-mismatch"
    assert shell.key == "intent"
    if level == "minimal":
        assert shell.detail == EXTERNAL_STATEMENTS["product-request-violation"]
        for declared in _DECLARED_INTENTS:
            assert declared not in rendered, (declared, rendered)
        assert "detail" in decision.withheld
    else:
        assert shell.detail == internal.detail
        for declared in _DECLARED_INTENTS:
            assert declared in shell.detail
    # The caller's own intent crosses at every level — it is the caller's.
    assert _PRESENTED_INTENT in rendered
