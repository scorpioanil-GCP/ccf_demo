"""The assembler seam — `ContextAssemblerProtocol`, conformed to structurally.

[ADAPT] all of it. [MECHANISM] the Protocol this satisfies.

**THE STANDALONE PROPERTY IS THE POINT OF THIS FILE, AND IT IS A CLAIM THIS FILE
CAN BE CHECKED AGAINST.** This module imports `deployment` and `produce` and
NOTHING ELSE from the example. It imports nothing from `ccf.client`, nothing from
`ccf_runtime`, nothing MCP-shaped, and it holds no notion of a transport, a
server, a tool or a resource. **Gate `CFT-G14` is that check** — one standalone
assembler serving both callers — and it is sabotaged by giving `server/serve.py`
its own assembly path.

**WHY THAT MATTERS HERE AND NOT AT EARLIER RUNGS.** `D-21` rules the assembler
standalone with two thin callers, and this is the first rung with two: `run.py`
in process and `server/serve.py` over MCP. The standalone property is
DEMONSTRATED by two callers sharing one module, and it is only demonstrable if
this module knows nothing about either of them. A second assembly path behind
the MCP door would make both callers green while proving nothing.

**AND IT IS NOT hw1's CLAIM.** `cp-04` is the first `cp-*` rung to consume
through the client seam at all, but its portability claim is `D-21`'s — one
assembler, two callers — and NOT the `hw1-*` trees' *"same `consume.py`,
different `CCF_BINDING`, identical `Result`"*. Both are legitimate; they are not
the same claim, and no cp-04 document may imply this one re-proves that one
(`D-IMPL-225`).

**Nothing here reads a clock.** The instant is `request.asked_at`, supplied by
the caller at serve time and by replay at replay time through the same code
path. Everything downstream — the as-of boundary, the freshness figure, the
content address — is a function of that argument.

**IDENTITY FIRST, THEN THE GOVERNED REFUSAL** — the ordering `D-IMPL-216` limb 1
established and `cp-01` first implemented. This deployment reads its declared
tenant and its declared role roster before the spine runs, so identity is
settled before a governed refusal is even considered.

**THE PERSPECTIVE CHECK IS A ROSTER CHECK HERE, WHICH IS NEW ON THE LADDER.**
Rungs 01 through 03 each declare one role and refuse any other. This product's
§D.2.1 role 3 claim is that TWO roles see the same family differently, so a
product that could only be asked as one of them could not exhibit it. The roster
is `artifacts/source-vocabulary.yaml::perspective_conditioning.roles`; an
UNDECLARED role is still refused, and refused BY NAME rather than served a
default view.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Protocol, cast

from ccf.agents.assembler import NO_CONSULTATIONS, AssemblyOutcome
from ccf.agents.errors import (
    ASSEMBLY_REASON_TENANT_MISMATCH,
    ASSEMBLY_REASON_UNDECLARED_ROLE,
    AssemblyRefusal,
)
from ccf.products.constraints import (
    CAPABILITY_TRAVERSAL_DEPTH,
    ConstraintRefusal,
    PolicyResolutionConflict,
    ReferencePolicyConstraintResolver,
    TechnicalCapability,
)
from ccf.products.refusal import SubjectUnavailableRefusal
from ccf.products.request import (
    AnchorAmbiguityRefusal,
    ProductRequest,
    ProductRequestViolation,
)
from ccf.projection.plan import Perspective

import deployment
import produce

#: Who assembled this product, and under what version of that behavior. Both
#: travel on the outcome because a payload is only reproducible alongside the
#: computation that produced it.
ASSEMBLER_ID = "cp-04.corporate-family-tree"

#: PATCH, and the compatibility measurement D-25 asks for is the reason.
#:
#: `D-25`: *"cp-04 versions — product lane MINOR -> 1.1.0; assembler PATCH if
#: its own interface remains compatible."* Measured against `1.0.1`'s return
#: set: `AssemblyOutcome`, `ProductRequestViolation` and
#: `AnchorAmbiguityRefusal` are ALL STILL RETURNED, none changed shape, and
#: none changed the conditions it is returned under. What `24.6-L-01`/`L-02`
#: added is three more members — `AssemblyRefusal`, `SubjectUnavailableRefusal`
#: and `ConstraintRefusal` (with `PolicyResolutionConflict` beside it) — each
#: standing where a raise stood, so a caller written against `1.0.1` that
#: handled every value it could receive still handles every value it can
#: receive. The union WIDENED ADDITIVELY; nothing narrowed. Under the
#: Standard's change-class table (§14) that is PATCH on this lane, and
#: `D-IMPL-245` am.3's *"one bump for the phase, PATCH only"* is satisfied by
#: this single move.
#:
#: The PRODUCT lane moves MINOR in the same change and for a different reason
#: (`ccf_config.yaml`): a request at depth 8 that was refused now produces a
#: product, which is an additive capability a CONSUMER can see. Two lanes, two
#: things versioned.
ASSEMBLER_VERSION = "1.0.2"


class _AssemblyState(Protocol):
    """The one thing the assembler reads off the deployment's own scenario."""

    @property
    def halflife_debt_profile(self) -> str:
        """The pinned ``ccf-artifact://`` reference the assembly ran under."""


