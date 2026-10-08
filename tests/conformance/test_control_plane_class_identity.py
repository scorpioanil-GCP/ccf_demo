"""Conformance: a Control Plane refuses a document that states another class (`D-IMPL-378` K2).

Dave, 2026-10-08 12:29 MST, ruling K2 (b): amend the ``ControlPlaneProtocol``
text so registration must validate the way the SDK's registry does, *"plus a
conformance check demonstrating rejection by a third-party implementation.
Documentation alone is not enforcement evidence."*

What the obligation is. ``src/ccf/controlplane/artifact_base.py::ArtifactClass.validate``
refuses an artifact whose own top-level ``class_id`` disagrees with the class
it is presented as, raising
``src/ccf/controlplane/artifact_base.py::ArtifactClassIdMismatch`` (lane
378d-classid). The SDK's ``ControlPlaneRegistry.register_typed`` and
``.register_versioned`` call it before anything is stored or audited, and every
SDK boot door parses through it. A third-party ``ControlPlaneProtocol`` got the
registry-level guard only if it validated the same way, and nothing the SDK
offered could tell whether it did.

**This module is that acceptance bar**, in the shape of the SDK's other
Protocol conformance suites (`D-16`; ``tests/conformance/test_gate_closure_and_conditional_write.py``):
:func:`check_registration_refuses_a_document_stating_another_class` runs against
every factory in :data:`PLANES`. A deployment that supplies its own Control
Plane adds its factory there and runs this module unchanged. The check fails a
plane by name — :class:`ClassIdentityNotEnforced`, naming the method — when the
plane admits a disagreeing document, refuses it with anything other than
``ArtifactClassIdMismatch``, or files or audits anything before refusing; and it
fails a plane that refuses everything, because the same plane must register an
agreeing document.

Demonstrated with two minimal third-party implementations, below: one that
validates with ``artifact_class.validate`` passes the check, and one that checks
only the contract — what a third-party plane written before `D-IMPL-378` does —
is failed by the check, by name, for each method. Test vocabulary only (CINV-01).
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any

import pytest

from ccf.authz.capability import Register
from ccf.controlplane.audit import AuditEvent, AuditLog
from ccf.controlplane.artifacts import (
    ArtifactClass,
    ArtifactClassIdMismatch,
    DeclaredArtifact,
    VersionedArtifact,
    declared_artifact_class,
)
from ccf.controlplane.registry import ControlPlaneProtocol, ControlPlaneRegistry
from tests.controlplane.capabilities import register_capability

pytestmark = pytest.mark.conformance

TENANT = "conformance-tenant"
TYPED_KEY = f"{TENANT}/policy-bundle"
VERSIONED_KEY = f"{TENANT}/versioned-document"
CONTROL_KEY = f"{TENANT}/agreeing-bundle"

#: The class a document is presented as, and the class it states instead.
PRESENTED = "conformance.policy-bundle"
STATES = "conformance.other-bundle"


class _SelfNamingVersioned(VersionedArtifact):
    """An author-versioned contract that states its own class (test vocabulary, CINV-01)."""

    class_id: str
    artifact_version: str
    body: str


class ClassIdentityNotEnforced(AssertionError):
    """The conformance check's failure: a Control Plane did not hold a document to its class.

    An ``AssertionError``, so a deployment running this module sees an ordinary
    test failure, named.

    Attributes:
        method: The ``ControlPlaneProtocol`` method that did not enforce it.
    """

    def __init__(self, method: str, detail: str) -> None:
        super().__init__(
            f"ControlPlaneProtocol.{method} {detail}; registration must validate with"
            " artifact_class.validate(artifact) and refuse a document whose own class_id"
            " disagrees with the class it is registered as, raising ArtifactClassIdMismatch"
            " before anything is stored or audited (D-IMPL-378 K2)"
        )
        self.method = method


def _expect_refused(
    plane: ControlPlaneProtocol, method: str, register: Callable[[], object], *, key: str, presented: str
) -> None:
    """``register`` must raise ``ArtifactClassIdMismatch`` naming both classes, filing and auditing nothing."""
    audited = len(plane.audit_events())
    try:
        outcome = register()
    except ArtifactClassIdMismatch as refused:
        if (refused.presented_class_id, refused.document_class_id) != (presented, STATES):
            raise ClassIdentityNotEnforced(
                method,
                f"refused naming {refused.presented_class_id!r} and {refused.document_class_id!r},"
                f" not {presented!r} and {STATES!r}",
            ) from refused
    except Exception as other:  # noqa: BLE001 - any other refusal is the wrong mechanism
        raise ClassIdentityNotEnforced(
            method, f"refused with {type(other).__name__}, not ArtifactClassIdMismatch"
        ) from other
    else:
        raise ClassIdentityNotEnforced(
            method, f"admitted a document stating {STATES!r} as {presented!r} (returned {outcome!r})"
        )
    if len(plane.audit_events()) != audited:
        raise ClassIdentityNotEnforced(method, "audited something before refusing")
    try:
        plane.resolve_latest(key)
    except Exception:  # noqa: BLE001 - the Protocol names no exception for an empty key
        return
    raise ClassIdentityNotEnforced(method, f"filed something under {key!r} before refusing")


def check_registration_refuses_a_document_stating_another_class(plane: ControlPlaneProtocol) -> None:
    """THE CONFORMANCE CHECK. Raises :class:`ClassIdentityNotEnforced` for a plane that does not enforce it.

    1. ``register_typed`` refuses an open-envelope document stating another class.
    2. ``register_versioned`` refuses an author-versioned document stating another class.
    3. The same plane registers and resolves a document stating the class it is
       registered as — so a plane that refuses everything does not pass.
    """
    if not isinstance(plane, ControlPlaneProtocol):
        raise ClassIdentityNotEnforced("register_typed", "is not offered: the plane is not a ControlPlaneProtocol")
    envelope = DeclaredArtifact(semver="1.0.0", class_id=STATES, declaration={"permitted": ["conformance"]})
    _expect_refused(
        plane,
        "register_typed",
        lambda: plane.register_typed(
            register_capability(TYPED_KEY, Register), envelope, declared_artifact_class(PRESENTED)
        ),
        key=TYPED_KEY,
        presented=PRESENTED,
    )
    versioned = _SelfNamingVersioned(semver="1.0.0", class_id=STATES, artifact_version="1.0.0", body="b")
    _expect_refused(
        plane,
        "register_versioned",
        lambda: plane.register_versioned(
            register_capability(VERSIONED_KEY, Register),
            versioned,
            ArtifactClass(class_id=PRESENTED, contract=_SelfNamingVersioned),
        ),
        key=VERSIONED_KEY,
        presented=PRESENTED,
    )
    agreeing = DeclaredArtifact(semver="1.0.0", class_id=PRESENTED, declaration={"permitted": ["conformance"]})
    try:
        version = plane.register_typed(
            register_capability(CONTROL_KEY, Register), agreeing, declared_artifact_class(PRESENTED)
        )
    except Exception as refused:  # noqa: BLE001 - a plane refusing a conforming document is not conforming
        raise ClassIdentityNotEnforced(
            "register_typed", f"refused a document stating the class it is registered as ({type(refused).__name__})"
        ) from refused
    if plane.resolve(CONTROL_KEY, version) != agreeing:
        raise ClassIdentityNotEnforced("register_typed", "did not resolve the agreeing document it registered")


# ---------------------------------------------------------------------------
# Two minimal third-party implementations. Each is a whole ControlPlaneProtocol:
# its OWN admission rule, per registration method, over the reference
# registry's untyped `register` as its store and its audit log.
# ---------------------------------------------------------------------------

#: The two registration methods the amended Protocol text obliges.
BOTH_METHODS = frozenset({"register_typed", "register_versioned"})


class ThirdPartyPlane:
    """A third-party Control Plane. ``validated`` names the methods that admit through ``artifact_class.validate``.

    A method not named admits any instance of the class's contract — the check a
    plane written before `D-IMPL-378` made. ``ThirdPartyPlane()`` validates both,
    as the amended Protocol text requires; ``ThirdPartyPlane(validated=frozenset())``
    is the contract-only implementation.
    """

    def __init__(self, *, validated: frozenset[str] = BOTH_METHODS) -> None:
        self._store = ControlPlaneRegistry()
        self._validated = validated

    def _admit(self, method: str, artifact: object, artifact_class: ArtifactClass) -> None:
        if method in self._validated:
            artifact_class.validate(artifact)
        elif not isinstance(artifact, artifact_class.contract):
            raise TypeError(f"artifact is not a {artifact_class.contract.__name__}")

    def register(self, authorized: Any, artifact: object) -> str:
        return self._store.register(authorized, artifact)

    def register_typed(self, authorized: Any, artifact: object, artifact_class: ArtifactClass) -> str:
        self._admit("register_typed", artifact, artifact_class)
        return self._store.register(authorized, artifact)

    def register_versioned(
        self, authorized: Any, artifact: object, artifact_class: ArtifactClass, *, reissuable: bool = False
    ) -> str:
        self._admit("register_versioned", artifact, artifact_class)
        return self._store.register(authorized, artifact)

    def resolve(self, key: str, version: str) -> object:
        return self._store.resolve(key, version)

    def resolve_latest(self, key: str) -> tuple[str, object]:
        return self._store.resolve_latest(key)

    def audit_events(self) -> tuple[AuditEvent, ...]:
        return self._store.audit_events()

    @property
    def audit_log(self) -> AuditLog:
        return self._store.audit_log


#: Every factory a deployment's own Control Plane joins. The SDK's reference
#: registry, and the validating third-party implementation as the worked example.
PLANES = [
    pytest.param(ControlPlaneRegistry, id="reference-registry"),
    pytest.param(ThirdPartyPlane, id="third-party-validating"),
]


@pytest.mark.parametrize("make_plane", PLANES)
def test_registration_refuses_a_document_stating_another_class(make_plane: Callable[[], Any]) -> None:
    """The acceptance bar, run against every listed Control Plane."""
    check_registration_refuses_a_document_stating_another_class(make_plane())


@pytest.mark.parametrize("method", sorted(BOTH_METHODS))
def test_the_check_fails_a_third_party_plane_that_does_not_validate_by_name(method: str) -> None:
    """K2's demonstration: a third-party plane that checks only the contract is failed, by name.

    Each method is made contract-only on its own, so the check is shown to catch
    either one rather than only the first it reaches.
    """
    with pytest.raises(AssertionError) as failed:
        check_registration_refuses_a_document_stating_another_class(
            ThirdPartyPlane(validated=BOTH_METHODS - {method})
        )
    assert type(failed.value).__name__ == "ClassIdentityNotEnforced", type(failed.value)
    assert getattr(failed.value, "method", None) == method, failed.value
    assert "admitted a document stating" in str(failed.value), failed.value
    assert "ArtifactClassIdMismatch" in str(failed.value), failed.value


def test_the_check_fails_the_contract_only_third_party_plane_at_its_first_method() -> None:
    """The second minimal implementation, whole: contract-only on both methods."""
    with pytest.raises(ClassIdentityNotEnforced) as failed:
        check_registration_refuses_a_document_stating_another_class(ThirdPartyPlane(validated=frozenset()))
    assert failed.value.method == "register_typed"


def test_the_check_fails_a_plane_that_refuses_everything() -> None:
    """Non-vacuity: refusing every document is not conformance."""

    class RefusesEverything(ThirdPartyPlane):
        def _admit(self, method: str, artifact: object, artifact_class: ArtifactClass) -> None:
            artifact_class.validate(artifact)
            raise TypeError("this plane refuses every registration")

    with pytest.raises(ClassIdentityNotEnforced) as failed:
        check_registration_refuses_a_document_stating_another_class(RefusesEverything())
    assert failed.value.method == "register_typed"
    assert "refused a document stating the class it is registered as" in str(failed.value)


def test_both_third_party_planes_are_whole_control_plane_protocols() -> None:
    """The demonstration is about real Protocol implementations, not partial stubs."""
    for plane in (ThirdPartyPlane(), ThirdPartyPlane(validated=frozenset())):
        assert isinstance(plane, ControlPlaneProtocol), type(plane)


def test_the_protocol_states_the_class_identity_obligation() -> None:
    """K2 (b): the Protocol's own text obliges both registration methods to validate this way."""
    for method in (ControlPlaneProtocol.register_typed, ControlPlaneProtocol.register_versioned):
        text = inspect.getdoc(method) or ""
        assert "artifact_class.validate(artifact)" in text, (method.__name__, text)
        assert "ArtifactClassIdMismatch" in text, (method.__name__, text)
        assert "tests/conformance/test_control_plane_class_identity.py" in text, (method.__name__, text)
