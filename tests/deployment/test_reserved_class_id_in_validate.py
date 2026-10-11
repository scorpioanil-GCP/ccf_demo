"""``ArtifactClass.validate`` refuses a self-stating document under a reserved ``ccf.`` id (`D-IMPL-378` K1 follow-up).

Dave, 2026-10-08 16:40 MST, item 4 of the second owed-rulings sheet: *"K1 follow-up: (b). Close the
direct-construction bypass while preserving legitimate SDK classes."* Option (b) on the sheet he ruled on:
*"Also refuse an envelope stating a `ccf.` id inside `ArtifactClass.validate`, where the class-identity guard
already reads the stated id — one check that closes every route."*

**What was open.** K1 (b) made ``src/ccf/controlplane/artifacts.py::declared_artifact_class`` refuse an id in
the SDK's reserved ``ccf.`` namespace (``D-IMPL-84``) with ``ReservedArtifactClassId``. The public constructor
builds the same class without it: ``ArtifactClass(class_id="ccf.workflow-definition", contract=DeclaredArtifact)``.
Measured on ``6942dadc`` (lane 378f-k1b, ``probe-r1-repro-6942dad.txt``): ``ArtifactClass.validate``,
``parse_artifact``, ``load_artifact`` and ``ControlPlaneRegistry.register_typed`` all admitted the open envelope
stating that id, and the registry bound the key to ``ccf.workflow-definition`` and audited it — an SDK class name
over content no SDK contract validated.

**What is asserted, by mechanism.**

1. *The hole as worded.* Every route a directly built class takes to registration refuses a document that states
   its own class — the open envelope, a subclass of it, or an adopter's own contract declaring ``class_id`` —
   under a reserved id: ``validate``, ``parse_artifact``, ``load_artifact``, ``register_typed``,
   ``register_versioned``, a third-party Control Plane that validates as ``D-IMPL-378`` K2 obliges, and a class id
   built as a ``str`` subclass that answers ``startswith`` for itself. Each refusal is ``ReservedArtifactClassId``
   by name, carries the id, is raised inside ``ArtifactClass.validate``, and comes before anything is registered
   or audited.
2. *Legitimate SDK classes are preserved.* Every SDK class — every ``ArtifactClass`` constant any module of ``ccf``
   or ``ccf_runtime`` defines — parses to its own contract, validates and registers through the method its
   contract requires. No SDK contract states a class id, so the check cannot reach one. The manifest door
   registers every manifest-addressable SDK class in one boot, and on the manifest door, the config door and the
   paved road ``validate`` refuses nothing an SDK class presents.
3. *Adopters, the class-identity guard and the boot doors are unchanged.* An adopter's own namespace still takes
   the envelope through a directly built class. A document stating a reserved id presented as an adopter class is
   still ``ArtifactClassIdMismatch``, because the identity check runs first. Each boot door still refuses an
   envelope stating a ``ccf.`` id by its own mechanism, before anything is audited, because no door builds a
   reserved class over the envelope.

The refusal is asserted by its class NAME as a string, not by an import, so a tree without the guard fails each
test on its behavior rather than on an import.
"""

from __future__ import annotations

import functools
import importlib
import pathlib
import pkgutil
import traceback
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
import yaml

import ccf
import ccf_runtime
from ccf.authz.capability import Register
from ccf.controlplane import artifact_base
from ccf.controlplane.artifacts import (
    ArtifactClass,
    DeclaredArtifact,
    VersionedArtifact,
    declared_artifact_class,
    load_artifact,
    parse_artifact,
)
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment import load_and_boot, load_config_and_boot
from ccf.deployment.classes import (
    SDK_ARTIFACT_CLASSES,
    SDK_ARTIFACT_ROLES,
    SDK_VERSIONED_ARTIFACT_CLASSES,
)
from ccf.products.contract import SUBJECT_WITHHOLDING_NEVER
from ccf.products.product import open_product
from ccf.replay.serve import ServedProduct

from tests.composition import declare_wide_temporal_boundary, declared_erasure_trust
from tests.conformance.test_control_plane_class_identity import ThirdPartyPlane
from tests.controlplane.capabilities import register_capability
from tests.controlplane.test_artifact_roundtrip import CASES
from tests.deployment.conftest import ARTIFACT_SET, TENANT, Deployment, manifest_document, write_artifact
from tests.products import paved_fixture as fixture
from tests.support.sqlite_lease import lock_dir_beside

