"""`D-IMPL-344` — retention follows admission; a refused composite reconstructs.

**The invariant (Dave, verbatim):** *"Admitted-child contracts must be retained
by exact content address whenever the parent records their admission, whether
the parent subsequently serves or refuses. Retention follows admission, not
composition success."*

**Why the old proof was not enough.** `CP14-F-32` measured that a composite
which admitted a child and then refused could not be replayed from its own
store, because the admitted bytes were filed on the non-blocking path only.
Storing the bytes is necessary and not sufficient: the replay engine had no
refusal branch at all, so a retained child merely moved the failure from
"missing child" to "no plan named `no-fabric-read`". Every control below is
therefore a POSITIVE reconstruction — `replay_refusal` returns — never the
absence of the old error, and the record-kind guard is covered in both
directions on its own.

The seven cases of the design (`docs/D-IMPL-344-DESIGN.md` §5), each driven
through the REAL composite fixture — a real grant, a real dispatch through the
child's own door, real admission — and the two sabotages recorded in the
candidate's report:

| # | case | control |
| --- | --- | --- |
| 1 | admitted child + blocking required sibling | `test_case_1_...` |
| 2 | admitted child + later tolerance refusal | `test_case_2_...` |
| 3 | no admitted children | `test_case_3_...` |
| 4 | fresh reconstruction, producers stopped | `test_case_4_...` (early and late) |
| 5 | missing / substituted / unparseable retained bytes | `test_case_5_...` |
| 6 | existing served composite unchanged | `test_case_6_...` |
| 7 | persistence failure | `test_case_7_...` |
| 8 | optional child invoked, then refused (`D-IMPL-336` F1) | `test_case_8_...` |
| 9 | requirements declared, no child resolver wired (parent-scope refusal) | `test_case_9_...` |
| 10 | an outcome for an undeclared class (`undeclared-outcome`) | `test_case_10_...` |
| 11 | an admitted child re-bound under another slot (`requirement-mismatch` WITH a row) | `test_case_11_...` |
| guard | the record-kind guard: valid served, valid refused, both present, neither present | `test_the_record_kind_guard_...` |

Cases 8–10 are the completion Dave asked for on 2026-09-16: the first version
of the refusal-to-row check assumed every early composite refusal names a
required child row, and rejected two determinations the SDK legitimately
records. *"A refusal must agree with the evidence and scope of the
determination that actually occurred — not with an assumption that every
composite refusal is a required-slot failure."* `requirement-mismatch` (one
class declared twice) is handled by the helper but has no control here: the
product-class registration refuses the duplicate before any composition, so
the shape is unreachable through the supported writer path.
"""

from __future__ import annotations

import json
import pathlib
from collections.abc import Iterator, Mapping
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.products.composite import (
    ADMITTED_CHILD_CONTRACT_CLASS,
    CHILD_REFUSAL_REASONS,
    ChildAdmissionRefusal,
)
from ccf.products.contract import ContextProductContract
from ccf.products.refusal import REFUSAL_KINDS
from ccf.products.resolver import GovernedResolver, ReplayRefusalRecorder
from ccf.replay.engine import (
    ReplayDivergence,
    RefusalReplayOutcome,
    ReplayRecordKindMismatch,
    ReplayUnresolvable,
    replay,
    replay_refusal,
)
from ccf.replay.record import (
    CHILD_ADMITTED,
    NO_ASSEMBLY_REFUSAL,
    NO_FABRIC_READ,
    NO_PRODUCT_ADDRESS,
    DecisionReplayRecord,
)
from tests.products.composite_fixture import (
    CHILD_CLASS,
    TENANT,
    _Booted,
    _child_door,
    ask_composite,
    boot_composite,
    build_composite,
)
from tests.products.test_d_impl_339_child_contract_view import (
    CHILD_VALUE_KEY,
    TOLERANCE_ARGUMENT,
    _ChildReadingFactory,
    _FreshEnvironment,
    _LegacyScorerSpy,
    _one_shot,
    _refused,
    _served,
    _wired,
)
from tests.products.test_resolver_seam import POLICY_BUNDLE_KEY, PRODUCT_CLASS, _arguments

#: A second REQUIRED class the parent declares and nothing in the fixture
#: produces — the blocking sibling of case 1.
SIBLING_CLASS = "fixture.sibling-product"
TWO_REQUIREMENTS = {
    "requires": [
        {"product_class": CHILD_CLASS, "required": True, "compatible_from": "1.0.0"},
        {"product_class": SIBLING_CLASS, "required": True, "compatible_from": "1.0.0"},
    ]
}

