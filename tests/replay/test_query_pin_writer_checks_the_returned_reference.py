"""The query-pin writer hands out only the references of the query bytes it wrote (``D-IMPL-378`` decision 5 (a)).

Dave, 2026-10-09 16:38 MST, adopting Grok's recommendation on the "j" batch's decision 5, verbatim: *"(a) Fix
the four writers in one small lane."* The option he ruled on: the decision 5 (a) defect class at four neighbor
writers, one of them measured returning query 1's reference for query 2. Decision 5 (a) itself (06:06 MST,
confirmed at 06:21 MST), verbatim: *"Verify the returned record address against the record actually
written."* It was built for ``src/ccf/replay/serve.py::ReplayWriter.write_replay_record``; this module holds
its neighbor ``src/ccf/replay/serve.py::QueryPinWriter.write_query_bytes`` to the same rule.

Measured on ``dl-378-integ`` @ ``6cd6023e`` (the small lane's probe ``probe_query_pin_writer_returned_ref.py``,
re-run by this lane): a store that filed every query faithfully and answered every write with the first
query's reference made the writer return query 1's reference for query 2.

What the writer knows before the store answers (``D-IMPL-26``): each query is named by its own
``content_hash``; the store's address for its bytes is that same hash, because both are
``sha256(canonical_bytes(query))``; the tenant and the class are the writer's capability's; and the versioned
URI is ``ccf-artifact://{tenant}/{class}/{hash}@{hash}``.

What is asserted, by mechanism:

1. **The hole as evidenced.** The probe, as a test: the first query's reference answered for every write is
   refused by name (``QueryPinReferenceMismatch``), and no reference is handed out.
2. **Every field of the reference.** One field of a query's reference answered as another query's (the
   address, the URI, the name) or as another tenant's or class's is refused by name; so is a changed field
   carried in a ``str`` subclass that claims to equal the query's own.
3. **The governed serve.** ``src/ccf/replay/serve.py::serve`` discards the pin writer's references, so before
   this check none of them left the serve; the pin writer's refusal now propagates out of the serve, so a pin
   store answering another query's reference delivers nothing and appends no record.
4. **Control.** An honest store's references are handed out, and each is exactly the query's own.

The refusal is asserted by its class NAME as a string, so a tree without the check fails each test on its
behavior (the reference it handed out, or the product it delivered), never on an import. Fixture vocabulary
only (CINV-01).
"""

from __future__ import annotations

import pathlib
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import ArtifactRef, ArtifactStoreProtocol, DerivedWrite, artifact_uri
from ccf.contracts.canonical import content_hash
from ccf.graph.protocols import GraphQuery
from ccf.replay.serve import QueryPinWriter, ServedProduct, serve
from tests.controlplane.capabilities import replay_mint
from tests.integration.test_proto_quickstart import _Fabric, _product_class
from tests.projection.test_segmentation import FOUR_OPERATORS
from tests.replay.authority import pin_writer, replay_store, replay_writer
from tests.replay.test_query_sequence_pin import (  # noqa: F401 — pytest fixtures, used by name
    _execute,
    _record_for,
    control,
    events,
    fabric,
    ontology,
)

#: The refusal this check raises, by name (absent on a tree without the check).
REFUSAL = "QueryPinReferenceMismatch"

TENANT = "tenant-fixture"
QUERY_CLASS = "ccf.graph-query"

#: The one field each lying store changes, and the foreign value it answers with.
#: ``None`` means "the other query's value for that field".
FIELDS: dict[str, str | None] = {
    "content_address": None,
    "uri": None,
    "name": None,
    "tenant_id": "another-tenant",
    "artifact_class": "another-query-class",
}


def _query(day: int) -> GraphQuery:
    """A pinned question; ``day`` alone makes two queries two contents."""
    return GraphQuery(tenant_id=TENANT, as_of=datetime(2026, 1, day, tzinfo=UTC))


def _expected(query: GraphQuery, *, tenant: str = TENANT, artifact_class: str = QUERY_CLASS) -> ArtifactRef:
    """The reference of ``query`` filed by a pin writer for ``tenant`` and ``artifact_class``, per D-IMPL-26."""
    address = content_hash(query)
    return ArtifactRef(
        content_address=address,
        uri=artifact_uri(tenant_id=tenant, artifact_class=artifact_class, name=address, artifact_version=address),
        tenant_id=tenant,
        artifact_class=artifact_class,
        name=address,
    )