#: The refusal's class name, asserted by name rather than imported (see the module docstring).
REFUSAL = "ReservedArtifactClassId"

#: The reserved ids K1's own tests name: an SDK class id a manifest addresses, one no manifest addresses, an id the
#: SDK does not own at all, and the bare prefix.
RESERVED = ["ccf.workflow-definition", "ccf.hitl-policy", "ccf.made-up-class", "ccf."]

#: Ids in an adopter's own namespace, including two that merely CONTAIN the letters.
ADOPTER = ["acme.policy-bundle", "ccfx.policy-bundle", "notccf.thing", "fixture.ccf.thing"]

KEY = f"{TENANT}/squat"


class _VersionedEnvelope(DeclaredArtifact):
    """The open envelope with an author lane, so ``register_versioned`` can take it (test vocabulary, CINV-01)."""

    artifact_version: str


class _SelfStating(VersionedArtifact):
    """An adopter's own contract that states its class, as ``test_artifact_class_identity`` writes one (CINV-01)."""

    class_id: str
    artifact_version: str
    body: str


class _Disguised(str):
    """A class id built in code that answers ``startswith`` for itself while comparing equal to the plain id."""

    def startswith(self, *args: Any, **kwargs: Any) -> bool:  # type: ignore[override]
        return False


def _envelope(states: str) -> dict[str, Any]:
    return {"semver": "1.0.0", "class_id": states, "declaration": {"anything": "x"}}


def _direct(class_id: str, contract: type[Any] = DeclaredArtifact) -> ArtifactClass:
    """The public constructor, called directly: the route K1 (b) left open."""
    return ArtifactClass(class_id=class_id, contract=contract)


def _raised_in(refusal: BaseException) -> str:
    """``module.py::function`` of the innermost SDK frame the refusal was raised in."""
    frames = [frame for frame in traceback.extract_tb(refusal.__traceback__) if "/src/ccf/" in frame.filename]
    assert frames, f"no SDK frame raised {type(refusal).__name__}: {refusal}"
    return f"{pathlib.Path(frames[-1].filename).name}::{frames[-1].name}"


def _assert_named(refusal: BaseException, *, class_id: str) -> None:
    """The reserved-namespace refusal, by name, carrying the id, raised inside ``ArtifactClass.validate``."""
    assert type(refusal).__name__ == REFUSAL, f"{type(refusal).__name__}: {refusal}"
    assert getattr(refusal, "class_id", None) == class_id, refusal
    assert repr(str(class_id)) in str(refusal), f"the refusal does not name {class_id!r}: {refusal}"
    assert "D-IMPL-84" in str(refusal), f"the refusal does not cite the reservation it enforces: {refusal}"
    assert isinstance(refusal, ValueError), type(refusal).__mro__
    assert _raised_in(refusal) == "artifact_base.py::validate", _raised_in(refusal)


# ---------------------------------------------------------------------------
# 1. THE HOLE AS WORDED: every route a directly built class takes to registration.
# ---------------------------------------------------------------------------

#: route name -> a builder taking the reserved id and returning (the attempt, the plane it files into or None).
_Route = Callable[[str], tuple[Callable[[], object], Any]]


def _validate(class_id: str) -> tuple[Callable[[], object], Any]:
    artifact = DeclaredArtifact.model_validate(_envelope(class_id))
    return (lambda: _direct(class_id).validate(artifact)), None


def _parse(class_id: str) -> tuple[Callable[[], object], Any]:
    return (lambda: parse_artifact(_envelope(class_id), _direct(class_id))), None


def _load(class_id: str) -> tuple[Callable[[], object], Any]:
    return (lambda: load_artifact(yaml.safe_dump(_envelope(class_id)), _direct(class_id))), None


def _register_typed(class_id: str) -> tuple[Callable[[], object], Any]:
    plane = ControlPlaneRegistry()
    artifact = DeclaredArtifact.model_validate(_envelope(class_id))
    return (lambda: plane.register_typed(register_capability(KEY, Register), artifact, _direct(class_id))), plane


def _register_versioned(class_id: str) -> tuple[Callable[[], object], Any]:
    plane = ControlPlaneRegistry()
    artifact = _VersionedEnvelope.model_validate({**_envelope(class_id), "artifact_version": "1.0.0"})
    presented = _direct(class_id, _VersionedEnvelope)
    return (lambda: plane.register_versioned(register_capability(KEY, Register), artifact, presented)), plane


