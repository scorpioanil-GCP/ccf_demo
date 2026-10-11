"""One rule, one refusal name: the manifest door's reservation refusal is ``ReservedArtifactClassId`` (OWED-RULINGS-3 3P2 (b)).

Dave, 2026-10-09 06:21 MST, ``D-IMPL-378``, verbatim: *"3P1(a), 3P2(b)"*. The
option he picked (OWED-RULINGS-3 item 3, P2 (b), from lane ``378f-k1b`` §7 P2):
*"Have ``resolve_artifact_class`` raise ``ReservedArtifactClassId`` too, so that
one rule has one name. It is a ``ValueError`` subclass, so existing callers keep
catching it, but its message would change."*

``D-IMPL-84`` reserves the ``ccf.`` prefix for the SDK. Three places refuse it:
``src/ccf/controlplane/artifacts.py::declared_artifact_class`` and
``src/ccf/controlplane/artifact_base.py::ArtifactClass.validate`` by the name
``ReservedArtifactClassId``, and
``src/ccf/deployment/classes.py::resolve_artifact_class`` — the resolver the
manifest door, the single-file config door and the paved road share — which,
measured on ``a539c215``, raised a plain ``ValueError`` for the same reservation.

What is asserted, by mechanism:

1. **The rule's one name.** ``resolve_artifact_class`` refuses a ``ccf.`` id the
   SDK does not ship (an SDK id no manifest addresses, an invented one, the bare
   prefix) as ``ReservedArtifactClassId``, carrying the id, raised in
   ``resolve_artifact_class`` itself.
2. **Existing callers keep catching it**: it is a ``ValueError``, and its text
   still names the id and cites ``D-IMPL-84``.
3. **Controls.** The resolver's other refusal (an empty id) keeps its own plain
   ``ValueError``; every SDK id resolves to its own constant; an adopter's
   namespace takes the envelope.

Fixture vocabulary only (CINV-01).
"""

from __future__ import annotations

import pathlib
import traceback

import pytest

from ccf.controlplane.artifact_base import ReservedArtifactClassId
from ccf.controlplane.artifacts import DeclaredArtifact
from ccf.deployment import SDK_ARTIFACT_CLASSES, SDK_VERSIONED_ARTIFACT_CLASSES
from ccf.deployment.classes import resolve_artifact_class

#: A ``ccf.`` id the SDK does not ship: one an SDK document names but no manifest
#: addresses, an invented one, and the bare prefix.
RESERVED = ("ccf.hitl-policy", "ccf.made-up-class", "ccf.")


def _raised_in(refusal: BaseException) -> str:
    """``module.py::function`` of the innermost SDK frame the refusal was raised in."""
    frames = [frame for frame in traceback.extract_tb(refusal.__traceback__) if "/src/ccf/" in frame.filename]
    assert frames, f"no SDK frame raised {type(refusal).__name__}: {refusal}"
    return f"{pathlib.Path(frames[-1].filename).name}::{frames[-1].name}"


@pytest.mark.parametrize("class_id", RESERVED)
def test_3p2_b_the_resolver_refuses_a_reserved_id_as_reserved_artifact_class_id(class_id: str) -> None:
    """The manifest door's refusal of the reservation is the reservation's own type, carrying the id."""
    with pytest.raises(ValueError) as raised:
        resolve_artifact_class(class_id)
    refusal = raised.value
    assert type(refusal) is ReservedArtifactClassId, (
        f"resolve_artifact_class refused {class_id!r} as {type(refusal).__name__}, not as the reservation's own"
        f" type ReservedArtifactClassId: {refusal}"
    )
    assert refusal.class_id == class_id, refusal.class_id
    assert _raised_in(refusal) == "classes.py::resolve_artifact_class", _raised_in(refusal)


@pytest.mark.parametrize("class_id", RESERVED)
def test_3p2_b_a_caller_catching_value_error_keeps_catching_it(class_id: str) -> None:
    """It is a ``ValueError``, and its text still names the id and cites the reservation it enforces."""
    with pytest.raises(ValueError) as raised:
        resolve_artifact_class(class_id)
    assert isinstance(raised.value, ValueError)
    assert repr(class_id) in str(raised.value), str(raised.value)
    assert "D-IMPL-84" in str(raised.value), str(raised.value)


@pytest.mark.parametrize("class_id", ["", " ", "\t\n"])
def test_control_an_unnamed_class_id_keeps_its_own_plain_refusal(class_id: str) -> None:
    """Another rule, another refusal: an empty id is still a plain ``ValueError``, never the reservation's."""
    with pytest.raises(ValueError, match="empty artifact class id") as raised:
        resolve_artifact_class(class_id)
    assert type(raised.value) is ValueError, type(raised.value)


def test_control_sdk_ids_resolve_and_an_adopter_namespace_takes_the_envelope() -> None:
    """The reservation is one prefix wide and no wider, and every SDK id still resolves to its own constant."""
    owned = {**SDK_ARTIFACT_CLASSES, **SDK_VERSIONED_ARTIFACT_CLASSES}
    assert owned, "no SDK class to resolve"
    for class_id, constant in owned.items():
        assert resolve_artifact_class(class_id) is constant, class_id
    for class_id in ("acme.policy-bundle", "ccfx.policy-bundle", "notccf.thing"):
        assert resolve_artifact_class(class_id).contract is DeclaredArtifact, class_id
