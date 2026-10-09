"""What the reserved ``ccf.`` namespace does not stop, disclosed and measured (OWED-RULINGS-3 3P1 (a)).

Dave, 2026-10-09 06:21 MST, ``D-IMPL-378``, verbatim: *"3P1(a), 3P2(b)"*. The
option he picked (OWED-RULINGS-3 item 3, P1 (a), from lane ``378f-k1b`` §7 P1):
*"Disclose and leave it. Writing a contract class and building an SDK-named
class over it is deliberate code. The reservation still holds for every
document, manifest, config and envelope route."*

R3, measured by lane ``378f-k1b`` on ``ae948439`` and again by this lane on
``a539c215`` (``probe_residuals.py``, line R3):
``ArtifactClass(class_id="ccf.workflow-definition", contract=AdopterTyped)`` and
then ``register_typed(...)`` registers, where ``AdopterTyped`` is a contract with
a ``semver`` and a ``body`` and no ``class_id``; the key is bound to
``ccf.workflow-definition`` and the registration is audited.

What is asserted:

1. **The disclosed behavior, as it stands.** R3 registers. A change that closes
   R3 turns this test red, and the disclosure must then be revisited.
2. **The routes the disclosure says are refused, refuse**, by the reservation's
   one name, ``ReservedArtifactClassId``, with nothing registered or audited: the
   public declaration function, the manifest door's resolver, and a class built
   directly under a ``ccf.`` id handed a document that states its own class.
3. **The disclosure is written where the ruling's work was assigned**: the
   docstrings of ``ArtifactClass`` and ``ReservedArtifactClassId`` and the
   Control Plane artifacts reference page each cite test 1 by its id, so the
   sentence and its measurement cannot drift apart unnoticed.

Fixture vocabulary only (CINV-01).
"""

from __future__ import annotations

import pathlib
from typing import Any

import pytest

from ccf.authz.capability import Register
from ccf.controlplane.artifact_base import ArtifactClass, ReservedArtifactClassId
from ccf.controlplane.artifacts import (
    DeclaredArtifact,
    VersionedArtifact,
    declared_artifact_class,
    parse_artifact,
)
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment.classes import resolve_artifact_class
from tests.controlplane.capabilities import register_capability

#: The SDK class id R3 builds an adopter's contract under.
SDK_ID = "ccf.workflow-definition"
KEY = f"tenant-x/{SDK_ID}/w"

#: Test 1, by the id the disclosure cites.
PIN = (
    "tests/controlplane/test_reserved_namespace_disclosed_residual.py::"
    "test_3p1_a_r3_a_ccf_class_built_over_an_adopter_contract_stating_no_class_id_registers"
)

#: The reference page the brief assigns the disclosure to.
PAGE = pathlib.Path(__file__).resolve().parents[2] / "public" / "reference" / "artifacts" / "control-plane-artifacts.md"


class AdopterTyped(VersionedArtifact):
    """An adopter's own typed contract: a version lane and a body, and no ``class_id``."""

    body: str


class AdopterSelfStating(VersionedArtifact):
    """An adopter's own contract that states its class."""

    class_id: str
    body: str


def _envelope(class_id: str) -> dict[str, Any]:
    return {"semver": "1.0.0", "class_id": class_id, "declaration": {"anything": "x"}}


# --- 1. the disclosed behavior, as it stands -----------------------------------------------------


def test_3p1_a_r3_a_ccf_class_built_over_an_adopter_contract_stating_no_class_id_registers() -> None:
    """R3: deliberate code builds an SDK-named class over its own contract, and the document registers under it."""
    registry = ControlPlaneRegistry()
    artifact_class = ArtifactClass(class_id=SDK_ID, contract=AdopterTyped)
    version = registry.register_typed(
        register_capability(KEY, Register), AdopterTyped(semver="1.0.0", body="x"), artifact_class
    )
    registrations = [(event.action, event.key, event.artifact_class) for event in registry.audit_events()]
    assert registrations == [("register_typed", KEY, SDK_ID)], "the registration is audited under the SDK's class id"
    assert registry.artifact_class_of(KEY) == SDK_ID, "the key is bound to the SDK's class id"
    assert registry.resolve(KEY, version) == AdopterTyped(semver="1.0.0", body="x")


# --- 2. what the disclosure says is refused, refuses ---------------------------------------------


def _refused_by_name(call: Any) -> ReservedArtifactClassId:
    with pytest.raises(ValueError) as raised:
        call()
    assert type(raised.value) is ReservedArtifactClassId, f"{type(raised.value).__name__}: {raised.value}"
    return raised.value


def test_3p1_a_the_declaration_function_refuses_every_ccf_id() -> None:
    assert _refused_by_name(lambda: declared_artifact_class(SDK_ID)).class_id == SDK_ID


def test_3p1_a_the_manifest_doors_resolver_refuses_a_ccf_id_the_sdk_does_not_ship() -> None:
    assert _refused_by_name(lambda: resolve_artifact_class("ccf.made-up-class")).class_id == "ccf.made-up-class"


@pytest.mark.parametrize("document", ["envelope", "adopter-contract-stating-its-class"])
def test_3p1_a_a_directly_built_ccf_class_refuses_a_document_stating_it_before_anything_is_filed(document: str) -> None:
    """The open envelope, and an adopter's contract declaring ``class_id``, parsed and registered under a ``ccf.`` class."""
    if document == "envelope":
        artifact_class = ArtifactClass(class_id=SDK_ID, contract=DeclaredArtifact)
        payload: dict[str, Any] = _envelope(SDK_ID)
        built: Any = DeclaredArtifact.model_validate(payload)
    else:
        artifact_class = ArtifactClass(class_id=SDK_ID, contract=AdopterSelfStating)
        payload = {"semver": "1.0.0", "class_id": SDK_ID, "body": "x"}
        built = AdopterSelfStating.model_validate(payload)
    _refused_by_name(lambda: parse_artifact(payload, artifact_class))
    registry = ControlPlaneRegistry()
    _refused_by_name(lambda: registry.register_typed(register_capability(KEY, Register), built, artifact_class))
    assert registry.artifact_class_of(KEY) is None and registry.audit_events() == (), "something was filed"


# --- 3. the disclosure is written where it was assigned ------------------------------------------


@pytest.mark.parametrize("place", ["ArtifactClass", "ReservedArtifactClassId", "control-plane-artifacts.md"])
def test_3p1_a_the_disclosure_cites_its_measurement(place: str) -> None:
    """Each place the brief names discloses R3 and cites test 1, so a change to either is seen by the other."""
    text = {
        "ArtifactClass": ArtifactClass.__doc__ or "",
        "ReservedArtifactClassId": ReservedArtifactClassId.__doc__ or "",
        "control-plane-artifacts.md": PAGE.read_text(encoding="utf-8"),
    }[place]
    assert PIN in text, f"{place} does not disclose R3 by citing its measurement {PIN}"