def _adopter_self_stating_contract(class_id: str) -> tuple[Callable[[], object], Any]:
    plane = ControlPlaneRegistry()
    artifact = _SelfStating(semver="1.0.0", class_id=class_id, artifact_version="1.0.0", body="b")
    presented = _direct(class_id, _SelfStating)
    return (lambda: plane.register_versioned(register_capability(KEY, Register), artifact, presented)), plane


def _third_party_plane(class_id: str) -> tuple[Callable[[], object], Any]:
    plane = ThirdPartyPlane()
    artifact = DeclaredArtifact.model_validate(_envelope(class_id))
    return (lambda: plane.register_typed(register_capability(KEY, Register), artifact, _direct(class_id))), plane


def _disguised_class_id(class_id: str) -> tuple[Callable[[], object], Any]:
    plane = ControlPlaneRegistry()
    artifact = DeclaredArtifact.model_validate(_envelope(class_id))
    presented = _direct(_Disguised(class_id))
    return (lambda: plane.register_typed(register_capability(KEY, Register), artifact, presented)), plane


ROUTES: dict[str, _Route] = {
    "validate": _validate,
    "parse_artifact": _parse,
    "load_artifact": _load,
    "register_typed": _register_typed,
    "register_versioned": _register_versioned,
    "adopter-self-stating-contract": _adopter_self_stating_contract,
    "third-party-plane": _third_party_plane,
    "disguised-class-id": _disguised_class_id,
}


def _assert_nothing_filed(plane: Any) -> None:
    assert plane.audit_events() == (), "something was registered or audited before the refusal"
    with pytest.raises(Exception):  # noqa: B017 - the Protocol names no exception for an empty key
        plane.resolve_latest(KEY)
    if isinstance(plane, ControlPlaneRegistry):
        assert plane.versions(KEY) == ()
        assert plane.artifact_class_of(KEY) is None


@pytest.mark.parametrize("class_id", RESERVED)
@pytest.mark.parametrize("route", sorted(ROUTES))
def test_a_directly_built_reserved_class_refuses_a_document_stating_it_by_name(route: str, class_id: str) -> None:
    """K1 follow-up (b): the check inside ``ArtifactClass.validate`` closes every route a directly built class takes."""
    attempt, plane = ROUTES[route](class_id)
    with pytest.raises(ValueError) as raised:
        attempt()
    _assert_named(raised.value, class_id=class_id)
    if plane is not None:
        _assert_nothing_filed(plane)


# ---------------------------------------------------------------------------
# 2. Controls: the SDK's own classes, every one of them.
# ---------------------------------------------------------------------------

