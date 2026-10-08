"""A freshly started process that has asked nothing replays earlier records (`D-IMPL-378` R-A (b)).

Whitepaper §7.10 (Decision Replay). Dave's ruling R-A (b), 2026-10-08 10:47
MST, verbatim *"Agree with recommended option b"*: the resolver also registers
the request contract when it is built
(``src/ccf/products/resolver.py::GovernedResolver.__post_init__``), so any
process that builds the deployment's resolver can replay earlier records,
served or refused, before it has answered a question; record bytes do not
change, and a changed contract still fails replay.

**The hole as worded.** The Control Plane is in-process
(``src/ccf/controlplane/registry.py::ControlPlaneRegistry``), so a new process
holds only what its own boot and its own resolver registered. Every record a
governed resolver writes after resolution pins the TYPED request contract at
its own content address on dimension 2 (`D-IMPL-310`); a boot registers no
typed contract, and the resolver registered it only while answering. So a
process started to replay — an examiner's, after a restart — that had asked
nothing could not resolve that pin for ANY earlier record, served or refused:
``src/ccf/replay/engine.py::replay`` and ``replay_refusal`` raised
``ReplayUnresolvable`` in their prologue (measured by lane ``378d-replayfix``
before the ruling, on two trees).

**What is held here.** This process writes a served and a refused record
through each of two composition roots. A NEW Python process — a subprocess, so
nothing this process registered survives into it — then boots the deployment,
builds its resolver the way that root builds it, asks nothing, and replays
each record against its OWN Control Plane: ``replay`` for the served record,
``replay_refusal`` for the refused one. Each must reconstruct to its own record
address, and the served one to its recorded product address. The child files
no decision record, which the parent checks against the store.

1. The in-process transport
   (``src/ccf/client/adapters/inprocess.py::InProcessAdapter``), whose boot
   builds the resolver. The child reaches the adapter's boot directly, which
   is what ``ask`` does before it answers.
2. The paved road (``src/ccf/products/product.py::open_product``), whose
   replay environment (``src/ccf/replay/environment.py::RecordedEnvironment``,
   `D-IMPL-346`) builds the resolver.

The in-process transport offers no replay environment of its own, so the
served in-process replay uses :class:`_InProcessEnvironment` below:
``RecordedEnvironment``'s construction over the same public members of the
in-process root's resolver.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from collections.abc import Callable, Iterator
from datetime import timedelta
from pathlib import Path
from typing import Any

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
from ccf.controlplane.artifacts import DeclaredArtifact, ProductClassDeclaration
from ccf.controlplane.registry import namespaced_key
from ccf.deployment.operators import build_operator_registry
from ccf.products.contract import ContextProductContract, ProductLineage
from ccf.products.provenance import EffectiveRequest
from ccf.products.refusal import RefusalEnvelope
from ccf.products.request import ProductRequestContract
from ccf.replay.engine import replay, replay_refusal
from ccf.replay.record import NO_PRODUCT_ADDRESS, DecisionReplayRecord
from ccf.replay.serve import ServedProduct
from tests.client.conftest import FIXTURE_DEPLOYMENT, SEEDED_AT, seed
from tests.products import test_paved_road as paved

#: This tree's root: the child imports THIS tree's SDK and test helpers.
_TREE = Path(__file__).resolve().parents[2]

#: The client fixture's product and its one required parameter.
_PRODUCT = "fixture.widgets-over-score"
_THRESHOLD = "minimum_score"

#: How long a child may take before the test calls it a failure.
_CHILD_TIMEOUT_SECONDS = 300


# --- the child: a NEW process that boots, asks nothing, and replays ----------------


class _InProcessEnvironment:
    """``RecordedEnvironment``'s construction, over the in-process root's own resolver.

    Every member is read from the record or from a public member of the
    resolver the in-process boot built; the engine checks everything returned
    (a wrong plan fails the step sequence, a wrong parameter set the parameter
    hash, a wrong envelope the content address).
    """

    def __init__(self, booted: Any, record: DecisionReplayRecord) -> None:
        resolver, fabric = booted.resolver, booted.fabric
        path = record.content_generation_path
        resolution = record.policy_bindings.request_resolution
        effective = (
            EffectiveRequest.model_validate_json(resolution)
            if isinstance(resolution, str)
            else resolution
        )
        assert isinstance(effective, EffectiveRequest) and path.request is not None
        declaration = fabric.artifacts.get(resolver.product_class_key)
        assert isinstance(declaration, ProductClassDeclaration)
        self._declaration = declaration
        self._plan_factory = resolver.plan_factory
        self._policy_key = resolver.policy_bundle_key
        self._window = timedelta(seconds=int(resolver.product_ttl_seconds))
        self._request = path.request.model_copy(update={"parameters": dict(effective.values())})
        self._required = tuple(path.operator_plan)
        self._operators = build_operator_registry(
            parameters=resolver.operator_parameters(self._request),
            view=fabric.handle.reader.as_of(
                tenant_id=record.tenant_id,
                at=record.context_fabric_snapshot.temporal_boundary,
            ),
            pins=fabric.pins,
            policy_bundle_key=self._policy_key,
        )

    def resolve_plan(self, *, plan_id: str) -> Any:
        return self._plan_factory(required=self._required, request=self._request)

    def resolve_operators(self, *, operator_keys: tuple[str, ...]) -> Any:
        return self._operators

    def rehydrate_product(self, *, record: DecisionReplayRecord, projection: Any) -> ContextProductContract:
        path, snapshot = record.content_generation_path, record.context_fabric_snapshot
        return ContextProductContract(
            schema_name=self._declaration.schema_name,
            schema_version=self._declaration.schema_version,
            plan_id=projection.plan_id,
            tenant_id=record.tenant_id,
            temporal_boundary=snapshot.temporal_boundary,
            expires_at=(path.ttl_anchor_at or snapshot.temporal_boundary) + self._window,
            ttl_anchor=self._declaration.ttl_anchor,
            ttl_anchor_at=path.ttl_anchor_at,
            lineage=ProductLineage(
                operators_invoked=frozenset(path.operator_plan),
                policy_bundle_versions=frozenset(
                    binding.version
                    for binding in record.policy_bindings.bindings
                    if binding.key == self._policy_key
                ),
                graph_snapshot_at=snapshot.temporal_boundary,
            ),
            payload=projection.payload,
            debt=path.debt,
            debt_evidence=path.debt_evidence,
            source_refresh_recency=path.source_refresh_recency,
            obligation_in_force=path.obligation_in_force,
            computed_empty=path.computed_empty,
        )


def _replay_one(
    *,
    address: str,
    record: DecisionReplayRecord,
    store: Any,
    reader: Any,
    control_plane: Any,
    environment: Callable[[], Any],
) -> dict[str, Any]:
    """Replay one record by its kind and report what came back, or what was raised."""
    served = record.content_generation_path.product_content_address != NO_PRODUCT_ADDRESS
    try:
        if served:
            outcome = replay(
                record_address=address, store=store, reader=reader,
                control_plane=control_plane, environment=environment(),
            )
            return {
                "outcome": type(outcome).__name__,
                "record_address": outcome.record_content_address,
                "product_address": outcome.product_content_address,
            }
        refused = replay_refusal(
            record_address=address, store=store, reader=reader,
            control_plane=control_plane, environment=environment(),
        )
        return {"outcome": type(refused).__name__, "record_address": refused.record_content_address}
    except Exception as error:  # noqa: BLE001 - reported to the parent by name
        return {"outcome": f"RAISED {type(error).__name__}: {error}"}


def _inprocess_store(root: Path) -> FileArtifactStore:
    document = load_binding_document(root)
    return FileArtifactStore(
        root=document.artifact_store,
        write_kinds=WriteKinds.declare({document.replay_record_class: (ReplayMint,)}),
    )


def _child_in_process(spec: dict[str, Any]) -> dict[str, Any]:
    root = Path(spec["deployment"])
    adapter = InProcessAdapter(str(root), clock=lambda: SEEDED_AT)
    # The boot `ask` performs before it answers — and nothing after it.
    booted = adapter._ensure_booted()
    store = _inprocess_store(root)
    results: dict[str, Any] = {}
    try:
        for label, address in spec["records"].items():
            record = DecisionReplayRecord.model_validate_json(store.get(content_address=address))
            results[label] = _replay_one(
                address=address, record=record, store=store,
                reader=booted.fabric.handle.reader, control_plane=booted.control_plane,
                environment=lambda record=record: _InProcessEnvironment(booted, record),
            )
        report_key = spec.get("report_key")
        if report_key is not None:
            # What THIS process's Control Plane holds under the key, and the
            # content address of the contract this deployment holds now.
            declared = booted.fabric.artifacts[report_key]
            assert isinstance(declared, DeclaredArtifact), type(declared)
            results["_registered"] = list(booted.control_plane.versions(report_key))
            results["_now"] = content_hash(ProductRequestContract.from_declared(declared))
    finally:
        inprocess.reset_boot_cache()
    return results


def _child_paved(spec: dict[str, Any]) -> dict[str, Any]:
    from ccf.deployment import load_config_and_boot
    from ccf.replay.environment import RecordedEnvironment

    results: dict[str, Any] = {}
    # A fresh Control Plane: `_open` grants the declared skills into a new registry.
    with paved._open(Path(spec["tree"]), Path(spec["scratch"])) as opened:
        for label, entry in spec["records"].items():
            record = DecisionReplayRecord.model_validate_json(
                opened.artifact_store.get(content_address=entry["address"])
            )
            # The question's own minted substrate, reopened read-only (dr-01's shape).
            fabric = load_config_and_boot(
                opened.config_path, registry=opened.control_plane,
                connection={"database_path": entry["minted"]}, read_only=True,
            )
            try:
                environment = RecordedEnvironment(record=record, opened=opened, fabric=fabric)
                results[label] = _replay_one(
                    address=entry["address"], record=record, store=opened.artifact_store,
                    reader=fabric.handle.reader, control_plane=opened.control_plane,
                    environment=lambda environment=environment: environment,
                )
            finally:
                fabric.handle.close()
    return results


_CHILDREN: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "in-process": _child_in_process,
    "paved": _child_paved,
}


def _child(spec_path: str) -> None:
    """The NEW process's entry point: replay what the spec names, write the results."""
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    results = _CHILDREN[spec["root"]](spec)
    Path(spec["results"]).write_text(json.dumps(results, sort_keys=True), encoding="utf-8")


