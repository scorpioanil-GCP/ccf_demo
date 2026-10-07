"""FW-2 (whole-branch review I-1): replay of a classification decision runs beside a live writer (SEC-013 x SEC-023; `D-IMPL-374`).

Whitepaper §7.10 (Decision Replay) is load-bearing, and the whole-branch review
measured it unreachable on every persistent store. Two rulings, each true in
its own lane, failed together: SEC-013 takes the cross-process writer lease at
the boot-token mint, and SEC-023's classification authority is minted only by
``ccf.boot.boot`` — so the only reader that can answer a classification read
came from a boot that always minted a writer and therefore needed the lease the
live serving process holds. An examiner's replay tool in a second process got
``SingleWriterViolation`` from the boot and ``ClassificationAuthorityMissing``
from a raw store reader.

The ruled repair is a READ-ONLY boot: it opens the reader, mints the
classification authority from the governing resolution spec through the same
private mint path as the writer boot, and mints no writer and takes no lease.
The replay environment's fabric is that boot.

Held here, each against the hole as worded:

* (a) a live writer holds the lease on a persistent store — a SQLite file, and
  the Fluree store over the SEC-013 suite's offline network doubles — and a
  second PROCESS replays a classification decision through
  :class:`~ccf.replay.environment.RecordedEnvironment` (SQLite) or answers a
  classification query through the read-only reader (Fluree). Before the
  repair: ``SingleWriterViolation`` caused by ``WriterLeaseHeld``.
* (b) the read-only handle refuses every write, by name, and writes nothing.
* (c) the authority on its views is boot-minted, and a hand-built one is still
  refused.

Offline: SQLite files and in-process network doubles under ``tmp_path``.
"""

from __future__ import annotations

import inspect
import multiprocessing as mp
import pathlib
import uuid
from collections.abc import Callable, Iterator, Mapping
from datetime import UTC, datetime
from typing import Any

import pytest

from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.signal.envelope import SignalEnvelope, SourceIdentity

_TIMEOUT_SECONDS = 180

#: The paved fixture's Policy operator and the entity class it admits on.
POLICY_OPERATOR = "policy.principal-subgraph"
CLASSIFIED_CLASS = "account"
CLASSIFICATION_ATTRIBUTE = "classification"
#: The one source the fixture spec authorizes to assert the classification.
AUTHORIZED_SOURCE = "fixture-system"


def _contract(module: str, name: str) -> Any:
    """The ruled name, or a MISSING CONTRACT failure that names it (FW-2)."""
    import importlib

    try:
        return getattr(importlib.import_module(module), name)
    except (ImportError, AttributeError):
        pytest.fail(f"MISSING CONTRACT: {module}.{name} (FW-2; D-IMPL-374) does not exist on this tree")


def _offers_read_only(function: Callable[..., Any]) -> bool:
    return "read_only" in inspect.signature(function).parameters


# --- (a) SQLite: a second process replays a classification decision -------------


def _classification_config() -> dict[str, Any]:
    """The paved fixture deployment, with a governed Policy operator on its plan.

    The stock paved class declares the traversal alone; a classification
    decision needs the Policy operator on the plan, admitting on an attribute
    the resolution spec governs (SEC-023) — so only the fixture's own source
    may assert it. Fixture vocabulary (CINV-01).
    """
    from tests.deployment.test_replay_binding import OPERATOR_ID
    from tests.products import test_paved_road as paved

    document = paved._config()
    document["product_class"]["required_operator_keys"] = [POLICY_OPERATOR, OPERATOR_ID]
    document["operators"][POLICY_OPERATOR] = {
        "classification_attribute_by_class": {CLASSIFIED_CLASS: CLASSIFICATION_ATTRIBUTE},
        "permitted_classifications": ["fixture-open"],
    }
    document["resolution"]["entity_rules"][0]["attribute_authorities"] = {
        CLASSIFICATION_ATTRIBUTE: [AUTHORIZED_SOURCE]
    }
    return document


def _replay_road(config_path: pathlib.Path, *, registry: Any, connection: Mapping[str, object]) -> Any:
    """The road to a replay reader as this tree offers it.

    Where the deployment door takes ``read_only`` (FW-2), the replay road is the
    read-only boot; on a tree without one it is the only boot there is — the
    writer boot, which needs the lease the live writer holds.
    """
    from ccf.deployment import load_config_and_boot

    if _offers_read_only(load_config_and_boot):
        return load_config_and_boot(config_path, registry=registry, connection=connection, read_only=True)
    return load_config_and_boot(config_path, registry=registry, connection=connection)


