"""How a request parameter got the value the fabric will act on — and on whose authority.

**SDK-defined, not whitepaper-derived.** The whitepaper makes the Control
Plane the place where policy is declared and held against the decisions made
under it (§7.8), and makes Decision Replay reconstruct a decision years later
(§7.10). It does not specify how a *product default*, a *caller's value*, a
*policy boundary* and a *technical capability* combine into the one number an
operator plan is built from. This module is the CCF SDK's extension of that
surface, ruled in ``D-IMPL-253`` Q1/Q2/Q4/Q6 and Amendment 2 (1), and framed
by ``D-IMPL-254``'s four layers — Determination, Authority, Disclosure,
Delivery. **This module is the Authority layer's value.** It resolves nothing;
it is the shape a resolution has to be able to say.

The derivation comes first, and the models come after it, because the models
are consequences (Dave, ``24.6-RULINGS.md`` §1: *"don't begin with Pydantic
classes. Start with the authority/resolution semantics and a few worked
cases."*).

The four worked cases
---------------------

Dave's four cases, quoted from ``24.6-RULINGS.md`` §1. **The numbers are
illustration, never calibration** — the SDK ships no tolerance, no depth and
no ceiling, and nothing below is a value this module holds (CLAUDE.md §6.4,
CINV-01). Each case is read as a *triple* per parameter, never as a scalar:

===== ======= ======= ============ ========= ========= ========= ==========
case  default caller  policy       technical effective authority bound
                                             value     of value  authority
===== ======= ======= ============ ========= ========= ========= ==========
1     .25     .30     none         --        .30       caller    none
2     .25     omitted none         --        .25       default   none
3     .25     .30     maximum .20  --        .20       policy    policy
4     6       8       none         100       8         caller    technical
===== ======= ======= ============ ========= ========= ========= ==========

What each case forces
---------------------

**Case 1 — the caller's value wins over the product's default, and the record
says ``caller``.** A default is what omission means, not a competitor to a
value the caller actually stated. So the effective value is the caller's and
its authority is ``caller``; its source is the request itself, which is an
identity and not a versioned artifact.

**Case 2 — omission resolves to the contract's default, with authority
``default``.** The source is the request contract's own artifact pin — a
declared default is Control Plane data, so here a ``(identity, version)`` pin
exists and is recorded. This is why a default lives on
:class:`~ccf.products.request.ProductRequestContract` rather than in code:
omission has to mean something a deployment declared and an examiner can
resolve.

**Case 3 — a policy ``maximum`` bounds the caller's value; the effective value
is the policy's, the authority is ``policy``, and the caller's ``.30``
survives.** It survives on ``RequestIdentity.parameters`` — *what the caller
supplied* — which this module never replaces and never rewrites. The
distinction is the whole response semantics: the fabric must be able to say
*"you asked for .30 and policy P at version V bounds you to .20"*, not
*"you asked for .20"*. A representation that overwrote the request with the
resolved value would destroy the one fact the refusal shell exists to state.

**Case 4 — two authorities at once.** The effective value is the caller's 8
(``caller``), and the *bound* that admitted it is the backend's technical
maximum (``technical``). The bound's source is a **backend capability
identity, never a Control Plane artifact**: Amendment 2 (1) — *"Do not create
fake artifacts just to satisfy a uniform provenance schema."* That ruling is
made structural here by :class:`ProvenanceSource`'s own validator, which
refuses a version on a ``capability`` or ``request`` source and refuses an
``artifact`` source that carries none.

So the resolution output per parameter is at least ``(value, authority,
source)``, plus the bound — itself carrying its own authority and source —
when one applied. Two authorities can be in force for one parameter at the
same instant, which is precisely what a single number cannot express.

Comparability, and the defect this shape rules out
--------------------------------------------------

``D-IMPL-253`` Q4: *"Most restrictive wins only among constraints whose
semantics are actually comparable."* ``maximum`` and ``minimum`` compare on
one numeric axis; ``allowed_set`` intersects; ``required`` is not
restrictiveness at all; and ``preferred`` is guidance the resolver never
refuses on (Q5). Restrictiveness is therefore a comparison *within* a
comparable family, never a fold across authorities.

The defect being ruled out has a name and a shipped instance:
``ccf.products.gates::effective_debt_ceiling`` computes ``min(declared,
requested)`` and returns a bare number. The result cannot say whether the
ceiling in force is the class's or the caller's, and it collapses two
different authorities — class governance and a consumer constraint — into one
scalar. Dave: *"I would avoid describing the first three simply as values that
are always collapsed into one 'effective tolerance.' We need to preserve
provenance of authority. Otherwise we recreate exactly the defect the scout
found with min()."* **Any post-resolution scalar is that same defect in new
clothes**, however it is spelled; the shape below is what makes the collapsed
form unrepresentable rather than merely discouraged.

What this module does not do
----------------------------

It resolves nothing, reads no Control Plane, holds no clock and names no
parameter. The instant a resolution was performed at is a *field* of
:class:`EffectiveRequest` (``asked_at``), so a resolution is reproducible
rather than time-of-day dependent — the same discipline every comparison in
this package is held to, and the reason ``D-IMPL-253`` Q6 puts effectivity at
``asked_at``. Values are typed so that
:func:`~ccf.contracts.canonical.canonical_bytes` accepts them: decimals, ints,
strings and tuples of strings, **never a float** — refused here by name
rather than left to fail at rendering time.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any, Final, Literal, get_args

from pydantic import Field, field_validator, model_validator

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import HASH_TRANSPARENT_KEY

__ccf_mode__ = "algorithmic"

__all__ = [
    "AUTHORITIES",
    "Authority",
    "EffectiveParameter",
    "EffectiveRequest",
    "OverrideRecord",
    "ParameterBound",
    "ProvenanceSource",
]


#: Who established a value or a bound (``D-IMPL-253`` Q1). Four members and no
#: fifth: a product's declaration, the caller's own question, a Control Plane
#: policy constraint, and the backend capability the fabric is executing on.
Authority = Literal["default", "caller", "policy", "technical"]

#: The same four members, closed by value so a caller can compare against the
#: set without importing ``typing.get_args`` — derived from the ``Literal``
#: rather than restated, so the vocabulary cannot drift into two spellings.
AUTHORITIES: Final[frozenset[str]] = frozenset(get_args(Authority))


def _refuse_float(value: object, path: str) -> None:
    """Refuse a float anywhere inside a recorded value.

    A float is not canonically encodable — it is not bit-stable across
    platforms, and :func:`~ccf.contracts.canonical.canonical_bytes` refuses
    one outright — so a resolved parameter carrying one could be constructed
    and then never hashed, which is a replay record that fails at the moment
    it is needed. Refusing it at construction moves that failure to the site
    that made it (D-IMPL-38, D-IMPL-26).

    Walked recursively, because a tuple of floats is the same defect wearing a
    container. ``bool`` is an ``int`` to Python and is canonically encodable,
    so it is admitted by the ``float`` test rather than exempted by a branch.
    """
    if isinstance(value, float):
        raise ValueError(
            f"{path or '<value>'}: float is not canonically encodable (not"
            " bit-stable across platforms); use int or decimal.Decimal"
        )
    if isinstance(value, Mapping):
        for key, item in value.items():
            _refuse_float(item, f"{path}.{key}" if path else str(key))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for index, item in enumerate(value):
            _refuse_float(item, f"{path}[{index}]")


class ProvenanceSource(CCFContract):
    """Where an authority's statement came from, at the granularity it has.

    ``D-IMPL-253`` Amendment 2 (1), in Dave's words: *"Each effective parameter
    records its authority ... and the identity/version of its source where that
    source is a versioned artifact, together with sufficient source provenance
    to reconstruct resolution otherwise. ... Do not create fake artifacts just
    to satisfy a uniform provenance schema."*

    So the shape is deliberately **not** uniform. Three kinds, and the version
    lane exists for exactly one of them:

    ``artifact``
        A Control Plane artifact — a request contract, a policy constraint.
        ``version`` is required, because replay resolves an exact version and
        never "latest" (CLAUDE.md §7.4, ``D-IMPL-26``).
    ``request``
        The caller's own question. ``identity`` is the request's identity;
        there is no lane, because a question is not a versioned document.
    ``capability``
        A backend or adapter capability — the technical maximum of case 4.
        ``identity`` names the capability; there is no lane, because a
        capability is a property of the substrate in force, and minting a
        version for it would be the manufactured artifact the ruling forbids.

    The validator below is that ruling made structural: an ``artifact`` with no
    version is refused, and a version on either of the other two is refused.
    A schema that merely *allowed* ``version=None`` everywhere would leave the
    fake-artifact path open and rely on discipline to keep it shut.

    Attributes:
        kind: Which of the three the source is.
        identity: The artifact key, request identity or capability name — the
            string an examiner resolves the source by.
        version: The artifact's version, and ``None`` for the other two kinds.
            No default: an author who never stated the lane of an artifact
            source has not stated the source (D-IMPL-38).
    """

    kind: Literal["artifact", "request", "capability"]
    identity: str
    version: str | None

    @model_validator(mode="after")
    def _only_an_artifact_has_a_lane(self) -> "ProvenanceSource":
        if self.kind == "artifact" and self.version is None:
            raise ValueError(
                "an 'artifact' provenance source must carry its version:"
                " replay resolves an exact version and never 'latest'"
                " (D-IMPL-26)"
            )
        if self.kind != "artifact" and self.version is not None:
            raise ValueError(
                f"a {self.kind!r} provenance source must not carry a version:"
                " a request identity and a backend capability have no version"
                " lane, and minting one would be the manufactured artifact"
                " D-IMPL-253 amendment 2 (1) refuses"
            )
        return self


class ParameterBound(CCFContract):
    """A boundary that applied to one parameter, with the authority that set it.

    Case 3's policy ``maximum`` and case 4's technical maximum are both this
    type; the difference is the ``authority`` and the ``source``, which is
    exactly the difference a scalar loses. A bound is recorded whether or not
    it changed the value — case 4's technical maximum admitted the caller's
    value unchanged, and *that it was checked* is part of the determination.

    Attributes:
        operator: The comparison the bound expresses, in the Control Plane's
            own constraint vocabulary
            (:data:`~ccf.controlplane.artifacts.CONSTRAINT_OPERATORS`). A
            plain ``str`` and not that ``Literal``: a technical bound is not a
            policy constraint and does not come from that artifact class, so
            typing this against the policy vocabulary would claim a
            relationship the ``technical`` authority does not have.
        value: The boundary's own value. Never a float.
        authority: Who set it — ``policy`` and ``technical`` are the two the
            worked cases produce; the type admits all four because a class
            declaration and a caller constraint are bounds too.
        source: Where it came from, at the granularity it has.
        policy_id: The policy this bound belongs to, when a policy set it, and
            ``None`` otherwise. Hash-transparent at ``None`` (``D-IMPL-243``):
            a bound with no policy behind it renders without the key.
    """

    operator: str
    value: Any
    authority: Authority
    source: ProvenanceSource
    policy_id: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )

    @field_validator("value")
    @classmethod
    def _value_is_canonically_encodable(cls, value: Any) -> Any:
        _refuse_float(value, "value")
        return value


class EffectiveParameter(CCFContract):
    """One parameter's resolved value, and why it is that value.

    The triple the four worked cases force, plus the bound when one applied.
    **Never collapsed to a number** (``D-IMPL-253`` Q1: *"Provenance is part of
    the semantics, not merely audit metadata. Do not collapse authority after
    resolution."*).

    Attributes:
        name: The parameter's name, as the request contract declares it.
        value: The value the fabric will act on. Never a float.
        authority: Who established that value — case 1 and case 4 are
            ``caller``, case 2 is ``default``, case 3 is ``policy``.
        source: Where that authority's statement came from.
        bound: The boundary in force, or ``None`` when nothing bounded this
            parameter. A bound's authority may differ from the value's —
            case 4 has a ``caller`` value inside a ``technical`` bound — which
            is the second thing a scalar cannot say. Hash-transparent at
            ``None`` (``D-IMPL-243``).
    """

    name: str
    value: Any
    authority: Authority
    source: ProvenanceSource
    bound: ParameterBound | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )

    @field_validator("value")
    @classmethod
    def _value_is_canonically_encodable(cls, value: Any) -> Any:
        _refuse_float(value, "value")
        return value


class OverrideRecord(CCFContract):
    """A caller's attempt to override a named policy, and what came of it.

    ``D-IMPL-253`` Q7, with Dave's addition: *"Naming the policy is necessary
    but not sufficient authority to override it. The resolver must also
    establish that the caller/principal is entitled to exercise that override.
    Otherwise anyone who knows a policy ID could bypass it."*

    So the record carries **both** halves separately: whether the principal was
    entitled, and whether the override was honored. They are two facts and a
    single boolean would lose the one that matters at audit — an unentitled
    attempt is a thing that happened and must be recordable.

    Attributes:
        policy_id: The policy the caller named.
        policy_version: The version of the constraint artifact that was in
            force when the attempt was made — required, because an override of
            "the policy" without a lane is not replayable.
        principal_id: Who attempted it.
        entitled: Whether the principal was established as entitled to
            exercise this override.
        honored: Whether the override actually took effect. An unentitled
            attempt is recorded with ``entitled=False`` and ``honored=False``
            rather than omitted.
        grant_source: Where the entitlement was established, when it was, and
            ``None`` when no entitlement was found. Hash-transparent at
            ``None`` (``D-IMPL-243``).
    """

    policy_id: str
    policy_version: str
    principal_id: str
    entitled: bool
    honored: bool
    grant_source: ProvenanceSource | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )


class EffectiveRequest(CCFContract):
    """Every parameter a request resolved to, with provenance intact.

    The Authority layer's value (``D-IMPL-254``). It is what a resolver
    produces, what the gates are held against, what replay dimension 2 records,
    and what a refusal shell reads to say which authority refused — one value
    serving four readers, so the four cannot disagree about what was in force.

    Attributes:
        parameters: The resolved parameters. A tuple rather than a mapping so
            the record has a declaration order and one canonical rendering;
            :meth:`values` is the mapping view an engine wants.
        guidance: Bounds that applied but never refuse — ``preferred``
            (``D-IMPL-253`` Q5: *"preferred must remain non-refusing
            guidance"*). Carried beside the parameters rather than inside
            them, so that a reader cannot mistake guidance for a boundary that
            decided anything.
        overrides: Every override attempt, entitled or not.
        applied: The sources consulted to produce this resolution — the pin set
            an examiner replays against. Present even when nothing constrained
            the request, because *"nothing applied"* is a claim that needs the
            same evidence as *"this applied"*.
        asked_at: The instant the resolution was performed against. A field,
            not a clock read: constraint effectivity is evaluated at this
            instant (``D-IMPL-253`` Q6 — *"otherwise replay of the same
            historical decision can resolve a different policy"*), so a
            resolution is reproducible.
    """

    parameters: tuple[EffectiveParameter, ...]
    guidance: tuple[ParameterBound, ...]
    overrides: tuple[OverrideRecord, ...]
    applied: tuple[ProvenanceSource, ...]
    asked_at: datetime

    @model_validator(mode="after")
    def _one_record_per_parameter(self) -> "EffectiveRequest":
        names = [parameter.name for parameter in self.parameters]
        duplicated = sorted({name for name in names if names.count(name) > 1})
        if duplicated:
            raise ValueError(
                f"parameters resolved more than once: {duplicated} — one"
                " parameter has one effective value, and two records for one"
                " name is a resolution that did not finish"
            )
        return self

    def values(self) -> Mapping[str, Any]:
        """Name to effective value, for the engine that has to execute.

        The *only* place the triple is narrowed to a value, and it is narrowed
        at the point of use rather than at the point of resolution — which is
        the whole difference between this shape and the collapsed scalar the
        module docstring rules out. Nothing is stored in this form; the record
        keeps its provenance and hands out a view.
        """
        return {parameter.name: parameter.value for parameter in self.parameters}

    def parameter(self, name: str) -> EffectiveParameter | None:
        """The full record for ``name``, or ``None`` when it did not resolve.

        ``None`` is the positive statement *this request has no effective value
        for that name* — the parameter was neither supplied, defaulted, nor
        bound — and not an error, because asking about a parameter a class does
        not declare is an ordinary thing for a caller of this record to do.
        """
        for parameter in self.parameters:
            if parameter.name == name:
                return parameter
        return None
