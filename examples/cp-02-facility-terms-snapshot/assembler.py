"""The assembler seam — `ContextAssemblerProtocol`, conformed to structurally.

[ADAPT] all of it. [MECHANISM] the Protocol this satisfies.

**Nothing here reads a clock.** The instant is ``request.asked_at``, supplied by
the caller at serve time and by replay at replay time through the same code
path. Everything downstream — the as-of boundary, the freshness figure, the
content address — is a function of that argument.

**AND `expires_at` IS NOT EVEN A FUNCTION OF THAT.** It is the credit
agreement's own effective date plus the declared window (`deployment.expires_at`)
— the primitive this rung teaches. Two calls for the same facility at two
different instants return the same expiry, and gate `FTS-G01` asserts it.

**IDENTITY FIRST, THEN THE GOVERNED REFUSAL** — the ordering `D-IMPL-216` limb 1
established and `cp-01` first implemented. This deployment reads its declared
tenant and perspective from `ccf_config.yaml` before the spine runs, so identity
is settled before a governed refusal is even considered.
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
ASSEMBLER_ID = "cp-02.facility-terms-snapshot"
ASSEMBLER_VERSION = "1.0.0"


class _AssemblyState(Protocol):
    """The one thing the assembler reads off the deployment's own scenario."""

    @property
    def halflife_debt_profile(self) -> str:
        """The pinned ``ccf-artifact://`` reference the assembly ran under."""


def _unobserved(assembled: object) -> None:
    """The default observer: the run happened and nobody watched it."""


def _not_available(facility_id: str) -> str:
    """The ONE refusal text for "you are not getting this facility".

    A single function with a single caller-facing string, because §B.2's
    suppression rule is a statement about what a caller can DISTINGUISH, and two
    separately-worded messages drift apart the moment either is edited. A
    facility that does not exist and a facility this principal may not see
    produce byte-identical output; only the replay record tells them apart.

    It deliberately does not say "not entitled", does not name the principal,
    and does not say whether the facility exists.
    """
    return (
        f"facility {facility_id!r} is not available (404); §D.2 fails closed"
        " rather than returning an empty payload. A facility_id has no external"
        " registry behind it, so an empty payload would read as 'this facility"
        " has no terms'"
    )


