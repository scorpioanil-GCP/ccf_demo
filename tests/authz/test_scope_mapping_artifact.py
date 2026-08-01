"""The ScopeMappingArtifact and its D-01 tenant-pattern grammar (10-01).

HARD-04; D-IMPL-68; 10-CONTEXT D-01/D-03/D-04. The artifact is a dedicated
typed Control Plane policy class registered and versioned like every other
bundle; the tenant-pattern grammar is exact match plus single trailing
``*`` only — refused at registration, not discovered at decision time.

Scope strings, tenant names, and mapping values below are test fixture
vocabulary; the SDK ships the grammar and the matcher, never a value
(CINV-01).
"""

from __future__ import annotations

import inspect

import pytest
from pydantic import ValidationError

from ccf.controlplane.registry import ControlPlaneRegistry
from ccf_runtime.authz.artifact import (
    SCOPE_MAPPING,
    ScopeEntry,
    ScopeMappingArtifact,
    tenant_pattern_matches,
)


def _mapping(*patterns: str) -> ScopeMappingArtifact:
    return ScopeMappingArtifact(
        semver="1.0.0",
        scopes={
            "test:scope": ScopeEntry(
                tenant_patterns=tuple(patterns),
                action_ids=("test.action",),
            )
        },
    )


# --- D-01 grammar: refused at the boundary -----------------------------------


@pytest.mark.parametrize("pattern", ["tenant-a", "tenant-*"])
def test_exact_and_trailing_wildcard_patterns_are_accepted(
    pattern: str,
) -> None:
    artifact = _mapping(pattern)
    assert artifact.scopes["test:scope"].tenant_patterns == (pattern,)


@pytest.mark.parametrize("pattern", ["*tenant", "te*nt", "t*n*", "*a*"])
def test_mid_string_and_leading_globs_are_refused(pattern: str) -> None:
    """D-01: no regex, no mid-string globs — only placement of ``*`` is
    validated; everything else is a literal."""
    with pytest.raises(ValidationError):
        _mapping(pattern)


def test_a_malformed_semver_is_refused() -> None:
    with pytest.raises(ValidationError):
        ScopeMappingArtifact(semver="not-a-version", scopes={})


# --- the two-branch matcher (no regex — D-01) --------------------------------


@pytest.mark.parametrize(
    ("pattern", "tenant", "expected"),
    [
        ("tenant-*", "tenant-a", True),
        ("tenant-a", "tenant-a", True),
        ("tenant-a", "tenant-b", False),
        ("tenant-*", "other", False),
    ],
)
def test_tenant_pattern_matches(
    pattern: str, tenant: str, expected: bool
) -> None:
    assert tenant_pattern_matches(pattern, tenant) is expected


def test_no_regex_anywhere_in_the_authz_package() -> None:
    """D-01 structurally: the grammar is two string branches, never regex."""
    import ccf_runtime.authz.artifact as artifact
    import ccf_runtime.authz.protocol as protocol
    import ccf_runtime.authz.refusals as refusals

    for module in (artifact, protocol, refusals):
        assert "import re" not in inspect.getsource(module)


# --- Control Plane registration (D-03/D-04) ----------------------------------


def test_the_artifact_registers_and_resolves_through_the_control_plane() -> (
    None
):
    """The scope mapping is a versioned Control Plane bundle like any other:
    typed registration, semver lane, exact-version resolution."""
    registry = ControlPlaneRegistry()
    artifact = _mapping("tenant-*")

    version = registry.register_typed(
        "test/scope-mapping", artifact, SCOPE_MAPPING
    )
    resolved_version, resolved = registry.resolve_latest("test/scope-mapping")

    assert resolved_version == version
    assert resolved == artifact


def test_a_wrong_class_registration_is_refused_typed() -> None:
    registry = ControlPlaneRegistry()
    with pytest.raises(TypeError):
        registry.register_typed(
            "test/scope-mapping", {"semver": "1.0.0"}, SCOPE_MAPPING
        )
