"""The scope-mapping Control Plane artifact and its D-01 grammar (HARD-04).

SDK-defined (CLAUDE.md §8.2; D-IMPL-68; 10-CONTEXT D-01–D-04). The mapping
from token scopes to ``tenant-pattern × action-id`` sets is a dedicated
typed Control Plane policy artifact — Pydantic ``extra=forbid``, its own
semver lane, registered and versioned like every other bundle (the
``HitlPolicy`` precedent) — never folded into another policy class (D-03).

**Placement (RESEARCH Open Q1, adopted):** this artifact class lives in
``runtime/`` beside its interpreter rather than in ``/src``, because
nothing in ``/src`` reads it — the doors and the authorizer are runtime
surfaces — and Control Plane ``register_typed`` accepts an
:class:`~ccf.controlplane.artifacts.ArtifactClass` from any module. D-05's
"/src core untouched" then holds literally for HARD-04.

**The D-01 grammar** is exact match plus a single trailing ``*`` prefix
glob — no regex, no mid-string globs, and the glob requires a non-empty
literal prefix: the empty pattern and the bare ``"*"`` are refused, so a
one-character artifact typo can never become an all-tenant grant (WR-03).
Every non-``*`` character is a literal. Malformed patterns are refused at
registration (the boundary), not discovered at decision time.
The matcher is two string branches; ``re`` is deliberately not imported.

**The same grammar now spans two axes** (``SEC-002``). A scope entry states
which tenants it reaches *and* which **resources** — the artifact key a
registration rewrites, the content address a read dereferences, the product
class a retrieval serves. One grammar and one matcher for both, deliberately:
two pattern languages in one artifact is two chances for an author to read a
pattern as the other axis would have read it, and the axis that ships second
is always the one nobody re-reads.

**A resource axis, not a second tenant axis, and the distinction is the
finding.** ``(grant, tenant, action)`` decides *who counts as recognized*;
``SEC-002``'s stated harm — *any recognized bearer can rewrite the prompt
artifact an underwriting agent runs on* — survives that decision intact and
merely becomes *any bearer holding the register action can rewrite it*. The
resource axis is what makes the second sentence false as well.

Scope strings, tenant names, resource names, action identifiers, and mapping
values are deployment data carried by registered artifacts; this module holds
none of them (CINV-01).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import field_validator

from ccf.contracts.base import CCFContract
from ccf.controlplane.artifact_base import ArtifactClass, validate_semver

__ccf_mode__ = "algorithmic"

__all__ = [
    "SCOPE_MAPPING",
    "ScopeEntry",
    "ScopeMappingArtifact",
    "pattern_matches",
    "validate_patterns",
]


def pattern_matches(pattern: str, value: str) -> bool:
    """Return whether ``value`` satisfies one D-01 pattern.

    Two branches and nothing else: a pattern ending in ``*`` is a prefix
    glob over everything before it; any other pattern is an exact match.
    Grammar *validity* is the artifact's registration-time concern
    (:func:`validate_patterns`), not this function's.

    **One matcher for both axes** (``SEC-002``). It was
    ``tenant_pattern_matches`` while a tenant was the only thing a scope entry
    matched; the resource axis matches by the identical rule, and giving each
    axis its own copy of two string branches is how the two copies eventually
    disagree about a trailing ``*``. The name lost the ``tenant_`` because the
    function never had anything to do with tenancy — the parameter was already
    just a string.
    """
    if pattern.endswith("*"):
        return value.startswith(pattern[:-1])
    return value == pattern


def validate_patterns(value: tuple[str, ...], *, axis: str) -> tuple[str, ...]:
    """Refuse any pattern outside the D-01 grammar, naming the axis.

    Args:
        value: The declared patterns.
        axis: Which axis is being validated, for the message an artifact
            author reads. The two axes share a grammar, so they share this
            function; they do not share a message, because an author who
            mistyped a resource pattern should not be told about tenants.

    Returns:
        ``value`` unchanged when every pattern conforms.

    Raises:
        ValueError: a pattern is empty, is the bare ``"*"``, or carries a glob
            anywhere but as its final character.
    """
    for pattern in value:
        prefix = pattern[:-1] if pattern.endswith("*") else pattern
        if not pattern or not prefix or "*" in prefix:
            raise ValueError(
                f"{axis} pattern {pattern!r} is not exact-match or"
                " single-trailing-* — the D-01 grammar admits 'a-name' and"
                " 'a-prefix-*' shapes only; no regex, no mid-string or"
                " leading globs, no empty pattern, and no bare '*' (a"
                " grant-everything glob must be an explicit non-empty"
                " prefix, never a one-character typo) (D-IMPL-68;"
                " 10-CONTEXT D-01; SEC-002)"
            )
    return value


class ScopeEntry(CCFContract):
    """One scope's statement: which tenants, which actions, which resources.

    Attributes:
        tenant_patterns: D-01 patterns naming the tenants this scope reaches.
        action_ids: The door-declared action identifiers this scope may
            perform (D-02; :mod:`ccf_runtime.authz.refusals` holds the
            vocabulary every shipped door declares from).
        resource_patterns: D-01 patterns naming the **things** those actions
            may be performed on — the Control Plane key a registration
            rewrites, the content address a read dereferences, the product
            class a retrieval serves, or, for a door that acts on no
            addressable subject, the door's own action id
            (:class:`~ccf_runtime.authz.route_declaration.ResourceSource`).

            **Required, with no permissive default, and that is the point**
            (``SEC-002``). A field defaulting to *everything* would make the
            axis opt-in: an artifact written before the field existed would
            keep authorizing exactly as widely as it did, and the finding
            would be closed in the code and open in every deployment. An
            author who means *every resource this action can name* writes an
            explicit non-empty prefix and can be seen to have written it.
    """

    tenant_patterns: tuple[str, ...]
    action_ids: tuple[str, ...]
    resource_patterns: tuple[str, ...]

    @field_validator("tenant_patterns")
    @classmethod
    def _tenant_patterns_satisfy_the_d01_grammar(
        cls, value: tuple[str, ...]
    ) -> tuple[str, ...]:
        return validate_patterns(value, axis="tenant")

    @field_validator("resource_patterns")
    @classmethod
    def _resource_patterns_satisfy_the_d01_grammar(
        cls, value: tuple[str, ...]
    ) -> tuple[str, ...]:
        return validate_patterns(value, axis="resource")


class ScopeMappingArtifact(CCFContract):
    """The Control Plane scope-mapping policy artifact (D-IMPL-68; D-03).

    Maps each token scope string to the tenants, door-declared actions and
    resources it authorizes. Interpreted by
    :class:`~ccf_runtime.authz.protocol.ControlPlaneTenantAuthorizer`;
    which scopes exist, and what they reach, are the deployment's
    statements (CINV-01) — the SDK invents no scope vocabulary (D-02).

    Attributes:
        semver: The artifact's own semver lane (D-04; whitepaper §6.3).
        scopes: Scope string → :class:`ScopeEntry`.
    """

    semver: str
    scopes: Mapping[str, ScopeEntry]

    @field_validator("semver")
    @classmethod
    def _semver_is_well_formed(cls, value: str) -> str:
        return validate_semver(value)


#: The scope-mapping artifact class (D-IMPL-68; D-03/D-04).
SCOPE_MAPPING = ArtifactClass(
    class_id="ccf.scope-mapping", contract=ScopeMappingArtifact
)