def _examiner_replays(
    root: str, scratch: str, minted: str, record_address: str, queue: "mp.Queue[tuple[str, str]]"
) -> None:
    """A second PROCESS — an examiner's replay tool — reconstructing the recorded decision."""
    try:
        from ccf.replay.engine import replay
        from ccf.replay.environment import RecordedEnvironment
        from ccf.replay.record import DecisionReplayRecord
        from tests.products import test_paved_road as paved

        opened = paved._open(pathlib.Path(root), pathlib.Path(scratch))
        record = DecisionReplayRecord.model_validate_json(
            opened.artifact_store.get(content_address=record_address)
        )
        try:
            fabric = _replay_road(
                opened.config_path, registry=opened.control_plane, connection={"database_path": minted}
            )
        except BaseException as exc:  # noqa: BLE001 - reported by name, asserted by the parent
            queue.put(("REFUSED", f"{type(exc).__name__}<-{type(exc.__cause__).__name__}"))
            return
        try:
            stamped = fabric.handle.reader.as_of(
                tenant_id=record.tenant_id, at=record.context_fabric_snapshot.temporal_boundary
            ).classification_authority
            environment = RecordedEnvironment(record=record, opened=opened, fabric=fabric)
            outcome = replay(
                record_address=record_address,
                store=opened.artifact_store,
                reader=fabric.handle.reader,
                control_plane=opened.control_plane,
                environment=environment,
            )
            minted_authority = stamped is not None and bool(getattr(stamped, "minted", False))
            queue.put(("REPLAYED", f"{outcome.product_content_address}|stamped={minted_authority}"))
        finally:
            fabric.handle.close()
    except BaseException:  # noqa: BLE001 - the parent asserts on the text
        import traceback

        queue.put(("ERROR", traceback.format_exc()))


def test_a_second_process_replays_a_classification_decision_beside_a_live_sqlite_writer(
    tmp_path: pathlib.Path,
) -> None:
    from ccf.deployment import load_config_and_boot
    from tests.products import test_paved_road as paved

    root = paved._write_tree(tmp_path, config=_classification_config())
    scratch = tmp_path / "scratch"
    opened = paved._open(root, scratch)
    served = opened.answer(paved._question(opened))
    record = opened.record_of(served)
    # The premise: a CLASSIFICATION decision — the Policy operator ran on its plan.
    assert POLICY_OPERATOR in record.content_generation_path.operator_plan, record.content_generation_path
    minted = str(sorted(scratch.glob("paved_fixture*.sqlite3"))[-1])

    # The serving deployment's live writer, holding the SQLite file's cross-process lease.
    live = load_config_and_boot(
        opened.config_path, registry=opened.control_plane, connection={"database_path": minted}
    )
    try:
        assert live.handle.lease_scope == "cross-process", live.handle.lease_scope
        context = mp.get_context("spawn")
        queue: mp.Queue[tuple[str, str]] = context.Queue()
        process = context.Process(
            target=_examiner_replays,
            args=(str(root), str(scratch), minted, served.replay_ref.content_address, queue),
        )
        process.start()
        try:
            status, detail = queue.get(timeout=_TIMEOUT_SECONDS)
        finally:
            process.join(timeout=_TIMEOUT_SECONDS)
    finally:
        live.handle.close()

    assert status == "REPLAYED", (
        f"the second process could not replay the classification decision beside the live"
        f" writer: {status} {detail}"
    )
    replayed_address, stamped = detail.split("|")
    assert replayed_address == record.content_generation_path.product_content_address
    assert stamped == "stamped=True", detail


# --- (a) Fluree: a second process reads a classification query beside a live writer --


def _classification_query() -> Any:
    from ccf.graph.protocols import GraphQuery
    from tests.conftest import FIXTURE_TENANTS

    return GraphQuery(
        tenant_id=FIXTURE_TENANTS[0],
        as_of=datetime(2026, 3, 1, tzinfo=UTC),
        permitted_policy_bundle_versions=frozenset({"v1"}),
        classification_attribute_by_class={"counterparty": "classification"},
        permitted_classifications=frozenset({"public"}),
    )


