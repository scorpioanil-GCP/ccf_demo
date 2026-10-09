"""The record writer hands out only the reference of the record it wrote (``D-IMPL-378`` decision 5 (a)).

Dave, 2026-10-09 06:06 MST, confirmed at 06:21 MST ("5a"), verbatim: *"(a). Verify
the returned record address against the record actually written."* The final
panel's G-REF-UNCHECKED: ``src/ccf/replay/serve.py::ReplayWriter.write_replay_record``
returned whatever :class:`~ccf.artifacts.protocol.ArtifactRef` the store's ``put``
answered, while the resolver already holds the store's answer for an admitted
child contract to the contract's own address
(``src/ccf/products/resolver.py::GovernedResolver._retain_child_contracts``).
Measured on ``dl-378-integ`` @ ``a539c215`` (the panel's probe
``p_b05_returned_ref.py``, re-run by this lane): a store that filed record A
faithfully and answered with record B's reference had record B's reference
handed out for record A.

Under ``D-IMPL-26`` and Q11 the writer knows the whole reference of what it
wrote before the store answers: the address is ``content_hash(record)``, the
name is that address, the tenant and class are its capability's, and the
versioned URI is ``ccf-artifact://{tenant}/{class}/{address}@{address}``
(``src/ccf/artifacts/protocol.py``: *"with ``artifact_version`` being the content
address"*). The refusal path hands its caller the URI, not the address
(``src/ccf/products/resolver.py::ReplayRefusalRecorder`` copies
``reference.uri`` into the shell's ``replay_reference``), so each field of the
returned reference is held here, not the address alone.

What is asserted, by mechanism:

1. **The hole as evidenced.** The panel's probe, step for step, on the paved
   road's own served and refused records: a store answering record B's genuine
   reference for record A is refused by name (``ReplayReferenceMismatch``), and
   nothing is handed out.
2. **Every field of the reference.** A store answering record A's reference with
   one field changed — the address, the URI, the tenant, the class or the name
   — is refused by name, on the served path and on the refusal path.
3. **Control.** An honest store's reference is handed out, and it is exactly the
   reference of the record written.

The refusal is asserted by its class NAME as a string, so a tree without the
check fails each test on its behavior (the reference it handed out), never on
an import. Fixture vocabulary only (CINV-01).
"""

from __future__ import annotations

import pathlib
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import ArtifactRef, ArtifactStoreProtocol, artifact_uri
from ccf.contracts.canonical import content_hash
from ccf.products.product import OpenedProduct
from ccf.projection.engine import ExecutionStep
from ccf.replay.record import (
    ContentGenerationPath,
    ContextFabricSnapshot,
    DecisionReplayRecord,
    ModelVersionRecord,
    PerspectiveConditioning,
    PolicyBinding,
    PolicyBindingsSnapshot,
)
from ccf.replay.serve import ReplayWriter, record_refusal
from tests.controlplane.capabilities import replay_mint
from tests.products.test_paved_road import _open, _write_tree
from tests.replay.authority import replay_store
from tests.replay.test_record_content_address_integrity import _refused, _served

#: The refusal this check raises, by name (absent on a tree without the check).
REFUSAL = "ReplayReferenceMismatch"

TENANT = "tenant-fixture"
RECORD_CLASS = "decision-replay-record"
NOW = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)

#: The one field each lying store changes, and the foreign value it answers with.
#: ``None`` means "record B's value for that field".
FIELDS: dict[str, str | None] = {
    "content_address": None,
    "uri": None,
    "name": None,
    "tenant_id": "another-tenant",
    "artifact_class": "another-record-class",
}


def _record(plan_id: str) -> DecisionReplayRecord:
    """A minimal valid replay record; ``plan_id`` alone makes two records two contents."""
    snapshot = ContextFabricSnapshot.build(
        tenant_id=TENANT,
        temporal_boundary=NOW - timedelta(minutes=1),
        store_watermark="watermark",
        touched_entities=("counterparty://a",),
        touched_relationships=(),
    )
    return DecisionReplayRecord(
        tenant_id=TENANT,
        recorded_at=NOW,
        context_fabric_snapshot=snapshot,
        policy_bindings=PolicyBindingsSnapshot(
            bindings=(PolicyBinding(key=f"{TENANT}/policy-bundle/x", version="v1"),)
        ),
        model_version=ModelVersionRecord(assembly_mode="algorithmic"),
        perspective_conditioning=PerspectiveConditioning(principal_id="p", role="r"),
        content_generation_path=ContentGenerationPath(
            plan_id=plan_id,
            operator_plan=("policy.principal-subgraph",),
            steps=(
                ExecutionStep(
                    operator_key="policy.principal-subgraph",
                    category="policy",
                    parameter_hash="0" * 64,
                ),
            ),
            product_content_address="0" * 64,
        ),
    )