class _AnswersWith:
    """A store that files every write faithfully through ``inner`` and answers with ``answer(the honest ref)``.

    A buggy or hostile artifact server whose bytes are right and whose reference is not. ``lies_for`` names the
    classes it lies about; writes of any other class are answered honestly. Reads delegate unchanged.
    """

    def __init__(
        self,
        inner: ArtifactStoreProtocol,
        answer: Callable[[ArtifactRef], ArtifactRef],
        *,
        lies_for: frozenset[str] | None = None,
    ) -> None:
        self._inner = inner
        self._answer = answer
        self._lies_for = lies_for
        self.filed: list[ArtifactRef] = []
        self.put_classes: list[str] = []

    def put(self, authorized: Any, artifact: Any) -> ArtifactRef:
        honest = self._inner.put(authorized, artifact)
        self.filed.append(honest)
        self.put_classes.append(honest.artifact_class)
        lies = self._lies_for is None or (
            isinstance(artifact, DerivedWrite) and artifact.artifact_class in self._lies_for
        )
        return self._answer(honest) if lies else honest

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


class _AnswersTheFirst:
    """The small lane's probe store: it files every write faithfully and answers each with the FIRST reference."""

    def __init__(self, inner: ArtifactStoreProtocol, *, lies_for: frozenset[str] | None = None) -> None:
        self._first: ArtifactRef | None = None
        self.store = _AnswersWith(inner, self._first_answer, lies_for=lies_for)

    def _first_answer(self, honest: ArtifactRef) -> ArtifactRef:
        if self._first is None:
            self._first = honest
        return self._first


class _ClaimsEquality(str):
    """A ``str`` whose equality answers for itself: equal to anything, unequal to nothing."""

    def __eq__(self, other: object) -> bool:
        return True

    def __ne__(self, other: object) -> bool:
        return False

    __hash__ = str.__hash__


def _outcome(call: Callable[[], Any]) -> Any:
    """What the call handed out, or the exception it raised instead."""
    try:
        return call()
    except Exception as raised:  # noqa: BLE001 — judged by its type's name below, never by its text
        return raised


def _not_own(handed: object, own: ArtifactRef) -> list[str]:
    """The fields of ``handed`` that are not, as exact strings, ``own``'s (the test's own reading, type first)."""
    return [
        field
        for field in ArtifactRef.model_fields
        if not (type(getattr(handed, field, None)) is str and getattr(handed, field) == getattr(own, field))
    ]


def _assert_refused_by_name(outcome: Any, *, case: str, written: GraphQuery, foreign: ArtifactRef | None) -> None:
    """Nothing was handed out, and the refusal is the check's own, by its type's name."""
    if not isinstance(outcome, Exception):
        refs = tuple(outcome)
        handed = refs[-1] if refs else None
        is_foreign = handed is not None and foreign is not None and not _not_own(handed, foreign)
        pytest.fail(
            f"[{case}] the query-pin writer handed out, unchecked, a reference for the query at"
            f" {content_hash(written)} whose {_not_own(handed, _expected(written))} are not the query's own"
            f" (it is exactly the other query's reference: {is_foreign}): {handed!r}"
        )
    assert any(klass.__name__ == REFUSAL for klass in type(outcome).__mro__), (
        f"[{case}] refused, but not by the returned-reference check ({REFUSAL}): {type(outcome).__name__}: {outcome}"
    )


@pytest.fixture()
def store(tmp_path: pathlib.Path) -> FileArtifactStore:
    return replay_store(tmp_path / "artifacts", QUERY_CLASS)


def _writer(store: ArtifactStoreProtocol) -> QueryPinWriter:
    return QueryPinWriter(authorized=replay_mint(tenant=TENANT, artifact_class=QUERY_CLASS), store=store)


# --- 1. the hole as evidenced: the small lane's probe ----------------------------------------


def test_a_store_answering_the_first_querys_reference_for_every_write_is_refused_by_name(
    store: FileArtifactStore,
) -> None:
    """``probe_query_pin_writer_returned_ref.py`` as a test: query 1's reference answered for query 2.

    Measured on ``6cd6023e``: the writer returned query 1's reference as the second reference.
    """
    q1, q2 = _query(1), _query(2)
    lying = _AnswersTheFirst(store)

    outcome = _outcome(lambda: _writer(lying.store).write_query_bytes(queries=(q1, q2)))

    assert [ref.content_address for ref in lying.store.filed] == [content_hash(q1), content_hash(q2)], (
        "the case was not constructed: the lying store must have filed both queries faithfully"
    )
    _assert_refused_by_name(outcome, case="query 1's reference for query 2", written=q2, foreign=_expected(q1))


# --- 2. every field of the returned reference ------------------------------------------------


