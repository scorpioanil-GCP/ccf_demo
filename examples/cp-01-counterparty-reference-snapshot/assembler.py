"""The assembler seam — `ContextAssemblerProtocol`, conformed to structurally.

[ADAPT] all of it. [MECHANISM] the Protocol this satisfies.

**Nothing here reads a clock.** The instant is ``request.asked_at``, supplied
by the caller at serve time and by replay at replay time through the same code
path. Everything downstream — the as-of boundary, the TTL verdict, the freshness
figure, the content address — is a function of that argument.

**THE REFUSAL ORDERING IS CORRECTED HERE, AND THAT IS THIS FILE'S ONE
INHERITED OBLIGATION.** `D-IMPL-216` limb 1 records that
`examples/cp-00-institutional-holders/assembler.py::HoldersAssembler.assemble`
returns the governed `ProductRequestViolation` **before** its tenant and
perspective checks, while
`src/ccf/agents/assembler.py::DeterministicAssembler.assemble` does the
opposite — so a caller asking a non-conforming question OF THE WRONG TENANT got
a contract refusal from the example and an identity refusal from the SDK. Two
reviewers found it at the 24.1.1 close panel; it was left uncorrected because
fixing it in cp-00 meant restructuring that example's data flow, which criterion
16 fenced, and **"the next Context Product example" was named as the
inheritor.** This is that example.

The fix is available here for a reason worth stating rather than assuming: cp-00
learns its tenant from the spine's return value, which exists only *after*
assembly, so it could not check identity first without a redesign. **This
deployment reads its declared tenant and perspective from `ccf_config.yaml`
before the spine runs**, so identity is settled before a governed refusal is
even considered — the SDK's ordering, reached by having the value earlier rather
than by moving a branch.
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
#: computation that produced it. Changing what `assemble` does is a version
#: change here.
ASSEMBLER_ID = "cp-01.counterparty-reference-snapshot"
ASSEMBLER_VERSION = "1.0.1"


class _AssemblyState(Protocol):
    """The one thing the assembler reads off the deployment's own scenario.

    A narrow structural type rather than an import of the deployment's
    dataclass: this module needs the pinned axis-5 reference and nothing else
    from the run.
    """

    @property
    def halflife_debt_profile(self) -> str:
        """The pinned ``ccf-artifact://`` reference the assembly ran under."""


def _unobserved(assembled: object) -> None:
    """The default observer: the run happened and nobody watched it."""