def _boot_governed(connection: Mapping[str, Any], *, read_only: bool) -> Any:
    """A Fluree fabric over the SEC-013 doubles whose spec governs the classification attribute."""
    from ccf.boot import boot
    from tests.classification_authority import spec_governing
    from tests.composition import register_at_composition
    from tests.conftest import (
        FIXTURE_TENANTS,
        POLICY_BUNDLE_KEY,
        RESOLUTION_SPEC_KEY,
        _policy_bundle,
        _resolution_spec,
    )

    registry = ControlPlaneRegistry()
    spec = spec_governing(_resolution_spec(), {"counterparty": {"classification": frozenset({"core"})}})
    spec_version = register_at_composition(registry, RESOLUTION_SPEC_KEY, spec)
    policy_version = register_at_composition(registry, POLICY_BUNDLE_KEY, _policy_bundle())
    arguments: dict[str, Any] = dict(
        backend="fluree",
        connection=dict(connection),
        registry=registry,
        resolution_spec_key=RESOLUTION_SPEC_KEY,
        resolution_spec_version=spec_version,
        policy_bundle_key=POLICY_BUNDLE_KEY,
        policy_bundle_version=policy_version,
        tenant_ids=FIXTURE_TENANTS,
    )
    if read_only and _offers_read_only(boot):
        arguments["read_only"] = True
    return boot(**arguments)


def _guard_outcome(reader: Any) -> str:
    """Whether a classification query passes the SEC-023 authority guard on ``reader``.

    The offline doubles answer nothing a query can parse, so a query that got
    PAST the guard fails on the double's empty answer — that is the positive
    signal; the guard's own refusals are reported by name.
    """
    from ccf.graph.protocols import (
        ClassificationAuthorityMissing,
        ClassificationAuthorityNotMinted,
        UngovernedClassificationAttribute,
    )

    try:
        reader.query(_classification_query())
    except (ClassificationAuthorityMissing, ClassificationAuthorityNotMinted, UngovernedClassificationAttribute) as refused:
        return f"guard:{type(refused).__name__}"
    except Exception as past:  # noqa: BLE001 - the doubles answer nothing useful past the guard
        return f"past-guard:{type(past).__name__}"
    return "past-guard:answered"


def _examiner_reads(connection: Mapping[str, Any], queue: "mp.Queue[tuple[str, str]]") -> None:
    """A second PROCESS reading the network graph a live writer holds."""
    from tests.graph.test_network_store_writer_lease import _offline_clients

    with _offline_clients():
        try:
            handle = _boot_governed(connection, read_only=True)
        except BaseException as exc:  # noqa: BLE001 - reported by name, asserted by the parent
            queue.put(("REFUSED", f"{type(exc).__name__}<-{type(exc.__cause__).__name__}"))
            return
        try:
            queue.put(("BOOTED", f"{_guard_outcome(handle.reader)}|{handle.lease_scope}"))
        finally:
            handle.close()


def test_a_second_process_reads_a_classification_query_beside_a_live_fluree_writer(
    tmp_path: pathlib.Path,
) -> None:
    from tests.graph.test_network_store_writer_lease import LEASE_FIELD, _connection, _offline_clients

    connection = _connection("fluree", f"fw2_{uuid.uuid4().hex}")
    connection[LEASE_FIELD] = str(tmp_path)
    with _offline_clients():
        live = _boot_governed(connection, read_only=False)
        try:
            # Positive control: the live writer's own governed reader passes the guard.
            assert _guard_outcome(live.reader).startswith("past-guard:"), _guard_outcome(live.reader)
            context = mp.get_context("spawn")
            queue: mp.Queue[tuple[str, str]] = context.Queue()
            process = context.Process(target=_examiner_reads, args=(connection, queue))
            process.start()
            try:
                status, detail = queue.get(timeout=_TIMEOUT_SECONDS)
            finally:
                process.join(timeout=_TIMEOUT_SECONDS)
        finally:
            live.close()

    assert status == "BOOTED", f"the second process obtained no classification reader: {status} {detail}"
    guard, scope = detail.split("|")
    assert guard.startswith("past-guard:"), detail
    assert scope == "read-only", detail


# --- (b) and (c): the read-only handle, in this process --------------------------


def _sqlite_boot(database: pathlib.Path, *, read_only: bool) -> Any:
    """A hand-composed SQLite fabric whose spec governs the classification attribute (SEC-023)."""
    from ccf.boot import boot
    from tests.deployment.test_classification_authority_consumer import POLICY_KEY, SPEC_KEY, TENANT, _spec
    from tests.composition import register_at_composition

    registry = ControlPlaneRegistry()
    spec_version = register_at_composition(registry, SPEC_KEY, _spec(governed=True))
    policy_version = register_at_composition(registry, POLICY_KEY, {"regime": "fw-2"})
    arguments: dict[str, Any] = dict(
        backend="sqlite",
        connection={"database_path": str(database)},
        registry=registry,
        resolution_spec_key=SPEC_KEY,
        resolution_spec_version=spec_version,
        policy_bundle_key=POLICY_KEY,
        policy_bundle_version=policy_version,
        tenant_ids=(TENANT,),
    )
    if read_only:
        arguments["read_only"] = True
    return boot(**arguments)


