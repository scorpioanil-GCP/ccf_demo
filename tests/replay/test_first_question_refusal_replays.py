"""A refusal asked FIRST of a fresh Control Plane replays against that Control Plane (`CP17-F-09`).

Whitepaper §7.10 (Decision Replay); CLAUDE.md §9's three-issue cap; lane
``378d-replayfix`` of ``D-IMPL-378``. The finding was recorded twice and carried
unrepaired: ``CP17-F-09`` (cp-17, charged to the cap at ``D-GATE-cp-17``) and
``ATM-F-11`` (cp-19, its second instance), each kept executable only as an
estate-gated strict expected failure. It was reproduced again on 2026-10-08 on
the always-on client fixture, with no estate and no demonstration declaration.

**The mechanism.** A governed refusal reached AFTER the request was resolved
against the class's request contract — a resolution-stage refusal, a temporal
bound, a refusal held at the acquisition seam — records that resolution on
dimension 2, so its record pins the request contract at the TYPED contract's
own content address (`D-IMPL-310`: the pin belongs there). The resolver
registered that exact version only inside
``src/ccf/products/resolver.py::GovernedResolver._register``, which the served
path reaches and those refusals never do. Asked first of a fresh Control Plane,
such a refusal leaves a record whose pin nothing registered, and
``src/ccf/replay/engine.py::replay_refusal`` refuses it in its prologue with
``ReplayUnresolvable`` — *"the configuration this decision was made under is
gone"* — although that configuration never changed. A served question before it
masked the gap, so the record's replayability depended on unrelated history.

**What is held here, on two composition roots.** The record replays against
the deciding deployment's own Control Plane — ``replay_refusal`` returns the
reconstruction at the record's own address with its own refusal block — and the
pin it resolves is the version the record already carried: the typed request
contract's content address, derived here independently of the record. Nothing
about a record's bytes or address is changed by the repair; it registers the
version the record already pins, before the first record that pins it.

1. ``src/ccf/client/adapters/inprocess.py::InProcessAdapter`` over the client
   fixture, with the request contract declared ``role: load`` and
   ``role: register`` (the boot registers the declared wrapper under the same
   key at a DIFFERENT version, so ``register`` does not rescue the pin), for a
   resolution-stage refusal and a temporal-bound refusal.
2. ``src/ccf/products/product.py::OpenedProduct`` (the paved road) with an
   acquisition seam that raises a governed refusal — ``CP17-F-09`` exactly as
   worded, offline.

Neither the reader nor the environment is consulted on the no-read refusal
path, and both are stand-ins that raise if reached.
"""

from __future__ import annotations

import pathlib
import shutil
from collections.abc import Iterator
from datetime import timedelta
from typing import Any, cast

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import WriteKinds
from ccf.authz.capability import ReplayMint
from ccf.client.adapters import inprocess
from ccf.client.adapters.binding_document import load_binding_document
from ccf.client.adapters.inprocess import InProcessAdapter
from ccf.client.codec import decode_outcome
from ccf.client.wire import WireRequest
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import DeclaredArtifact
from ccf.controlplane.registry import namespaced_key
from ccf.products.request import ProductRequestContract
from ccf.products.refusal import (
    RESOLVED_BY_THE_RESOLVER,
    GovernedRefusalRaised,
    RefusalEnvelope,
    SubjectUnavailableRefusal,
)
from ccf.replay.engine import RefusalReplayOutcome, replay_refusal
from ccf.replay.record import NO_FABRIC_READ, DecisionReplayRecord
from tests.client.conftest import FIXTURE_DEPLOYMENT, SEEDED_AT, seed
from tests.products.test_paved_road import (  # noqa: F401 — `tree` is a fixture
    _open,
    _question,
    tree,
)

#: The fixture's one required parameter, read from its own document by name.
_THRESHOLD = "minimum_score"

#: The request-contract section's role line in the fixture document; the
#: ``register`` variant rewrites exactly this line and nothing else.
_ROLE_LINE = "  class_id: fixture.request-contract\n  role: load\n"


class _Unreachable:
    """A reader or environment the no-read refusal path must never consult."""

    def __getattr__(self, name: str) -> Any:
        raise AssertionError(
            f"the no-read refusal path consulted `{name}`; it reads no fabric and"
            " resolves no plan"
        )


@pytest.fixture(autouse=True)
def _no_boot_cache() -> Iterator[None]:
    """No booted in-process deployment leaks into or out of a test."""
    inprocess.reset_boot_cache()
    yield
    inprocess.reset_boot_cache()


def _deployment(tmp_path: pathlib.Path, *, role: str) -> pathlib.Path:
    """A seeded private copy of the client fixture, its request contract at ``role``."""
    root = tmp_path / "deployment"
    shutil.copytree(FIXTURE_DEPLOYMENT, root)
    config = root / "ccf_config.yaml"
    text = config.read_text(encoding="utf-8")
    assert text.count(_ROLE_LINE) == 1, "the fixture's request-contract role line moved"
    config.write_text(
        text.replace(_ROLE_LINE, _ROLE_LINE.replace("role: load", f"role: {role}")),
        encoding="utf-8",
    )
    seed(root)
    return root


#: Two refusals reached after the request was resolved against its contract,
#: and before anything is acquired or served. Each is the FIRST question its
#: deployment's Control Plane is ever asked.
_FIRST_QUESTIONS = {
    # The resolution stage: the one required parameter omitted.
    "missing-required-parameter": ({}, timedelta(0)),
    # The temporal bound: asked twenty years before the fixture's pinned clock,
    # past its declared ten-year reach.
    "asked-at-outside-temporal-bound": ({_THRESHOLD: 20}, -timedelta(days=365 * 20)),
}