@dataclass(frozen=True)
class FacilityAssembler:
    """Assemble one facility terms snapshot through the governed spine.

    Conforms to ``src/ccf/agents/assembler.py::ContextAssemblerProtocol``
    structurally. ``assemble`` is keyword-only because the Protocol declares it
    so, and the Protocol says why: *"the cost of a transposition would be an
    assembly attributed to the wrong tenant."*

    **``observer`` is not an escape hatch.** The Protocol pins the return type
    to ``AssemblyOutcome``, which carries the governance of the *assembly* and
    not the served vessel, its content address or its replay reference. A client
    that wants those needs the spine's full return value, and the honest way to
    give it one is a callback that observes rather than a widened return type
    that would make this seam a different seam.
    """

    config: Path
    root: Path
    connection: Mapping[str, str]
    read: Callable[..., Any]
    plan_class: type[Any]
    #: Declared-but-inert parameters, from the deployment's request contract
    #: (Standard §2.4). Defaulted to the deployment's own declaration rather
    #: than to an empty mapping — a seam that silently supported everything the
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
            AssemblyRefused: ``tenant_id`` or ``perspective`` disagrees with
                what this deployment declares, or the anchor resolved to no
                facility. **Identity and existence only.**
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

        # A GOVERNED REFUSAL IS RETURNED, NOT RAISED (D-60). A bad question is a
        # bad question, not a broken deployment, and a verdict returned as a
        # value cannot be swallowed by a bare `except`.
        if isinstance(assembled, ProductRequestViolation):
            return assembled

        # A DECLARED-BUT-INERT PARAMETER IS A CONTRACT VERDICT AND THIS SEAM
        # CANNOT RETURN IT AS ONE — the same SDK-surface finding `cp-01`
        # recorded, met a second time and therefore no longer a one-off.
        #
        #   `ProductRequestViolation.reason` is a CLOSED `Literal` of four
        #   values — undeclared-parameter · missing-required-parameter ·
        #   type-mismatch · class-mismatch. Standard §9 requires
        #   `400 not_supported_at_tier` as a DISTINCT condition and §2.4 makes
        #   the declared-but-inert parameter a first-class obligation. The
        #   vocabulary has no member for it.
        #
        # It matters more here than at rung 01: a facility carrying 21
        # amendments visibly HAS a history to ask about, so `as_of` is a
        # question a caller will actually ask.
        if isinstance(assembled, produce.ParameterNotSupported):
            raise AssemblyRefused(
                f"{assembled.status} {assembled.reason}: {assembled.parameter}"
                " — declared by this class and always refused (Standard §2.4)."
                " This verdict is raised rather than returned because"
                " ProductRequestViolation.reason is a closed Literal with no"
                " member for it; see CP-SPEC-002 §F.4"
            )

        # AN UNRESOLVABLE ANCHOR IS A DIFFERENT KIND OF THING. A
        # `ProductRequestViolation` says *this class does not answer that
        # question*; §D.2 step 1's 404 says *this class answers it, and there is
        # no such facility*.
        if isinstance(assembled, produce.AnchorUnresolvable):
            raise AssemblyRefused(_not_available(assembled.anchor))

        # AND A SUPPRESSED FACILITY MUST BE INDISTINGUISHABLE FROM THAT ONE.
        # §B.2, §D.3, gate `FTS-G04`.
        #
        # THIS WAS A DEFECT IN THE FIRST BUILD OF THIS EXAMPLE AND THE RUN IS
        # WHAT FOUND IT. A facility the Policy step removed returned `200` with
        # `facility: null`, while a facility that does not exist raised `404`.
        # Two different answers — so a caller probing facility ids could learn
        # WHICH IDS EXIST simply by watching which ones came back null rather
        # than refused. That is precisely the disclosure the suppression rule
        # forbids: the payload carried no marker of what was withheld, and the
        # STATUS carried it instead.
        #
        # Both now raise the same refusal, with the same text, so the caller
        # cannot separate "not entitled" from "not there".
        #
        # THE DISTINCTION IS NOT LOST — IT MOVES TO WHERE IT BELONGS. The
        # product was assembled, gated, and its replay record written before
        # this branch is reached, so the audit plane holds the full account:
        # which principal asked, which policy version was in force, and that a
        # facility existed and was withheld. The audit knows; the caller does
        # not. That is the shape §B.2 asks for.
        if assembled.product.payload.get("facility") is None:
            raise AssemblyRefused(_not_available(request.subject))

        return AssemblyOutcome(
            payload=assembled.product.payload,
            # THIS ASSEMBLY REACHED FOR NOTHING OUTSIDE ITSELF, said as a named
            # claim rather than as a bare pair of empty tuples.
            consultations=NO_CONSULTATIONS,
            # Assembly Mode 1: no content is acquired at decision time. In
            # particular NO DOCUMENT IS REACHED — `source_offsets` is populated
            # on 60 of 60 rows and is deliberately never read (§C.4 trap 3).
            acquisitions=(),
            assembler_id=self.assembler_id,
            assembler_version=self.assembler_version,
            # This assembly binds no skill. Empty is the positive statement for
            # a wholly deterministic product.
            skill_set_in_force=(),
            halflife_debt_profile=cast(
                _AssemblyState, assembled.scenario
            ).halflife_debt_profile,
        )


def observed_at(assembled: object) -> datetime | None:
    """The instant one assembly was asked as of, or ``None``."""
    request = getattr(getattr(assembled, "scenario", None), "request", None)
    return None if request is None else cast(datetime, request.asked_at)