#: The one requirement declared OPTIONAL, with the absence treatment the
#: fixture prices an honest absence at — so that an invoked-and-refused child
#: is provably not treated as that absence (`D-IMPL-336` F1).
OPTIONAL_REQUIREMENT = {
    "requires": [
        {
            "product_class": CHILD_CLASS,
            "required": False,
            "compatible_from": "1.0.0",
            "absence_treatment": {
                "completeness_when_absent": "0.2",
                "omissible_outcomes": ["optional-absent"],
            },
        }
    ]
}


# --- fixtures and helpers ---------------------------------------------------------


@pytest.fixture
def booted(tmp_path: pathlib.Path) -> Iterator[_Booted]:
    yield from boot_composite(tmp_path)


@pytest.fixture
def booted_with_a_sibling(tmp_path: pathlib.Path) -> Iterator[_Booted]:
    """Two required children; the fixture can produce exactly one of them."""
    yield from boot_composite(tmp_path, product_class_overrides=TWO_REQUIREMENTS)


@pytest.fixture
def booted_with_an_optional_child(tmp_path: pathlib.Path) -> Iterator[_Booted]:
    yield from boot_composite(tmp_path, product_class_overrides=OPTIONAL_REQUIREMENT)


@pytest.fixture
def booted_with_a_tight_tolerance(tmp_path: pathlib.Path) -> Iterator[_Booted]:
    yield from boot_composite(
        tmp_path,
        product_class_overrides={"serve_obligations": {"default_debt_tolerance": "0.10"}},
        request_contract_overrides=TOLERANCE_ARGUMENT,
    )


class _NeverConsulted:
    """An environment whose every member raises: the pre-projection path must
    not resolve a plan, an operator, or a product."""

    def resolve_plan(self, **_: Any) -> Any:
        raise AssertionError("resolve_plan was reached on a no-read refusal")

    def resolve_composite_plan(self, **_: Any) -> Any:
        raise AssertionError("resolve_composite_plan was reached on a no-read refusal")

    def resolve_operators(self, **_: Any) -> Any:
        raise AssertionError("resolve_operators was reached on a no-read refusal")

    def rehydrate_product(self, **_: Any) -> Any:
        raise AssertionError("rehydrate_product was reached on a refusal")


class _NoProductEnvironment(_FreshEnvironment):
    """The 339 replay environment with the ONE member a refusal must never
    reach turned into a trap."""

    def rehydrate_product(self, **_: Any) -> Any:
        raise AssertionError("rehydrate_product was called for a refused decision")


def _fresh_environment(booted: _Booted, record: DecisionReplayRecord) -> _NoProductEnvironment:
    from ccf.deployment.operators import build_operator_registry

    path = record.content_generation_path
    configuration = GovernedResolver(**{**_arguments(booted), "composite_children": None})
    return _NoProductEnvironment(
        request=path.request,
        required=tuple(path.operator_plan),
        operators=build_operator_registry(
            parameters=configuration._operator_parameters(path.request),
            view=booted.fabric.handle.reader.as_of(
                tenant_id=record.tenant_id,
                at=record.context_fabric_snapshot.temporal_boundary,
            ),
            pins=booted.fabric.pins,
            policy_bundle_key=POLICY_BUNDLE_KEY,
        ),
        ttl_seconds=_arguments(booted)["product_ttl_seconds"],
    )


def _address_of(outcome: Any, store: FileArtifactStore) -> str:
    return store.resolve_uri(uri=outcome.replay_reference)


def _admitted_addresses(record: DecisionReplayRecord) -> tuple[str, ...]:
    return tuple(
        row.child_content_address or ""
        for row in record.content_generation_path.child_resolutions
        if row.outcome_status == CHILD_ADMITTED
    )


def _reconstruct(
    booted: _Booted, outcome: Any, environment: Any
) -> tuple[RefusalReplayOutcome, FileArtifactStore]:
    """`replay_refusal` off a FRESH store instance — nothing the serve held."""
    fresh = FileArtifactStore(root=booted.store.root)
    reconstructed = replay_refusal(
        record_address=_address_of(outcome, fresh),
        store=fresh,
        reader=booted.fabric.handle.reader,
        control_plane=booted.control_plane,
        environment=environment,
    )
    return reconstructed, fresh


