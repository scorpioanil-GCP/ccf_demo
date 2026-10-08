"""The declared-scope generation refusal at ``replay()`` (``D-IMPL-243`` amendment 1).

Whitepaper §7.10 (a decision reconstructible years later against the exact
identities it was made with); CLAUDE.md §7.4 (replay resolves exact versions,
never "latest"). Phase 24.5's close review (CR-01) measured that a
sentinel-defaulted field added to a hashed contract moves every hash replay
re-computes, so a record written before the field existed diverges on a
parameter hash for operators that are exactly the ones that ran.
``D-IMPL-243`` rules a refusal by name instead — ``canonical_generation_mismatch``
— and amendment 1 rules its scope, in Dave's words: *"``True`` → omit.
``False`` → generation boundary, refuse by name. No key → D-IMPL-89 lineage:
render, never refuse. Do not put this in ``resolve_artifact``."*

Three things are proven here, each against the real
:class:`~ccf.replay.record.DecisionReplayRecord` and the real engine:

1. **The lineage is untouched.** ``PRE_CHANGE_CANONICAL`` — the pre-extension
   record ``D-IMPL-89``'s own regression resolves — lacks FIFTEEN fields the
   running record declares, none of them marked. ``replay()`` passes it
   through the generation check and fails **later**, on the binding the
   empty control plane cannot resolve, which is exactly where it failed
   before the check existed. The fifteen are asserted as a roster.
2. **A planted boundary refuses by name, before anything else.** One real
   field marked ``False`` in memory, the same bytes: ``replay()`` raises
   :class:`~ccf.replay.engine.ReplayGenerationMismatch` naming
   ``DecisionReplayRecord.policy_bindings.hitl_actions``, with the control
   plane never consulted and the environment never touched.
3. **The two controls.** The same field marked ``True``, or left unmarked,
   is not named — the record proceeds to the same later failure as (1).

The marks are planted **in memory and restored**; no field in ``src/`` is
marked ``False`` by this module or by the tree it ships in. The engine's own
``_refuse_generation_mismatch`` is also held against a scratch contract, so
the rule is proven without a decision record in the loop.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import BaseModel, Field

from ccf.artifacts.file_store import FileArtifactStore
from ccf.contracts import canonical
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import HASH_TRANSPARENT_KEY, generation_mismatch
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.replay.engine import (
    ReplayDivergence,
    ReplayGenerationMismatch,
    ReplayUnresolvable,
    _refuse_generation_mismatch,
    replay,
)
from ccf.replay.record import (
    ContentGenerationPath,
    ContextFabricSnapshot,
    DecisionReplayRecord,
    ModelVersionRecord,
    PolicyBindingsSnapshot,
)
from tests.replay.authority import replay_store
from tests.replay.test_harness_trace import PRE_CHANGE_CANONICAL
from tests.replay.test_query_sequence_pin import VERBATIM_RECORD_CLASS, _stored_verbatim

#: The fifteen fields ``PRE_CHANGE_CANONICAL`` lacks that the running record
#: declares — amendment 1's own measurement, as a roster and never a count.
#: None carries the key; every one is the ``D-IMPL-89`` lineage. Under
#: ``D-IMPL-243`` amendment 2 this is the ONLY place the fifteen are a named
#: roster: the CINV-06 lint no longer lists them (they are in its committed
#: ``13bd250`` base roster like every other pre-phase field, silent by
#: construction), and this module holds them by name because they are a fact
#: about the RECORD's shape — what a pre-extension record lacks and still
#: replays past — not about the lint's universe.
THE_FIFTEEN: tuple[str, ...] = (
    "context_fabric_snapshot.source_attestation",
    "policy_bindings.hitl_actions",
    "policy_bindings.survivor_cap",
    "policy_bindings.graph_adapter",
    "policy_bindings.graph_adapter_version",
    "policy_bindings.graph_secret_refs",
    "model_version.harness_trace",
    "content_generation_path.workflow_step_sequence",
    "content_generation_path.assembly_refusal",
    "content_generation_path.graph_query_sequence",
    "content_generation_path.debt",
    "content_generation_path.debt_evidence",
    "content_generation_path.source_refresh_recency",
    "content_generation_path.obligation_in_force",
    "content_generation_path.request",
)


def _absent_fields(
    model_cls: type[BaseModel], stored: Mapping[str, Any]
) -> tuple[tuple[str, bool | None], ...]:
    """Every field ``model_cls`` declares that ``stored`` lacks, with its key state.

    The unscoped walk, test-local, so the roster of the fifteen is measured
    here rather than copied from the decision log. Each entry is
    ``(dotted name, key)`` where the key is ``True``, ``False`` or ``None``
    (absent). Under ``generation_mismatch``'s first specification every entry
    but the ``True`` ones was named; amendment 1 measured that as fifteen.
    """
    missing: list[tuple[str, bool | None]] = []
    for name, field in model_cls.model_fields.items():
        if name not in stored:
            extra = field.json_schema_extra
            key = extra.get(HASH_TRANSPARENT_KEY) if isinstance(extra, Mapping) else None
            missing.append((name, key if isinstance(key, bool) else None))
            continue
        nested = canonical._nested_model_class(field.annotation)
        value = stored[name]
        if nested is not None and isinstance(value, Mapping):
            missing.extend(
                (f"{name}.{inner}", key) for inner, key in _absent_fields(nested, value)
            )
    return tuple(missing)


@contextmanager
def _key_state(model_cls: type[BaseModel], name: str, state: bool | None) -> Iterator[None]:
    """Plant ``HASH_TRANSPARENT_KEY`` = ``state`` on one real field, in memory.

    ``None`` removes the key. The declaration is restored on exit and both
    canonicalizer memos are cleared on entry and exit, so no other test sees
    the plant. Nothing under ``src/`` is edited.
    """
    field = model_cls.model_fields[name]
    before = field.json_schema_extra
    extra: dict[str, Any] = dict(before) if isinstance(before, Mapping) else {}
    if state is None:
        extra.pop(HASH_TRANSPARENT_KEY, None)
    else:
        extra[HASH_TRANSPARENT_KEY] = state
    field.json_schema_extra = extra or None
    canonical._TRANSPARENT_SENTINELS.clear()
    canonical._BOUNDARY_FIELDS.clear()
    try:
        yield
    finally:
        field.json_schema_extra = before
        canonical._TRANSPARENT_SENTINELS.clear()
        canonical._BOUNDARY_FIELDS.clear()


class _UntouchableEnvironment:
    """A replay environment that fails the test if the engine reaches it."""

    def resolve_plan(self, *, plan_id: str) -> Any:
        raise AssertionError(f"the environment was consulted for {plan_id!r}")

    def resolve_operators(self, *, operator_keys: tuple[str, ...]) -> Any:
        raise AssertionError("the environment was consulted for operators")

    def rehydrate_product(self, *, record: Any, projection: Any) -> Any:
        raise AssertionError("the environment was asked to rehydrate")


class _UntouchableReader:
    """A graph reader that fails the test if anything reads through it."""

    def __getattr__(self, name: str) -> Any:
        raise AssertionError(f"the reader was touched ({name})")


def _replay_pre_change(store: FileArtifactStore, address: str) -> None:
    replay(
        record_address=address,
        store=store,
        reader=cast(Any, _UntouchableReader()),
        control_plane=ControlPlaneRegistry(),
        environment=_UntouchableEnvironment(),
    )


@pytest.fixture
def stored(tmp_path: Path) -> tuple[FileArtifactStore, str]:
    store = replay_store(tmp_path / "artifacts", VERBATIM_RECORD_CLASS)
    return store, _stored_verbatim(store, PRE_CHANGE_CANONICAL)


# --- 1. the lineage: fifteen absent fields, none named --------------------------


def test_the_pre_extension_record_lacks_exactly_the_fifteen_plus_one_transparent() -> None:
    """Amendment 1's measurement, re-measured: a roster, not a count.

    Twenty-five fields are absent from the bytes: the fifteen, none keyed,
    and TEN marked ``True`` — ``context_fabric_snapshot.store_snapshot_pin``
    (24.5's row 5), which the first specification already excluded and which
    the amendment therefore did not count; ``policy_bindings.request_resolution``
    (``24.6-03``); and ``24.6-07``'s three, the assembler in force on
    dimension 4 (``D-IMPL-253`` Q16) and the disclosure decision on
    dimension 5 (``D-IMPL-254``); and ``D-IMPL-336``'s child resolutions, also
    on dimension 5 — the composite surface's requirement-to-grant-to-child
    mapping, which is empty and therefore silent for every non-composite
    decision ever recorded. Every one of the nine joins that side and **not**
    the fifteen: a keyed field is one whose absence at its sentinel is silence
    by declaration, which is exactly why it is not a generation boundary.

    ``THE_FIFTEEN`` is unchanged by ``24.6-07``, by ``D-IMPL-336``, by
    ``D-IMPL-346``, by ``D-IMPL-347`` and by ``D-IMPL-358``, and that
    is the load-bearing
    half of this assertion — the lineage a pre-extension record replays past
    is a closed historical fact, and a row that grew it would be a row that
    made an old record refuse.
    """
    absent = _absent_fields(DecisionReplayRecord, json.loads(PRE_CHANGE_CANONICAL))
    assert tuple(name for name, key in absent if key is None) == THE_FIFTEEN
    assert tuple(name for name, key in absent if key is True) == (
        "context_fabric_snapshot.store_snapshot_pin",
        "policy_bindings.request_resolution",
        # `D-IMPL-346`: dimension 3's Mode-2 packaging block. It joins this
        # side and NOT `THE_FIFTEEN` for the reason the docstring gives — a
        # Mode-1 decision packaged nothing, its absence at the sentinel is
        # silence by declaration, and a row that grew the lineage would make
        # every pre-extension record refuse.
        "model_version.packaging_trace",
        "perspective_conditioning.assembler_id",
        "perspective_conditioning.assembler_version",
        "content_generation_path.disclosure_decision",
        # `D-IMPL-347` A2: which deployment seam held a refusal. Sentinel on
        # every record written before the seams were wrapped, and on every
        # refusal the resolver raised on its own account. Placed by the
        # model's own field order, which is what the walk reports.
        "content_generation_path.refusal_seam",
        # `D-IMPL-341`: the served product's anchor instant, `None` on every
        # record written before it existed — decision-anchored by that sentinel.
        "content_generation_path.ttl_anchor_at",
        # SEC-020 (`D-IMPL-370`, corrective round): the served product's empty
        # finding, `None` on every record written before it existed and on every
        # record whose product carried none — silence by declaration, so it
        # joins this side and NOT `THE_FIFTEEN`.
        "content_generation_path.computed_empty",
        # `D-IMPL-358` ruling 1: when the answer was served. `None` on every
        # record written before the member existed, so it joins this side and
        # NOT `THE_FIFTEEN` — a row that grew the lineage would make an old
        # record refuse, and that is the load-bearing half of this assertion.
        "content_generation_path.served_at",
        "content_generation_path.child_resolutions",
        # Dave's Q11 (`D-IMPL-378`, lane 378-s020record PROPOSAL): the answer's
        # per-answer issuance. `NO_ISSUANCE` on every record written before it
        # existed, so it joins this side and NOT `THE_FIFTEEN`.
        "content_generation_path.issuance",
    )
    assert not [name for name, key in absent if key is False]


def test_none_of_the_fifteen_carries_the_key() -> None:
    """The fifteen are the ``D-IMPL-89`` lineage: no key, by ruling."""
    owners: dict[str, type[BaseModel]] = {
        "context_fabric_snapshot": ContextFabricSnapshot,
        "policy_bindings": PolicyBindingsSnapshot,
        "model_version": ModelVersionRecord,
        "content_generation_path": ContentGenerationPath,
    }
    for dotted in THE_FIFTEEN:
        outer, _, inner = dotted.partition(".")
        extra = owners[outer].model_fields[inner].json_schema_extra
        assert not (isinstance(extra, Mapping) and HASH_TRANSPARENT_KEY in extra), dotted


def test_the_pre_extension_record_crosses_no_declared_boundary() -> None:
    assert generation_mismatch(DecisionReplayRecord, json.loads(PRE_CHANGE_CANONICAL)) == ()


def test_the_pre_extension_record_passes_the_check_and_fails_later_as_it_always_did(
    stored: tuple[FileArtifactStore, str],
) -> None:
    """The generation check is silent; the *next* stage refuses, as before.

    The empty control plane cannot resolve ``policy.bundle`` at ``v1``, which
    is where this record failed before the check existed. Reaching that
    failure IS the proof the check let the record through.
    """
    store, address = stored
    with pytest.raises(ReplayUnresolvable, match="policy.bundle"):
        _replay_pre_change(store, address)


# --- 2. a planted boundary refuses by name, before anything else ----------------


def test_a_planted_boundary_field_is_refused_by_name_before_re_execution(
    stored: tuple[FileArtifactStore, str],
) -> None:
    store, address = stored
    with _key_state(PolicyBindingsSnapshot, "hitl_actions", False):
        with pytest.raises(ReplayGenerationMismatch) as refused:
            _replay_pre_change(store, address)
    assert refused.value.reason == "canonical_generation_mismatch"
    assert refused.value.fields == ("DecisionReplayRecord.policy_bindings.hitl_actions",)
    assert refused.value.content_address == address
    message = str(refused.value)
    assert "canonical_generation_mismatch" in message
    assert "DecisionReplayRecord.policy_bindings.hitl_actions" in message
    assert "D-IMPL-243" in message
    # Its own finding, not either of the two that existed before it.
    assert not isinstance(refused.value, ReplayDivergence)
    assert not isinstance(refused.value, ReplayUnresolvable)


def test_two_planted_boundaries_are_both_named_in_declaration_order(
    stored: tuple[FileArtifactStore, str],
) -> None:
    store, address = stored
    with (
        _key_state(ContentGenerationPath, "request", False),
        _key_state(ContextFabricSnapshot, "source_attestation", False),
    ):
        with pytest.raises(ReplayGenerationMismatch) as refused:
            _replay_pre_change(store, address)
    assert refused.value.fields == (
        "DecisionReplayRecord.context_fabric_snapshot.source_attestation",
        "DecisionReplayRecord.content_generation_path.request",
    )


# --- 3. the two controls: True and no key are never named ---------------------


@pytest.mark.parametrize("state", [True, None], ids=["marked-true", "no-key"])
def test_a_true_mark_and_no_key_are_not_named(
    stored: tuple[FileArtifactStore, str], state: bool | None
) -> None:
    """The same field, the same bytes, the other two states: not refused.

    ``True`` on ``hitl_actions`` is a plant for the control only — the field
    is NOT transparent in the tree — and its sentinel here is the default the
    record fills in, so the omission rule has nothing to say either.
    """
    store, address = stored
    with _key_state(PolicyBindingsSnapshot, "hitl_actions", state):
        assert generation_mismatch(DecisionReplayRecord, json.loads(PRE_CHANGE_CANONICAL)) == ()
        with pytest.raises(ReplayUnresolvable, match="policy.bundle"):
            _replay_pre_change(store, address)


# --- the rule without a decision record: a scratch contract ------------------------


class _Scratch(CCFContract):
    a: int
    boundary: int = Field(default=0, json_schema_extra={HASH_TRANSPARENT_KEY: False})
    transparent: int = Field(default=0, json_schema_extra={HASH_TRANSPARENT_KEY: True})
    lineage: int = 0


def test_the_engine_refuses_a_scratch_contract_by_its_boundary_field_alone() -> None:
    with pytest.raises(ReplayGenerationMismatch) as refused:
        _refuse_generation_mismatch(
            contract=_Scratch, stored={"a": 1}, content_address="addr"
        )
    assert refused.value.fields == ("_Scratch.boundary",)
    assert "_Scratch.transparent" not in str(refused.value)
    assert "_Scratch.lineage" not in str(refused.value)

    # Both controls, on the same scratch model: the boundary present, the
    # other two absent, is silence.
    _refuse_generation_mismatch(
        contract=_Scratch, stored={"a": 1, "boundary": 0}, content_address="addr"
    )


# --- the second read is held to the same arithmetic ------------------------------


class _SecondReadLies:
    """A store whose second ``get`` returns other bytes for the same address."""

    def __init__(self, inner: FileArtifactStore) -> None:
        self._inner = inner
        self.reads = 0

    def get(self, *, content_address: str) -> bytes:
        self.reads += 1
        payload = self._inner.get(content_address=content_address)
        return payload if self.reads == 1 else payload.replace(b"tenant-a", b"tenant-b")

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


def test_a_store_that_changes_its_answer_between_the_two_reads_is_divergence(
    stored: tuple[FileArtifactStore, str],
) -> None:
    store, address = stored
    lying = _SecondReadLies(store)
    with pytest.raises(ReplayDivergence, match="second read"):
        replay(
            record_address=address,
            store=cast(Any, lying),
            reader=cast(Any, _UntouchableReader()),
            control_plane=ControlPlaneRegistry(),
            environment=_UntouchableEnvironment(),
        )
    assert lying.reads == 2
    assert hashlib.sha256(store.get(content_address=address)).hexdigest() == address
