"""This deployment's assembler — the producer seam, implemented.

[ADAPT] the identity and the wiring. [MECHANISM] the seam itself is the SDK's.

``src/ccf/agents/assembler.py::ContextAssemblerProtocol`` is the surface a
Context Product's *producer* implements, and its own docstring is explicit
about how: *"a deployment substitutes its own assembler by conforming, never by
inheriting, and the SDK's reference implementation carries no privileged
status."* This module is a deployment doing exactly that. It inherits nothing
and imports the Protocol only so a reader — and a test — can check the
conformance the type system is otherwise silent about.

**Why this is not
``src/ccf/agents/assembler.py::DeterministicAssembler``, stated so the next
reader does not conclude the SDK's reference assembler is the path a Context
Product takes.** The reference assembler exists *"to give a deployment
something to diff its own assembler against"*, and three properties make it
that rather than this:

* it does not run Π — it **holds** Π's already-computed output, which means
  something else has to have run the two-stage execution before it is
  constructed;
* it returns an ``src/ccf/agents/assembler.py::AssemblyOutcome`` rather than a
  ``src/ccf/products/contract.py::ContextProductContract``, so it is not on the
  path that reaches the three validation gates;
* constructing one requires an ``src/ccf/agents/agent.py::Agent``, which
  ``tools/lints/no_hardcoding.py``'s factory-bypass rule requires come from
  ``src/ccf/agents/factory.py::AgentFactory`` reading a definition artifact —
  a whole Control Plane surface this product does not declare and does not
  need.

Diffing against it is the point of naming it here.

**Why this module puts the tree outside one guard, and that is deliberate.**
The import of ``ccf.agents`` below is precisely why
``tests/examples/test_section_one_is_agent_free.py`` is not widened to cover
``cp-*`` (`24-CONTEXT.md` `D-23`/`D-24`). *"Section 1 declares no agent"* is a
Section-1 rule — it says the fabric can be shown without an agent in front of
it — and it is not a Context-Product rule. Bringing this tree under that guard
would fail the example on its own core design, which is the opposite of what a
guard is for. The matching reason is written into the guard's own file; this
paragraph is the other end of that pair.

**This module prints nothing and opens no marker region.** Exactly one module
in the tree drives the run and prints, and it is ``run.py``; exactly one opens
the canonical regions, and it is ``produce.py``.
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

import produce

#: Who assembled this product, and under what version of that behaviour. Both
#: travel on the outcome because a payload is only reproducible alongside the
#: computation that produced it — the same reason the freshness scorer pins its
#: own id. Changing what `assemble` does is a version change here.
ASSEMBLER_ID = "cp-00.institutional-holders"
ASSEMBLER_VERSION = "1.0.0"


class _AssemblyState(Protocol):
    """The one thing the assembler reads off the deployment's own scenario.

    A narrow structural type rather than an import of the deployment's
    dataclass: this module needs the pinned axis-5 reference and nothing else
    from the run, and naming exactly that keeps the seam from quietly acquiring
    a second reason to know about the deployment's vocabulary.
    """

    @property
    def halflife_debt_profile(self) -> str:
        """The pinned ``ccf-artifact://`` reference the assembly ran under."""


def _unobserved(assembled: object) -> None:
    """The default observer: the run happened and nobody watched it."""


