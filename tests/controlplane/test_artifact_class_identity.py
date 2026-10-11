"""A document that states one artifact class is refused as another, by name, before anything is registered.

`D-IMPL-378`, lane 378d-classid (CLAUDE.md §9: the three-issue cap, lightweight
remediation). The open envelope,
``src/ccf/controlplane/artifacts.py::DeclaredArtifact`` — ``semver``,
``class_id``, ``declaration`` — is the one Control Plane contract whose document
STATES the class it is, and
``src/ccf/controlplane/artifacts.py::declared_artifact_class`` builds an
``ArtifactClass`` over that one contract for every adopter class id. What a
document is presented as and what it says it is are therefore two statements,
and before this guard nothing compared them. Measured on ``a15f92ee``:

* ``parse_artifact`` and ``load_artifact`` admitted a document stating
  ``fixture.other-bundle`` as ``fixture.policy-bundle``, and a document stating
  the SDK's own ``ccf.workflow-definition`` as an adopter's
  ``acme.policy-bundle`` (``D-IMPL-84`` refuses that id as a manifest class, and
  nothing read it inside the document).
* ``register_typed`` registered it: the key bound to ``fixture.policy-bundle``,
  the audit plane recorded ``fixture.policy-bundle``, and the artifact resolved
  back said ``fixture.other-bundle``.
* ``register_versioned`` did the same for an adopter's own author-versioned
  contract that states its class.

Every refusal here is asserted by the refusal's own class NAME and its own
attributes, against a Control Plane that recorded nothing. The name is a string
rather than an import so that a tree without the guard fails each test on its
behavior, not on an import. The controls hold that a document stating the class
it is presented as still parses and registers.
"""

from __future__ import annotations

from typing import Any

import pytest
import yaml

from ccf.authz.capability import Register
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import (
    ArtifactClass,
    DeclaredArtifact,
    VersionedArtifact,
    declared_artifact_class,
    load_artifact,
    parse_artifact,
)
from ccf.controlplane.registry import ControlPlaneRegistry
from tests.controlplane.capabilities import register_capability

#: The refusal's class name, asserted by name rather than imported (see the module docstring).
REFUSAL = "ArtifactClassIdMismatch"

#: ``(presented as, the document states)``: an adopter class filed as another adopter class, and an
#: adopter class filed while the document claims an SDK class id the SDK reserves (`D-IMPL-84`).
DISAGREEING = [
    ("fixture.policy-bundle", "fixture.other-bundle"),
    ("acme.policy-bundle", "ccf.workflow-definition"),
]

KEY = "tenant-fixture/policy-bundle"


def _document(states: str) -> dict[str, Any]:
    return {"semver": "1.0.0", "class_id": states, "declaration": {"permitted_classifications": ["fixture-open"]}}


def _assert_named(refusal: BaseException, *, presented: str, states: str) -> None:
    """The guard's own refusal, by name: the class it was presented as and the class the document states."""
    assert type(refusal).__name__ == REFUSAL, f"{type(refusal).__name__}: {refusal}"
    assert getattr(refusal, "presented_class_id", None) == presented, refusal
    assert getattr(refusal, "document_class_id", None) == states, refusal
    for class_id in (presented, states):
        assert repr(class_id) in str(refusal), f"the refusal does not name {class_id!r}: {refusal}"


class _SelfNamingVersioned(VersionedArtifact):
    """An adopter's own author-versioned contract that states its class (test-side vocabulary, CINV-01)."""

    class_id: str
    artifact_version: str
    body: str


# ---------------------------------------------------------------------------
# The parse door: every boot door's parse step.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("presented", "states"), DISAGREEING, ids=["adopter-as-adopter", "sdk-id-as-adopter"])
@pytest.mark.parametrize("door", ["parse_artifact", "load_artifact"])
def test_a_document_stating_another_class_is_refused_at_parse(door: str, presented: str, states: str) -> None:
    """THE HOLE AS WORDED, at the earliest point both are known: the parse that names the class."""
    document = _document(states)
    artifact_class = declared_artifact_class(presented)
    with pytest.raises((ValueError, TypeError)) as raised:
        if door == "parse_artifact":
            parse_artifact(document, artifact_class)
        else:
            load_artifact(yaml.safe_dump(document), artifact_class)
    _assert_named(raised.value, presented=presented, states=states)
    # A caller that catches ValueError around a parse, as every boot door's caller does, keeps catching it.
    assert isinstance(raised.value, ValueError), type(raised.value).__mro__


def test_control_a_document_stating_the_class_it_is_presented_as_still_parses() -> None:
    parsed = parse_artifact(_document("fixture.policy-bundle"), declared_artifact_class("fixture.policy-bundle"))
    assert isinstance(parsed, DeclaredArtifact) and parsed.class_id == "fixture.policy-bundle"


# ---------------------------------------------------------------------------
# The registration doors.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("presented", "states"), DISAGREEING, ids=["adopter-as-adopter", "sdk-id-as-adopter"])
def test_register_typed_refuses_an_artifact_stating_another_class_and_registers_nothing(
    presented: str, states: str
) -> None:
    registry = ControlPlaneRegistry()
    artifact = DeclaredArtifact.model_validate(_document(states))
    with pytest.raises((ValueError, TypeError)) as raised:
        registry.register_typed(register_capability(KEY, Register), artifact, declared_artifact_class(presented))
    _assert_named(raised.value, presented=presented, states=states)
    # `register_typed` documents TypeError for an artifact that does not satisfy its class.
    assert isinstance(raised.value, TypeError), type(raised.value).__mro__
    assert registry.versions(KEY) == ()
    assert registry.artifact_class_of(KEY) is None
    assert registry.audit_events() == (), "something was registered or audited before the refusal"


def test_register_versioned_refuses_an_artifact_stating_another_class_and_registers_nothing() -> None:
    registry = ControlPlaneRegistry()
    artifact = _SelfNamingVersioned(
        semver="1.0.0", class_id="fixture.versioned-b", artifact_version="1.0.0", body="b"
    )
    presented = ArtifactClass(class_id="fixture.versioned-a", contract=_SelfNamingVersioned)
    with pytest.raises((ValueError, TypeError)) as raised:
        registry.register_versioned(register_capability(KEY, Register), artifact, presented)
    _assert_named(raised.value, presented="fixture.versioned-a", states="fixture.versioned-b")
    assert registry.versions(KEY) == ()
    assert registry.artifact_class_of(KEY) is None
    assert registry.audit_events() == (), "something was registered or audited before the refusal"


def test_control_an_artifact_stating_the_class_it_is_registered_as_still_registers() -> None:
    registry = ControlPlaneRegistry()
    artifact_class = declared_artifact_class("fixture.policy-bundle")
    artifact = parse_artifact(_document("fixture.policy-bundle"), artifact_class)
    version = registry.register_typed(register_capability(KEY, Register), artifact, artifact_class)
    assert version == content_hash(artifact)
    assert registry.resolve(KEY, version) == artifact
    assert registry.artifact_class_of(KEY) == "fixture.policy-bundle"

    versioned = ControlPlaneRegistry()
    agreeing = _SelfNamingVersioned(semver="1.0.0", class_id="fixture.versioned-a", artifact_version="1.0.0", body="a")
    outcome = versioned.register_versioned(
        register_capability(KEY, Register),
        agreeing,
        ArtifactClass(class_id="fixture.versioned-a", contract=_SelfNamingVersioned),
    )
    assert outcome == content_hash(agreeing)
