"""Typed failures of the agent-definition surface (CLAUDE.md §6 — SDK-defined).

The taxonomy mirrors :class:`~ccf.controlplane.artifacts.ArtifactLoadError`:
raised — never repaired — because each failure mode is a silent-corruption
risk if softened. A definition that almost satisfies its schema, or a prompt
whose parameters almost match its template, is exactly the artifact that
produces an unreplayable decision later.

One member here is a **value**, not an exception: :class:`AssemblyRefusal`
(``24.5-L-11``) is the returned-as-data form of an assembly-time refusal,
housed beside the exception it is the sibling of so the two channels are read
together.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from typing import Final

from ccf.contracts.base import CCFContract

__ccf_mode__ = "algorithmic"

__all__ = [
    "ASSEMBLY_REASON_TENANT_MISMATCH",
    "ASSEMBLY_REASON_UNDECLARED_ROLE",
    "AgentConstructionError",
    "AgentDefinitionError",
    "AssemblyRefusal",
    "AssemblyRefused",
    "ConsumptionRefused",
    "FalseGrantClaimError",
    "NotYetBound",
    "PromptRenderRefused",
    "PromptValidationError",
    "SkillNotBound",
]


#: :attr:`AssemblyRefusal.reason` for a question addressed to an agent declared
#: for a different tenant (``24.6-L-02``; ``D-IMPL-253`` amendment 2 (3), which
#: names tenant mismatch as a governed determination: the fabric holds both
#: tenants and knows exactly which two disagreed). An SDK token because the
#: SDK's own :class:`~ccf.agents.assembler.DeterministicAssembler` is what
#: makes this determination; a deployment's assembler keeps its own vocabulary.
ASSEMBLY_REASON_TENANT_MISMATCH: Final[str] = "tenant-mismatch"

#: :attr:`AssemblyRefusal.reason` for a question asked under a role the agent
#: was not declared under (``24.6-L-02``; ``D-IMPL-253`` amendment 2 (3), which
#: names undeclared role beside tenant mismatch). Axis 3 is channel-1 identity,
#: so a different perspective is a different agent — but *which* two roles
#: disagreed is something the fabric knows, which is what makes it a
#: determination rather than a failure.
ASSEMBLY_REASON_UNDECLARED_ROLE: Final[str] = "undeclared-role"


class AgentDefinitionError(ValueError):
    """An agent definition artifact cannot be admitted as written.

    Raised — never repaired — for defects the schema alone cannot express:
    the schema layer refuses malformed documents at parse time, and this error
    covers definition-level rule violations discovered after parsing
    (CLAUDE.md §6.4; D-IMPL-28).
    """


class PromptValidationError(ValueError):
    """A prompt artifact or instruction binding fails parse-only validation.

    Raised — never repaired — when a template's undeclared variables and its
    declared parameters differ in either direction, when a binding's declared
    parameters mismatch the artifact's, or when the template itself does not
    parse (D-13; CLAUDE.md §6.2 axis 6).
    """


class PromptRenderRefused(ValueError):
    """A prompt render was refused rather than performed (T-06-60).

    Raised — never degraded around, never rendered partially — for the two
    conditions :func:`ccf.agents.prompts.render_instruction` refuses:

    * the template attempted something the Jinja2 sandbox forbids (attribute
      traversal toward ``__class__``/``__globals__``/``__subclasses__`` and the
      rest of the escape vocabulary), chained from the underlying
      ``jinja2.exceptions.SecurityError``;
    * the supplied parameter values do not exactly match the binding's pinned
      parameters, in either direction.

    Distinct from :class:`PromptValidationError`, which is about an artifact
    being *admissible*; this is about a render being *performed*. Keeping them
    apart matters because I.3 makes artifact sources remote-influenced, and a
    refusal at render time is a security event a caller may want to audit
    differently from a malformed artifact at load time.
    """


class AgentConstructionError(ValueError):
    """The inputs handed to ``Agent`` do not describe one coherent agent.

    Raised by the ``Agent`` constructor when the identity block, the
    definition, and the composed components disagree — a mismatched content
    hash, a composition that is not the definition's declared archetype list,
    or components that do not realize it. The factory computes these inputs
    from one resolved definition, so this firing means construction was
    attempted around the factory or against drifted state (CLAUDE.md §6.4;
    D-12: the constructor validates, the lint enforces no-bypass — no token).
    """


class SkillNotBound(KeyError):
    """An agent was asked to invoke a skill no grant has bound to it.

    ``KeyError``-shaped because the bound skill-set is a mapping and an absent
    capability is an absent key — but typed, because "this agent does not
    currently have that capability" is a governance fact (CLAUDE.md §6.2
    channel 2), not a lookup accident. Grants land with the skilling wave.
    """


class NotYetBound(RuntimeError):
    """A granted ``mcp`` or ``a2a`` skill was dispatched in a build that
    lacks its transport.

    An **exception, not a returned refusal**, and the line is deliberate
    (PATTERNS "Refusal vs exception line"; 05-RESEARCH.md Open Question 2 —
    RESOLVED as typed exception): nothing about the artifact is bad — the
    entry validated, registered, and passed both governance tiers — but this
    *build* ships no MCP/A2A dispatch transport (D-08; I.3 binds them).
    A missing transport is a deployment-shape fact, like a missing Control
    Plane key, not an expected governance outcome a caller inspects.
    """


class FalseGrantClaimError(ValueError):
    """A dimension-4 serialization would record a false zero-grants claim.

    Raised — never repaired — when a caller passes the positive
    ``NO_GRANTS_SET_HASH`` claim to
    :meth:`~ccf.agents.agent.Agent.perspective_conditioning` while the
    agent's bound skill-set is non-empty: the agent itself knows zero grants
    cannot be true, so recording the claim would corrupt replay dimension 4
    at write time (WR-01; CLAUDE.md §6.2 — the skill-set in force at decision
    time lands in replay *by construction*, not by caller discipline).
    """


class AssemblyRefused(ValueError):
    """An assembler could not reach a valid governed determination at all.

    Raised — never repaired — when an internal invariant, a configuration
    contradiction or a runtime condition leaves the assembler unable to
    determine anything: a corrupted declaration, two authoritative inputs that
    disagree about what is true, a substrate that did not answer. It is the
    *failure* channel, and it is deliberately narrow.

    **The boundary, in Dave's words** (``D-IMPL-253`` amendment 2 (3), recorded
    at ``24.6-RULINGS.md`` §4; the layers are ``D-IMPL-254``'s):

        *"If the fabric has enough information to reach a valid governed
        determination, return data. If it cannot reliably reach a governed
        determination because an internal invariant/configuration/runtime
        condition has failed, raise."*

    **``24.5-L-11``'s framing is SUPERSEDED by that rule** (``24.6-L-02``,
    ``24.6-L-16``). This class used to say it was *"kept as a raise, and not
    retyped"* for channel-1 identity — a tenant that is not the agent's, a
    perspective that is not the axis-3 role it was declared under. Those two
    are outcomes the fabric **can** determine: it holds both tenants and both
    roles and knows exactly which pair disagreed, so under the rule above they
    are governed determinations and they RETURN, as
    :class:`AssemblyRefusal` carrying
    :data:`ASSEMBLY_REASON_TENANT_MISMATCH` or
    :data:`ASSEMBLY_REASON_UNDECLARED_ROLE`. The SDK's own
    :class:`~ccf.agents.assembler.DeterministicAssembler` returns them, and
    ``src/`` raises this class nowhere.

    **It is not converted mechanically, and that half of the ruling is as
    load-bearing as the first** (``D-IMPL-253`` Q15: *"Don't mechanically
    convert every existing AssemblyRefused call merely because it currently
    uses that class."*). A deployment that raises this for a genuine
    invariant failure is right to, and no door catches it: a raised
    ``AssemblyRefused`` still reaches a client as the protocol-native error,
    which is what a broken deployment should look like. Returning it as data
    would hide the break behind a governed "no".

    The sibling of :class:`ConsumptionRefused` on the other face of the fabric:
    that one refuses a product an agent may not read, this one says an assembly
    could not be determined at all (CLAUDE.md §6.2; §6.1).

    The value form is :class:`AssemblyRefusal`, and :meth:`as_refusal` is the
    conversion an assembler that has caught **its own** raise may perform. The
    SDK performs none on anyone's behalf.
    """

    def as_refusal(self) -> AssemblyRefusal:
        """This raise, as the value the D-60 channel carries.

        ``reason`` is the fixed token ``"assembly-refused"`` — the exception's
        own name in the vocabulary's spelling — and ``detail`` is
        ``str(self)``, unchanged. A conversion and nothing more: it invents no
        prose and reads no state, so an assembler that catches its own raise
        and returns this envelopes identically to one that returned the value
        to begin with.
        """
        return AssemblyRefusal(reason="assembly-refused", detail=str(self))


class AssemblyRefusal(CCFContract):
    """An assembly-time refusal, returned as data (``24.5-L-11``).

    SDK-defined (CLAUDE.md §6, §11: *refusal is data*). The whitepaper
    specifies the three validation gates that refuse a candidate product
    (§7.6); it specifies no shape for an *assembler's own* refusal, so this
    one is the SDK's, on the posture :mod:`ccf.products.gates` states at its
    head — a refusal returned as data cannot be swallowed by a bare
    ``except`` — and on the D-60 channel :class:`~ccf.agents.assembler.ContextAssemblerProtocol`
    already opened for :class:`~ccf.products.request.ProductRequestViolation`.

    **Why a value beside the kept exception.** :class:`AssemblyRefused` is
    raised for channel-1 identity disagreements and stays so. But the ladder
    met assembly-time refusals that are *answers*, not mis-deliveries — a tier
    the class does not serve, a capability it does not have — and an
    exception is the wrong shape for those: measured against ``mcp==1.28.1``
    (``24.4`` deferred item 9), a raise escaping the MCP tool body reaches the
    client as ``ToolError`` prose with ``isError=True``, which a consumer would
    have to string-parse. Returning this value instead lets
    :func:`~ccf.products.door.door_refusal` translate it through
    :data:`~ccf.products.refusal.REFUSAL_KINDS` (token ``assembly-refusal``)
    into the one canonical envelope, so the verdict arrives typed.

    A deployment chooses per refusal: raise for identity, return this for an
    answer. The SDK ships the kind and converts nothing on the deployment's
    behalf.

    Attributes:
        reason: The assembler's own token for why. A closed vocabulary is the
            deployment's to declare (CINV-01); the SDK fixes **three** tokens
            and no more — the conversion token :meth:`AssemblyRefused.as_refusal`
            mints, and the two identity determinations the SDK's own
            :class:`~ccf.agents.assembler.DeterministicAssembler` makes
            (:data:`ASSEMBLY_REASON_TENANT_MISMATCH`,
            :data:`ASSEMBLY_REASON_UNDECLARED_ROLE`, ``24.6-L-02``). The
            examples' reasons stay the examples'.
        detail: The human-readable statement, for an operator reading a log.
    """

    reason: str
    detail: str


class ConsumptionRefused(ValueError):
    """A Context Product was refused at the agent's consumption seam.

    Raised — never degraded around — when a product falls outside the agent's
    context contract (axis 2), belongs to another tenant, or is TTL-expired:
    an expired product is contract-invalid, not stale (INV-CH6-05; DESIGN.md
    §3.1 — the base refuses rather than degrading).
    """