#: A document for every SDK class that ``tests/controlplane/test_artifact_roundtrip.py::CASES`` does not carry.
#: Fixture vocabulary only, shaped after instances the suite already admits (CINV-01: the SDK ships shapes,
#: deployments ship values).
_AT = datetime(2026, 3, 2, 11, 59, tzinfo=UTC)
_LINEAGE = {"graph_snapshot_at": _AT, "operators_invoked": ["temporal.as-of-boundary"], "policy_bundle_versions": ["v"]}
_UNCASED: dict[str, dict[str, Any]] = {
    "ccf.admission-record": {
        "tenant_id": TENANT,
        "peer_id": "fixture-peer",
        "product_content_address": "0" * 64,
        "producer_lineage": _LINEAGE,
        "consumer_lineage": _LINEAGE,
        "merged_lineage": _LINEAGE,
        "admitted_at": _AT,
        "issuance": {
            "answered": {"asked_at": _AT, "freshness": "fixture-freshness", "intent": "fixture-intent", "subject": "s"},
            "echo": {"parameters": {"subject": "s"}, "product_id": "fixture.product", "temporal_boundary": _AT},
            "issued_at": _AT,
            "nonce": "fixture-nonce-0001",
            "schema_version": "1.0.0",
        },
    },
    "ccf.agent-definition": {
        "schema_version": "1.0.0",
        "artifact_version": "1.0.0",
        "name": "fixture-agent",
        "tenant": TENANT,
        "archetypes": ["context_assembly"],
        "context_contract": {"consumes": [{"product_class": "fixture.child", "schema_version": "1.0.0"}], "emits": []},
        "perspective": {"role": "analyst", "selection_params": {}},
        "policy_regime": {"ref": f"ccf-artifact://{TENANT}/fixture.policy-bundle/regime@1.0.0"},
        "halflife_debt_profile": {"ref": f"ccf-artifact://{TENANT}/debt-profile/fixture@1.0.0"},
        "instruction_bindings": [],
    },
    "ccf.approval-policy": {"semver": "1.0.0", "eligible_principals": ["fixture-approver"]},
    "ccf.eligibility-evidence-policy": {"max_evidence_age_seconds": 1, "permitted_clock_skew_seconds": 1},
    "ccf.entity-invalidation-record": {
        "semver": "1.0.0",
        "tenant_id": TENANT,
        "entity_uri": "entity://fixture",
        "invalidated_from": "2026-03-02T12:00:00.000000Z",
        "reason": "entity-claim-superseded",
        "source": "claim-fixture",
    },
    "ccf.erasure-subject-declaration": {
        "semver": "1.0.0",
        "tenant_id": TENANT,
        "subjects": [
            {
                "class_id": "fixture-person",
                "identifier_kind": "opaque",
                "key_paths": ["customer.id"],
                "artifact_classes": ["fixture-note"],
                "subject_ref_salt": "fixture-salt-not-a-secret",
            }
        ],
    },
    "ccf.hitl-policy": {"semver": "1.0.0"},
    "ccf.peering-inbound-payload-ceiling": {"semver": "1.0.0", "max_payload_bytes": 16},
    "ccf.peering-trust-policy": {
        "semver": "1.0.0",
        "tenant_id": TENANT,
        "peers": {
            "fixture-peer": {
                "permitted_clock_skew_seconds": 60,
                "permitted_policy_regimes": ["fixture-policy"],
                "permitted_producer_hashes": ["sha256:fixture-producer"],
                "permitted_schema_names": ["fixture.product"],
                "signature_max_age_seconds": 900,
                # A PUBLIC key, the one tests/peering already commits; nothing here is secret.
                "signing_keys": {
                    "fixture-key-1": {
                        "crv": "P-256",
                        "kid": "fixture-key-1",
                        "kty": "EC",
                        "x": "eWDQK4FVfn6TFEzQPuMTM1VH9j4uk7CsH54XYTDaB5k",
                        "y": "EXbSh4qzBfl_d9e4YvZjmdvaCaFGp8IEgaqDlFIWhnI",
                    }
                },
            }
        },
    },
    "ccf.product-entitlement-policy": {
        "tenant_id": TENANT,
        "policy_version": "1.0.0",
        "principals": {
            "fixture-principal": {"permitted_roles": ["fixture-role"], "permitted_schema_names": ["fixture.product"]}
        },
    },
    "ccf.product-request-contract": {
        "semver": "1.0.0",
        "schema_name": "fixture.product",
        "schema_version": "1.0.0",
        "arguments": {"properties": {}, "required": []},
    },
    "ccf.prompt-artifact": {
        "schema_version": "1.0.0",
        "artifact_version": "1.0.0",
        "name": "fixture-prompt",
        "tenant": TENANT,
        "template": "fixture body",
        "declared_parameters": [],
    },
    "ccf.retention-hold-policy": {"semver": "1.0.0", "tenant_id": TENANT, "classes": {}},
    "ccf.scope-mapping": {
        "semver": "1.0.0",
        "scopes": {
            "fixture:scope": {
                "action_ids": ["fixture.action"],
                "resource_patterns": ["fixture-resource"],
                "tenant_patterns": ["tenant-*"],
            }
        },
    },
    "ccf.skill-catalog-entry": {
        "schema_version": "1.0.0",
        "artifact_version": "1.0.0",
        "name": "fixture-skill",
        "tenant": TENANT,
        "skill_type": "peering",
        "description": "fixture skill",
        "argument_schema": {"properties": {}, "required": []},
        "binding": {"endpoint": "fixture-endpoint"},
        "requirements": {"required_context_products": [], "required_scopes": []},
        "produces": "fixture.product",
    },
    "ccf.skill-grant": {
        "schema_version": "1.0.0",
        "artifact_version": "1.0.0",
        "name": "fixture-grant",
        "tenant": TENANT,
        "agent_definition_hash": "0" * 64,
        "skill_name": "fixture-skill",
        "skill_version": "1.0.0",
    },
    "ccf.task-definition": {
        "schema_version": "1.0.0",
        "artifact_version": "1.0.0",
        "name": "fixture-task",
        "tenant": TENANT,
        "steps": [{"kind": "hitl-gate", "name": "fixture-approval", "ref": None}],
        "instruction_bindings": [],
    },
    "ccf.workflow-definition": {
        "schema_version": "2.0.0",
        "artifact_version": "1.0.0",
        "name": "fixture-workflow",
        "tenant": TENANT,
        "task_definition_ref": f"ccf-artifact://{TENANT}/ccf.task-definition/fixture-task@1.0.0",
        "start": "fixture-approval",
        "transitions": [],
        "terminal_states": ["fixture-approval"],
        "gate_policies": {"fixture-approval": f"ccf-artifact://{TENANT}/approval-policy/fixture@1.0.0"},
        "gate_routes": {},
        "exception_refs": {},
    },
}