class _SpyStore:
    """The real store, with every parent-side `put` recorded by class and one
    class optionally refused. Delegates everything else."""

    def __init__(self, inner: FileArtifactStore, *, refuse_class: str | None = None) -> None:
        self._inner = inner
        self._refuse = refuse_class
        self.puts: list[str] = []

    def put(self, *, tenant_id: str, artifact_class: str, name: str, artifact: Any) -> Any:
        self.puts.append(artifact_class)
        if artifact_class == self._refuse:
            raise OSError(f"the store refused to file {artifact_class!r}")
        return self._inner.put(
            tenant_id=tenant_id, artifact_class=artifact_class, name=name, artifact=artifact
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


def _wired_over(
    booted: _Booted, store: _SpyStore, *, grant: bool = True, **overrides: Any
) -> GovernedResolver:
    """`_wired`, with the parent's own store AND its refusal recorder over ``store``."""
    _resolver, children = build_composite(booted, grant=grant, child_door=_child_door(booted))
    arguments = _arguments(booted)
    recorder = arguments["refusal_recorder"]
    arguments.update(
        composite_children=children,
        artifact_store=store,
        refusal_recorder=ReplayRefusalRecorder(
            artifact_store=store,
            replay_record_class=recorder.replay_record_class,
            tenant_id=recorder.tenant_id,
            assembly_mode=recorder.assembly_mode,
            policy_bundle_pin=recorder.policy_bundle_pin,
        ),
        **overrides,
    )
    return GovernedResolver(**arguments)


# --- case 1: admitted child + blocking required sibling ----------------------------


def test_case_1_an_early_blocking_refusal_retains_the_admitted_sibling_and_runs_no_plan(
    booted_with_a_sibling: _Booted,
) -> None:
    """One child admitted, a required sibling nothing produces: the refusal is
    recorded before any projection, the admitted child's bytes are in the
    store at the row's address and re-hash to it, and the sibling has a row
    and no bytes.
    """
    booted = booted_with_a_sibling
    factory = _ChildReadingFactory()
    door = _one_shot(_child_door(booted))
    outcome = ask_composite(_wired(booted, door=door, plan_factory=factory))
    record = _refused(booted, outcome, "composite-child-refusal")

    assert factory.calls == [], factory.calls
    path = record.content_generation_path
    assert path.plan_id == NO_FABRIC_READ and path.steps == ()
    assert path.product_content_address == NO_PRODUCT_ADDRESS
    by_class = {row.required_product_class: row for row in path.child_resolutions}
    admitted, sibling = by_class[CHILD_CLASS], by_class[SIBLING_CLASS]
    assert admitted.outcome_status == CHILD_ADMITTED and admitted.child_content_address
    assert sibling.outcome_status == "no-producing-skill" and sibling.required
    assert sibling.child_content_address is None

    fresh = FileArtifactStore(root=booted.store.root)
    assert fresh.exists(content_address=admitted.child_content_address)
    retained = ContextProductContract.model_validate_json(
        fresh.get(content_address=admitted.child_content_address)
    )
    assert content_hash(retained) == admitted.child_content_address
    assert retained.payload["threshold"] == "1000"
    assert len(door.calls) == 1


# --- case 2: admitted children + a later tolerance refusal -------------------------


def test_case_2_a_tolerance_refusal_after_projection_keeps_its_children_and_reconstructs(
    booted_with_a_tight_tolerance: _Booted,
) -> None:
    """The plan ran over the child, then the tolerance comparison refused. The
    admitted contract is resolvable from a fresh store; `replay_refusal`
    re-executes the recorded operator path, holds it to the record, and
    returns — without `rehydrate_product` and without a second acquisition.
    """
    booted = booted_with_a_tight_tolerance
    factory = _ChildReadingFactory()
    door = _one_shot(_child_door(booted))
    outcome = ask_composite(
        _wired(
            booted,
            door=door,
            plan_factory=factory,
            debt_scorer=_LegacyScorerSpy(freshness=Decimal("0.8")),
        )
    )
    record = _refused(booted, outcome, "tolerance-exceeded")
    assert factory.calls == ["children"], factory.calls  # computed, provisional
    path = record.content_generation_path
    assert path.plan_id != NO_FABRIC_READ and path.steps != ()
    assert path.product_content_address == NO_PRODUCT_ADDRESS
    (address,) = _admitted_addresses(record)

    reconstructed, fresh = _reconstruct(booted, outcome, _fresh_environment(booted, record))
    assert isinstance(reconstructed, RefusalReplayOutcome)
    assert reconstructed.child_contract_addresses == (address,)
    assert reconstructed.graph_snapshot_id == record.context_fabric_snapshot.graph_snapshot_id
    assert reconstructed.assembly_refusal == path.assembly_refusal
    assert reconstructed.record == record
    assert content_hash(ContextProductContract.model_validate_json(fresh.get(content_address=address))) == address
    assert len(door.calls) == 1, "reconstruction reached the provider"
    assert "product" not in type(reconstructed).model_fields


# --- case 3: no admitted children ---------------------------------------------------


def test_case_3_no_admitted_children_files_no_admitted_child_artifact(booted: _Booted) -> None:
    """Every requirement unreachable: zero artifacts of the admitted-child
    class are filed — while the refusal record itself IS written — and the
    reconstruction returns with an empty address tuple, consulting nothing.
    """
    spy = _SpyStore(booted.store)
    # No in-force grant — the catalog entry, the callable and the door all
    # still exist — so the one required child is unreachable (the 339
    # module's `grant=False` shape).
    outcome = ask_composite(
        _wired_over(booted, spy, grant=False, plan_factory=_ChildReadingFactory())
    )
    record = _refused(booted, outcome, "composite-child-refusal")
    (row,) = record.content_generation_path.child_resolutions
    assert row.outcome_status == "no-producing-skill" and row.child_content_address is None

    assert ADMITTED_CHILD_CONTRACT_CLASS not in spy.puts, spy.puts
    assert spy.puts, "the refusal record was not written at all"

    reconstructed, _fresh = _reconstruct(booted, outcome, _NeverConsulted())
    assert reconstructed.child_contract_addresses == ()
    assert reconstructed.graph_snapshot_id == NO_FABRIC_READ


# --- case 4: fresh reconstruction with the producer stopped -----------------------


def test_case_4_early_blocking_refusal_reconstructs_with_the_producer_stopped(
    booted_with_a_sibling: _Booted,
) -> None:
    """A fresh store instance, a one-shot door already spent, an environment
    that raises if consulted: the pre-projection refusal reconstructs, the
    admitted address is the one returned, and `replay()` refuses the same
    record by name — the guard, covered in the refused→served direction.
    """
    booted = booted_with_a_sibling
    door = _one_shot(_child_door(booted))
    outcome = ask_composite(_wired(booted, door=door, plan_factory=_ChildReadingFactory()))
    record = _refused(booted, outcome, "composite-child-refusal")
    (address,) = _admitted_addresses(record)

    reconstructed, fresh = _reconstruct(booted, outcome, _NeverConsulted())
    assert reconstructed.child_contract_addresses == (address,)
    assert reconstructed.graph_snapshot_id == NO_FABRIC_READ
    assert reconstructed.record_content_address == _address_of(outcome, fresh)
    assert len(door.calls) == 1, "reconstruction reached the provider"

    with pytest.raises(ReplayRecordKindMismatch, match=r"replay\(\) reconstructs a served decision"):
        replay(
            record_address=_address_of(outcome, fresh),
            store=fresh,
            reader=booted.fabric.handle.reader,
            control_plane=booted.control_plane,
            environment=_NeverConsulted(),
        )
    assert len(door.calls) == 1


def test_case_4_late_tolerance_refusal_reconstructs_with_the_producer_stopped(
    booted_with_a_tight_tolerance: _Booted,
) -> None:
    """The post-projection half of case 4: the same fresh-store, spent-door
    posture over a `tolerance-exceeded` record; `replay()` refuses it by name.
    """
    booted = booted_with_a_tight_tolerance
    door = _one_shot(_child_door(booted))
    outcome = ask_composite(
        _wired(
            booted,
            door=door,
            plan_factory=_ChildReadingFactory(),
            debt_scorer=_LegacyScorerSpy(freshness=Decimal("0.8")),
        )
    )
    record = _refused(booted, outcome, "tolerance-exceeded")
    environment = _fresh_environment(booted, record)
    reconstructed, fresh = _reconstruct(booted, outcome, environment)
    assert reconstructed.child_contract_addresses == _admitted_addresses(record)
    assert len(door.calls) == 1
    with pytest.raises(ReplayRecordKindMismatch):
        replay(
            record_address=_address_of(outcome, fresh),
            store=fresh,
            reader=booted.fabric.handle.reader,
            control_plane=booted.control_plane,
            environment=environment,
        )


# --- case 5: missing, substituted, unparseable retained bytes ----------------------


def _retained_file(booted: _Booted, address: str) -> pathlib.Path:
    target = booted.store.root / address
    assert target.is_file(), target
    return target


def test_case_5_missing_retained_bytes_fail_by_name_with_no_substitution(
    booted_with_a_sibling: _Booted,
) -> None:
    booted = booted_with_a_sibling
    door = _one_shot(_child_door(booted))
    outcome = ask_composite(_wired(booted, door=door, plan_factory=_ChildReadingFactory()))
    (address,) = _admitted_addresses(_refused(booted, outcome, "composite-child-refusal"))
    _retained_file(booted, address).unlink()
    with pytest.raises(ReplayUnresolvable, match="is not retained in the store"):
        _reconstruct(booted, outcome, _NeverConsulted())
    assert len(door.calls) == 1, "the missing child was re-acquired"


def test_case_5_substituted_retained_bytes_fail_as_a_divergence_naming_both_hashes(
    booted_with_a_sibling: _Booted,
) -> None:
    """Valid contract bytes at the row's address that hash elsewhere: the
    child the decision consumed is not the child the store now answers."""
    booted = booted_with_a_sibling
    door = _one_shot(_child_door(booted))
    outcome = ask_composite(_wired(booted, door=door, plan_factory=_ChildReadingFactory()))
    (address,) = _admitted_addresses(_refused(booted, outcome, "composite-child-refusal"))
    target = _retained_file(booted, address)
    genuine = ContextProductContract.model_validate_json(target.read_bytes())
    impostor = genuine.model_copy(update={"payload": {**genuine.payload, "threshold": "999"}})
    assert content_hash(impostor) != address
    target.write_bytes(canonical_bytes(impostor))
    with pytest.raises(ReplayDivergence, match=content_hash(impostor)):
        _reconstruct(booted, outcome, _NeverConsulted())
    assert len(door.calls) == 1


def test_case_5_unparseable_retained_bytes_fail_as_a_divergence(
    booted_with_a_sibling: _Booted,
) -> None:
    booted = booted_with_a_sibling
    door = _one_shot(_child_door(booted))
    outcome = ask_composite(_wired(booted, door=door, plan_factory=_ChildReadingFactory()))
    (address,) = _admitted_addresses(_refused(booted, outcome, "composite-child-refusal"))
    _retained_file(booted, address).write_bytes(b"{\"not\": \"a contract\"}")
    with pytest.raises(ReplayDivergence, match="do not rehydrate as a context product contract"):
        _reconstruct(booted, outcome, _NeverConsulted())
    assert len(door.calls) == 1


# --- case 6: the served composite is unchanged ---------------------------------------


def test_case_6_a_served_composite_replays_as_before_and_replay_refusal_refuses_it_by_name(
    booted: _Booted,
) -> None:
    """The served path: retention now runs one branch earlier and files the
    same bytes at the same address; `replay()` reproduces the product exactly
    as `D-IMPL-339` proved; `replay_refusal()` refuses the served record by
    name — the guard, covered in the served→refused direction.
    """
    door = _one_shot(_child_door(booted))
    served = ask_composite(_wired(booted, door=door, plan_factory=_ChildReadingFactory()))
    product, record = _served(booted, served)
    path = record.content_generation_path
    assert path.assembly_refusal == NO_ASSEMBLY_REFUSAL
    assert path.product_content_address == content_hash(product)
    (address,) = _admitted_addresses(record)
    fresh = FileArtifactStore(root=booted.store.root)
    assert fresh.exists(content_address=address)

    environment = _fresh_environment(booted, record)
    with pytest.raises(ReplayRecordKindMismatch, match=r"replay_refusal\(\) reconstructs a refused decision"):
        replay_refusal(
            record_address=served.replay_ref.content_address,
            store=fresh,
            reader=booted.fabric.handle.reader,
            control_plane=booted.control_plane,
            environment=environment,
        )
    replayed = replay(
        record_address=served.replay_ref.content_address,
        store=fresh,
        reader=booted.fabric.handle.reader,
        control_plane=booted.control_plane,
        environment=_FreshEnvironment(
            request=path.request,
            required=tuple(path.operator_plan),
            operators=environment._operators,
            ttl_seconds=environment._ttl,
        ),
    )
    assert replayed.product_content_address == content_hash(product)
    assert replayed.product.payload[CHILD_VALUE_KEY] == "1000"
    assert len(door.calls) == 1


# --- case 7: persistence failure -----------------------------------------------------


def test_case_7_a_store_that_cannot_retain_fails_the_determination_before_any_record(
    booted_with_a_sibling: _Booted,
) -> None:
    """The store refuses to file the admitted child: the serve raises — no
    refusal envelope is returned and no record is written — because a
    determination whose evidence was not kept is not recorded as though it
    had been (`_record_refusal`'s posture, one step earlier).
    """
    booted = booted_with_a_sibling
    spy = _SpyStore(booted.store, refuse_class=ADMITTED_CHILD_CONTRACT_CLASS)
    _resolver, children = build_composite(booted, child_door=_child_door(booted))
    arguments = _arguments(booted)
    recorder = arguments["refusal_recorder"]
    arguments.update(
        composite_children=children,
        artifact_store=spy,
        plan_factory=_ChildReadingFactory(),
        refusal_recorder=ReplayRefusalRecorder(
            artifact_store=spy,
            replay_record_class=recorder.replay_record_class,
            tenant_id=recorder.tenant_id,
            assembly_mode=recorder.assembly_mode,
            policy_bundle_pin=recorder.policy_bundle_pin,
        ),
    )
    with pytest.raises(OSError, match="refused to file"):
        ask_composite(GovernedResolver(**arguments))
    assert spy.puts == [ADMITTED_CHILD_CONTRACT_CLASS], spy.puts


# --- case 8: an optional child invoked, then refused ---------------------------------


def _a_day_late(requirement: Any, asked_at: datetime) -> dict[str, str]:
    """The child answers at a different instant, so admission refuses it
    (`as-of-mismatch`) AFTER it was genuinely dispatched and served."""
    return {"subject": "acct-1", "asked_at": (asked_at + timedelta(days=1)).isoformat(), "threshold": "1000"}


def test_case_8_an_optional_child_invoked_and_refused_blocks_and_reconstructs_as_optional(
    booted_with_an_optional_child: _Booted,
) -> None:
    """`D-IMPL-336` F1: optional means optional ABSENCE, not optional
    governance. The child was dispatched through its door, served, and refused
    at admission; the composite refuses; the row records ``required=False``
    exactly as the determination did — and the reconstruction accepts the
    legitimate refusal without touching that flag. Its identity is retained on
    the row (Amendment 2); nothing was admitted, so nothing is filed.
    """
    booted = booted_with_an_optional_child
    factory = _ChildReadingFactory()
    door = _one_shot(_child_door(booted))
    _resolver, children = build_composite(booted, child_arguments=_a_day_late, child_door=door)
    arguments = _arguments(booted)
    arguments.update(composite_children=children, plan_factory=factory)
    outcome = ask_composite(GovernedResolver(**arguments))
    record = _refused(booted, outcome, "composite-child-refusal")
    assert factory.calls == [], factory.calls
    assert len(door.calls) == 1, "the child was not genuinely invoked"
    (row,) = record.content_generation_path.child_resolutions
    assert row.required is False
    assert row.outcome_status == "rejected-at-admission" and row.refusal_ref == "as-of-mismatch"
    assert row.child_reported_address, "the refused child's identity is retained on the row"
    block = json.loads(record.content_generation_path.assembly_refusal)
    assert json.loads(block["fields"]["reason"]) == "as-of-mismatch"

    reconstructed, fresh = _reconstruct(booted, outcome, _NeverConsulted())
    assert reconstructed.child_contract_addresses == ()
    assert reconstructed.graph_snapshot_id == NO_FABRIC_READ
    assert reconstructed.record.content_generation_path.child_resolutions[0].required is False
    assert len(door.calls) == 1


def test_case_8_control_an_optional_child_honestly_absent_still_serves(
    booted_with_an_optional_child: _Booted,
) -> None:
    """The other half of F1, so case 8 cannot pass for the wrong reason: the
    same optional requirement with NO in-force grant is priced as the declared
    absence and the composite serves."""
    booted = booted_with_an_optional_child
    # The seam's legacy plan, which reads no child: the child-reading plan
    # would look the absent child up by class and that is not what is proved.
    served = ask_composite(_wired(booted, grant=False))
    _product, record = _served(booted, served)
    (row,) = record.content_generation_path.child_resolutions
    assert row.required is False and row.outcome_status == "optional-absent"


# --- case 9: requirements declared, no child resolver wired ---------------------------


def test_case_9_a_composite_with_no_child_resolver_refuses_at_parent_scope_and_reconstructs(
    booted: _Booted,
) -> None:
    """The resolver records ``no-producing-skill`` against the composite's OWN
    class with NO child rows — nothing was attempted, so nothing is invented.
    The reconstruction validates that scope (the named class is the recorded
    request's class; the rows are empty) rather than demanding a child row
    that never existed.
    """
    factory = _ChildReadingFactory()
    arguments = _arguments(booted)
    arguments.update(composite_children=None, plan_factory=factory)
    outcome = ask_composite(GovernedResolver(**arguments))
    record = _refused(booted, outcome, "composite-child-refusal")
    assert factory.calls == [], factory.calls
    path = record.content_generation_path
    assert path.child_resolutions == ()
    block = json.loads(path.assembly_refusal)
    assert json.loads(block["fields"]["product_class"]) == PRODUCT_CLASS
    assert json.loads(block["fields"]["reason"]) == "no-producing-skill"
    assert path.request is not None and path.request.schema_name == PRODUCT_CLASS

    reconstructed, _fresh = _reconstruct(booted, outcome, _NeverConsulted())
    assert reconstructed.child_contract_addresses == ()
    assert reconstructed.graph_snapshot_id == NO_FABRIC_READ
    assert reconstructed.record == record


def test_case_9_control_a_parent_scope_claim_that_names_a_foreign_class_is_refused(
    booted: _Booted,
) -> None:
    """The scope check is not "empty rows means valid": the same record with
    its refusal re-pointed at a class the request does not name is refused."""
    arguments = _arguments(booted)
    arguments.update(composite_children=None, plan_factory=_ChildReadingFactory())
    outcome = ask_composite(GovernedResolver(**arguments))
    record = _refused(booted, outcome, "composite-child-refusal")
    path = record.content_generation_path
    block = json.loads(path.assembly_refusal)
    block["fields"]["product_class"] = json.dumps("fixture.some-other-class")
    from ccf.products.refusal import RefusalEnvelope  # noqa: PLC0415

    forged_block = canonical_bytes(RefusalEnvelope.model_validate(block)).decode("utf-8")
    forged = record.model_copy(
        update={"content_generation_path": path.model_copy(update={"assembly_refusal": forged_block})}
    )
    fresh = FileArtifactStore(root=booted.store.root)
    filed = fresh.put(tenant_id=TENANT, artifact_class="fixture.replay-record", name="forged", artifact=forged)
    with pytest.raises(ReplayRecordKindMismatch, match="not the parent-scope refusal"):
        replay_refusal(
            record_address=filed.content_address,
            store=fresh,
            reader=booted.fabric.handle.reader,
            control_plane=booted.control_plane,
            environment=_NeverConsulted(),
        )


# --- case 10: an outcome for a class the composite does not require ------------------


class _WithAnUndeclaredOutcome:
    """The fixture's resolver, returning one outcome too many."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner

    def __call__(self, **kw: Any) -> Mapping[str, object]:
        outcomes = dict(self._inner(**kw))
        outcomes["fixture.undeclared-product"] = object()
        return outcomes


def test_case_10_an_undeclared_outcome_refuses_and_reconstructs_with_the_admitted_row_retained(
    booted: _Booted,
) -> None:
    """The refusal names a class no row declares — by definition. The admitted
    child's row and its retained bytes are still there, and the reconstruction
    holds the refusal to the absence of a row for the undeclared class."""
    door = _one_shot(_child_door(booted))
    _resolver, children = build_composite(booted, child_door=door)
    arguments = _arguments(booted)
    arguments.update(composite_children=_WithAnUndeclaredOutcome(children), plan_factory=_ChildReadingFactory())
    outcome = ask_composite(GovernedResolver(**arguments))
    record = _refused(booted, outcome, "composite-child-refusal")
    block = json.loads(record.content_generation_path.assembly_refusal)
    assert json.loads(block["fields"]["reason"]) == "undeclared-outcome"
    assert json.loads(block["fields"]["product_class"]) == "fixture.undeclared-product"
    (address,) = _admitted_addresses(record)
    reconstructed, fresh = _reconstruct(booted, outcome, _NeverConsulted())
    assert reconstructed.child_contract_addresses == (address,)
    assert fresh.exists(content_address=address)
    assert len(door.calls) == 1


# --- case 11: an admitted child re-bound under another slot ----------------------------


class _UnderTheWrongSlot:
    """The fixture's resolver, handing the child it admitted for one
    requirement back under the OTHER requirement's key — the re-binding
    failure `resolve_child_outcomes` records as `requirement-mismatch` WITH a
    row, which the census found shares its token with the duplicate-declaration
    shape that records none."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner

    def __call__(self, **kw: Any) -> Mapping[str, object]:
        outcomes = dict(self._inner(**kw))
        outcomes[SIBLING_CLASS] = outcomes.pop(CHILD_CLASS)
        return outcomes


@pytest.fixture
def booted_with_the_sibling_first(tmp_path: pathlib.Path) -> Iterator[_Booted]:
    """Two required children, the unproducible one declared FIRST, so the
    re-binding refusal is the one the walk records (first refusal wins)."""
    yield from boot_composite(
        tmp_path,
        product_class_overrides={"requires": list(reversed(TWO_REQUIREMENTS["requires"]))},
    )


def test_case_11_a_child_rebound_under_another_slot_refuses_with_a_row_and_reconstructs(
    booted_with_the_sibling_first: _Booted,
) -> None:
    booted = booted_with_the_sibling_first
    door = _one_shot(_child_door(booted))
    _resolver, children = build_composite(booted, child_door=door)
    arguments = _arguments(booted)
    arguments.update(composite_children=_UnderTheWrongSlot(children), plan_factory=_ChildReadingFactory())
    outcome = ask_composite(GovernedResolver(**arguments))
    record = _refused(booted, outcome, "composite-child-refusal")
    block = json.loads(record.content_generation_path.assembly_refusal)
    assert json.loads(block["fields"]["reason"]) == "requirement-mismatch"
    assert json.loads(block["fields"]["product_class"]) == SIBLING_CLASS
    by_class = {row.required_product_class: row for row in record.content_generation_path.child_resolutions}
    rebound = by_class[SIBLING_CLASS]
    assert rebound.outcome_status == "rejected-at-admission" and rebound.refusal_ref == "requirement-mismatch"
    assert _admitted_addresses(record) == ()  # rejected, not admitted: nothing filed

    reconstructed, _fresh = _reconstruct(booted, outcome, _NeverConsulted())
    assert reconstructed.child_contract_addresses == ()
    assert reconstructed.graph_snapshot_id == NO_FABRIC_READ
    assert len(door.calls) == 1


# --- the record-kind guard, all four quadrants ----------------------------------------


def _refile(booted: _Booted, record: DecisionReplayRecord) -> tuple[str, FileArtifactStore]:
    fresh = FileArtifactStore(root=booted.store.root)
    filed = fresh.put(tenant_id=TENANT, artifact_class="fixture.replay-record", name="quadrant", artifact=record)
    return filed.content_address, fresh


@pytest.mark.parametrize("quadrant", ["both", "neither"])
def test_the_record_kind_guard_refuses_a_record_that_contradicts_itself(
    booted: _Booted, quadrant: str
) -> None:
    """A refusal block beside a product address, or neither: refused by name
    from BOTH entry points, before any child, plan or operator is resolved."""
    # The refused ask comes FIRST: a grant, once made effective on this fabric,
    # stays in force, so `grant=False` after a served ask would still serve.
    refused = ask_composite(_wired(booted, grant=False, plan_factory=_ChildReadingFactory()))
    block = _refused(booted, refused, "composite-child-refusal").content_generation_path.assembly_refusal
    door = _one_shot(_child_door(booted))
    served = ask_composite(_wired(booted, door=door, plan_factory=_ChildReadingFactory()))
    _product, record = _served(booted, served)
    path = record.content_generation_path
    if quadrant == "both":
        contradiction = path.model_copy(update={"assembly_refusal": block})
    else:
        contradiction = path.model_copy(update={"product_content_address": NO_PRODUCT_ADDRESS})
    address, fresh = _refile(booted, record.model_copy(update={"content_generation_path": contradiction}))
    for entry_point in (replay, replay_refusal):
        with pytest.raises(ReplayRecordKindMismatch, match="contradicts itself about its kind"):
            entry_point(
                record_address=address,
                store=fresh,
                reader=booted.fabric.handle.reader,
                control_plane=booted.control_plane,
                environment=_NeverConsulted(),
            )
    assert len(door.calls) == 1


def test_the_record_kind_guard_accepts_the_two_valid_kinds_from_their_own_entry_points(
    booted: _Booted,
) -> None:
    """The valid quadrants beside the contradictory ones: a served record is
    `served` and a refused record is `refused`, each read off the record."""
    from ccf.replay import engine  # noqa: PLC0415

    refused = ask_composite(_wired(booted, grant=False, plan_factory=_ChildReadingFactory()))
    refused_record = _refused(booted, refused, "composite-child-refusal")
    served = ask_composite(_wired(booted, plan_factory=_ChildReadingFactory()))
    _product, served_record = _served(booted, served)
    assert engine._record_kind(served_record, content_address="served") == engine._RECORD_KIND_SERVED
    assert engine._record_kind(refused_record, content_address="refused") == engine._RECORD_KIND_REFUSED


# --- the vocabulary the engine quotes -------------------------------------------------


def test_the_engines_quoted_tokens_are_the_live_vocabulary() -> None:
    from ccf.replay import engine

    assert engine._COMPOSITE_CHILD_REFUSAL_KIND == REFUSAL_KINDS[ChildAdmissionRefusal]
    for token in (engine._UNDECLARED_OUTCOME, engine._REQUIREMENT_MISMATCH, engine._NO_PRODUCING_SKILL):
        assert token in CHILD_REFUSAL_REASONS, token
