"""How far into the past a governed request may reach (`D-IMPL-358`, Wave 2 step 3).

A **Control Plane artifact**, because both members are values and the SDK holds
none (`D-IMPL-38`). There is no default, no calibration, and no fallback: a
deployment that wants its requests temporally bounded declares this, and one that
has not gets an explicit *undeclared* condition rather than an invented window.

**What this module establishes, and what it deliberately does not.** It proves
the artifact can be **declared, validated, tenant-resolved and pinned without
losing version identity**. It does *not* enforce anything: no clock is read
here, no request is bounded, no served or refusal record is touched. Threading
`PolicyBinding` into live records belongs with the resolver work after
``served_at`` exists. The truthful claim at this step is the first sentence of
this paragraph and not "requests are now temporally bounded."

**Why it lives in `ccf.controlplane` rather than beside a consumer.** The four
existing per-tenant policy artifacts each sit with the one subsystem that reads
them — `ccf/peering/trust_policy.py`, `ccf/peering/eligibility.py`,
`ccf/peering/admission.py`, `ccf/products/entitlement.py`. This one has three
prospective readers in different packages (the governed resolver, the ingress
write guard, and peering admission), so placing it with any one of them would
make the other two import across a subsystem boundary for a value that belongs
to neither.

The defect this module exists not to repeat
-------------------------------------------

`ccf/peering/eligibility.py::_evidence_too_old` resolves its policy as
``_version, policy = registry.resolve_latest(key)`` and **discards the
version**. The consequence is that no replay can name which version of the bound
authorized an admission: the value was in hand and thrown away one line later.
So resolution here returns `PinnedTemporalBoundary`, which keeps all three facts
together — canonical key, exact returned version, typed policy — and nothing in
this module resolves a policy without producing one.

`_evidence_too_old` carries a second conflation, and this module does not repeat
that either: its ``if not isinstance(policy, ...)`` branch returns
``eligibility-bound-undeclared`` for **both** an absent artifact and a wrong
object at the key. Those are different facts with different remedies — one is a
deployment that has not declared a bound, the other is a deployment that
declared the wrong thing — so they are separated here.

Three outcomes, three different facts
-------------------------------------

**absent** — nothing is registered at the key. Returns
`TemporalBoundaryUndeclared`, the condition a later governed refusal consumes,
carrying the key and class that were required and the reason, which is what
`D-IMPL-358` ruling 11 requires a refusal to record. No policy is invented.

**wrong artifact at the key** — something is registered and it is not a
`TemporalBoundaryPolicy`. Raises `TemporalBoundaryMisdeclared`. A configuration
error, never reclassified as undeclared.

**registry or control-plane failure** — anything else the registry raises
propagates untouched. Only `ControlPlaneMissing` is caught, and narrowly: a
broad ``except`` would report an outage as an undeclared bound, which is a
different fact with a different remedy, and would silently disable the boundary
on exactly the day the control plane was unwell.
"""

from __future__ import annotations

#: CINV-03. Declared by every sibling policy artifact and every other module in
#: this package (9 of 9 measured), and it is the right mark: nothing here calls a
#: model and nothing here reads a clock. `D-IMPL-159`'s stated blocker for an
#: algorithmic module is that it *"may not read a clock at all"*, which is exactly
#: the Wave 2 step 3 boundary — so the lint enforces structurally what this
#: module's own test asserts by reading its source.
__ccf_mode__ = "algorithmic"

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from pydantic import field_validator

from ccf.contracts.base import CCFContract
from ccf.controlplane.artifact_base import ArtifactClass
from ccf.controlplane.registry import ControlPlaneMissing, ControlPlaneProtocol

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ccf.replay.record import PolicyBinding

__all__ = [
    "TEMPORAL_BOUNDARY_POLICY",
    "PinnedTemporalBoundary",
    "TemporalBoundaryMisdeclared",
    "TemporalBoundaryPolicy",
    "TemporalBoundaryUndeclared",
    "resolve_temporal_boundary",
    "temporal_boundary_policy_key",
]