@dataclass(frozen=True)
class HoldersAssembler:
    """Assemble one institutional-holders product through the governed spine.

    Conforms to ``src/ccf/agents/assembler.py::ContextAssemblerProtocol``
    structurally. ``assemble`` is keyword-only because the Protocol declares it
    so, and the Protocol says why: *"the cost of a transposition would be an
    assembly attributed to the wrong tenant."*

    **Nothing here reads a clock.** The instant is ``request.asked_at``,
    supplied by the caller at serve time and by replay at replay time through
    the same code path. Everything downstream — the as-of boundary, the TTL
    verdict, the freshness figure, the content address — is a function of that
    argument.

    **``observer`` is not an escape hatch, and it is worth saying why it is
    here.** The Protocol pins the return type to ``AssemblyOutcome``, which
    carries the payload and the governance of the *assembly*: what was
    consulted, which skills were in force, which debt profile. It does not
    carry the served vessel, its content address, its debt figure or the replay
    reference — those belong to the product, not to the assembler. A client
    that wants to show them needs the spine's full return value, and the honest
    way to give it one is a callback that observes what happened rather than a
    widened return type that would make this seam a different seam. The
    observer cannot change the outcome: it is called with a frozen value and
    its return is discarded.

    Args:
        config: The one Control Plane document this deployment boots from.
        root: Scratch space for the run — the per-run graph file and the
            file-backed artifact store both land under it.
        connection: The composed backend settings, from the deployment.
        read: The deployment's own artifact reader.
        plan_class: Π, as a class the fabric constructs.
        observer: Called with the spine's return value before the outcome is
            built. Defaults to a no-op.
    """

    config: Path
    root: Path
    connection: Mapping[str, str]
    read: Callable[..., Any]
    plan_class: type[Any]
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

        Runs the spine, hands the observer what it produced, and returns the
        governed outcome.

        **The two cross-checks run after the spine, not before it, and that is
        a property of an in-process deployment rather than a shortcut.** The
        tenant and the perspective in force are facts of the *booted* fabric,
        and the fabric boots inside this call; a check before boot would be a
        check against values this assembler had to guess. Both are refusals
        rather than repairs, in the reference assembler's own posture: an
        assembler does not choose which of two disagreeing statements is right,
        because only the deployment's author knows which was meant.

        Returns:
            The :class:`~ccf.agents.assembler.AssemblyOutcome`, or a
            :class:`~ccf.products.request.ProductRequestViolation` RETURNED as
            data when the question does not conform to the declared contract
            (D-60, closed in phase 24.1.1).

        Raises:
            AssemblyRefused: ``tenant_id`` or ``perspective`` disagrees with
                what the booted deployment declares. **Identity only.** The
                third case — a question this class does not answer — is a
                GOVERNED refusal and is returned, not raised.
        """
        assembled = produce.assemble_and_serve(
            config=self.config,
            connection=self.connection,
            read=self.read,
            plan_class=self.plan_class,
            request=request,
            root=self.root,
        )
        self.observer(assembled)

        # A GOVERNED REFUSAL IS RETURNED, NOT RAISED (D-60, closed in phase
        # 24.1.1). `refuse_request` produces a `ProductRequestViolation` as
        # DATA — a bad question is a bad question, not a broken deployment —
        # and `ContextAssemblerProtocol.assemble` now has the return channel
        # to carry it, so this assembler hands the caller the value rather
        # than a message about it. A verdict returned as a value cannot be
        # swallowed by a bare `except`.
        if isinstance(assembled, ProductRequestViolation):
            return assembled

        if assembled.tenant_id != tenant_id:
            raise AssemblyRefused(
                f"assembly for tenant {tenant_id!r} was asked of a deployment"
                f" that booted as tenant {assembled.tenant_id!r} (question:"
                f" {request.schema_name!r}@{request.schema_version!r}); an"
                " assembler assembles for its own tenant and no other"
            )
        declared = assembled.scenario.perspective
        if perspective.role != declared.role:
            raise AssemblyRefused(
                f"assembly under role {perspective.role!r} was asked of a"
                f" deployment declared under role {declared.role!r} (question:"
                f" {request.schema_name!r}); the perspective conditions what Π"
                " produced, so a different one is a different answer"
            )

        return AssemblyOutcome(
            payload=assembled.product.payload,
            # THIS ASSEMBLY REACHED FOR NOTHING OUTSIDE ITSELF, said as a
            # named claim rather than as a bare pair of empty tuples — which
            # is what makes it distinguishable from a record somebody forgot
            # to populate.
            consultations=NO_CONSULTATIONS,
            # Assembly Mode 1: no content is acquired at decision time, so
            # there is nothing for the one route model-produced content may
            # travel to carry.
            acquisitions=(),
            assembler_id=self.assembler_id,
            assembler_version=self.assembler_version,
            # This assembly binds no skill. Empty is the positive statement
            # for a wholly deterministic product, and a decision replays
            # against the skills it had rather than the skills it has now.
            skill_set_in_force=(),
            # A REF, not the resolved artifact: the profile has its own
            # version lane, and inlining it would give one record two version
            # identities.
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
