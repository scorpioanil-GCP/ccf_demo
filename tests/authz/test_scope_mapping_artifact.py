"""The ScopeMappingArtifact and its D-01 pattern grammar (10-01; ``SEC-002``).

HARD-04; D-IMPL-68; 10-CONTEXT D-01/D-03/D-04. The artifact is a dedicated
typed Control Plane policy class registered and versioned like every other
bundle; the pattern grammar is exact match plus single trailing
``*`` only — refused at registration, not discovered at decision time.

The grammar now spans **two** axes, tenants and resources, through one
matcher and one validator. Both axes are exercised below against the same
table, because the whole reason they share a function is that two copies of
two string branches eventually disagree about a trailing ``*``.

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
    pattern_matches,
)

#: A conforming value for whichever axis a test is not the subject of.
_CONFORMING = ("a-resource",)


def _mapping(*patterns: str, axis: str = "tenant") -> ScopeMappingArtifact:
    """One mapping whose ``axis`` carries ``patterns``, the other conforming."""
    return ScopeMappingArtifact(
        semver="1.0.0",
        scopes={
            "test:scope": ScopeEntry(
                tenant_patterns=(
                    tuple(patterns) if axis == "tenant" else _CONFORMING
                ),
                action_ids=("test.action",),
                resource_patterns=(
                    tuple(patterns) if axis == "resource" else _CONFORMING
                ),
            )
        },
    )


# --- D-01 grammar: refused at the boundary -----------------------------------


@pytest.mark.parametrize("axis", ["tenant", "resource"])
@pytest.mark.parametrize("pattern", ["tenant-a", "tenant-*"])
def test_exact_and_trailing_wildcard_patterns_are_accepted(
    pattern: str, axis: str
) -> None:
    artifact = _mapping(pattern, axis=axis)
    entry = artifact.scopes["test:scope"]
    assert getattr(entry, f"{axis}_patterns") == (pattern,)


@pytest.mark.parametrize("axis", ["tenant", "resource"])
@pytest.mark.parametrize("pattern", ["*tenant", "te*nt", "t*n*", "*a*"])
def test_mid_string_and_leading_globs_are_refused(
    pattern: str, axis: str
) -> None:
    """D-01: no regex, no mid-string globs — only placement of ``*`` is
    validated; everything else is a literal."""
    with pytest.raises(ValidationError):
        _mapping(pattern, axis=axis)


@pytest.mark.parametrize("axis", ["tenant", "resource"])
@pytest.mark.parametrize("pattern", ["*", "", "**"])
def test_bare_glob_and_empty_patterns_are_refused(
    pattern: str, axis: str
) -> None:
    """WR-03: the bare ``"*"`` would silently match everything and ``""``
    is an exact match on the empty string — neither is a documented D-01
    shape, so both are refused at registration, never interpreted. **On both
    axes**: the resource axis is the one ``SEC-002`` added, and an axis that
    accepted the bare glob would hand back exactly the width the finding is
    about."""
    with pytest.raises(ValidationError):
        _mapping(pattern, axis=axis)


def test_resource_patterns_have_no_permissive_default() -> None:
    """``SEC-002``: the axis is not opt-in.

    What would fail here: ``resource_patterns`` given a default. An artifact
    written before the field existed would then keep authorizing exactly as
    widely as it did, and the finding would be closed in the code and open in
    every deployment.
    """
    with pytest.raises(ValidationError):
        ScopeEntry(tenant_patterns=("t",), action_ids=("a",))


def test_the_refusal_names_the_axis_that_was_wrong() -> None:
    """An author who mistyped a resource pattern is not told about tenants."""
    with pytest.raises(ValidationError, match="resource pattern"):
        _mapping("*", axis="resource")
    with pytest.raises(ValidationError, match="tenant pattern"):
        _mapping("*", axis="tenant")


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
def test_pattern_matches(pattern: str, tenant: str, expected: bool) -> None:
    assert pattern_matches(pattern, tenant) is expected


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