class TemporalBoundaryPolicy(CCFContract):
    """How far into the past a governed request may reach, as declared values.

    Both members are **deployment values** and the SDK supplies neither. A
    duration here is a policy decision about how much history a tenant will
    answer for and how much clock disagreement it will tolerate; the SDK supplies
    the shape, the validation, the key and the pinning, and no number.

    **Zero is a legal value and it is the STRICTEST bound, not "unbounded".**
    Read off the accepted semantics the sibling artifact already implements:
    `ccf/peering/eligibility.py::_evidence_too_old` compares ``age >
    policy.max_evidence_age_seconds``, so a declared ``0`` admits only an age of
    zero or less and refuses every positive one. The same reading applies here,
    and the comparison itself is **not implemented at this step** — this
    docstring states the semantics the later resolver work will honor, and claims
    no enforcement that exists.

    Attributes:
        max_past_seconds: How far before the evaluation instant a request may
            reach. A request older than this is out of window.
        permitted_clock_skew_seconds: How far *ahead* of the evaluation instant a
            presented instant may run before it is refused as impossible rather
            than merely current. Future-dated input is refused rather than
            treated as maximally fresh.
    """

    max_past_seconds: int
    permitted_clock_skew_seconds: int

    @field_validator("max_past_seconds", "permitted_clock_skew_seconds")
    @classmethod
    def _non_negative(cls, value: int) -> int:
        """A duration cannot be negative.

        Following `ccf/peering/eligibility.py::EligibilityEvidencePolicy`'s
        validator exactly: negative refuses, zero is admitted as the strictest
        bound. A negative window has no reading at all — it would name an
        interval that ends before it begins.
        """
        if value < 0:
            raise ValueError(
                "a temporal boundary is a duration and cannot be negative;"
                f" got {value}"
            )
        return value


#: The artifact class a deployment registers its temporal boundary under.
#: ``ccf.<kebab-case>`` per the convention every other class id follows, and the
#: direct sibling of ``ccf.eligibility-evidence-policy``.
TEMPORAL_BOUNDARY_POLICY: Final = ArtifactClass(
    class_id="ccf.temporal-boundary-policy", contract=TemporalBoundaryPolicy
)


def temporal_boundary_policy_key(*, tenant_id: str) -> str:
    """Return the Control Plane key one tenant's temporal boundary registers under.

    A derivation rather than a table, on the
    `ccf/peering/trust_policy.py::trust_policy_key` precedent: the SDK supplies
    the shape of the key so two components cannot disagree about where a tenant's
    policy lives, and supplies no tenant, so it holds no deployment's vocabulary
    (CINV-01).
    """
    # Tenant-first (``{tenant}/{class}``): the registry's one tenant comparison
    # reads the segment before the first ``/`` (`D-IMPL-353` §1.3), so a
    # class-first key could be registered only by a capability whose tenant was
    # the class name. It is also what keeps two tenants off one key — the
    # property `tools/../tests` pins and severing T2 falsifies.
    return f"{tenant_id}/{TEMPORAL_BOUNDARY_POLICY.class_id}"


class TemporalBoundaryMisdeclared(TypeError):
    """Something is registered at the temporal-boundary key and it is not one.

    A **configuration error**, raised rather than returned, and deliberately NOT
    folded into `TemporalBoundaryUndeclared`: a deployment that declared the
    wrong artifact and a deployment that declared none need different things
    done about them, and reporting the first as the second sends the operator to
    the wrong place. A ``TypeError`` subclass, so a caller already handling the
    refusal `ccf/controlplane/artifact_base.py::ArtifactClass.validate` raises
    for the same mistake keeps working.
    """


@dataclass(frozen=True)
class TemporalBoundaryUndeclared:
    """No temporal boundary is declared for this tenant, as a value.

    Returned rather than raised, because a later governed refusal **consumes**
    this: absence is a governance outcome a deployment can legitimately be in,
    not broken wiring. `D-IMPL-358` ruling 11 requires such a refusal to record
    *"the policy key or class that was required"* and *"the absence reason"*,
    and never to fabricate a version for a policy that does not exist — so both
    facts are carried here and no version field exists to fill in.

    Attributes:
        key: The canonical key that was consulted.
        required_class_id: The artifact class that was required there.
        reason: A stable token naming the absence, for a refusal to carry.
        detail: Prose for an operator, naming the remedy.
    """

    key: str
    required_class_id: str
    reason: str
    detail: str