_CASED: dict[str, dict[str, Any]] = {}
for _case in CASES:
    _CASED.setdefault(_case.artifact_class.class_id, _case.document)

#: One document per SDK class id: the round-trip module's own case first, this module's otherwise.
SDK_DOCUMENTS: dict[str, dict[str, Any]] = {**_UNCASED, **_CASED}


@functools.lru_cache(maxsize=1)
def _sdk_class_constants() -> dict[str, frozenset[ArtifactClass]]:
    """Every ``ArtifactClass`` constant any module of ``ccf`` or ``ccf_runtime`` defines, grouped by class id.

    ``tests/deployment/test_class_lookup.py::_every_sdk_artifact_class``'s walk, widened to ``ccf_runtime``, where
    ``ccf.scope-mapping`` lives. A module that needs an optional extra the environment lacks is skipped, as there;
    a class living in one would then be missing here and fail the coverage test below by name.
    """
    found: dict[str, set[ArtifactClass]] = {}
    for package in (ccf, ccf_runtime):
        for info in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
            try:
                module = importlib.import_module(info.name)
            except ImportError:  # pragma: no cover - optional extras
                continue
            for value in vars(module).values():
                if isinstance(value, ArtifactClass):
                    found.setdefault(value.class_id, set()).add(value)
    return {class_id: frozenset(group) for class_id, group in found.items()}


def _sdk_class(class_id: str) -> ArtifactClass:
    (constant,) = _sdk_class_constants()[class_id]
    return constant


def test_control_every_sdk_class_is_measured_here() -> None:
    """Non-vacuity: the classes below are exactly the SDK's, each one id to one class, all in the reserved namespace."""
    constants = _sdk_class_constants()
    assert constants, "the walk found no ArtifactClass constant; every SDK-class control below would prove nothing"
    assert set(constants) == set(SDK_DOCUMENTS), (
        f"SDK classes with no document here: {sorted(set(constants) - set(SDK_DOCUMENTS))};"
        f" documents for no SDK class: {sorted(set(SDK_DOCUMENTS) - set(constants))}"
    )
    assert not set(_UNCASED) & set(_CASED), sorted(set(_UNCASED) & set(_CASED))
    for class_id, group in constants.items():
        assert len(group) == 1, f"{class_id!r} names {len(group)} different classes: {group}"
        assert class_id.startswith("ccf."), class_id


def test_control_no_sdk_contract_states_a_class_id() -> None:
    """Why the check cannot reach an SDK class: it reads only a document that states its own class, and none does."""
    stating = sorted(
        class_id for class_id in _sdk_class_constants() if "class_id" in _sdk_class(class_id).contract.model_fields
    )
    assert stating == [], stating


@pytest.mark.parametrize("class_id", sorted(SDK_DOCUMENTS))
def test_control_every_sdk_class_still_parses_validates_and_registers(class_id: str) -> None:
    """Every SDK class, not a sample: its own contract, admitted by ``validate``, registered and bound to its id."""
    artifact_class = _sdk_class(class_id)
    parsed = parse_artifact(SDK_DOCUMENTS[class_id], artifact_class)
    assert type(parsed) is artifact_class.contract, (type(parsed), artifact_class.contract)
    assert artifact_class.validate(parsed) is parsed
    registry = ControlPlaneRegistry()
    key = f"{TENANT}/{class_id}"
    authorized = register_capability(key, Register)
    if "artifact_version" in artifact_class.contract.model_fields:
        version = registry.register_versioned(authorized, parsed, artifact_class)
    else:
        version = registry.register_typed(authorized, parsed, artifact_class)
    assert isinstance(version, str), version
    assert registry.artifact_class_of(key) == class_id
    assert registry.resolve(key, version) == parsed
    assert registry.audit_events()[0].artifact_class == class_id


