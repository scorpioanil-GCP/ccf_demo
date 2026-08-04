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

Scope strings, tenant names, action identifiers, and mapping values are
deployment data carried by registered artifacts; this module holds none of
them (CINV-01).

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
    "tenant_pattern_matches",
]


def tenant_pattern_matches(pattern: str, tenant: str) -> bool:
    """Return whether ``tenant`` satisfies one D-01 pattern.

    Two branches and nothing else: a pattern ending in ``*`` is a prefix
    glob over everything before it; any other pattern is an exact match.
    Grammar *validity* is the artifact's registration-time concern
    (:class:`ScopeEntry`), not this function's.
    """
    if pattern.endswith("*"):
        return tenant.startswith(pattern[:-1])
    return tenant == pattern


class ScopeEntry(CCFContract):
    """One scope's authorization statement: which tenants, which actions.

    Attributes:
        tenant_patterns: D-01 patterns (exact or single-trailing-``*``)
            naming the tenants this scope reaches.
        action_ids: The door-declared action identifiers this scope may
            perform (D-02; :mod:`ccf_runtime.authz.refusals` holds the
            HITL doors' declarations).
    """

    tenant_patterns: tuple[str, ...]
    action_ids: tuple[str, ...]

    @field_validator("tenant_patterns")
    @classmethod
    def _patterns_satisfy_the_d01_grammar(
        cls, value: tuple[str, ...]
    ) -> tuple[str, ...]:
        for pattern in value:
            prefix = pattern[:-1] if pattern.endswith("*") else pattern
            if not pattern or not prefix or "*" in prefix:
                raise ValueError(
                    f"tenant pattern {pattern!r} is not exact-match or"
                    " single-trailing-* — the D-01 grammar admits"
                    " 'tenant-a' and 'tenant-*' shapes only; no regex, no"
                    " mid-string or leading globs, no empty pattern, and"
                    " no bare '*' (a grant-every-tenant glob must be an"
                    " explicit non-empty prefix, never a one-character"
                    " typo) (D-IMPL-68; 10-CONTEXT D-01)"
                )
        return value


class ScopeMappingArtifact(CCFContract):
    """The Control Plane scope-mapping policy artifact (D-IMPL-68; D-03).

    Maps each token scope string to the tenants and door-declared actions
    it authorizes. Interpreted by
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