def _unobserved(assembled: object) -> None:
    """The default observer: the run happened and nobody watched it."""


def _not_available(lei: str) -> str:
    """The ONE refusal text for "you are not getting this family".

    A single function with a single caller-facing string, because §B.2's
    suppression rule is a statement about what a caller can DISTINGUISH, and two
    separately-worded messages drift apart the moment either is edited.

    **AN LEI THAT NAMES NO ENTITY AND AN ENTITY THIS PRINCIPAL MAY NOT SEE
    PRODUCE BYTE-IDENTICAL OUTPUT.** An LEI is a PUBLIC identifier with a public
    registry behind it — a caller can already look one up. What they must not be
    able to learn by probing is which companies THIS ESTATE covers, and separate
    answers would disclose exactly that.

    It deliberately does not say "not entitled", does not name the principal, and
    does not say whether the company exists.

    **THE DISTINCTION IS NOT LOST — IT MOVES TO WHERE IT BELONGS.** Where a
    product was assembled at all, it was gated and its replay record written
    before this refusal is reached, so the audit plane holds the full account.
    The audit knows; the caller does not.
    """
    return (
        f"family {lei!r} is not available (404); §D.2 fails closed rather than"
        " returning an empty payload. A family with no members would read as"
        " 'this company has no subsidiaries', which is a claim about the world"
        " rather than about the request"
    )