# ---------------------------------------------------------------------------
# 3. Controls: adopters and the class-identity guard are unchanged.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("class_id", ADOPTER)
def test_control_an_adopter_class_built_directly_still_takes_the_envelope(class_id: str) -> None:
    """The reservation is one prefix wide and no wider, on the constructor as on the declaration function."""
    presented = _direct(class_id)
    artifact = parse_artifact(_envelope(class_id), presented)
    assert load_artifact(yaml.safe_dump(_envelope(class_id)), presented) == artifact
    registry = ControlPlaneRegistry()
    key = f"{TENANT}/{class_id}"
    version = registry.register_typed(register_capability(key, Register), artifact, presented)
    assert registry.artifact_class_of(key) == class_id and registry.resolve(key, version) == artifact
    versioned = ControlPlaneRegistry()
    outcome = versioned.register_versioned(
        register_capability(key, Register),
        _VersionedEnvelope.model_validate({**_envelope(class_id), "artifact_version": "1.0.0"}),
        _direct(class_id, _VersionedEnvelope),
    )
    assert isinstance(outcome, str) and versioned.artifact_class_of(key) == class_id


@pytest.mark.parametrize(
    ("presented", "states"),
    [
        pytest.param(
            lambda: declared_artifact_class("acme.policy-bundle"), "ccf.workflow-definition", id="reserved-as-adopter"
        ),
        pytest.param(lambda: _direct("ccf.workflow-definition"), "acme.policy-bundle", id="adopter-as-reserved"),
    ],
)
def test_control_a_disagreeing_document_is_still_a_class_id_mismatch(
    presented: Callable[[], ArtifactClass], states: str
) -> None:
    """The identity check runs first: a document stating one class and presented as another keeps its own refusal."""
    artifact_class = presented()
    with pytest.raises(ValueError) as raised:
        parse_artifact(_envelope(states), artifact_class)
    assert type(raised.value).__name__ == "ArtifactClassIdMismatch", type(raised.value)
    assert getattr(raised.value, "presented_class_id", None) == artifact_class.class_id
    assert getattr(raised.value, "document_class_id", None) == states


# ---------------------------------------------------------------------------
# 4. Controls: the boot doors and the paved road.
# ---------------------------------------------------------------------------


@pytest.fixture()
def validate_spy(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[tuple[str, str]]]:
    """Every ``(class id, outcome)`` ``ArtifactClass.validate`` produced: ``"admitted"`` or the refusal's name."""
    seen: list[tuple[str, str]] = []
    real = artifact_base.ArtifactClass.validate

    def spy(self: ArtifactClass, artifact: object) -> Any:
        try:
            admitted = real(self, artifact)
        except Exception as refused:
            seen.append((self.class_id, type(refused).__name__))
            raise
        seen.append((self.class_id, "admitted"))
        return admitted

    monkeypatch.setattr(artifact_base.ArtifactClass, "validate", spy)
    yield seen