def _expected(record: DecisionReplayRecord, *, tenant: str, artifact_class: str) -> ArtifactRef:
    """The reference of ``record`` filed by a writer for ``tenant`` and ``artifact_class``, per D-IMPL-26 and Q11."""
    address = content_hash(record)
    return ArtifactRef(
        content_address=address,
        uri=artifact_uri(tenant_id=tenant, artifact_class=artifact_class, name=address, artifact_version=address),
        tenant_id=tenant,
        artifact_class=artifact_class,
        name=address,
    )


class _AnswersWith:
    """A store that files every write faithfully through ``inner`` and answers with ``answer(the honest ref)``.

    The panel's lying store: a buggy or hostile artifact server whose bytes are
    right and whose reference is not. Reads delegate unchanged.
    """

    def __init__(self, inner: ArtifactStoreProtocol, answer: Callable[[ArtifactRef], ArtifactRef]) -> None:
        self._inner = inner
        self._answer = answer
        self.filed: list[ArtifactRef] = []

    def put(self, authorized: Any, artifact: Any) -> ArtifactRef:
        honest = self._inner.put(authorized, artifact)
        self.filed.append(honest)
        return self._answer(honest)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


def _outcome(call: Callable[[], ArtifactRef]) -> ArtifactRef | Exception:
    """The reference the writer handed out, or the exception it raised instead."""
    try:
        return call()
    except Exception as raised:  # noqa: BLE001 — judged by its type's name below, never by its text
        return raised


def _assert_refused_by_name(outcome: ArtifactRef | Exception, *, written: str, case: str) -> None:
    """Nothing was handed out, and the refusal is the check's own, by its type's name."""
    if isinstance(outcome, ArtifactRef):
        pytest.fail(
            f"[{case}] the record writer handed out the store's reference unchecked for the record at"
            f" {written}: content_address={outcome.content_address}, uri={outcome.uri},"
            f" tenant_id={outcome.tenant_id}, artifact_class={outcome.artifact_class}, name={outcome.name}"
        )
    assert any(klass.__name__ == REFUSAL for klass in type(outcome).__mro__), (
        f"[{case}] refused, but not by the returned-reference check ({REFUSAL}):"
        f" {type(outcome).__name__}: {outcome}"
    )


@pytest.fixture()
def store(tmp_path: pathlib.Path) -> FileArtifactStore:
    return replay_store(tmp_path / "artifacts", RECORD_CLASS)


@pytest.fixture()
def opened(tmp_path: pathlib.Path) -> Iterator[OpenedProduct]:
    """The paved road's fixture product, the deployment the panel's probe read its two records from."""
    with _open(_write_tree(tmp_path), tmp_path / "scratch") as product:
        yield product


# --- 1. the hole as evidenced: the panel's probe on the paved road's own records ---------------


def test_a_store_answering_another_records_reference_is_refused_by_name(opened: OpenedProduct) -> None:
    """``p_b05_returned_ref.py`` as a test: record A filed faithfully, record B's genuine reference answered.

    Records A (a served answer) and B (a refusal) are the paved road's own. B's
    reference is the one the real store answers for B, obtained by filing B
    through an honest writer. Measured on ``a539c215``: the writer handed out
    B's reference for A.
    """
    served = _served(opened)
    refused = _refused(opened)
    record_a = opened.record_of(served)
    record_b = opened.record_of(refused)
    record_class = served.replay_ref.artifact_class
    assert content_hash(record_a) != content_hash(record_b), "the two records must be two contents"
    honest_b = ReplayWriter(
        authorized=replay_mint(tenant=record_b.tenant_id, artifact_class=record_class), store=opened.artifact_store
    ).write_replay_record(record=record_b).replay_ref
    lying = _AnswersWith(opened.artifact_store, lambda _honest: honest_b)
    writer = ReplayWriter(authorized=replay_mint(tenant=record_a.tenant_id, artifact_class=record_class), store=lying)

    outcome = _outcome(lambda: writer.write_replay_record(record=record_a).replay_ref)

    assert [ref.content_address for ref in lying.filed] == [content_hash(record_a)], (
        "the case was not constructed: the lying store must have filed record A faithfully"
    )
    _assert_refused_by_name(outcome, written=content_hash(record_a), case="record B's reference for record A")