@pytest.mark.parametrize("role", ["load", "register"])
@pytest.mark.parametrize("reason", sorted(_FIRST_QUESTIONS))
def test_an_in_process_refusal_asked_first_replays_against_its_own_control_plane(
    tmp_path: pathlib.Path, role: str, reason: str
) -> None:
    """The in-process transport's first answer is a refusal, and it reconstructs.

    The probe that reproduced ``CP17-F-09`` on 2026-10-08, held as a test:
    before the repair, ``replay_refusal`` raised ``ReplayUnresolvable`` naming
    the request-contract binding at the version the record pins.
    """
    root = _deployment(tmp_path, role=role)
    parameters, offset = _FIRST_QUESTIONS[reason]
    request = WireRequest(
        product_id="fixture.widgets-over-score",
        parameters=parameters,
        temporal_boundary=SEEDED_AT + offset,
    )
    adapter = InProcessAdapter(str(root), clock=lambda: SEEDED_AT)
    decoded = decode_outcome(adapter.ask(request), sent=request)
    refusal = decoded.outcome.refusal
    assert refusal is not None and refusal.reason == reason, refusal

    document = load_binding_document(root)
    store = FileArtifactStore(
        root=document.artifact_store,
        write_kinds=WriteKinds.declare({document.replay_record_class: (ReplayMint,)}),
    )
    address = store.resolve_uri(uri=decoded.outcome.replay_ref)
    record = DecisionReplayRecord.model_validate_json(store.get(content_address=address))
    assert record.content_generation_path.plan_id == NO_FABRIC_READ, "a pre-read refusal"
    booted = inprocess._BOOT_CACHE[root.resolve()]

    # THE HOLE AS WORDED: the record replays against its own deployment's
    # Control Plane, the first question that plane was ever asked.
    reconstructed = replay_refusal(
        record_address=address,
        store=store,
        reader=cast(Any, _Unreachable()),
        control_plane=booted.control_plane,
        environment=cast(Any, _Unreachable()),
    )
    assert isinstance(reconstructed, RefusalReplayOutcome), reconstructed
    assert reconstructed.record_content_address == address
    assert reconstructed.assembly_refusal == record.content_generation_path.assembly_refusal

    # AND THE PIN IS THE ONE THE RECORD ALREADY CARRIED: the typed request
    # contract's own content address, derived here from the deployment's
    # declaration rather than read back from the record or the registry.
    key = namespaced_key(tenant=booted.fabric.tenant_id, key=document.request_contract_key)
    declared = booted.fabric.artifacts[key]
    assert isinstance(declared, DeclaredArtifact), type(declared)
    typed = ProductRequestContract.from_declared(declared)
    pins = {binding.key: binding.version for binding in record.policy_bindings.bindings}
    assert pins[key] == content_hash(typed), "the record's request-contract pin moved"
    assert booted.control_plane.resolve(key, pins[key]) == typed


class _RefusesAtTheSeam:
    """An acquisition that holds a governed determination and raises it (``D-IMPL-304``)."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, context: Any) -> tuple[Any, ...]:
        self.calls += 1
        raise GovernedRefusalRaised(
            SubjectUnavailableRefusal(
                cause="nonexistent",
                detail="the fixture's source holds no such subject",
                error_code=None,
            ),
            resolution=RESOLVED_BY_THE_RESOLVER,
        )


def test_a_refusal_raised_at_the_acquisition_seam_first_of_a_fresh_product_reconstructs(
    tree: tuple[pathlib.Path, pathlib.Path],
) -> None:
    """``CP17-F-09`` as worded, on the paved road and offline.

    The product's FIRST question is refused at the acquisition seam, recorded
    with the resolver's own completed resolution; ``replay_refusal``
    reconstructs it from the product's one store against the product's one
    Control Plane, with no served question before it.
    """
    root, scratch = tree
    seam = _RefusesAtTheSeam()
    with _open(root, scratch, acquire=cast(Any, seam)) as opened:
        refused = opened.answer(_question(opened))
        assert isinstance(refused, RefusalEnvelope), refused
        assert refused.kind == "subject-unavailable" and seam.calls == 1
        record = opened.record_of(refused)
        address = opened.artifact_store.resolve_uri(uri=refused.replay_reference)
        assert record.content_generation_path.plan_id == NO_FABRIC_READ, "a pre-read refusal"

        reconstructed = replay_refusal(
            record_address=address,
            store=opened.artifact_store,
            reader=cast(Any, _Unreachable()),
            control_plane=opened.control_plane,
            environment=cast(Any, _Unreachable()),
        )
        resolved = [
            opened.control_plane.resolve(binding.key, binding.version)
            for binding in record.policy_bindings.bindings
        ]
    assert isinstance(reconstructed, RefusalReplayOutcome), reconstructed
    assert reconstructed.record_content_address == address
    assert reconstructed.assembly_refusal == record.content_generation_path.assembly_refusal
    # The request contract is among the pins, at its own content address.
    contracts = [
        (binding.version, artifact)
        for binding, artifact in zip(record.policy_bindings.bindings, resolved, strict=True)
        if isinstance(artifact, ProductRequestContract)
    ]
    assert len(contracts) == 1, contracts
    ((version, contract),) = contracts
    assert version == content_hash(contract)