@dataclass(frozen=True)
class FamilyTreeAssembler:
    """Assemble one corporate family tree through the governed spine.

    Conforms to ``src/ccf/agents/assembler.py::ContextAssemblerProtocol``
    structurally. ``assemble`` is keyword-only because the Protocol declares it
    so, and the Protocol says why: *"the cost of a transposition would be an
    assembly attributed to the wrong tenant."*

    **``observer`` is not an escape hatch.** The Protocol pins the return type to
    ``AssemblyOutcome``, which carries the governance of the *assembly* and not
    the served vessel, its content address or its replay reference. A client that
    wants those needs the spine's full return value, and the honest way to give
    it one is a callback that observes rather than a widened return type that
    would make this seam a different seam. It is also how `CFT-G10` sees which
    stores the ASSEMBLY opened rather than which stores a runner opened.
    """

    config: Path
    root: Path
    connection: Mapping[str, str]
    read: Callable[..., Any]
    plan_class: type[Any]
    claims: Callable[..., Any]
    #: Declared-but-inert parameters, from the deployment's request contract
    #: (Standard §2.4). Defaulted to the deployment's own declaration rather than
    #: to an empty mapping — a seam that silently supported everything the
    #: contract says it refuses would be worse than one that could not express
    #: the refusal at all.
    unsupported: Mapping[str, str] = field(
        default_factory=lambda: dict(deployment.unsupported_arguments())
    )
    observer: Callable[[object], None] = field(default=_unobserved)

    @property
    def assembler_id(self) -> str:
        return ASSEMBLER_ID

    @property
    def assembler_version(self) -> str:
        return ASSEMBLER_VERSION

    def assemble(
        self,
        *,
        request: ProductRequest,
        perspective: Perspective,
        tenant_id: str,
    ) -> (
        AssemblyOutcome
        | ProductRequestViolation
        | AnchorAmbiguityRefusal
        | AssemblyRefusal
        | SubjectUnavailableRefusal
        | ConstraintRefusal
        | PolicyResolutionConflict
    ):
        """Assemble one answer to ``request`` for ``perspective``.

        **EVERY GOVERNED DETERMINATION THIS SEAM REACHES IS RETURNED**
        (``24.6-L-02``, ``D-IMPL-255`` (5); Dave: *"If the fabric has enough
        information to reach a valid governed determination, return data."*).
        SUPERSEDED 2026-09-04: this method raised
        ``ccf.agents.errors.AssemblyRefused`` for a foreign tenant, an
        undeclared role, an over-bound depth and an unresolvable anchor. It
        raises for none of them now, and the class it raised is narrowed to
        invariant failure.

        Returns:
            The :class:`~ccf.agents.assembler.AssemblyOutcome`, or one of six
            governed determinations, every one of which is a member of
            ``ccf.products.refusal::REFUSAL_KINDS`` and therefore crosses
            either caller's door as a typed envelope with no translation:

            * :class:`~ccf.products.request.ProductRequestViolation` — the
              question does not conform to the declared contract (D-60),
              including a ``max_depth`` that is not an integer
              (``type-mismatch``) and a declared-but-inert parameter
              (``not-supported-at-tier``);
            * :class:`~ccf.products.request.AnchorAmbiguityRefusal` — the
              anchor LEI resolves to more than one node (`D-IMPL-245` (4),
              `CFT-G18`);
            * :class:`~ccf.agents.errors.AssemblyRefusal` — a foreign tenant
              or an undeclared role, carrying the SDK's own reason token;
            * :class:`~ccf.products.refusal.SubjectUnavailableRefusal` — the
              anchor resolves to no family;
            * :class:`~ccf.products.constraints.ConstraintRefusal` — a value
              the fabric may not act on, with the bound that refused it and
              the authority that set it;
            * :class:`~ccf.products.constraints.PolicyResolutionConflict` —
              two applicable constraints that cannot both be satisfied.

        Raises:
            ccf.agents.errors.AssemblyRefused: an internal invariant or
                configuration contradiction reached during the assembly — the
                three sites `D-33` classes as failures, all in
                ``deployment.py``. Never a verdict about the caller.
        """
        # --- Identity, settled BEFORE anything is assembled. ---------------
        declared_tenant = deployment.tenant_id()
        if declared_tenant != tenant_id:
            # A GOVERNED DETERMINATION, RETURNED. The fabric knows both
            # tenants, so it can say which is which — and the statement is the
            # one the raise carried, verbatim, because the channel changed and
            # the sentence did not.
            return AssemblyRefusal(
                reason=ASSEMBLY_REASON_TENANT_MISMATCH,
                detail=(
                    f"assembly for tenant {tenant_id!r} was asked of a"
                    f" deployment declared as tenant {declared_tenant!r}"
                    f" (question: {request.schema_name!r}@"
                    f"{request.schema_version!r}); an assembler assembles for"
                    " its own tenant and no other"
                ),
            )
        declared_roles = deployment.declared_roles()
        if perspective.role not in declared_roles:
            return AssemblyRefusal(
                reason=ASSEMBLY_REASON_UNDECLARED_ROLE,
                detail=(
                    f"assembly under role {perspective.role!r} was asked of a"
                    f" deployment that conditions on {list(declared_roles)}"
                    f" (question: {request.schema_name!r}); the perspective"
                    " conditions what Π produced, so an undeclared role served"
                    " a default view would be a perspective widened by"
                    " omission"
                ),
            )

        # THE EFFECTIVE REQUEST IS RESOLVED BEFORE THE SPINE RUNS, BY THE SDK
        # (`24.6-L-01`, `D-IMPL-253` Q4–Q8/Q21). Defaults, then the caller,
        # then policy, then technical capability, then validation — one
        # resolution, in one place, recording `(value, authority, source)` per
        # parameter. This deployment supplies the two things the SDK cannot
        # know: which Control Plane the constraints live in, and what its own
        # substrate can do.
        #
        # NO POLICY CONSTRAINT IS DECLARED, AND THAT IS `D-22` RATHER THAN AN
        # OMISSION. Dave: *"Do not manufacture a fake policy just to
        # demonstrate the feature."* The plane is empty, the resolution records
        # that nothing version-bearing bounded this request, and the layer is
        # proven by the SDK's own tests.
        #
        # THE ENTITLEMENT KEY IS `None` FOR THE SAME REASON: overrides are
        # entitled against a grant, this class asks for none, and `None` and an
        # absent policy are treated identically — no override is entitled,
        # which is deny-by-default.
        store = deployment.traversal_depth_capability()
        effective = ReferencePolicyConstraintResolver(
            control_plane=deployment.policy_constraint_plane(),
            entitlement_key=None,
        ).resolve(
            product_class=deployment.product_class_id(),
            request=request,
            declared=deployment.request_contract(),
            declared_source=deployment.request_contract_source(),
            perspective=perspective,
            intent=request.intent,
            tenant=tenant_id,
            capabilities=(
                TechnicalCapability(
                    capability=CAPABILITY_TRAVERSAL_DEPTH,
                    # OFF THE SUBSTRATE, NEVER OFF A DOCUMENT AND NEVER A
                    # LITERAL. `100` appears nowhere in this example; it is the
                    # Fluree adapter's own bound, read through the capability.
                    maximum=Decimal(store.max_traversal_depth),
                    identity=store.capability_identity,
                ),
            ),
        )
        # A VALUE THE FABRIC MAY NOT ACT ON IS RETURNED WITH THE BOUND THAT
        # SAID SO, and nothing is answered at a narrower depth. `D-IMPL-251`
        # C5 survives here for a GENUINE limit: over the substrate's own
        # capability the answer is `constraint-refusal` with
        # `bound.authority == "technical"`, so a consumer learns what they
        # asked for AND what the boundary was.
        if isinstance(
            effective,
            (ConstraintRefusal, PolicyResolutionConflict, ProductRequestViolation),
        ):
            return effective
        resolved_depth = effective.parameter(deployment.PARAM_MAX_DEPTH)
        # The SDK's own step 5 held every effective value to the declared
        # surface, so an `int` here is a fact the resolution established rather
        # than a hope; `max_depth` is declared with a default, so the record is
        # present whether or not the caller named one.
        assert resolved_depth is not None
        max_depth = cast(int, resolved_depth.value)

        assembled = produce.assemble_and_serve(
            config=self.config,
            connection=self.connection,
            read=self.read,
            plan_class=self.plan_class,
            claims=self.claims,
            request=request,
            root=self.root,
            max_depth=max_depth,
            role=perspective.role,
            unsupported=self.unsupported,
            # WHO ASSEMBLED THIS, THREADED FROM ITS OWNER. `produce.py` builds
            # the replay record and must not import this module — the import
            # runs the other way — so the identity travels as two arguments
            # rather than as a reach across the seam (`24.6-L-15`).
            assembler_id=self.assembler_id,
            assembler_version=self.assembler_version,
            # THE RESOLUTION THIS ANSWER WAS MADE UNDER, FOR DIMENSION 2
            # (`D-IMPL-260` P-H). The effective request resolved above — the
            # caller's depth, the technical bound that admitted it, the
            # contract pin that declared it — travels onto the fulfilled
            # record, as the refused half already carries its determination.
            resolution=effective,
        )
        self.observer(assembled)

        # A GOVERNED REFUSAL IS RETURNED, NOT RAISED (D-60). A bad question is a
        # bad question, not a broken deployment, and a verdict returned as a
        # value cannot be swallowed by a bare `except`.
        if isinstance(assembled, ProductRequestViolation):
            return assembled

        # A declared-but-inert parameter is refused by the SDK's own tier step —
        # `src/ccf/products/request.py::refuse_request` step 2 (`_refuse_tier`) — as a
        # `ProductRequestViolation(reason="not-supported-at-tier")` returned as DATA
        # through the branch above (`24.5-L-12`/`L-13`); this seam has no branch of its own.

        # AMBIGUITY IN E FAILS CLOSED AS TYPED DATA, AND THE DOOR CARRIES IT
        # (`D-IMPL-245` (4), `CFT-G18`). More than one node answered to the
        # anchor's LEI. Dave: *"Debt must not become a substitute vocabulary
        # for policy refusal, and ambiguity in E must not be allowed downstream
        # as merely another finding."* A 404 would say nothing resolved, which
        # is false; serving whichever candidate the store listed first, with a
        # finding attached, would let the collision flow on as one more row in
        # `findings`. So the SDK kind is RETURNED — it is in `REFUSAL_KINDS`,
        # so `transport.py` and `server/compose.py` hand it to the door as
        # `anchor-ambiguity-refusal` without an edit — and never raised.
        #
        # THE CANDIDATES ARE THE IRIs THE KIND CARRIES BY DESIGN; the detail
        # names the count and the rule and NOTHING about which of them this
        # principal may see. Visibility is the audit plane's account, not the
        # caller's (the same line `_not_available` draws).
        if isinstance(assembled, produce.AnchorAmbiguous):
            return AnchorAmbiguityRefusal(
                anchor=assembled.anchor,
                candidates=frozenset(assembled.candidates),
                detail=(
                    f"anchor {assembled.anchor!r} resolves to"
                    f" {len(assembled.candidates)} nodes; §D.2 step 1 fails"
                    " closed on ambiguity rather than choosing one of them"
                    " (D-IMPL-245 (4))"
                ),
            )

        # AN UNRESOLVABLE ANCHOR IS A DIFFERENT KIND OF THING. A
        # `ProductRequestViolation` says *this class does not answer that
        # question*; §D.2's 404 says *this class answers it, and there is no such
        # family*.
        if isinstance(assembled, produce.AnchorUnresolvable):
            # THE ONE CANONICAL OUTCOME AN UNRESOLVABLE ANCHOR AND AN
            # UNAUTHORIZED PRINCIPAL SHARE (`D-27`, `D-IMPL-253` Q27 with
            # amendment 2 (4)). The kind carries the fabric's own determination
            # — `cause="nonexistent"` — and the disclosure step decides what a
            # consumer at their level is permitted to see of it; below `full`
            # the two causes are indistinguishable, which is the suppression
            # property `_not_available`'s prose used to carry alone. The type
            # HAS NO `subject` FIELD, so naming the anchor is not something
            # this seam could do by accident.
            return SubjectUnavailableRefusal(
                cause="nonexistent",
                detail=_not_available(assembled.anchor),
            )

        return AssemblyOutcome(
            payload=assembled.product.payload,
            # THIS ASSEMBLY REACHED FOR NOTHING OUTSIDE ITSELF, said as a named
            # claim rather than as a bare pair of empty tuples.
            consultations=NO_CONSULTATIONS,
            # ASSEMBLY MODE 1: no content is acquired at decision time, and no
            # LLM is reachable from any §D step. The whole product is a walk, a
            # normalization, a batched join and a circuit enumeration — every one
            # deterministic. `CFT-G12` is the gate that holds it, and it is
            # sabotaged by making an LLM client reachable.
            acquisitions=(),
            assembler_id=self.assembler_id,
            assembler_version=self.assembler_version,
            # This assembly binds no skill. Empty is the POSITIVE statement for a
            # wholly deterministic product, not an omission.
            skill_set_in_force=(),
            halflife_debt_profile=cast(
                _AssemblyState, assembled.scenario
            ).halflife_debt_profile,
        )


def observed_at(assembled: object) -> datetime | None:
    """The instant one assembly was asked as of, or ``None``."""
    request = getattr(getattr(assembled, "scenario", None), "request", None)
    return None if request is None else cast(datetime, request.asked_at)


def stores_opened(assembled: object) -> tuple[str, ...]:
    """Which SOURCE stores the ASSEMBLY opened — what `CFT-G10` reads.

    **The subject is the assembly and NOT the runner** (criterion 34, as
    clarified by Dave at Gate 1). The value is recorded inside
    `deployment.source_read`, where the connections are actually made, so a
    fixture that pre-opened both stores and handed the product a populated graph
    would not satisfy the gate. Policy is not that proof and is not consulted for
    it.
    """
    return tuple(getattr(assembled, "stores_opened", ()))