def _as_text(value: Any) -> Any:
    """A document as an author writes it: decimals and instants as text (``load_artifact`` refuses a float)."""
    if isinstance(value, dict):
        return {key: _as_text(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_as_text(item) for item in value]
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def test_control_the_manifest_door_registers_every_manifest_addressable_sdk_class(
    deployment: Deployment, tmp_path: pathlib.Path, validate_spy: list[tuple[str, str]]
) -> None:
    """``load_and_boot`` over one manifest naming every class a manifest can address: all admitted, all bound."""
    addressable = {**SDK_ARTIFACT_CLASSES, **SDK_VERSIONED_ARTIFACT_CLASSES}
    document = manifest_document()
    named = {entry["class_id"] for entry in document["artifacts"]}
    for class_id in sorted(set(addressable) - named):
        filename = f"sdk-{class_id.removeprefix('ccf.')}.yaml"
        write_artifact(deployment.root, filename, _as_text(SDK_DOCUMENTS[class_id]))
        registration = "versioned" if class_id in SDK_VERSIONED_ARTIFACT_CLASSES else "typed"
        document["artifacts"].append(
            {
                "path": filename,
                "key": f"{TENANT}/{class_id}",
                "class_id": class_id,
                "role": "register",
                "registration": registration,
            }
        )
    registry = ControlPlaneRegistry()
    booted = load_and_boot(
        deployment.variant_manifest("every-sdk-class.yaml", document),
        registry=registry,
        connection={"database_path": str(tmp_path / "graph.sqlite3"), "writer_lease_lock_dir": lock_dir_beside(str(tmp_path / "graph.sqlite3"))},
    )
    try:
        pinned = {pin.class_id: pin.key for pin in booted.pins.entries}
    finally:
        booted.handle.close()
    loaded_only = {class_id for class_id, role in SDK_ARTIFACT_ROLES.items() if role == "load"}
    assert set(addressable) - loaded_only <= set(pinned), sorted(set(addressable) - loaded_only - set(pinned))
    for class_id in set(addressable) - loaded_only:
        assert registry.artifact_class_of(pinned[class_id]) == class_id, class_id
    admitted = {class_id for class_id, outcome in validate_spy if outcome == "admitted"}
    assert set(addressable) <= admitted, sorted(set(addressable) - admitted)
    assert [entry for entry in validate_spy if entry[1] != "admitted"] == []


def _paved_tree(tmp_path: pathlib.Path, **policy: str) -> pathlib.Path:
    # `D-IMPL-378` ruling P6 (a): this module opens the tree only with `fixture.plan_factory`, whose
    # projection never sets the withheld signal (it positively declares so, E2 (ii) (d)), and with
    # `fixture.Acquire`, which returns one constant envelope whatever subject it is asked about; at the
    # SDK's default stance the P6 probe refuses every question of it as a population read. Its stance,
    # stated from that behavior, is `never`, as `fixture.producer_config`'s other openers state it.
    config = fixture.producer_config(subject_withholding=SUBJECT_WITHHOLDING_NEVER)
    config["policy"] = {**config["policy"], **policy}
    return fixture.write_tree(tmp_path / "deployment", config=config, environment=fixture.producer_environment_text())


def _ask_on_the_paved_road(root: pathlib.Path, tmp_path: pathlib.Path, control_plane: ControlPlaneRegistry) -> Any:
    with open_product(
        erasure_trust=declared_erasure_trust(fixture.PRODUCER_TENANT),
        config_root=root,
        scratch=tmp_path / "scratch",
        acquire=fixture.Acquire(),
        project=fixture.plan_factory,
        assess=fixture.assess,
        environ={fixture.CHILD_DSN_VAR: "postgresql://fixture"},
        control_plane=control_plane,
        clock=lambda: fixture.ADMITTED_AT,
    ) as opened:
        return opened.answer(
            opened.question(
                subject="acct-1",
                asked_at=fixture.ASKED_AT,
                intent="fixture-intent",
                freshness="fixture-freshness",
                parameters={fixture.THRESHOLD_PARAMETER: 1000},
            )
        )


def _sdk_ids() -> set[str]:
    return set(_sdk_class_constants())


def test_control_the_config_door_and_the_paved_road_refuse_nothing_an_sdk_class_presents(
    tmp_path: pathlib.Path, validate_spy: list[tuple[str, str]]
) -> None:
    """``open_product`` serves and ``load_config_and_boot`` pins over one paved tree; ``validate`` refuses nothing."""
    root = _paved_tree(tmp_path)
    control_plane = ControlPlaneRegistry()
    declare_wide_temporal_boundary(control_plane, tenant_id=fixture.PRODUCER_TENANT)
    served = _ask_on_the_paved_road(root, tmp_path, control_plane)
    assert isinstance(served, ServedProduct), served
    paved = list(validate_spy)
    validate_spy.clear()
    fabric = load_config_and_boot(
        root / "ccf_config.yaml",
        registry=control_plane,
        connection={"database_path": str(tmp_path / "config-boot.sqlite3"), "writer_lease_lock_dir": lock_dir_beside(str(tmp_path / "config-boot.sqlite3"))},
        for_question=True,
    )
    try:
        for pin in fabric.pins.entries:
            assert control_plane.artifact_class_of(pin.key) == pin.class_id, pin
    finally:
        fabric.handle.close()
    for door, seen in (("paved road", paved), ("config door", validate_spy)):
        assert {class_id for class_id, _ in seen} & _sdk_ids(), f"the {door} presented no SDK class to validate"
        assert [entry for entry in seen if entry[1] != "admitted"] == [], (door, seen)


#: ``(manifest entry class, the class the document states, registration)`` -> the door's own refusal:
#: ``(refusal name, the SDK function that raises it)``.
#: The reservation's refusal in ``resolve_artifact_class`` is ``ReservedArtifactClassId``, one rule with one
#: name (OWED-RULINGS-3 3P2 (b), Dave, 2026-10-09 06:21 MST; it was a plain ``ValueError``).
MANIFEST_SHAPES = {
    "reserved-entry-not-shipped": (
        ("ccf.made-up-class", "ccf.made-up-class", "typed"),
        ("ReservedArtifactClassId", "classes.py::resolve_artifact_class"),
    ),
    "reserved-entry-not-addressable": (
        ("ccf.hitl-policy", "ccf.hitl-policy", "typed"),
        ("ReservedArtifactClassId", "classes.py::resolve_artifact_class"),
    ),
    "sdk-entry-envelope-document": (
        ("ccf.workflow-definition", "ccf.workflow-definition", "versioned"),
        ("ArtifactLoadError", "artifacts.py::parse_artifact"),
    ),
    "adopter-entry-reserved-document": (
        ("fixture.squat", "ccf.workflow-definition", "typed"),
        ("ArtifactClassIdMismatch", "artifact_base.py::validate"),
    ),
}


@pytest.mark.parametrize("shape", sorted(MANIFEST_SHAPES))
def test_control_the_manifest_door_refuses_an_envelope_stating_a_reserved_id_by_its_own_mechanism(
    shape: str, deployment: Deployment, tmp_path: pathlib.Path
) -> None:
    """No manifest builds a reserved class over the envelope, so the door's own refusals fire first, unchanged."""
    (entry_class, states, registration), (name, raised_in) = MANIFEST_SHAPES[shape]
    write_artifact(deployment.root, "squat.yaml", _envelope(states))
    document = manifest_document()
    document["artifacts"].append(
        {"path": "squat.yaml", "key": KEY, "class_id": entry_class, "role": "register", "registration": registration}
    )
    registry = ControlPlaneRegistry()
    with pytest.raises(ValueError) as raised:
        load_and_boot(
            deployment.variant_manifest("squat-manifest.yaml", document),
            registry=registry,
            connection={"database_path": str(tmp_path / "graph.sqlite3"), "writer_lease_lock_dir": lock_dir_beside(str(tmp_path / "graph.sqlite3"))},
        )
    assert (type(raised.value).__name__, _raised_in(raised.value)) == (name, raised_in), raised.value
    assert registry.audit_events() == (), "the manifest door audited something before refusing"


#: The paved config's adopter-owned ``policy`` section, restated -> the door's own refusal, as above.
CONFIG_SHAPES = {
    "reserved-class-not-shipped": (
        {"class_id": "ccf.made-up-class"},
        ("ReservedArtifactClassId", "classes.py::resolve_artifact_class"),
    ),
    "reserved-class-not-addressable": (
        {"class_id": "ccf.hitl-policy"},
        ("ReservedArtifactClassId", "classes.py::resolve_artifact_class"),
    ),
    "sdk-class-versioned": (
        {"class_id": "ccf.workflow-definition", "registration": "versioned"},
        ("ArtifactLoadError", "artifacts.py::parse_artifact"),
    ),
    "sdk-class-typed": (
        {"class_id": "ccf.workflow-definition", "registration": "typed"},
        ("ValueError", "classes.py::refuse_registration_the_sdk_fixes"),
    ),
}


@pytest.mark.parametrize("door", ["config-door", "paved-road"])
@pytest.mark.parametrize("shape", sorted(CONFIG_SHAPES))
def test_control_the_config_door_and_the_paved_road_refuse_a_reserved_policy_class_by_their_own_mechanism(
    shape: str, door: str, tmp_path: pathlib.Path
) -> None:
    """The envelope a config materializes states the class its section names, so the same refusals fire first."""
    policy, (name, raised_in) = CONFIG_SHAPES[shape]
    root = _paved_tree(tmp_path, **policy)
    control_plane = ControlPlaneRegistry()
    declare_wide_temporal_boundary(control_plane, tenant_id=fixture.PRODUCER_TENANT)
    audited = len(control_plane.audit_events())
    with pytest.raises(ValueError) as raised:
        if door == "config-door":
            load_config_and_boot(
                root / "ccf_config.yaml",
                registry=control_plane,
                connection={"database_path": str(tmp_path / "config-boot.sqlite3"), "writer_lease_lock_dir": lock_dir_beside(str(tmp_path / "config-boot.sqlite3"))},
                for_question=True,
            )
        else:
            _ask_on_the_paved_road(root, tmp_path, control_plane)
    assert (type(raised.value).__name__, _raised_in(raised.value)) == (name, raised_in), raised.value
    assert len(control_plane.audit_events()) == audited, f"the {door} audited something before refusing"