# --- 2. every field of the returned reference, on both paths that hand one out -----------------


def _one_field_changed(field: str, *, foreign: ArtifactRef) -> Callable[[ArtifactRef], ArtifactRef]:
    value = FIELDS[field]
    replacement = getattr(foreign, field) if value is None else value
    return lambda honest: honest.model_copy(update={field: replacement})


@pytest.mark.parametrize("field", sorted(FIELDS))
def test_the_served_path_refuses_a_reference_with_any_field_not_the_records_own(
    store: FileArtifactStore, field: str
) -> None:
    """``write_replay_record``: one field of record A's reference answered as another record's (or tenant's, class's)."""
    record_a, record_b = _record("plan-a"), _record("plan-b")
    foreign = _expected(record_b, tenant=TENANT, artifact_class=RECORD_CLASS)
    lying = _AnswersWith(store, _one_field_changed(field, foreign=foreign))
    writer = ReplayWriter(authorized=replay_mint(tenant=TENANT, artifact_class=RECORD_CLASS), store=lying)

    outcome = _outcome(lambda: writer.write_replay_record(record=record_a).replay_ref)

    assert lying.filed == [_expected(record_a, tenant=TENANT, artifact_class=RECORD_CLASS)], (
        "the case was not constructed: the store must have filed record A under its own reference"
    )
    _assert_refused_by_name(outcome, written=content_hash(record_a), case=f"served path, {field}")


@pytest.mark.parametrize("field", sorted(FIELDS))
def test_the_refusal_path_refuses_a_reference_with_any_field_not_the_records_own(
    store: FileArtifactStore, field: str
) -> None:
    """``record_refusal``: the path whose caller receives the URI (the refusal shell's ``replay_reference``)."""
    record_a, record_b = _record("plan-a"), _record("plan-b")
    foreign = _expected(record_b, tenant=TENANT, artifact_class=RECORD_CLASS)
    lying = _AnswersWith(store, _one_field_changed(field, foreign=foreign))
    writer = ReplayWriter(authorized=replay_mint(tenant=TENANT, artifact_class=RECORD_CLASS), store=lying)

    outcome = _outcome(lambda: record_refusal(record=record_a, replay_writer=writer))

    assert len(lying.filed) == 1, "the case was not constructed: the store must have filed record A"
    _assert_refused_by_name(outcome, written=content_hash(record_a), case=f"refusal path, {field}")


# --- 3. control: an honest store's reference is handed out ------------------------------------


def test_control_an_honest_stores_reference_is_handed_out_and_is_the_records_own(store: FileArtifactStore) -> None:
    """The file store answers exactly the reference of the record written, on both paths, and it is handed out."""
    writer = ReplayWriter(authorized=replay_mint(tenant=TENANT, artifact_class=RECORD_CLASS), store=store)
    served = _outcome(lambda: writer.write_replay_record(record=_record("plan-a")).replay_ref)
    refused = _outcome(lambda: record_refusal(record=_record("plan-b"), replay_writer=writer))
    assert served == _expected(_record("plan-a"), tenant=TENANT, artifact_class=RECORD_CLASS), served
    assert refused == _expected(_record("plan-b"), tenant=TENANT, artifact_class=RECORD_CLASS), refused
    assert isinstance(served, ArtifactRef) and store.resolve_uri(uri=served.uri) == served.content_address


def test_control_the_paved_roads_own_store_hands_out_the_records_own_reference(opened: OpenedProduct) -> None:
    """The deployment's real store, through the real served and refused answers: each reference names its own record."""
    served = _served(opened)
    refused = _refused(opened)
    record = opened.record_of(served)
    assert served.replay_ref == _expected(
        record, tenant=record.tenant_id, artifact_class=served.replay_ref.artifact_class
    ), served.replay_ref
    refusal_record = opened.record_of(refused)
    assert refused.replay_reference == _expected(
        refusal_record, tenant=refusal_record.tenant_id, artifact_class=served.replay_ref.artifact_class
    ).uri, refused.replay_reference