def _one_field_changed(field: str, *, foreign: ArtifactRef) -> Callable[[ArtifactRef], ArtifactRef]:
    value = FIELDS[field]
    replacement = getattr(foreign, field) if value is None else value
    return lambda honest: honest.model_copy(update={field: replacement})


@pytest.mark.parametrize("field", sorted(FIELDS))
def test_a_reference_with_any_field_not_the_querys_own_is_refused_by_name(
    store: FileArtifactStore, field: str
) -> None:
    """One field of query 1's reference answered as query 2's (or another tenant's, or another class's)."""
    q1, q2 = _query(1), _query(2)
    foreign = _expected(q2)
    lying = _AnswersWith(store, _one_field_changed(field, foreign=foreign))

    outcome = _outcome(lambda: _writer(lying).write_query_bytes(queries=(q1,)))

    assert lying.filed == [_expected(q1)], "the case was not constructed: the store must have filed query 1 as its own"
    _assert_refused_by_name(outcome, case=f"one field, {field}", written=q1, foreign=foreign)


@pytest.mark.parametrize("field", sorted(FIELDS))
def test_a_reference_field_that_only_claims_equality_is_refused_by_name(store: FileArtifactStore, field: str) -> None:
    """Query 2's value in one field, carried in a ``str`` subclass that says it equals query 1's.

    The comparison reads the type first, so the claim is not taken: the field differs, and the writer refuses by
    name rather than handing anything out.
    """
    q1, q2 = _query(1), _query(2)
    foreign = _expected(q2)
    value = FIELDS[field]
    disguised = _ClaimsEquality(getattr(foreign, field) if value is None else value)
    lying = _AnswersWith(store, lambda honest: honest.model_construct(**{**dict(honest), field: disguised}))

    outcome = _outcome(lambda: _writer(lying).write_query_bytes(queries=(q1,)))

    assert disguised == getattr(lying.filed[0], field), "the case was not constructed: the value must claim equality"
    _assert_refused_by_name(outcome, case=f"claimed equality, {field}", written=q1, foreign=foreign)


# --- 3. the governed serve: what these references reach ---------------------------------------


def test_the_governed_serve_delivers_nothing_when_the_pin_store_answers_another_querys_reference(
    fabric: _Fabric, tmp_path: pathlib.Path
) -> None:
    """The serve seam persists the executed queries first, then appends the record, then delivers.

    It discards the pin writer's references, so before this check a pin store answering query 1's reference for
    query 2 changed nothing that left the serve: the product was delivered and its record appended (measured on
    ``6cd6023e``). The pin writer now refuses by name, and the refusal propagates out of the serve before the
    record append: nothing is delivered and no record is filed.
    """
    record_class = fabric.control["artifacts"]["replay_record_class"]
    honest = replay_store(tmp_path / "artifacts", record_class, QUERY_CLASS)
    execution = _execute(fabric, FOUR_OPERATORS)
    assert len(execution.executed_queries) == 2, "the case was not constructed: two queries must be pinned"
    gated, record = _record_for(fabric, execution, _product_class(fabric))
    lying = _AnswersTheFirst(honest, lies_for=frozenset({QUERY_CLASS}))

    outcome = _outcome(
        lambda: serve(
            product=gated,
            record=record,
            replay_writer=replay_writer(lying.store, tenant=fabric.tenant_id, artifact_class=record_class),
            query_pin_writer=pin_writer(lying.store, tenant=fabric.tenant_id, artifact_class=QUERY_CLASS),
            executed_queries=execution.executed_queries,
        )
    )

    if isinstance(outcome, ServedProduct):
        pytest.fail(
            "the governed serve delivered although the pin store answered query 1's reference for query 2;"
            f" the store filed {lying.store.put_classes} (the serve discards the pin writer's references, so"
            " none of them left it)"
        )
    assert any(klass.__name__ == REFUSAL for klass in type(outcome).__mro__), (
        f"refused, but not by the returned-reference check ({REFUSAL}): {type(outcome).__name__}: {outcome}"
    )
    assert lying.store.put_classes == [QUERY_CLASS, QUERY_CLASS], (
        f"a record was filed after the pin writer refused: {lying.store.put_classes}"
    )


# --- 4. control -------------------------------------------------------------------------------


def test_control_an_honest_stores_references_are_handed_out_and_are_the_queries_own(store: FileArtifactStore) -> None:
    """The file store answers exactly each query's own reference, and the writer hands those out, in order."""
    q1, q2 = _query(1), _query(2)
    refs = _outcome(lambda: _writer(store).write_query_bytes(queries=(q1, q2)))
    assert refs == (_expected(q1), _expected(q2)), refs
    assert all(store.resolve_uri(uri=ref.uri) == ref.content_address for ref in refs)
