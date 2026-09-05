"""The Disclosure layer — the ONE step from internal truth to the permitted statement.

**SDK-defined, not whitepaper-derived** (CLAUDE.md §11). The whitepaper
specifies the Context Product Contract (§6.3), the three validation gates
(§7.6) and Decision Replay (§7.10); it specifies neither a client nor a
suppression posture, so what a *consumer* may learn from a refusal has no
whitepaper shape. This module is the CCF SDK's extension, ruled in
``D-IMPL-253`` Q17 and Q27 with amendment 2 (4), and framed by ``D-IMPL-254``.

The architectural invariant, in Dave's own text. It is
SDK-defined under CLAUDE.md §11 and not whitepaper-derived (``D-IMPL-254``;
the whitepaper is deliberately **not** edited, ``D-IMPL-253`` Q28):

    *"Internal truth, governing authority, and permitted disclosure are
    distinct concerns. The fabric preserves the governed truth of why a
    determination was reached; Policy determines what of that truth may cross
    the consumer boundary; the response shell expresses only the permitted
    disclosure. Decision Replay preserves sufficient governed evidence to
    reconstruct both the determination and the disclosure decision."*

    **Determination → Authority → Disclosure → Delivery**

**This module is the Disclosure layer, and it is the only one.** It is the
single step between the internal, fully-known refusal and the shell a consumer
sees; both doors render only its output, and nothing else in ``src/`` writes
:attr:`~ccf.products.refusal.RefusalEnvelope.disclosure`. A second place that
decided what may cross is how audit truth gets destroyed to achieve suppression
silence — which is one of the four mistakes ``D-IMPL-254`` names the separation
as existing to prevent.

Three levels, and ``minimal`` is the default
--------------------------------------------
``D-IMPL-253`` Q17, Dave: *"Essential. Suppression silence should be
policy-controlled, with minimal disclosure as the safe default."* So the level
is a **Control Plane** value — :attr:`~ccf.products.entitlement.ProductEntitlementPolicy.disclosure_level`
per tenant, with an optional per-principal override on the grant — and the
default is the safe one. No level is a number and none is ordered arithmetically:
they are three named postures, and a comparison between two of them is a lookup
rather than a ``<``.

Field **presence** never differs
--------------------------------
``D-IMPL-253`` amendment 2 (4), Dave: *"Unauthorized and nonexistent subjects
must be consumer-observationally equivalent at the same disclosure level: same
transport status, kind, external reason, body schema/field presence and
permitted disclosure behavior."*

That sentence is why a withheld member's **value** is replaced and its **key**
is kept. Removing a key would make the shell's shape a channel — a consumer
counting keys would learn which internal cause it hit — and a shape channel is
harder to notice than a prose one. Every withheld value becomes the canonical
rendering of :data:`WITHHELD`, which is a positive statement rather than an
empty string a reader would have to interpret.

The rule that keeps the two clauses consistent is *the same treatment on both
sides at one level*, not *the same key set as the internal shell*. A **whole
member** the table names for a kind is normalized to its own declared sentinel
(``D-IMPL-258`` (2)) — which the canonical rendering may then omit — and it is
normalized for **every** determination of that kind, so both subjects lose the
key together and neither shell's shape says which one it is. A member replaced
for one cause and not the other is the channel; a member normalized for both
is the closure of it.

The permitted set is mechanism, and the rule is stated once
-----------------------------------------------------------
:data:`PERMITTED_AT_MINIMAL` says, per shipped kind, which of the refusal's own
declared fields survive at ``minimal``. The rule that produced it is one
sentence and it holds for every entry: **a field crosses at ``minimal`` only
when it states what the caller must satisfy or may do next, and reveals nothing
about fabric state, another tenant, another principal, or the existence of a
subject.** A deployment that wants more says so through its own policy, at
``reasoned`` or ``full``; the SDK ships the machinery and no deployment's
appetite (CINV-01).

The table holds SDK types and SDK field names only. It contains no deployment's
vocabulary, no threshold and no domain value, so it is mechanism in the sense
CLAUDE.md §6.4 requires — the same sense in which
:data:`~ccf.products.refusal.REFUSAL_KINDS` is.

Algorithmic module (CINV-03): pure functions over typed values, no I/O, no
clock, no LLM dependency ever.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import TYPE_CHECKING, Final, Literal

from pydantic_core import PydanticUndefined

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes
from ccf.products.provenance import ProvenanceSource

if TYPE_CHECKING:  # pragma: no cover - typing only
    # Deferred against a cycle that is REAL rather than hypothetical, and it
    # was measured before it was written around: ``ccf.products.entitlement``
    # holds the disclosure level (``24.6-L-16``) and therefore imports this
    # module at runtime; this module's subject is
    # :class:`~ccf.products.refusal.RefusalEnvelope`; and
    # ``ccf.products.refusal`` imports ``ccf.products.constraints``, which
    # imports ``ccf.products.entitlement``. A module-level import here closes
    # that loop and a cold ``import ccf.products.entitlement`` raises
    # ``ImportError`` on ``PrincipalNotEntitled``.
    #
    # Nothing here needs the class at runtime: ``disclose`` reads the
    # envelope's own attributes and returns ``model_copy``'s result, and
    # ``from __future__ import annotations`` leaves the annotations unevaluated.
    # The vocabulary's closure against
    # :data:`~ccf.products.refusal.REFUSAL_KINDS` is asserted in
    # ``tests/products/test_disclosure.py``, which imports both — the check is
    # the same check, run where it costs nothing (``D-IMPL-56``'s discipline,
    # in the shape ``ccf.agents.assembler`` already uses for the same module).
    from ccf.products.refusal import RefusalEnvelope

__ccf_mode__ = "algorithmic"

__all__ = [
    "DISCLOSURE_LEVELS",
    "DISCLOSURE_MINIMAL",
    "EXTERNAL_STATEMENTS",
    "INDISTINGUISHABLE_BELOW_FULL",
    "PERMITTED_AT_MINIMAL",
    "SUPPRESSED_BELOW_FULL",
    "WITHHELD",
    "DisclosureDecision",
    "DisclosureLevel",
    "disclose",
]


#: The three postures a policy may put in force.
#:
#: ``minimal``
#:     The safe default. The reason prose becomes the one external sentence
#:     :data:`EXTERNAL_STATEMENTS` holds for the kind; every field outside
#:     :data:`PERMITTED_AT_MINIMAL` is withheld; the evidence, the authority
#:     resolution and the pre-assembly lineage do not cross at all.
#: ``reasoned``
#:     The fabric's own prose, its declared fields, the permitted evidence, the
#:     authority resolution and the lineage all cross — except the members
#:     :data:`INDISTINGUISHABLE_BELOW_FULL` names for the kind, which are what
#:     ``D-IMPL-253`` Q27 makes indistinguishable at every level below ``full``.
#: ``full``
#:     Internal truth crosses whole. A policy setting this has said, in a
#:     versioned artifact an examiner can resolve, that this reader may see what
#:     the fabric determined.
DisclosureLevel = Literal["minimal", "reasoned", "full"]

#: The closed level vocabulary, by value — read from the ``Literal`` above
#: rather than restated, so the two cannot drift.
DISCLOSURE_LEVELS: Final[frozenset[str]] = frozenset({"minimal", "reasoned", "full"})

#: The safe default (``D-IMPL-253`` Q17). A mechanism token: the SDK names the
#: posture, the deployment names when it applies.
#:
#: Annotated ``Final[DisclosureLevel]`` rather than ``Final[str]``. It **is** a
#: string — the ``Literal`` is one — but the narrower annotation is what lets a
#: type checker see that a field defaulting to it satisfies its own declared
#: level type, and what makes a typo here a red build rather than a value the
#: disclosure step refuses at runtime.
DISCLOSURE_MINIMAL: Final[DisclosureLevel] = "minimal"

#: What a withheld value becomes. A positive statement — *this was withheld* —
#: rather than an empty string or a removed key, either of which a consumer
#: would have to interpret and either of which would make the shell's shape a
#: channel. It is also the value :class:`~ccf.products.refusal.SubjectUnavailableRefusal`
#: declares as its third ``cause``, so the withheld form of that field is a
#: value its own type already admits.
WITHHELD: Final[str] = "undisclosed"


#: One external sentence per shipped kind — what a consumer is told at
#: ``minimal``, and for the kinds :data:`INDISTINGUISHABLE_BELOW_FULL` names,
#: at ``reasoned`` too.
#:
#: **Mechanism prose, never a deployment's voice.** Each sentence says what the
#: fabric did in the SDK's own vocabulary and names no tenant, no principal, no
#: subject, no threshold and no artifact. Coverage is closed by set equality
#: against :data:`~ccf.products.refusal.REFUSAL_KINDS` in
#: ``tests/products/test_disclosure.py``, so a kind added to the vocabulary
#: without a sentence is a red build rather than a shell with no statement.
EXTERNAL_STATEMENTS: Final[Mapping[str, str]] = {
    # The gate family (whitepaper §7.6) and the attestation gate beside it. A
    # candidate existed and a declared gate did not admit it; which gate is the
    # promoted `reason`, which crosses at every level.
    "gate-refusal": "a declared validation gate did not admit this product",
    "empty-operator-refusal": (
        "a product computed by no operator cannot be served"
    ),
    "lineage-mismatch-refusal": (
        "the product's declared lineage and the lineage resolved for it are not"
        " the same lineage"
    ),
    "lineage-attribution-refusal": (
        "the product's lineage could not be attributed to the content it was"
        " assembled from"
    ),
    "ttl-refusal": (
        "the product's declared time-to-live is outside the bound in force"
    ),
    "attestation-refusal": (
        "the source attestation required for this product is not in force"
    ),
    "declared-obligation-refusal": (
        "an obligation the product class declares was not satisfied"
    ),
    # Q10's own sentence, Dave verbatim: "I would not make the shell itself
    # imply that Debt is invalid; the product was constructible, but
    # fulfillment was withheld because an applicable declared tolerance was
    # exceeded."
    "tolerance-exceeded": (
        "fulfillment was withheld because an applicable declared tolerance was"
        " exceeded"
    ),
    # The peering family (CLAUDE.md §7.2). Each names the boundary, never the
    # peer's state.
    "admission-refusal": (
        "an inbound Context Product was not admitted across the federation"
        " boundary"
    ),
    "payload-too-large-refusal": (
        "the inbound payload exceeds the size this boundary admits"
    ),
    "signature-refusal": (
        "the inbound product's signature was not accepted at this boundary"
    ),
    "contract-refusal": (
        "the inbound product does not satisfy the contract this boundary admits"
    ),
    "policy-binding-refusal": (
        "the inbound product's policy bindings were not accepted at this"
        " boundary"
    ),
    "lineage-continuity-refusal": (
        "the inbound product's lineage does not continue the consumer's"
    ),
    "product-mount-refusal": (
        "the requested product could not be mounted as a graph source"
    ),
    # The conformity verdicts and the anchor determination.
    "product-request-violation": (
        "the question does not conform to the contract it addresses"
    ),
    "payload-schema-violation": (
        "the payload does not conform to the schema it declares"
    ),
    "anchor-ambiguity-refusal": (
        "the anchor this question named does not identify a single subject"
    ),
    # The Authority layer's two determinations.
    "constraint-refusal": (
        "an applicable policy or technical constraint does not admit this"
        " request"
    ),
    "policy-resolution-conflict": (
        "the constraints applicable to this request cannot be reconciled"
    ),
    # Assembly.
    "mixing-refusal": (
        "the constituents of this product may not be assembled together"
    ),
    "assembly-refusal": "the assembler did not assemble an answer",
    # `D-IMPL-253` Q27's whole substance: ONE sentence, and it is the SAME
    # sentence whether the subject does not exist or the principal may not
    # receive it. A reader that could tell the two apart from this string would
    # be the suppression leak the ruling closes.
    "subject-unavailable": (
        "the requested subject is not available to this principal under this"
        " product"
    ),
}


#: Per kind, the refusal's own declared fields that survive at ``minimal``.
#:
#: The rule is in this module's docstring and holds for every entry: a field
#: crosses only when it states what the caller must satisfy or may do next and
#: reveals nothing about fabric state, another tenant, another principal, or the
#: existence of a subject. An empty set is a real answer and the commonest one.
#:
#: The promoted members are governed elsewhere:
#: :attr:`~ccf.products.refusal.RefusalEnvelope.kind`,
#: ``reason`` and ``key`` cross at every level — the kind and its reason token
#: are what make a refusal auditable at all, and ``key`` is the parameter the
#: caller itself named — while ``detail`` is replaced at ``minimal`` by
#: :data:`EXTERNAL_STATEMENTS`.
#:
#: Closed by set equality against
#: :data:`~ccf.products.refusal.REFUSAL_KINDS` in the tests, and every named
#: field is asserted to be a field the type actually declares, so a rename in a
#: refusal type turns this table red rather than silently withholding a field
#: that no longer exists while passing one that does.
PERMITTED_AT_MINIMAL: Final[Mapping[str, frozenset[str]]] = {
    # A candidate existed and a gate refused it. Which gate is the promoted
    # reason; everything the gate measured is fabric state.
    "gate-refusal": frozenset(),
    "empty-operator-refusal": frozenset(),
    "lineage-mismatch-refusal": frozenset(),
    "lineage-attribution-refusal": frozenset(),
    # The declared ceiling is actionable — a caller can ask for a shorter TTL.
    # The product's own expiry and the deciding instant are fabric state.
    "ttl-refusal": frozenset({"max_ttl_seconds"}),
    # What the deployment declares acceptable is actionable; which dimension
    # failed and what mode the source is in are fabric state.
    "attestation-refusal": frozenset({"accepted_modes"}),
    # The obligation and what the class declares are actionable; what was
    # observed is fabric state.
    "declared-obligation-refusal": frozenset({"obligation", "declared"}),
    # Q10 by name: "Preserve which authority established the tolerance." The
    # tolerance itself is the bound the caller must satisfy. The observed D_c
    # and its breakdown are the fabric's own measurement.
    "tolerance-exceeded": frozenset({"authority", "tolerance"}),
    # The peering family. The two boundary identities are what the peer itself
    # asserted; the permitted sets, the observed failures and the merged
    # lineages are the consumer's own governance state.
    "admission-refusal": frozenset({"tenant_id", "peer_id"}),
    "payload-too-large-refusal": frozenset(
        {"tenant_id", "peer_id", "observed_bytes", "ceiling_bytes"}
    ),
    "signature-refusal": frozenset({"tenant_id", "peer_id", "declared_key_id"}),
    "contract-refusal": frozenset({"tenant_id", "peer_id", "schema_name"}),
    "policy-binding-refusal": frozenset(
        {"tenant_id", "peer_id", "assertion", "asserted"}
    ),
    "lineage-continuity-refusal": frozenset({"tenant_id", "peer_id"}),
    "product-mount-refusal": frozenset({"tenant_id", "schema_name"}),
    # Conformity is entirely about a contract the caller addressed and a
    # document it supplied. Nothing here is fabric state, so the four
    # conformity members cross: a caller that cannot see what it got wrong
    # cannot correct it. `overrides` (`D-IMPL-260` P-I) is an entitlement
    # verdict and stays withheld, as it is on `constraint-refusal`.
    "product-request-violation": frozenset(
        {"declared_type", "presented_type", "declared_keys", "presented_keys"}
    ),
    "payload-schema-violation": frozenset(
        {"declared_type", "presented_type", "declared_keys", "presented_keys"}
    ),
    # The anchor is what the caller supplied. The candidate set names ENTITIES,
    # and naming them is an existence claim about each.
    "anchor-ambiguity-refusal": frozenset({"anchor"}),
    # The bound is what the request must satisfy. The requested value is the
    # caller's own and already stands on `request.parameters`.
    "constraint-refusal": frozenset({"bound"}),
    # Which of the deployment's own policy artifacts disagree is internal
    # governance state, and a caller can do nothing with it.
    "policy-resolution-conflict": frozenset(),
    "mixing-refusal": frozenset(),
    "assembly-refusal": frozenset(),
    # Nothing. The type declares only the internal cause and the internal code,
    # and both are exactly what `D-IMPL-253` Q27 makes indistinguishable.
    "subject-unavailable": frozenset(),
}


#: Per kind, the members that stay withheld at **every level below** ``full`` —
#: the envelope's own ``detail``, any of the refusal's declared fields, and any
#: **whole member of the envelope** that is sentinel-defaulted.
#:
#: ``D-IMPL-253`` Q27, Dave: *"Internally/replay, the governed cause may be
#: retained if policy permits, while the consumer-visible shell remains
#: indistinguishable."* ``reasoned`` is a level at which the fabric's own prose
#: crosses, so without this table a ``reasoned`` shell would state which of the
#: two causes it hit — in the detail, in ``cause`` and in ``error_code`` alike.
#: The distinction may cross only at ``full``, which is a policy saying in a
#: versioned artifact that this reader may see internal truth.
#:
#: ``policy_bindings`` joined the entry in ``D-IMPL-258`` (2), Dave: *"If
#: unauthorized and nonexistent subjects differ in* ``policy_bindings`` *by
#: either key presence or value, then they are not consumer-observationally
#: equivalent… replay/internal determination may retain the actual policy
#: bindings that produced the decision; the externally disclosed*
#: ``RefusalEnvelope`` *must normalize/suppress that field so unauthorized and
#: nonexistent cases have the same observable policy-binding shape at the same
#: disclosure level."* An entitlement denial pins the policy that decided it
#: and an assembler's nonexistent-subject determination pins nothing, so the
#: member differed in **value** and — because the canonical rendering omits an
#: empty tuple — in **key presence** too. Normalizing it to its own declared
#: empty form below ``full`` closes both halves at once, for every kind that
#: names it, and the internal envelope the replay record holds is untouched:
#: what changed is what may cross, never what the fabric determined.
#:
#: ``resource`` joined the entry in ``D-IMPL-260`` P-J (the Phase 24.6 close),
#: for the same reason read off the same shell: a delivery-boundary denial
#: carries the :class:`~ccf.products.refusal.ResourceRequestIdentity` it was
#: decided against and an assembler's nonexistent-subject determination carries
#: none, so **key presence** told the two apart at every level — the exact
#: channel ``D-IMPL-253`` amendment 2 (4) names. Dave: *"normalize `resource`
#: key presence below `full`, retain internally/replay."* The member's own
#: sentinel is ``None``, hash-transparent, so below ``full`` neither shell
#: renders the key; the internal envelope on the record keeps the identity —
#: what resource, on which surface, at what instant — for the examiner
#: (``D-IMPL-256`` (1)).
#:
#: One entry today, and it is a table rather than a branch so that a second kind
#: with the same property has a place to be declared rather than a condition to
#: be added.
INDISTINGUISHABLE_BELOW_FULL: Final[Mapping[str, frozenset[str]]] = {
    "subject-unavailable": frozenset(
        {"detail", "cause", "error_code", "policy_bindings", "resource"}
    ),
}

#: Per kind, per ``fields`` key, the SUB-MEMBERS of a rendered value that are
#: suppressed at **every level below** ``full`` — the key itself stays, its
#: rendering loses the named members, and the internal envelope and the replay
#: record keep all of them.
#:
#: ``D-IMPL-260`` P-F and P-G, on the constraint refusal's ``bound``: *"Minimal
#: /reasoned must normalize or suppress it consistently with the same
#: equivalence rules used for policy_bindings. Internal/replay may retain it"*
#: and *"the shell crossing the boundary is governed by disclosure level."* The
#: bound's ``operator``, ``value`` and ``authority`` are the actionable part —
#: what a caller must satisfy and who says so — and cross with the key. Its
#: ``source`` is a Control Plane artifact pin or a substrate identity, its
#: ``policy_id`` names the governing policy, and its ``reason`` is that policy's
#: own justification: fabric state, in the register of ``policy_bindings``. The
#: three are suppressed as ONE set for every authority, so a bound with a
#: policy behind it and a bound read off a substrate render with the same keys
#: below ``full`` — presence would otherwise say which authority answered
#: (``D-IMPL-253`` amendment 2 (4)).
SUPPRESSED_BELOW_FULL: Final[Mapping[str, Mapping[str, frozenset[str]]]] = {
    "constraint-refusal": {"bound": frozenset({"source", "policy_id", "reason"})},
}


class DisclosureDecision(CCFContract):
    """What the Disclosure layer decided, recorded so replay can reconstruct it.

    **SDK-defined** (CLAUDE.md §11); the ruling of record is ``D-IMPL-254``,
    which names *"producing replay that can reconstruct the decision but not
    why the consumer saw the particular response it saw"* as one of the four
    mistakes the four-layer separation exists to prevent. This is what closes
    that one: the record holds the internal determination **and** this, so an
    examiner can derive the shell from the pair rather than having to trust it.

    It is recorded on replay dimension 5
    (:attr:`~ccf.replay.record.ContentGenerationPath.disclosure_decision`)
    because it is a fact about *how the content that crossed came to be*, not
    about which bindings were in force.

    Attributes:
        level: Which posture was applied.
        policy: The Control Plane source that set the level, when one did.
            ``None`` is the positive *no policy was registered, so the safe
            default applied* — asserted rather than left as a silence, because
            a deployment that forgot to register a policy and one that
            deliberately chose ``minimal`` are different facts.
        internal_kind: The kind the determination actually was.
        external_kind: The kind the shell reports. Equal to
            :attr:`internal_kind` today, at every level. The pair exists
            because a future level that translated a kind would otherwise
            record only the translated one, and replay would lose what was
            determined; a single field could not say both.
        withheld: The member and field names whose values were replaced, in
            sorted order so two disclosures of one determination are
            byte-identical. Empty at ``full``.
    """

    level: DisclosureLevel
    policy: ProvenanceSource | None
    internal_kind: str
    external_kind: str
    withheld: tuple[str, ...]


def _suppressed_rendering(
    rendered: str, members: frozenset[str]
) -> tuple[str, tuple[str, ...]]:
    """One ``fields`` value with the named sub-members removed from its rendering.

    The value arrives as the canonical rendering :func:`~ccf.products.refusal.envelope_for`
    gave it — a JSON object for the one field :data:`SUPPRESSED_BELOW_FULL`
    names today — and leaves as the canonical rendering of that object without
    ``members``. The keys are REMOVED rather than replaced: a hash-transparent
    member (``policy_id``, ``reason``) is already absent from the rendering when
    it has nothing to say, so removal is the only form under which a bound that
    had one and a bound that had none render identically. Returns the new
    rendering and the members that were actually present, in sorted order, so
    the :class:`DisclosureDecision` records what was withheld and not what the
    table would have withheld had it been there.

    A value that is not a JSON object — the withheld sentinel, or a field a
    later kind renders as a scalar — is returned untouched with nothing
    withheld; the table names object-valued fields and a scalar has no members.
    """
    try:
        document = json.loads(rendered)
    except ValueError:
        return rendered, ()
    if not isinstance(document, dict):
        return rendered, ()
    gone = tuple(sorted(member for member in members if member in document))
    if not gone:
        return rendered, ()
    projected = {name: value for name, value in document.items() if name not in members}
    return canonical_bytes(projected).decode("utf-8"), gone


def _withheld_whole_member(envelope: RefusalEnvelope, member: str) -> object:
    """What a withheld **whole member** of the shell becomes.

    Read off the member's own declaration rather than spelled here, so the
    sentinel a field declares and the form a withheld one takes cannot drift:
    :attr:`~ccf.products.refusal.RefusalEnvelope.policy_bindings` declares the
    empty tuple as *nothing governed version-bearingly*, and that is exactly
    what *this disclosure level says nothing about what governed it* has to
    look like for the two ``D-IMPL-258`` (2) subjects to share one shape.

    Args:
        envelope: The shell whose member is being withheld — read for its
            class, never for its values.
        member: The member name, from
            :data:`INDISTINGUISHABLE_BELOW_FULL`.

    Returns:
        The member's declared sentinel.

    Raises:
        ValueError: the member declares no sentinel. A required member has no
            *nothing* to become, so withholding it whole would put a made-up
            value on the wire — and inventing one is the fake artifact
            ``D-IMPL-253`` amendment 2 (1) forbids. Declare a sentinel on the
            field, or withhold the member's own entries instead.
    """
    field = type(envelope).model_fields[member]
    empty = field.get_default(call_default_factory=True)
    if empty is PydanticUndefined:
        raise ValueError(
            f"{member!r} is named in INDISTINGUISHABLE_BELOW_FULL as a whole"
            " member of the refusal shell, but it declares no sentinel, so"
            " there is no form of it that says 'nothing'. Give the field a"
            " declared empty value, or name the entries it carries rather than"
            " the member (D-IMPL-258 (2))"
        )
    return empty


def _withheld_rendering() -> str:
    """:data:`WITHHELD` in the SDK's one canonical form.

    Not the bare string: :attr:`~ccf.products.refusal.RefusalEnvelope.fields`
    holds *canonically rendered* values — a string arrives quoted, which is
    what keeps a presented ``"3"`` distinguishable from a presented ``3`` after
    the crossing. A withheld value that arrived unquoted would be the one
    member of that mapping in a different form.
    """
    return canonical_bytes(WITHHELD).decode("utf-8")


def disclose(
    envelope: RefusalEnvelope,
    *,
    level: DisclosureLevel,
    policy: ProvenanceSource | None,
) -> tuple[RefusalEnvelope, DisclosureDecision]:
    """Turn one internal determination into the permitted external statement.

    The ONE step between the Determination/Authority layers and Delivery
    (``D-IMPL-254``). Every door renders this function's first return value and
    nothing else; the second is what replay records beside the internal
    envelope, so the transformation is reconstructible rather than trusted.

    **Pure, and total over** :data:`~ccf.products.refusal.REFUSAL_KINDS`. It
    reads no Control Plane and no clock: the level and its policy source are
    resolved by the caller (:class:`~ccf.products.resolver.ReplayRefusalRecorder`,
    the one seam that calls this) and passed in, so one determination discloses
    identically wherever it is disclosed.

    Args:
        envelope: The internal, fully-known shell — the determination as the
            fabric reached it. Its
            :attr:`~ccf.products.refusal.RefusalEnvelope.disclosure` is
            expected to be ``None``, which is what *"nothing has decided what
            may cross"* means.
        level: The posture in force, from :data:`DISCLOSURE_LEVELS`.
        policy: The Control Plane source that set ``level``, or ``None`` when no
            policy was registered and the safe default applied.

    Returns:
        The disclosed shell and the :class:`DisclosureDecision` that produced
        it. The shell's ``disclosure`` is ``level`` at **every** level,
        ``full`` included: *"internal truth was permitted to cross"* is itself
        a disclosure decision, and a shell that said nothing at ``full`` would
        be indistinguishable from one nothing had decided about.

    Raises:
        ValueError: ``level`` is not one of :data:`DISCLOSURE_LEVELS`; or the
            envelope's kind is not one this module holds a statement for; or
            :data:`INDISTINGUISHABLE_BELOW_FULL` names a whole member of the
            shell that declares no sentinel (see
            :func:`_withheld_whole_member`). All three are refused rather than
            defaulted to ``minimal``: a level nobody declared, a kind with no
            external sentence and a member with no *nothing* are deployment
            defects, and quietly answering them with the safe default would
            hide the defect behind correct-looking behaviour.
    """
    if level not in DISCLOSURE_LEVELS:
        raise ValueError(
            f"{level!r} is not a disclosure level; the three are"
            f" {sorted(DISCLOSURE_LEVELS)}. A level is a named posture, never a"
            " number, and an unknown one is refused rather than resolved to the"
            " safe default — which would hide the defect behind correct-looking"
            " behaviour (D-IMPL-253 Q17)"
        )
    kind = envelope.kind
    if kind not in EXTERNAL_STATEMENTS:
        raise ValueError(
            f"no external statement is declared for the refusal kind {kind!r};"
            " add it to EXTERNAL_STATEMENTS and PERMITTED_AT_MINIMAL in"
            " `src/ccf/products/disclosure.py`. A shell with no permitted"
            " statement cannot cross a consumer boundary"
        )

    if level == "full":
        # Nothing is withheld, and the decision says so positively.
        return (
            envelope.model_copy(update={"disclosure": level}),
            DisclosureDecision(
                level=level,
                policy=policy,
                internal_kind=kind,
                external_kind=kind,
                withheld=(),
            ),
        )

    rendering = _withheld_rendering()
    indistinguishable = INDISTINGUISHABLE_BELOW_FULL.get(kind, frozenset())
    withheld: set[str] = set()
    update: dict[str, object] = {"disclosure": level}

    # `detail` — the fabric's own prose. Replaced wholesale at `minimal`, and
    # at `reasoned` for the kinds whose prose is itself the distinction.
    if level == DISCLOSURE_MINIMAL or "detail" in indistinguishable:
        if envelope.detail != EXTERNAL_STATEMENTS[kind]:
            withheld.add("detail")
        # D-17: detail withheld at minimal
        update["detail"] = EXTERNAL_STATEMENTS[kind]

    # Whole members of the ENVELOPE that the table names for this kind.
    # `detail` has its own step above and every other name the table carries
    # today is a key in `fields`, handled below; what is left is a member of
    # the shell itself, and a withheld one becomes the value its own
    # declaration already calls "nothing" (`D-IMPL-258` (2)).
    #
    # A member normalized here has its key REMOVED from the canonical
    # rendering rather than kept — the empty tuple is hash-transparent at its
    # sentinel — and that is the shape the ruling asks for rather than an
    # exception to the keep-the-key rule above: the same member is normalized
    # on BOTH sides at one level, so the two shells are identical in presence
    # and in value. A per-cause replacement is what would have made the shape
    # a channel; a uniform one is what closes it.
    members = type(envelope).model_fields
    for member in sorted(indistinguishable):
        if member == "detail" or member not in members:
            continue
        empty = _withheld_whole_member(envelope, member)
        if getattr(envelope, member) != empty:
            withheld.add(member)
        update[member] = empty

    # `fields` — every KEY is kept and only the VALUE is replaced, so the
    # shell's shape is identical for every internal cause at one level
    # (`D-IMPL-253` amendment 2 (4)).
    permitted = (
        PERMITTED_AT_MINIMAL[kind]
        if level == DISCLOSURE_MINIMAL
        else frozenset(envelope.fields)
    )
    suppressed = SUPPRESSED_BELOW_FULL.get(kind, {})
    fields = {}
    for name, value in envelope.fields.items():
        if name in permitted and name not in indistinguishable:
            if name in suppressed:
                value, gone = _suppressed_rendering(value, suppressed[name])
                withheld.update(f"{name}.{member}" for member in gone)
            fields[name] = value
            continue
        if value != rendering:
            withheld.add(name)
        fields[name] = rendering
    update["fields"] = fields

    # The three whole-member disclosures. Each is internal by construction —
    # the permitted evidence of the search, the Authority layer's resolution,
    # and the partial lineage that existed at the point of refusal — and none
    # crosses at `minimal`. `replay_reference` and `request` are deliberately
    # untouched: the first is the address of the record this determination
    # produced, and the second is what the caller itself asked. `policy_bindings`
    # and `resource` are untouched HERE and normalized above for the kinds
    # `INDISTINGUISHABLE_BELOW_FULL` names them for — per kind rather than at
    # this level, because `D-IMPL-258` (2) and `D-IMPL-260` P-J are rulings
    # about the two subjects that share one kind and not about what every
    # refusal may say about the policy that governed it or the address it was
    # decided against.
    if level == DISCLOSURE_MINIMAL:
        for member in ("evidence", "provenance", "pre_assembly_lineage"):
            if getattr(envelope, member) is not None:
                withheld.add(member)
            update[member] = None

    return (
        envelope.model_copy(update=update),
        DisclosureDecision(
            level=level,
            policy=policy,
            internal_kind=kind,
            external_kind=kind,
            withheld=tuple(sorted(withheld)),
        ),
    )