@dataclass(frozen=True)
class CounterpartyAssembler:
    """Assemble one counterparty reference snapshot through the governed spine.

    Conforms to ``src/ccf/agents/assembler.py::ContextAssemblerProtocol``
    structurally. ``assemble`` is keyword-only because the Protocol declares it
    so, and the Protocol says why: *"the cost of a transposition would be an
    assembly attributed to the wrong tenant."*

    **``observer`` is not an escape hatch.** The Protocol pins the return type
    to ``AssemblyOutcome``, which carries the governance of the *assembly* and
    not the served vessel, its content address or its replay reference. A client
    that wants those needs the spine's full return value, and the honest way to
    give it one is a callback that observes rather than a widened return type
    that would make this seam a different seam. The observer is called with a
    frozen value and its return is discarded.

    Args:
        config: The one Control Plane document this deployment boots from.
        root: Scratch space for the run.
        connection: The composed backend settings, from the deployment.
        read: The deployment's own artifact reader.
        plan_class: Π, as a class the fabric constructs.
        observer: Called with the spine's return value. Defaults to a no-op.
    """

    config: Path
    root: Path
    connection: Mapping[str, str]
    read: Callable[..., Any]
    plan_class: type[Any]
    #: Declared-but-inert parameters, from the deployment's request contract
    #: (Standard §2.4). Carried for the declaration's sake and defaulted to
    #: the deployment's own declaration rather than to an empty mapping. The
    #: refusal itself is the SDK's tier step (`refuse_request`,
    #: `not-supported-at-tier`), not anything this seam does.
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

        **IDENTITY FIRST, THEN THE GOVERNED REFUSAL** — the ordering
        `D-IMPL-216` limb 1 asked this example to establish. An assembly
        attributed to the wrong tenant is not a question worth evaluating, so
        the tenant and the perspective are checked against what this deployment
        DECLARES, before the spine runs and before a contract verdict exists.

        Returns:
            The :class:`~ccf.agents.assembler.AssemblyOutcome`, or a
            :class:`~ccf.products.request.ProductRequestViolation` RETURNED as
            data when the question does not conform to the declared contract
            (D-60).

        Raises:
            AssemblyRefused: ``tenant_id`` or ``perspective`` disagrees with
                what this deployment declares, or the anchor resolved to no
                entity. **Identity and existence only.** A question this class
                does not answer is a GOVERNED refusal and is returned.
        """
        # --- Identity, settled BEFORE anything is assembled. ---------------
        # Read from `ccf_config.yaml`, which is the same document the fabric
        # boots from — so this is a check against what the deployment declares
        # rather than against a value the assembler had to guess.
        declared_tenant = deployment.tenant_id()
        if declared_tenant != tenant_id:
            raise AssemblyRefused(
                f"assembly for tenant {tenant_id!r} was asked of a deployment"
                f" declared as tenant {declared_tenant!r} (question:"
                f" {request.schema_name!r}@{request.schema_version!r}); an"
                " assembler assembles for its own tenant and no other"
            )
        declared_perspective = deployment.perspective()
        if perspective.role != declared_perspective.role:
            raise AssemblyRefused(
                f"assembly under role {perspective.role!r} was asked of a"
                f" deployment declared under role {declared_perspective.role!r}"
                f" (question: {request.schema_name!r}); the perspective"
                " conditions what Π produced, so a different one is a"
                " different answer"
            )

        assembled = produce.assemble_and_serve(
            config=self.config,
            connection=self.connection,
            read=self.read,
            plan_class=self.plan_class,
            request=request,
            root=self.root,
            unsupported=self.unsupported,
        )
        self.observer(assembled)

        # A GOVERNED REFUSAL IS RETURNED, NOT RAISED (D-60). `refuse_request`
        # produces a `ProductRequestViolation` as DATA — a bad question is a bad
        # question, not a broken deployment — and the Protocol has the return
        # channel to carry it. A verdict returned as a value cannot be swallowed
        # by a bare `except`.
        if isinstance(assembled, ProductRequestViolation):
            return assembled

        # A declared-but-inert parameter is refused by the SDK's own tier step —
        # `src/ccf/products/request.py::refuse_request` step 2 (`_refuse_tier`) — as a
        # `ProductRequestViolation(reason="not-supported-at-tier")` returned as DATA
        # through the branch above (`24.5-L-12`/`L-13`); this seam has no branch of its own.

        # AN UNRESOLVABLE ANCHOR IS A DIFFERENT KIND OF THING, and the
        # distinction is worth keeping rather than collapsing into the line
        # above. A `ProductRequestViolation` says *this class does not answer
        # that question*; §D.2 step 1's 404 says *this class answers it, and
        # there is no such entity*. The Protocol's return channel carries
        # contract verdicts, so existence is raised — a caller that wants the
        # 404 as data calls the spine, which returns it as data (`run.py`).
        if isinstance(assembled, produce.AnchorUnresolvable):
            raise AssemblyRefused(
                f"anchor {assembled.anchor!r} resolved to no entity through"
                " either identity authority (404); §D.2 step 1 fails closed"
                " rather than returning an empty payload"
            )

        return AssemblyOutcome(
            payload=assembled.product.payload,
            # THIS ASSEMBLY REACHED FOR NOTHING OUTSIDE ITSELF, said as a named
            # claim rather than as a bare pair of empty tuples — which is what
            # makes it distinguishable from a record somebody forgot to
            # populate.
            consultations=NO_CONSULTATIONS,
            # Assembly Mode 1: no content is acquired at decision time.
            acquisitions=(),
            assembler_id=self.assembler_id,
            assembler_version=self.assembler_version,
            # This assembly binds no skill. Empty is the positive statement for
            # a wholly deterministic product, and a decision replays against the
            # skills it had rather than the skills it has now.
            skill_set_in_force=(),
            # A REF, not the resolved artifact: the profile has its own version
            # lane, and inlining it would give one record two version identities.
            halflife_debt_profile=cast(
                _AssemblyState, assembled.scenario
            ).halflife_debt_profile,
        )


def observed_at(assembled: object) -> datetime | None:
    """The instant one assembly was asked as of, or ``None``.

    A reader for whatever the observer captured, so a client never reaches into
    the spine's return type by attribute name in more than one place.
    """
    request = getattr(getattr(assembled, "scenario", None), "request", None)
    return None if request is None else cast(datetime, request.asked_at)
