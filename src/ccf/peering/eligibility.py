"""Producer-attested child eligibility, carried in the signed envelope.

**SDK-defined** (CLAUDE.md §11; ``docs/DECISIONS.md`` **D-IMPL-336** Amendment
2). The whitepaper commits Control Plane verification at the A2A boundary
(§8.3 Pattern 4) and ``D-IMPL-16`` rules that every inbound product is
verified; neither says how a *consumer* learns whether a *remote* product is
still eligible to serve.

The problem, stated once
------------------------

``D-IMPL-334``/``D-IMPL-335`` answer *may this product still serve* by reading
the tenant's :class:`~ccf.controlplane.invalidation.EntityInvalidationRegister`
and comparing each touched entity's invalidation boundary against the product's
``graph_snapshot_at``. That register is **tenant-scoped**: it records what *this*
tenant learned was superseded. It knows nothing about the entities a remote
producer read.

So for a child produced by another fabric, the local register's **silence is
not eligibility**. It is *don't know*, and reading it as *pass* is the exact
collapse this project's measurement rules forbid — absence of a failure signal
is not presence of a success signal.

The resolution, and why it invents no wire contract
---------------------------------------------------

:meth:`~ccf.peering.identity.IdentityProvider.sign` already accepts
``assertions``, and already places them in the JWS **protected** header, which
is part of the signing input — so an assertion is covered by the signature
exactly as the payload is. :class:`~ccf.peering.admission.PeeringAdmissionGate`
already holds a peer to header assertions (the producing-agent assertion). This
module adds **one more member on that established seam**.

What binds it, and why each binding is load-bearing
----------------------------------------------------

An assertion that said only *"eligible"* could be lifted from any envelope and
replayed into any composition. :class:`EligibilityAssertion` is bound to six
facts, and admission checks every one:

* ``child_content_address`` — so it cannot be moved to a different product.
* ``requested_as_of`` — so an eligibility checked for one reconstruction
  instant cannot authorize another.
* ``producer`` — so it cannot be re-signed as another fabric's claim.
* ``consumer_scope`` — so an assertion minted for one consumer is not currency
  at another.
* ``checked_at`` — **the instant the producer actually ran its checks**, which
  is neither the reconstruction instant nor any source's observation time.
* ``composition_invocation`` — so an assertion is **single-use**: replaying a
  previously valid one into a later composition fails the binding.

**Three clocks stay separate and none substitutes for another.**
``requested_as_of`` is the decision instant, ``checked_at`` is when eligibility
was established, and the source observation times live in the product's own
lineage. Collapsing any pair would let a stale check authorize a current
decision.

**This evidence never enters the child's content identity.** The assertion
travels in the envelope's protected header; the child's content address is the
hash of the product's own canonical bytes. A product asked for by two
compositions is the same product, and its address must not move because a
different invocation asked for it (``24.11-C-01``).

Minting is not a substitute for checking
-----------------------------------------

:func:`mint_eligibility_assertion` takes the producer's **already-computed**
verdict. It does not evaluate eligibility, cannot, and must not: the producer's
own Control Plane is the only thing that can, and a minting function that also
decided would let a caller obtain an attestation without ever consulting one.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Final

from pydantic import field_validator

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.artifact_base import ArtifactClass
from ccf.controlplane.registry import ControlPlaneMissing, ControlPlaneProtocol

__ccf_mode__ = "algorithmic"

__all__ = [
    "ELIGIBILITY_ASSERTION_HEADER",
    "ELIGIBILITY_ASSERTION_SCHEMA_VERSION",
    "EligibilityAssertion",
    "EligibilityAssertionMalformed",
    "decode_eligibility_assertion",
    "encode_eligibility_assertion",
    "mint_eligibility_assertion",
]

#: The protected-header member the assertion travels in. A distinct name from
#: the producing-agent assertion, because they answer different questions and a
#: shared member would let one be presented as the other.
ELIGIBILITY_ASSERTION_HEADER: Final = "ccf-child-eligibility"

#: The assertion contract's own lane. Versioned so a consumer can refuse a
#: shape it does not understand rather than reading unknown members as absent
#: — which is how an added binding would otherwise be silently ignored.
ELIGIBILITY_ASSERTION_SCHEMA_VERSION: Final = "1.0.0"


class EligibilityAssertionMalformed(ValueError):
    """The header member is absent, unparseable, or a version we cannot read.

    Raised at the decode boundary so the gate can turn it into a typed refusal
    with the peer named. Malformed and *mismatched* are deliberately different:
    this is "I cannot read the claim", and a binding mismatch is "I read it and
    it is not about this composition".
    """


class EligibilityAssertion(CCFContract):
    """A producer's signed claim that a child was eligible when it checked.

    Every member is a **binding**; none is decorative. See the module docstring
    for why each exists and what lifting it would permit.

    Attributes:
        schema_version: This contract's lane
            (:data:`ELIGIBILITY_ASSERTION_SCHEMA_VERSION`).
        child_content_address: The address of the product this claim is about.
        requested_as_of: The reconstruction instant eligibility was established
            *for* — the composite's ``asked_at``, passed down unchanged.
        producer: The producing fabric's identity, as the producing agent's
            definition content hash.
        consumer_scope: The consumer this assertion was minted for. An
            assertion is not bearer currency.
        checked_at: When the producer actually ran its eligibility checks.
            **Not** the reconstruction instant and **not** any source's
            observation time.
        composition_invocation: The single composition invocation this
            assertion may be spent in. What makes replay detectable.
        eligible: The verdict. ``False`` is a legitimate, signed claim — a
            producer saying *"I checked, and it is not"* — and admission
            refuses on it just as it refuses on a missing assertion, but the
            two are distinguishable in the record.
    """

    schema_version: str
    child_content_address: str
    requested_as_of: datetime
    producer: str
    consumer_scope: str
    checked_at: datetime
    composition_invocation: str
    eligible: bool


def mint_eligibility_assertion(
    *,
    child_content_address: str,
    requested_as_of: datetime,
    producer: str,
    consumer_scope: str,
    checked_at: datetime,
    composition_invocation: str,
    eligible: bool,
) -> EligibilityAssertion:
    """Record a verdict the producer's Control Plane has **already** reached.

    This function performs no eligibility check and has no access to a
    register. ``eligible`` is an input because the only thing that can decide
    it is the producing fabric's own
    :func:`~ccf.products.gates.refuse_dependency_invalidation` over its own
    tenant's register — and a mint that also decided would let a caller obtain
    an attestation without one ever having been consulted.
    """
    return EligibilityAssertion(
        schema_version=ELIGIBILITY_ASSERTION_SCHEMA_VERSION,
        child_content_address=child_content_address,
        requested_as_of=requested_as_of,
        producer=producer,
        consumer_scope=consumer_scope,
        checked_at=checked_at,
        composition_invocation=composition_invocation,
        eligible=eligible,
    )


def encode_eligibility_assertion(assertion: EligibilityAssertion) -> str:
    """Render the assertion for the protected header.

    Canonical bytes, so the string a producer signs and the string a consumer
    re-derives cannot differ by key order or whitespace.
    """
    return canonical_bytes(assertion).decode("utf-8")


def decode_eligibility_assertion(claim: object) -> EligibilityAssertion:
    """Parse a protected-header member back into the typed assertion.

    Raises:
        EligibilityAssertionMalformed: the member is absent, not a string, not
            JSON, not this contract's shape, or declares a schema version this
            build does not read.
    """
    if not isinstance(claim, str) or not claim:
        raise EligibilityAssertionMalformed(
            "the signed header carries no child-eligibility assertion; a"
            " product whose producer does not say it checked eligibility is"
            " not eligible — absence is not a pass (D-IMPL-336)"
        )
    try:
        parsed = json.loads(claim)
    except json.JSONDecodeError as error:
        raise EligibilityAssertionMalformed(
            f"the child-eligibility assertion is not JSON: {error}"
        ) from error
    if not isinstance(parsed, dict):
        raise EligibilityAssertionMalformed(
            "the child-eligibility assertion is not an object"
        )
    declared = parsed.get("schema_version")
    if declared != ELIGIBILITY_ASSERTION_SCHEMA_VERSION:
        raise EligibilityAssertionMalformed(
            f"child-eligibility assertion declares schema version {declared!r};"
            f" this build reads {ELIGIBILITY_ASSERTION_SCHEMA_VERSION!r}."
            " Refused rather than read leniently: an unknown lane may bind"
            " facts this build would silently ignore"
        )
    try:
        return EligibilityAssertion.model_validate(parsed)
    except Exception as error:  # pydantic ValidationError
        raise EligibilityAssertionMalformed(
            f"the child-eligibility assertion is not well formed: {error}"
        ) from error


# --- verification: the consumer's side of the assertion ----------------------
#
# `D-IMPL-336` **Amendment 5**. Everything below was in
# `ccf.products.composite`, where it made the composite surface carry a second
# trust apparatus for the peered case. Dave's ruling: *"Remove duplicated
# verification machinery from `composite.py`, not the verification itself…
# composition consumes the verified result or refusal."*
#
# It is verification, so it lives with the thing it verifies. Composition calls
# :func:`verify_child_eligibility` once and reads the answer.


class EligibilityEvidencePolicy(CCFContract):
    """How old a producer's eligibility check may be (`F7`).

    A **Control Plane artifact**, because both members are values and the SDK
    holds none (``D-IMPL-38``). There is no default and no calibration: a
    deployment that admits peered children declares this, and one that has not
    gets an explicit refusal rather than an invented bound.

    **Validated against the ACTUAL ADMISSION TIME, never against ``asked_at``.**
    ``asked_at`` is a reconstruction instant and may be historical, so a
    producer legitimately checks eligibility *today* for a request *about last
    quarter*. Comparing the two would refuse every honest peered answer about
    the past — measured on this tree's own fixtures, where ``checked_at`` is
    correctly later than ``asked_at``.

    Attributes:
        max_evidence_age_seconds: How long after ``checked_at`` the producer's
            determination may still authorize an admission.
        permitted_clock_skew_seconds: How far *ahead* of admission time a
            producer's clock may run before its evidence is refused as
            impossible rather than merely fresh.
    """

    max_evidence_age_seconds: int
    permitted_clock_skew_seconds: int

    @field_validator("max_evidence_age_seconds", "permitted_clock_skew_seconds")
    @classmethod
    def _non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError(
                "an evidence-age bound is a duration and cannot be negative;"
                f" got {value}"
            )
        return value


#: The artifact class a deployment registers its evidence bound under.
ELIGIBILITY_EVIDENCE_POLICY = ArtifactClass(
    class_id="ccf.eligibility-evidence-policy", contract=EligibilityEvidencePolicy
)


def eligibility_evidence_policy_key(*, tenant_id: str) -> str:
    """The Control Plane key the bound registers under, per tenant."""
    return f"{tenant_id}/{ELIGIBILITY_EVIDENCE_POLICY.class_id}"


@dataclass(frozen=True)
class EligibilityEvidence:
    """What a VERIFIED producer assertion establishes, as a value.

    Carried into the composite's replay row so a reader can name which
    assertion authorized a peered child and when the producer checked.
    """

    checked_at: datetime
    assertion_address: str
    producer: str


@dataclass(frozen=True)
class EligibilityRefused:
    """Why eligibility could not be established, as a value.

    ``reason`` is one of the composite surface's refusal tokens, chosen here
    because the *reason* a peered assertion fails is peering's knowledge, not
    composition's. Composition maps it to its own refusal and adds nothing.
    """

    reason: str
    detail: str


def verify_child_eligibility(
    *,
    header: Mapping[str, object],
    child_content_address: str,
    requested_as_of: datetime,
    verified_producer: str,
    consumer_scope: str,
    composition_invocation: str,
    admitted_at: datetime,
    registry: ControlPlaneProtocol,
    tenant_id: str,
) -> EligibilityEvidence | EligibilityRefused:
    """Verify a producer's child-eligibility assertion, or say why not.

    The **one** call a consumer makes. ``header`` is the **authenticated**
    protected header a peering admission carried out — never a mapping a caller
    assembled, which is the distinction `F16` exists to preserve, and which is
    why ``verified_producer`` is passed separately: it is the identity the
    verified envelope asserted, and comparing the assertion against a sibling
    field the same caller wrote would compare two caller-supplied strings.

    Five facts are bound by **equality** and ``checked_at`` is held to a
    **declared age bound**. Those are different checks and this docstring does
    not claim otherwise.
    """
    try:
        assertion = decode_eligibility_assertion(header.get(ELIGIBILITY_ASSERTION_HEADER))
    except EligibilityAssertionMalformed as error:
        return EligibilityRefused("eligibility-evidence-missing", str(error))

    if assertion.child_content_address != child_content_address:
        return EligibilityRefused(
            "eligibility-evidence-mismatch",
            "the eligibility assertion is about"
            f" {assertion.child_content_address!r} and this child is"
            f" {child_content_address!r}",
        )
    if assertion.requested_as_of != requested_as_of:
        return EligibilityRefused(
            "eligibility-evidence-mismatch",
            "the eligibility assertion was made for reconstruction instant"
            f" {assertion.requested_as_of.isoformat()} and the child answers"
            f" for {requested_as_of.isoformat()}",
        )
    if assertion.producer != verified_producer:
        return EligibilityRefused(
            "eligibility-evidence-mismatch",
            f"the eligibility assertion names producer {assertion.producer!r}"
            f" and the VERIFIED envelope was produced by {verified_producer!r}",
        )
    if assertion.consumer_scope != consumer_scope:
        return EligibilityRefused(
            "eligibility-evidence-mismatch",
            "the eligibility assertion was minted for consumer"
            f" {assertion.consumer_scope!r} and this gate admits for"
            f" {consumer_scope!r}; an assertion is not bearer currency",
        )
    if assertion.composition_invocation != composition_invocation:
        return EligibilityRefused(
            "eligibility-evidence-mismatch",
            "the eligibility assertion was minted for composition"
            f" {assertion.composition_invocation!r} and this is"
            f" {composition_invocation!r}; the binding is to one invocation, so"
            " an assertion cannot be carried into a different composition",
        )

    stale = _evidence_too_old(
        assertion, admitted_at=admitted_at, registry=registry, tenant_id=tenant_id
    )
    if stale is not None:
        return stale

    if not assertion.eligible:
        return EligibilityRefused(
            "ineligible",
            "the producing fabric attests this child is NOT eligible as of"
            f" {assertion.checked_at.isoformat()}; a signed negative is a"
            " governed answer and is honored",
        )
    return EligibilityEvidence(
        checked_at=assertion.checked_at,
        assertion_address=content_hash(assertion),
        producer=assertion.producer,
    )


def _evidence_too_old(
    assertion: EligibilityAssertion,
    *,
    admitted_at: datetime,
    registry: ControlPlaneProtocol,
    tenant_id: str,
) -> EligibilityRefused | None:
    """Hold the producer's check to a DECLARED age bound (`F7`).

    Measured against ``admitted_at`` — when this admission is running — and
    **never** against the reconstruction instant, which may legitimately be
    years earlier than an honest check.
    """
    key = eligibility_evidence_policy_key(tenant_id=tenant_id)
    policy: object = None
    try:
        # `resolve_latest` returns (version, artifact); the artifact is the
        # second member, and reading the tuple as the artifact was a live bug
        # caught by mypy before any test ran.
        _version, policy = registry.resolve_latest(key)
    except ControlPlaneMissing:
        # NARROW, deliberately. A bare `except` would swallow a registry outage
        # and report it as an undeclared bound — a different fact, different
        # remedy.
        policy = None
    if not isinstance(policy, EligibilityEvidencePolicy):
        return EligibilityRefused(
            # Its OWN reason: a tenant that declared no bound has a
            # configuration error, and telling the operator their peer's
            # evidence is stale would name the wrong party.
            "eligibility-bound-undeclared",
            "this tenant has declared no eligibility-evidence bound at"
            f" {key!r}, so how old a producer's check may be is unknown."
            " Refused rather than defaulted: the SDK holds no duration"
            " (D-IMPL-38), and an unbounded attestation would authorize a"
            " determination of any age (D-IMPL-336 F7)",
        )

    age = (admitted_at - assertion.checked_at).total_seconds()
    if age > policy.max_evidence_age_seconds:
        return EligibilityRefused(
            "eligibility-evidence-stale",
            "the producer checked eligibility at"
            f" {assertion.checked_at.isoformat()}, {int(age)}s before this"
            f" admission at {admitted_at.isoformat()}; the declared maximum"
            f" evidence age is {policy.max_evidence_age_seconds}s",
        )
    if -age > policy.permitted_clock_skew_seconds:
        return EligibilityRefused(
            "eligibility-evidence-stale",
            f"the producer's check is dated {assertion.checked_at.isoformat()},"
            f" {int(-age)}s AFTER this admission at {admitted_at.isoformat()};"
            f" the declared permitted clock skew is"
            f" {policy.permitted_clock_skew_seconds}s. Evidence from the future"
            " is refused rather than treated as maximally fresh",
        )
    return None
