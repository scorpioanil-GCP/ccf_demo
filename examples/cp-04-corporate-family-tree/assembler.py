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
from pathlib import Path
from typing import Any, Protocol, cast

from ccf.agents.assembler import NO_CONSULTATIONS, AssemblyOutcome
from ccf.agents.errors import AssemblyRefused
from ccf.products.request import ProductRequest, ProductRequestViolation
from ccf.projection.plan import Perspective

import deployment
import produce

#: Who assembled this product, and under what version of that behavior. Both
#: travel on the outcome because a payload is only reproducible alongside the
#: computation that produced it.
ASSEMBLER_ID = "cp-04.corporate-family-tree"
ASSEMBLER_VERSION = "1.0.0"


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
    ) -> AssemblyOutcome | ProductRequestViolation:
        """Assemble one answer to ``request`` for ``perspective``.

        Returns:
            The :class:`~ccf.agents.assembler.AssemblyOutcome`, or a
            :class:`~ccf.products.request.ProductRequestViolation` RETURNED as
            data when the question does not conform to the declared contract
            (D-60).

        Raises:
            AssemblyRefused: ``tenant_id`` or ``perspective`` disagrees with what
                this deployment declares, the requested ``max_depth`` is outside
                the declared bounds, a declared-but-inert parameter was supplied,
                or the anchor resolved to no servable family. **Identity,
                contract and existence only.**
        """
        # --- Identity, settled BEFORE anything is assembled. ---------------
        declared_tenant = deployment.tenant_id()
        if declared_tenant != tenant_id:
            raise AssemblyRefused(
                f"assembly for tenant {tenant_id!r} was asked of a deployment"
                f" declared as tenant {declared_tenant!r} (question:"
                f" {request.schema_name!r}@{request.schema_version!r}); an"
                " assembler assembles for its own tenant and no other"
            )
        declared_roles = deployment.declared_roles()
        if perspective.role not in declared_roles:
            raise AssemblyRefused(
                f"assembly under role {perspective.role!r} was asked of a"
                f" deployment that conditions on {list(declared_roles)}"
                f" (question: {request.schema_name!r}); the perspective"
                " conditions what Π produced, so an undeclared role served a"
                " default view would be a perspective widened by omission"
            )

        # THE DEPTH IS RESOLVED BEFORE THE SPINE RUNS, and the split is
        # deliberate rather than an awkward signature: an over-ceiling depth is a
        # 400 and an unresolvable anchor is a 404, and one return type cannot
        # hold both without the caller telling them apart by inspection.
        max_depth = deployment.resolve_max_depth(request.parameters)

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
        )
        self.observer(assembled)

        # A GOVERNED REFUSAL IS RETURNED, NOT RAISED (D-60). A bad question is a
        # bad question, not a broken deployment, and a verdict returned as a
        # value cannot be swallowed by a bare `except`.
        if isinstance(assembled, ProductRequestViolation):
            return assembled

        # ABOVE THE CEILING IS REFUSED BY NAME AND NEVER CLAMPED (`D-07`,
        # `CFT-G03`). The sabotage that gate names is a silent clamp, and a
        # clamp is a different program rather than a nearby one: the request
        # says 8, the walk does 6, the payload looks fine and the content
        # address greens.
        if isinstance(assembled, deployment.DepthOutOfBounds):
            raise AssemblyRefused(
                f"400 {assembled.parameter}={assembled.requested} is outside the"
                f" declared bounds {assembled.minimum}..{assembled.maximum}."
                " REFUSED BY NAME, never clamped — a clamped depth answers a"
                " question nobody asked, with no error"
            )

        # A DECLARED-BUT-INERT PARAMETER IS A CONTRACT VERDICT AND THIS SEAM
        # CANNOT RETURN IT AS ONE — the SDK-surface finding `cp-01` recorded,
        # `cp-02` met a second time and `cp-03` a third. **THIS IS THE FOURTH
        # RUNG IN A ROW**, which is what turns a repeated observation into a
        # shape:
        #
        #   `ProductRequestViolation.reason` is a CLOSED `Literal` of four
        #   values — undeclared-parameter · missing-required-parameter ·
        #   type-mismatch · class-mismatch. Standard §9 requires
        #   `400 not_supported_at_tier` as a DISTINCT condition and §2.4 makes
        #   the declared-but-inert parameter a first-class obligation. The
        #   vocabulary has no member for it.
        #
        # The pressure is specific at this rung: this is the first product whose
        # STORE carries a time axis of its own, so "give me the family as it
        # stood last March" looks answerable and is not.
        if isinstance(assembled, produce.ParameterNotSupported):
            raise AssemblyRefused(
                f"{assembled.status} {assembled.reason}: {assembled.parameter}"
                " — declared by this class and always refused (Standard §2.4)."
                " This verdict is raised rather than returned because"
                " ProductRequestViolation.reason is a closed Literal with no"
                " member for it; see CP-SPEC-004 §F.4"
            )

        # AN UNRESOLVABLE ANCHOR IS A DIFFERENT KIND OF THING. A
        # `ProductRequestViolation` says *this class does not answer that
        # question*; §D.2's 404 says *this class answers it, and there is no such
        # family*.
        if isinstance(assembled, produce.AnchorUnresolvable):
            raise AssemblyRefused(_not_available(assembled.anchor))

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
