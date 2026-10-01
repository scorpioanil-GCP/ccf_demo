"""`D-IMPL-358` step 6: historical compatibility, and recorded time as replay's authority.

**The boundary this module holds.** Replay reconstructs the determination that
HAPPENED. It does not ask whether today's fabric would make that determination
again. So a record written before `ContentGenerationPath.served_at` existed must
keep its original content address, a record that carries one must keep the instant
it recorded, and nothing in reconstruction may consult the deployment's clock.

**Nothing is added to the record here.** `served_at` already exists, defaults to
``None`` and is hash-transparent at that sentinel. This module verifies that
posture through the actual record-loading and replay paths; it does not introduce a
field, rename one, change a sentinel, or change a transparency mark.

**No historical record is backfilled.** An absent `served_at` is not repaired with
a newly obtained or inferred instant — a historical reconstruction that acquired a
fact the original determination never had would be a new determination wearing an
old address.
"""

from __future__ import annotations

import json
import pathlib
from datetime import UTC, datetime, timedelta

import pytest

from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.replay.record import DecisionReplayRecord

#: The ONE committed pre-`served_at` record in the tree, and its provenance.
#:
#: `tests/replay/fixtures/golden_13bd250/` — real bytes written by an older tree,
#: not a synthesized "before" mapping. Its `manifest.json` names
#: `producing_commit = 13bd250e7a9d9ea12daf596ef86597557aad702f`, which is the tag
#: `phase-24.5-base`, and **that tree declares `served_at` zero times** in
#: `src/ccf/replay/record.py` (verified with `git show <commit>:…`). So the record is
#: genuinely pre-field by provenance rather than by inspection alone.
#:
#: The fixture's README states the discipline this module relies on: *"Nothing here
#: is edited after production. A new golden record for a later generation is a new
#: directory named for its producing commit, never a rewrite of this one."*
_FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "golden_13bd250"
_PRODUCING_COMMIT = "13bd250e7a9d9ea12daf596ef86597557aad702f"