def _run_child(tmp_path: Path, spec: dict[str, Any]) -> dict[str, Any]:
    """Run :func:`_child` in a NEW Python process over THIS tree, and read its results."""
    spec = {**spec, "results": str(tmp_path / f"results-{spec['root']}.json")}
    spec_path = tmp_path / f"spec-{spec['root']}.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    inherited = os.environ.get("PYTHONPATH", "")
    roots = [str(_TREE / "src"), str(_TREE / "runtime"), str(_TREE), str(_TREE / "tests")]
    environment = {**os.environ, "PYTHONPATH": os.pathsep.join([*roots, *([inherited] if inherited else [])])}
    completed = subprocess.run(
        [
            sys.executable, "-B", "-c",
            "import sys; from tests.replay.test_fresh_process_replay import _child; _child(sys.argv[1])",
            str(spec_path),
        ],
        cwd=_TREE, env=environment, capture_output=True, text=True,
        timeout=_CHILD_TIMEOUT_SECONDS, check=False,
    )
    assert completed.returncode == 0, completed.stderr[-4000:]
    return json.loads(Path(spec["results"]).read_text(encoding="utf-8"))


# --- the parent: write the records, then hand them to a fresh process --------------


@pytest.fixture(autouse=True)
def _no_boot_cache() -> Iterator[None]:
    """No booted in-process deployment leaks into or out of a test."""
    inprocess.reset_boot_cache()
    yield
    inprocess.reset_boot_cache()