def _envelope(envelope_id: str, label: str) -> SignalEnvelope:
    from tests.deployment.test_classification_authority_consumer import TENANT

    return SignalEnvelope(
        tenant_id=TENANT,
        envelope_id=envelope_id,
        source=SourceIdentity(system_id="source-a"),
        ingestion_timestamp=datetime(2026, 2, 1, tzinfo=UTC),
        observed_time=datetime(2026, 1, 31, tzinfo=UTC),
        raw_payload={"counterparty_lei": "LEI-1", "classification": label},
    )


@pytest.fixture
def populated(tmp_path: pathlib.Path) -> Iterator[pathlib.Path]:
    """A SQLite graph a writer boot populated with one governed entity, then closed."""
    database = tmp_path / "graph.sqlite3"
    writer = _sqlite_boot(database, read_only=False)
    try:
        writer.worker.ingest(_envelope("env-1", "public"))
    finally:
        writer.close()
    yield database


def _entities(handle: Any) -> int:
    from tests.deployment.test_classification_authority_consumer import AS_OF, TENANT

    return len(list(handle.reader.as_of(tenant_id=TENANT, at=AS_OF).entities))


def test_b_a_read_only_handle_refuses_every_write_by_name_and_writes_nothing(populated: pathlib.Path) -> None:
    from ccf.contracts.claims import EntityClaim
    from tests.deployment.test_classification_authority_consumer import TENANT

    refused_type = _contract("ccf.boot", "ReadOnlyFabricRefused")
    handle = _sqlite_boot(populated, read_only=True)
    try:
        before = _entities(handle)
        assert before == 1, before
        with pytest.raises(refused_type) as ingest_refused:
            handle.worker.ingest(_envelope("env-2", "restricted"))
        assert "FW-2" in str(ingest_refused.value)
        claim = EntityClaim(
            tenant_id=TENANT,
            entity_uri="ccf://fw-2/written-anyway",
            entity_class="counterparty",
            attributes={"classification": "public"},
            observed_at=datetime(2026, 2, 3, tzinfo=UTC),
            valid_from=datetime(2026, 2, 3, tzinfo=UTC),
            lineage=frozenset(),
        )
        with pytest.raises(refused_type):
            handle.worker.admit_entity_claim(tenant_id=TENANT, claim=claim)
        assert _entities(handle) == before
        # It mints no writer and takes no lease: a writer boot beside it succeeds.
        assert handle.lease_scope == "read-only", handle.lease_scope
        assert handle.lease_mechanism is not None and "no writer" in handle.lease_mechanism, handle.lease_mechanism
        writer = _sqlite_boot(populated, read_only=False)
        writer.close()
    finally:
        handle.close()
    # Nothing the read-only handle was asked to write reached the graph.
    reopened = _sqlite_boot(populated, read_only=False)
    try:
        assert _entities(reopened) == 1
    finally:
        reopened.close()


def test_c_the_read_only_authority_is_boot_minted_and_a_hand_built_one_is_still_refused(
    populated: pathlib.Path,
) -> None:
    from ccf.contracts.canonical import content_hash
    from tests.deployment.test_classification_authority_consumer import (
        AS_OF,
        TENANT,
        _filter,
        _forge,
        _hand_built,
        _spec,
    )

    handle = _sqlite_boot(populated, read_only=True)
    try:
        view = handle.reader.as_of(tenant_id=TENANT, at=AS_OF)
        authority = view.classification_authority
        assert authority is not None and authority.minted, authority
        assert authority.spec_address == content_hash(_spec(governed=True))
        policy_version = next(iter(view.entities)).policy_bundle_version
        # The boot-minted stamp admits the Policy operator over the read-only view.
        admitted = _filter(policy_version).apply(view=view, tenant_id=TENANT, temporal_boundary=AS_OF, upstream=())
        assert len(admitted.view.entities) == 1
        # A hand-built authority, forged onto the read-only view, is still refused.
        forged = _forge(
            view,
            _hand_built(
                {"counterparty": {"classification": frozenset({"source-a"})}},
                {"counterparty": frozenset({"classification"})},
            ),
        )
        with pytest.raises(ValueError) as refused:
            _filter(policy_version).apply(view=forged, tenant_id=TENANT, temporal_boundary=AS_OF, upstream=())
        assert type(refused.value).__name__ == "ClassificationAuthorityNotMinted", refused.value
    finally:
        handle.close()