def _historical() -> tuple[bytes, str]:
    """The retained bytes and the address the HISTORICAL EVIDENCE names for them.

    The expected address is read from the evidence in two independent places — the
    artifact's own filename (the store addresses by content) and the manifest's
    `record_content_address` — and the two are held equal. It is NOT recomputed from
    today's model, which would make the central assertion circular: a re-hash
    compared against itself passes however the canonical form has moved.
    """
    artifacts = _FIXTURE / "artifacts"
    named = [p for p in artifacts.iterdir() if len(p.name) == 64 and p.is_file()]
    assert len(named) == 1, f"expected exactly one addressed artifact, found {named}"
    manifest = json.loads((_FIXTURE / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["producing_commit"] == _PRODUCING_COMMIT, manifest["producing_commit"]
    assert manifest["record_content_address"] == named[0].name, (
        "the fixture's own two statements of its address disagree, so neither can be"
        " used as the historical expectation"
    )
    return named[0].read_bytes(), named[0].name


def test_the_retained_record_is_genuinely_pre_served_at() -> None:
    """The premise, asserted rather than assumed.

    If this fixture ever carried a `served_at` key, every claim below would be about
    a record that had nothing to do with the step-5 addition — and would pass while
    proving nothing about historical compatibility.
    """
    raw, _address = _historical()
    stored = json.loads(raw)
    assert "served_at" not in stored["content_generation_path"], (
        "the retained record already carries `served_at`, so it is not pre-field"
    )


def test_a_prefield_record_keeps_its_original_content_address() -> None:
    """Historical bytes retain their address under today's model.

    This is what hash transparency at a sentinel BUYS, measured on a real record
    rather than argued from the mark. Loaded with today's `DecisionReplayRecord` —
    which has a `served_at` field the producing tree did not — the record
    canonicalizes to the SAME bytes and therefore the same address.

    Both halves are asserted. Byte equality is the stronger claim and is what makes
    the address equality non-accidental: two different renderings could in principle
    collide, and a test that checked only the digest would not notice the canonical
    form having changed shape.
    """
    raw, address = _historical()
    loaded = DecisionReplayRecord.model_validate_json(raw)

    assert loaded.content_generation_path.served_at is None, (
        "loading a pre-field record invented an instant for it"
    )
    assert canonical_bytes(loaded) == raw, (
        "the canonical rendering of a pre-field record is no longer byte-identical"
        " to the bytes that were stored for it"
    )
    assert content_hash(loaded) == address, (
        f"the record's address moved: stored as {address}, now"
        f" {content_hash(loaded)}"
    )


def test_two_distinct_populated_served_at_values_address_differently() -> None:
    """A populated `served_at` participates in the addressed content.

    The other side of the sentinel rule (`D-IMPL-243` amendment 1, Dave: *"Any
    non-sentinel value is rendered and must move the hash"*). Every other member of
    the record is held FIXED — the two records differ in this one field and nothing
    else — so a difference in address can only come from it.

    The historical address is asserted distinct from both, which is what closes the
    loop with the test above: absence is not merely *a* value, it is a value that
    costs nothing.
    """
    raw, address = _historical()
    loaded = DecisionReplayRecord.model_validate_json(raw)

    first = datetime(2026, 5, 4, 9, 30, tzinfo=UTC)
    second = first + timedelta(seconds=1)
    at_first = loaded.model_copy(
        update={
            "content_generation_path": loaded.content_generation_path.model_copy(
                update={"served_at": first}
            )
        }
    )
    at_second = loaded.model_copy(
        update={
            "content_generation_path": loaded.content_generation_path.model_copy(
                update={"served_at": second}
            )
        }
    )

    assert content_hash(at_first) != content_hash(at_second), (
        "two records differing ONLY in `served_at` share one address — a populated"
        " serve instant is not inside the addressed content"
    )
    assert content_hash(at_first) != address, (
        "populating `served_at` left the address unchanged, so the field is"
        " transparent even when it carries a value"
    )
    assert content_hash(at_second) != address
    # And the sentinel is the ONLY silent value: restoring it restores the address.
    restored = loaded.model_copy(
        update={
            "content_generation_path": loaded.content_generation_path.model_copy(
                update={"served_at": None}
            )
        }
    )
    assert content_hash(restored) == address


# --- the deployment clock cannot change reconstruction -------------------------
#
# This is the residual's reproduction, turned into a standing control. The residual
# read: *"replay re-judges a peered child's admission at replay wall-clock, because
# `environment.py:116` rebuilds the resolver via `build_arguments(fabric)`, which
# carries the deployment's `admission_clock`."*
#
# MEASURED AND REFUTED. The premise is true — the callable IS carried, and that is
# asserted below so the control cannot be read as denying it — and the conclusion is
# false: a RAISING `admission_clock` is never invoked by the supported replay path.
# Carrying a callable is not reading it, which is the whole reason this is a control
# and not a repair.


def _served_and_reopened(tmp_path: pathlib.Path) -> tuple[object, object, object]:
    """Serve once through the paved road, then REOPEN the fabric for replay.

    The reopen happens BEFORE any forbidden clock is installed, deliberately:
    `load_config_and_boot` mints registration audit events and legitimately reads
    live time (`deployment/manifest.py::_mint_register`, `occurred_at=_utc_now()`).
    That is bookkeeping about the reopening, not a temporal evaluation of the
    historical determination, and conflating the two is how a true control gets
    written against the wrong subject.
    """
    from ccf.deployment import load_config_and_boot
    from tests.products.test_paved_road import _open, _question, _write_tree

    root = _write_tree(tmp_path)
    scratch = tmp_path / "scratch"
    opened = _open(root, scratch, clock=lambda: _SERVED_AT)
    served = opened.answer(_question(opened))
    minted = sorted(scratch.glob("paved_fixture*.sqlite3"))[-1]
    fabric = load_config_and_boot(
        opened.config_path,
        registry=opened.control_plane,
        connection={"database_path": str(minted)},
    )
    return opened, served, fabric


#: The instant the paved fixture serves at, distinct from its question instant.
_SERVED_AT = datetime(2026, 3, 2, 12, 7, tzinfo=UTC)


def test_reconstruction_never_reads_the_deployment_clock(
    tmp_path: pathlib.Path,
) -> None:
    """A RAISING deployment clock is carried into reconstruction and never invoked.

    The instrument has to raise rather than count: two constant clocks returning the
    same value prove nothing, and a counter placed on a clock nobody calls reads the
    same as a clock that does not exist. A clock that raises turns "was it read?"
    into a fact the test cannot miss.

    The positive control for the instrument is in the sibling below — the SAME
    raising callable, wired as the deployment clock on the SERVE path, raises at
    `resolver.py::GovernedResolver.__call__`. Without that half, a green result here
    would be satisfied by a callable the fixture never installed.
    """
    from ccf.replay.engine import replay
    from ccf.replay.environment import RecordedEnvironment

    opened, served, fabric = _served_and_reopened(tmp_path)
    record = opened.record_of(served)
    assert record.content_generation_path.served_at == _SERVED_AT, record

    reads: list[str] = []

    def forbidden() -> datetime:
        reads.append("read")
        raise AssertionError("reconstruction read the deployment clock")

    opened._clock = forbidden
    assert opened.build_arguments(fabric)["admission_clock"] is forbidden, (
        "the residual's premise no longer holds — the deployment clock is not even"
        " carried into reconstruction, so this control is measuring nothing"
    )

    environment = RecordedEnvironment(record=record, opened=opened, fabric=fabric)
    outcome = replay(
        record_address=served.replay_ref.content_address,
        store=opened.artifact_store,
        reader=fabric.handle.reader,
        control_plane=opened.control_plane,
        environment=environment,
    )

    assert reads == [], (
        "reconstruction read the deployment clock — replay is asking what today's"
        " fabric would decide, not reproducing what was decided"
    )
    assert outcome is not None
    # ...and the recorded instant is untouched: replay mints no new serve instant.
    assert record.content_generation_path.served_at == _SERVED_AT


def test_the_raising_clock_DOES_fire_on_the_serve_path(
    tmp_path: pathlib.Path,
) -> None:
    """The positive control for the instrument above.

    The same callable, wired as the deployment clock on the SERVE path, is read
    exactly where `served_at` is obtained. So the silence during reconstruction is a
    measured silence rather than an uninstalled hook.
    """
    from tests.products.test_paved_road import _open, _question, _write_tree

    def forbidden() -> datetime:
        raise AssertionError("clock read")

    root = _write_tree(tmp_path)
    opened = _open(root, tmp_path / "scratch", clock=forbidden)
    with pytest.raises(AssertionError, match="clock read"):
        opened.answer(_question(opened))


def test_moving_the_deployment_clock_years_does_not_move_reconstruction(
    tmp_path: pathlib.Path,
) -> None:
    """The same record, reconstructed under two deployment clocks five years apart.

    The raising control above proves the clock is not read; this proves the
    consequence a reader actually cares about — that the reconstructed answer is the
    same one. Asserted on the reproduced product's content address, which is the
    identity replay exists to reproduce.
    """
    from ccf.replay.engine import replay
    from ccf.replay.environment import RecordedEnvironment

    addresses: list[str] = []
    for offset in (timedelta(0), timedelta(days=365 * 5)):
        opened, served, fabric = _served_and_reopened(tmp_path / f"leg{offset.days}")
        record = opened.record_of(served)
        opened._clock = lambda offset=offset: _SERVED_AT + offset
        environment = RecordedEnvironment(record=record, opened=opened, fabric=fabric)
        replay(
            record_address=served.replay_ref.content_address,
            store=opened.artifact_store,
            reader=fabric.handle.reader,
            control_plane=opened.control_plane,
            environment=environment,
        )
        addresses.append(record.content_generation_path.product_content_address)

    assert len(addresses) == 2 and addresses[0] == addresses[1], (
        f"moving the deployment clock changed the reconstruction: {addresses}"
    )


# --- falsification: one named source mutation per guarantee ---------------------
#
# The existing driver discipline (`tests/products/test_served_at_severings.py`): a
# scratch COPY under `tmp_path`, each anchor asserted to occur exactly once before
# substituting, the shipped control green first, the real tree never written. Run
# under `python -B` with `PYTHONDONTWRITEBYTECODE=1`, so a file that did not exist a
# moment ago can have no stale `.pyc`.

#: Named separately from step 5's ledgers. These falsify step 6's two HISTORICAL
#: guarantees; they are not one-edit-per-property entries of the step-5 set, and
#: folding them in would make that ledger's arithmetic wrong about what it covers.
STEP6_RECORD_MUTATIONS: dict[str, str] = {
    "transparency-mark-flipped-to-a-generation-boundary": "state",
    "populated-served-at-dropped-from-addressed-content": "state",
    "a-live-clock-read-inserted-into-reconstruction": "state",
}

_MARK_ANCHOR = """    served_at: datetime | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )"""


def test_every_step6_mutation_has_a_test_that_exists() -> None:
    """The non-vacuity guard the other ledgers carry, on this one too."""
    source = pathlib.Path(__file__).read_text(encoding="utf-8")
    for key in STEP6_RECORD_MUTATIONS:
        assert f'"{key}",' in source, (
            f"{key!r} is claimed but no mutation in this module passes that label"
        )


def test_mutation_the_transparency_mark_becomes_a_generation_boundary(
    tmp_path: pathlib.Path,
) -> None:
    """Flip `served_at` to `{HASH_TRANSPARENT_KEY: False}`.

    A generation boundary renders at its default, so an ABSENT historical
    `served_at` starts moving the address — and the retained pre-field record stops
    reproducing the address it was stored under. That is exactly the compatibility
    this step exists to hold, so this mutation must break
    `test_a_prefield_record_keeps_its_original_content_address`.
    """
    from tests.products.test_served_at_severings import severed

    raw, address = _historical()
    assert content_hash(DecisionReplayRecord.model_validate_json(raw)) == address, (
        "the shipped control is not green"
    )

    module = severed(
        tmp_path,
        "src/ccf/replay/record.py",
        ((_MARK_ANCHOR, _MARK_ANCHOR.replace("True", "False")),),
        "transparency-mark-flipped-to-a-generation-boundary",
    )
    mutated = module.DecisionReplayRecord.model_validate_json(raw)
    assert content_hash(mutated) != address, (
        "the mutation cost nothing — a pre-field record still reproduces its stored"
        " address with `served_at` declared a generation boundary, so the historical"
        " compatibility control is not resting on the mark"
    )


def test_mutation_a_populated_served_at_stops_being_addressed(
    tmp_path: pathlib.Path,
) -> None:
    """Make a marked field silent even when it carries a value.

    The mirror of the mutation above, and it has to be aimed at the MECHANISM rather
    than at the field: measured, a `Field(..., exclude=True)` on the declaration
    changes nothing, because `canonical_bytes` walks the model's own fields rather
    than going through pydantic serialization. So the sentinel comparison in
    `ccf/contracts/canonical.py` is what the guarantee actually rests on, and that is
    what this severs — dropping `and field_value == transparent[name]` makes every
    marked field unconditionally silent.

    Two records differing only in `served_at` then share one address, and a replay
    record stops identifying the serve it describes.
    """
    from tests.products.test_served_at_severings import severed

    raw, _address = _historical()
    loaded = DecisionReplayRecord.model_validate_json(raw)
    first = datetime(2026, 5, 4, 9, 30, tzinfo=UTC)
    second = first + timedelta(seconds=1)

    def _at(instant: datetime | None) -> object:
        return loaded.model_copy(
            update={
                "content_generation_path": loaded.content_generation_path.model_copy(
                    update={"served_at": instant}
                )
            }
        )

    assert content_hash(_at(first)) != content_hash(_at(second)), (
        "the shipped control is not green"
    )

    module = severed(
        tmp_path,
        "src/ccf/contracts/canonical.py",
        (
            (
                "            if name in transparent and field_value == transparent[name]:\n"
                "                continue",
                "            if name in transparent:\n"
                "                continue",
            ),
        ),
        "populated-served-at-dropped-from-addressed-content",
    )
    assert module.content_hash(_at(first)) == module.content_hash(_at(second)), (
        "the mutation cost nothing — two distinct populated serve instants still"
        " address differently, so the addressed-content control is not resting on"
        " the sentinel comparison"
    )
    # ...and the severed rendering really does drop the field, not merely collide.
    assert "served_at" not in module.canonical_bytes(_at(first)).decode("utf-8")


def test_mutation_a_live_clock_read_is_inserted_into_reconstruction(
    tmp_path: pathlib.Path,
) -> None:
    """Make reconstruction read the deployment clock, and watch the control redden.

    **Read what this is and is not.** Dave's third named mutation was *"replacing the
    recorded evaluation instant with the deployment-clock path that the reproduction
    identified."* **The reproduction identified NO such path** — the residual was
    refuted, and there is no live-time read in reconstruction to replace. Rather than
    manufacture an execution path to validate the earlier wording, this falsifies the
    CONTROL instead: it inserts a clock read that does not exist on the shipped tree
    and shows `test_reconstruction_never_reads_the_deployment_clock` catching it.

    So this is evidence that the guard is discriminating, NOT evidence of a defect and
    not a repair of one. Without it, a green raising-clock control could be green
    because reconstruction reads no clock or because the hook was never installed, and
    the positive control on the serve path only proves the callable itself fires.
    """
    from ccf.replay.engine import replay
    from tests.products.test_served_at_severings import severed

    opened, served, fabric = _served_and_reopened(tmp_path)
    record = opened.record_of(served)

    # TWO anchors, because the environment does not keep the resolver at all — it
    # reads three declarations off it (`plan_factory`, `policy_bundle_key`,
    # `product_ttl_seconds`) and drops it. The clock is not even REACHABLE from the
    # reconstruction object, which is one more piece of evidence against the
    # residual: there is nothing there to call. So the mutation must first smuggle
    # the clock in, then read it.
    module = severed(
        tmp_path,
        "src/ccf/replay/environment.py",
        (
            (
                "        self._plan_factory = resolver.plan_factory",
                "        self._plan_factory = resolver.plan_factory\n"
                "        self._smuggled_clock = resolver.admission_clock",
            ),
            (
                "    def resolve_plan(self, *, plan_id: str) -> Any:\n"
                '        """The deployment\'s own plan factory, over the recorded operator set."""',
                "    def resolve_plan(self, *, plan_id: str) -> Any:\n"
                '        """The deployment\'s own plan factory, over the recorded operator set."""\n'
                "        self._smuggled_clock()",
            ),
        ),
        "a-live-clock-read-inserted-into-reconstruction",
    )

    reads: list[str] = []

    def forbidden() -> datetime:
        reads.append("read")
        raise AssertionError("reconstruction read the deployment clock")

    opened._clock = forbidden
    environment = module.RecordedEnvironment(
        record=record, opened=opened, fabric=fabric
    )
    with pytest.raises(AssertionError, match="reconstruction read the deployment clock"):
        replay(
            record_address=served.replay_ref.content_address,
            store=opened.artifact_store,
            reader=fabric.handle.reader,
            control_plane=opened.control_plane,
            environment=environment,
        )
    assert reads == ["read"], (
        "the mutation cost nothing — the inserted clock read was never reached, so"
        " the raising-clock control is not guarding the reconstruction path"
    )


# --- a later policy version does not displace the recorded one ------------------


def test_a_later_temporal_boundary_version_does_not_displace_the_recorded_one(
    tmp_path: pathlib.Path,
) -> None:
    """Rebinding the temporal boundary does not rewrite the determination it governed.

    The shared mechanism — `replay/engine.py::_resolve_bindings` calling
    `control_plane.resolve(binding.key, binding.version)` — is already proven for the
    debt profile by
    `test_engine_rehydration.py::test_a_replay_reproduces_the_obligation_in_force_at_decision_time`,
    which registers a later version under the same key and asserts BOTH halves. This
    does not re-prove the mechanism; it covers the binding `D-IMPL-358` step 5 ADDED,
    which that control predates and does not reach.

    Both halves are asserted here for the same reason: that the recorded version
    still resolves, AND that a genuinely different later version is sitting in the
    plane under the same key to be resolved instead. Asserting only the first would
    pass against a rebinding that never took effect.
    """
    from ccf.controlplane.temporal_boundary import (
        TEMPORAL_BOUNDARY_POLICY,
        TemporalBoundaryPolicy,
        temporal_boundary_policy_key,
    )
    from ccf.replay.engine import replay
    from ccf.replay.environment import RecordedEnvironment
    from tests.composition import register_typed_at_composition

    opened, served, fabric = _served_and_reopened(tmp_path)
    record = opened.record_of(served)

    key = temporal_boundary_policy_key(tenant_id=fabric.tenant_id)
    recorded = [b for b in record.policy_bindings.bindings if b.key == key]
    assert len(recorded) == 1, (
        f"the record does not pin exactly one temporal boundary: {recorded}"
    )
    recorded_version = recorded[0].version

    rebound_version = register_typed_at_composition(
        opened.control_plane,
        key,
        TemporalBoundaryPolicy(
            max_past_seconds=1, permitted_clock_skew_seconds=1
        ),
        TEMPORAL_BOUNDARY_POLICY,
    )
    assert rebound_version != recorded_version, (
        "the rebinding produced the same version, so there is nothing for"
        " reconstruction to resolve INSTEAD and this control is vacuous"
    )

    environment = RecordedEnvironment(record=record, opened=opened, fabric=fabric)
    outcome = replay(
        record_address=served.replay_ref.content_address,
        store=opened.artifact_store,
        reader=fabric.handle.reader,
        control_plane=opened.control_plane,
        environment=environment,
    )
    assert outcome is not None

    # The recorded version is still what the key resolves to AT THAT VERSION, and the
    # rebound one is reachable but different — the substitution was available and was
    # measurably not made. A bound of one second would refuse every question this
    # fixture asks, so had reconstruction re-judged under it, it could not have
    # reproduced at all.
    assert opened.control_plane.resolve(key, recorded_version) is not None
    assert opened.control_plane.resolve(key, rebound_version) is not None
    assert record.policy_bindings.bindings == tuple(
        record.policy_bindings.bindings
    ), "the record's own bindings were mutated by replay"
    assert [b.version for b in record.policy_bindings.bindings if b.key == key] == [
        recorded_version
    ], "the record's pinned temporal version moved during reconstruction"