def _decision_records(directory: Path) -> set[str]:
    """The decision records filed under ``directory``, by file name — never by file count."""
    found: set[str] = set()
    for path in directory.rglob("*"):
        if not path.is_file() or path.name.startswith("."):
            continue
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, UnicodeDecodeError):
            continue
        if isinstance(document, dict) and "policy_bindings" in document:
            found.add(path.name)
    return found


def _write_in_process_records(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    """A seeded client-fixture deployment, and the served and refused records it wrote."""
    root = tmp_path / "deployment"
    shutil.copytree(FIXTURE_DEPLOYMENT, root)
    seed(root)
    adapter = InProcessAdapter(str(root), clock=lambda: SEEDED_AT)
    store = _inprocess_store(root)
    records: dict[str, str] = {}
    for label, parameters in (("served", {_THRESHOLD: 20}), ("refused", {})):
        request = WireRequest(product_id=_PRODUCT, parameters=parameters, temporal_boundary=SEEDED_AT)
        outcome = decode_outcome(adapter.ask(request), sent=request).outcome
        assert (outcome.refusal is None) == (label == "served"), outcome
        records[label] = store.resolve_uri(uri=outcome.replay_ref)
    # Release the writer: the child boots the same graph.
    inprocess.reset_boot_cache()
    return root, records


def _assert_each_reconstructs_to_its_own_address(
    results: dict[str, Any], records: dict[str, str], *, product_addresses: dict[str, str]
) -> None:
    for label, address in records.items():
        result = results[label]
        expected = "ReplayOutcome" if label == "served" else "RefusalReplayOutcome"
        assert result["outcome"] == expected, f"{label}: {result['outcome']}"
        assert result["record_address"] == address, label
    assert results["served"]["product_address"] == product_addresses["served"]


def test_a_fresh_process_that_asked_nothing_replays_in_process_records(tmp_path: Path) -> None:
    """The in-process transport: a new process boots the deployment, asks nothing, and replays."""
    root, records = _write_in_process_records(tmp_path)
    store = _inprocess_store(root)
    served = DecisionReplayRecord.model_validate_json(store.get(content_address=records["served"]))
    filed = _decision_records(Path(load_binding_document(root).artifact_store))

    results = _run_child(tmp_path, {"root": "in-process", "deployment": str(root), "records": records})

    _assert_each_reconstructs_to_its_own_address(
        results, records,
        product_addresses={"served": served.content_generation_path.product_content_address},
    )
    assert _decision_records(Path(load_binding_document(root).artifact_store)) == filed, (
        "the fresh process filed a decision record: it asked something"
    )


def test_a_fresh_process_that_asked_nothing_replays_paved_road_records(tmp_path: Path) -> None:
    """The paved road: a new process opens the product, asks nothing, builds the replay environment, and replays."""
    tree = paved._write_tree(tmp_path / "paved")
    scratch = tmp_path / "paved-scratch"
    records: dict[str, dict[str, str]] = {}
    product_addresses: dict[str, str] = {}
    with paved._open(tree, scratch) as opened:
        for label, extra in (("served", {}), ("refused", {"no_such_parameter": 1})):
            before = set(scratch.glob("paved_fixture_*.sqlite3"))
            outcome = opened.answer(paved._question(opened, **extra))
            (minted,) = set(scratch.glob("paved_fixture_*.sqlite3")) - before
            if label == "served":
                assert isinstance(outcome, ServedProduct), outcome
                address = outcome.replay_ref.content_address
                product_addresses[label] = opened.record_of(outcome).content_generation_path.product_content_address
            else:
                assert isinstance(outcome, RefusalEnvelope), outcome
                address = opened.artifact_store.resolve_uri(uri=outcome.replay_reference)
            records[label] = {"address": address, "minted": str(minted)}
    filed = _decision_records(scratch / "artifact-store")

    results = _run_child(
        tmp_path, {"root": "paved", "tree": str(tree), "scratch": str(scratch), "records": records}
    )

    _assert_each_reconstructs_to_its_own_address(
        results, {label: entry["address"] for label, entry in records.items()},
        product_addresses=product_addresses,
    )
    assert _decision_records(scratch / "artifact-store") == filed, (
        "the fresh process filed a decision record: it asked something"
    )


#: One property's description in the client fixture's request contract.
_DESCRIPTION = "description: Return widgets whose score exceeds this amount."


def test_a_changed_request_contract_still_fails_replay_in_a_fresh_process(tmp_path: Path) -> None:
    """R-A's guard: building the resolver registers the contract the deployment holds NOW.

    The records were decided under one request contract. The deployment's
    document then changes it — one property's description. A fresh process
    builds the resolver, which registers the CHANGED contract at its own,
    different content address, and replays: both records still pin the old
    version, and replay refuses each by name rather than letting the changed
    contract stand in for the one the decisions were made under.
    """
    root, records = _write_in_process_records(tmp_path)
    store = _inprocess_store(root)
    document = load_binding_document(root)
    decided = {
        label: DecisionReplayRecord.model_validate_json(store.get(content_address=address))
        for label, address in records.items()
    }
    key = namespaced_key(tenant=decided["served"].tenant_id, key=document.request_contract_key)
    pinned = {
        label: {binding.key: binding.version for binding in record.policy_bindings.bindings}[key]
        for label, record in decided.items()
    }
    assert pinned["served"] == pinned["refused"], pinned
    config = root / "ccf_config.yaml"
    text = config.read_text(encoding="utf-8")
    assert text.count(_DESCRIPTION) == 1, "the fixture's request-contract description moved"
    config.write_text(text.replace(_DESCRIPTION, f"{_DESCRIPTION[:-1]} (amended)."), encoding="utf-8")

    results = _run_child(
        tmp_path, {"root": "in-process", "deployment": str(root), "records": records, "report_key": key}
    )

    # Positive control: the fresh process's resolver DID register a request
    # contract under the key — the changed one, at a different address.
    assert results["_registered"] == [results["_now"]], results
    assert results["_now"] != pinned["served"], "the change did not change the contract's address"
    for label in records:
        outcome = results[label]["outcome"]
        assert outcome.startswith("RAISED ReplayUnresolvable: "), f"{label}: {outcome}"
        assert repr((key, pinned[label])) in outcome, f"{label}: {outcome}"