@dataclass(frozen=True)
class PinnedTemporalBoundary:
    """A resolved temporal boundary with its version identity intact.

    **The point of this class is the third field's survival.** The sibling
    artifact's resolution discards the version the registry returned, so the
    binding a replay needs has to be reconstructed later from whatever is
    registered *then* — which is a different fact from what authorized the
    decision. Holding key, version and policy in one frozen value makes
    discarding the version impossible to do by accident: there is no way to
    construct this without one.

    Attributes:
        key: The canonical Control Plane key the policy was resolved from.
        version: The **exact** version string the registry returned. Never
            derived, never reconstructed, never defaulted.
        policy: The typed policy itself.
    """

    key: str
    version: str
    policy: TemporalBoundaryPolicy

    @property
    def binding(self) -> PolicyBinding:
        """The `PolicyBinding` a later step will append to a served or refusal record.

        **One authority for the pin.** Three prospective call sites will need
        this binding, and three hand-built ``PolicyBinding(key=…, version=…)``
        constructions are three chances for one of them to reconstruct a version
        instead of carrying the resolved one — the defect this module exists not
        to repeat, reintroduced at the call site.

        The import is deferred rather than module-level on purpose:
        `ccf.replay.record` reaches `ccf.products.contract`, which imports
        `ccf.controlplane.registry`, so a module-level import here would close a
        package-level cycle and would pull 56 modules into `ccf.controlplane`
        for a two-field value. Deferred function-local imports of ``ccf.*`` are
        an established idiom in this tree for exactly this reason.

        **Nothing appends this yet** (Wave 2 step 3 boundary). It is established
        so the step that does has one place to get it from.
        """
        from ccf.replay.record import PolicyBinding

        return PolicyBinding(key=self.key, version=self.version)


def resolve_temporal_boundary(
    *, registry: ControlPlaneProtocol, tenant_id: str
) -> PinnedTemporalBoundary | TemporalBoundaryUndeclared:
    """Resolve one tenant's temporal boundary, keeping its version identity.

    The tenant arrives as an argument here because this is the mechanism; it is
    supplied by governed composition or runtime context at the call site, never
    read off a request payload and never declared by an envelope (`D-IMPL-358`
    ruling 3).

    Returns:
        `PinnedTemporalBoundary` when a policy is declared — carrying the
        canonical key, the exact version the registry returned, and the typed
        policy. `TemporalBoundaryUndeclared` when nothing is registered at the
        key.

    Raises:
        TemporalBoundaryMisdeclared: something is registered at the key and it
            is not a `TemporalBoundaryPolicy`. A configuration error, not an
            absence.
        Exception: anything else the registry raises propagates untouched — a
            control-plane outage, an authorization refusal, an ambiguous pin. A
            broad ``except`` here would report any of them as an undeclared
            bound and silently disable the boundary on the day the control plane
            was unwell.
    """
    key = temporal_boundary_policy_key(tenant_id=tenant_id)
    try:
        version, artifact = registry.resolve_latest(key)
    except ControlPlaneMissing:
        # NARROW, deliberately, and this is the one exception that means absence.
        return TemporalBoundaryUndeclared(
            key=key,
            required_class_id=TEMPORAL_BOUNDARY_POLICY.class_id,
            reason="temporal-boundary-undeclared",
            detail=(
                f"no {TEMPORAL_BOUNDARY_POLICY.class_id!r} is registered at"
                f" {key!r}, so how far into the past this tenant answers for is"
                " unknown. The SDK holds no duration (D-IMPL-38) and declares no"
                " default: register a temporal boundary for this tenant rather"
                " than expecting one"
            ),
        )
    if not isinstance(artifact, TemporalBoundaryPolicy):
        found = type(artifact)
        raise TemporalBoundaryMisdeclared(
            # FULLY QUALIFIED, because the bare class name produces the useless
            # message "is a TemporalBoundaryPolicy, not a TemporalBoundaryPolicy"
            # whenever two copies of the contract class are live at once — a
            # reload, an editable install shadowing an installed copy, or a
            # module imported twice under different names. Measured: the Step 3
            # severing campaign hit exactly that and the message said nothing.
            f"the artifact registered at {key!r} is a"
            f" {found.__module__}.{found.__qualname__}, not a"
            f" {TemporalBoundaryPolicy.__module__}.{TemporalBoundaryPolicy.__qualname__}."
            " This is a declaration error and NOT an undeclared boundary: the"
            " tenant has registered something there, so reporting it as absent"
            " would send an operator to add what is already present"
        )
    # The version is returned, not discarded. That is the whole difference from
    # the sibling artifact's resolution, and severing T1 falsifies it.
    return PinnedTemporalBoundary(key=key, version=version, policy=artifact)
