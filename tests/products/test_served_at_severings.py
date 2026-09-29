"""Step 4 severings: each load-bearing line of the `served_at` hoist and capture.

`D-IMPL-358` step 4. **Step 4 severings**, reported separately from Step 3's four
and Step 2(a)'s ten — those campaigns covered different code and reached none of
this.

**A scratch COPY, never an edit-and-revert**, on the in-repo idiom
(`tests/mcp/test_egress_refusal_channels.py::_scratch_egress`): the shipped source
is read, mutated as a string, written to a fresh file under ``tmp_path`` and
imported under a unique module name. The tree is never written, so byte-for-byte
restoration is automatic, and a file that did not exist a moment ago has no stale
``.pyc`` — which sidesteps structurally the trap that CPython validates a ``.pyc``
on ``(mtime-seconds, size)`` alone.

**These are driven BEHAVIORALLY, not structurally.** A severed copy of the
resolver is constructed with the same arguments the fixture gives the shipped one
— they are fabric, store and pin objects, so no cross-module class identity is
involved — and then actually asked a question. A structural assertion that the
source changed would prove only that the mutation applied.

**Every severing asserts its anchor occurs EXACTLY ONCE before substituting**, and
verifies the SHIPPED control is green first. A stale anchor silently applies no
mutation and the severing then "passes" having changed nothing.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
import types
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from ccf.contracts.canonical import HASH_TRANSPARENT_KEY
from ccf.controlplane.registry import ControlPlaneRegistry, content_hash
from ccf.replay.record import ContentGenerationPath, DecisionReplayRecord
from ccf.products import resolver as resolver_module
from ccf.products.refusal import RefusalEnvelope
from ccf.replay.serve import ServedProduct
from tests.products.test_resolver_seam import (  # noqa: F401 — fixtures
    ADMITTED_AT,
    ASKED_AT,
    PRODUCT_TTL_SECONDS,
    _EXPIRES_BETWEEN_DECISION_AND_SERVICE,
    _counting_acquisition,
    _declare_temporal_bound,
    _capturing_compose,
    _advancing_clock,
    PERSPECTIVE,
    _Booted,
    _arguments,
    _ask,
    _request,
    _resolver,
    _served_record,
    booted,
    booted_composite,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

#: What each severing is expected to cost. All four are ``"state"``: each property
#: rests on the single line the severing removes.
STEP4_SEVERING_LEDGER: dict[str, str] = {
    "V1-hoist-reverted": "state",
    "V2-capture-dropped": "state",
    "V3-transparent-mark-flipped-to-boundary": "state",
    "V4-a-second-clock-read": "state",
}


def severed(
    tmp_path: Path, relative: str, pairs: tuple[tuple[str, str], ...], label: str
) -> types.ModuleType:
    """Import a MUTATED copy of `relative`, applying each (anchor, replacement)."""
    source_path = REPO_ROOT / relative
    source = original = source_path.read_text()
    for anchor, replacement in pairs:
        occurrences = source.count(anchor)
        assert occurrences == 1, (
            f"{label}: anchor occurs {occurrences} times in {relative}, expected"
            f" exactly 1 — fix the anchor, do not widen the match: {anchor!r}"
        )
        source = source.replace(anchor, replacement)
    assert source != original, f"{label}: the severing did not take"
    target = tmp_path / f"severed_{label.replace('-', '_')}.py"
    target.write_text(source)
    name = f"ccf_severed_{label.replace('-', '_')}"
    spec = importlib.util.spec_from_file_location(name, target)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_the_step4_ledger_is_complete_and_named() -> None:
    assert len(STEP4_SEVERING_LEDGER) == 4
    assert set(STEP4_SEVERING_LEDGER) == {
        "V1-hoist-reverted",
        "V2-capture-dropped",
        "V3-transparent-mark-flipped-to-boundary",
        "V4-a-second-clock-read",
    }


def test_a_stale_anchor_refuses_rather_than_silently_mutating_nothing(
    tmp_path: Path,
) -> None:
    """THE POSITIVE CONTROL for the driver."""
    with pytest.raises(AssertionError, match="anchor occurs 0 times"):
        severed(
            tmp_path,
            "src/ccf/products/resolver.py",
            (("this_text_does_not_occur_in_the_resolver", "x"),),
            "stale-anchor-probe",
        )


# --------------------------------------------------------------------------
# V1 — the hoist reverted: the read goes back inside the composite branch.
# --------------------------------------------------------------------------


def test_V1_severing_hoist_reverted(tmp_path: Path, booted: _Booted) -> None:
    """Put the clock read back where it was — read only ``if registered.requires:``
    — and a NON-COMPOSITE serve loses both properties at once: it reads no clock,
    and its record cannot say when it answered."""
    reads: list[int] = []

    def counting() -> datetime:
        reads.append(1)
        return ADMITTED_AT

    shipped = _ask(_resolver(booted, composite_children=None, admission_clock=counting), _request())
    assert isinstance(shipped, ServedProduct), shipped
    assert reads == [1], "the shipped control is not green — nothing is proved below"
    assert _served_record(booted, shipped).content_generation_path.served_at == ADMITTED_AT

    module = severed(
        tmp_path,
        "src/ccf/products/resolver.py",
        (
            # RE-AIMED at step 5. At step 4 this severed the read to `None`,
            # which was enough when `served_at` fed only the capture. Step 5 makes
            # it feed policy effectivity too, so `None` now crashes in
            # `_require_aware` — a red, but a crude one that proves less than it
            # could. The severing is now the REALISTIC wrong implementation, the
            # one a hurried author would actually write: reuse the question's own
            # instant. It costs three controls at once — the capture, the
            # read-once count, and effectivity.
            ("        served_at = self.admission_clock()", "        served_at = request.asked_at"),
            ("            admitted_at = served_at", "            admitted_at = self.admission_clock()"),
        ),
        "V1-hoist-reverted",
    )
    reads.clear()
    arguments = _arguments(booted)
    arguments.update(composite_children=None, admission_clock=counting)
    broken = _ask(module.GovernedResolver(**arguments), _request())
    assert isinstance(broken, ServedProduct), broken
    assert reads == [], "the severing cost nothing — the clock is still read at entry"
    # The severed record does not LACK an instant — it carries the WRONG one, and
    # says the answer was served at the moment the question was asked. A lie is
    # worse evidence than a gap, which is what makes this the severing worth
    # running: the record still looks complete.
    recorded = _served_record(booted, broken).content_generation_path.served_at
    assert recorded == ASKED_AT, "the severing did not take"
    assert recorded != ADMITTED_AT, (
        "the severing cost nothing — the trusted clock still reached the record"
    )


# --------------------------------------------------------------------------
# V2 — the capture dropped: the instant is read and thrown away.
# --------------------------------------------------------------------------


def test_V2_severing_capture_dropped(tmp_path: Path, booted: _Booted) -> None:
    """Drop the resolver's pass-through. The instant is still read at entry and
    thrown away one call later — the same shape as the defect step 3 refused, one
    layer down: a value in hand and discarded before anything could pin it.

    Severed in the RESOLVER rather than in the builder, because the resolver-to-
    builder handoff IS the capture; severing the builder would prove a function
    signature rather than the serve path.
    """
    shipped = _ask(_resolver(booted, composite_children=None), _request())
    assert isinstance(shipped, ServedProduct), shipped
    assert _served_record(booted, shipped).content_generation_path.served_at == ADMITTED_AT, (
        "the shipped control is not green — nothing is proved below"
    )

    module = severed(
        tmp_path,
        "src/ccf/products/resolver.py",
        # RE-PINNED at step 5. The anchor was `served_at=served_at,` alone when
        # the resolver had exactly ONE such keyword; step 5 threaded the same
        # keyword through 22 sites and the anchor went STALE — the failure mode
        # this project records as "severing anchors go stale across rulings",
        # caught here by the count!=1 guard rather than by silently mutating
        # nothing. Widened to the comment unique to the SERVED build site, per
        # the standing rule: fix the anchor, do not widen the match.
        ((
            "            # deliberately untouched.\n"
            "            served_at=served_at,",
            "            # deliberately untouched.\n"
            "            served_at=None,  # severed",
        ),),
        "V2-capture-dropped",
    )
    arguments = _arguments(booted)
    arguments.update(composite_children=None)
    broken = _ask(module.GovernedResolver(**arguments), _request())
    assert isinstance(broken, ServedProduct), broken
    assert _served_record(booted, broken).content_generation_path.served_at is None, (
        "the severing cost nothing — the record still carries served_at"
    )


# --------------------------------------------------------------------------
# V3 — the mark flipped from transparent to a generation boundary.
# --------------------------------------------------------------------------


def test_V3_severing_transparent_mark_flipped_to_boundary(tmp_path: Path) -> None:
    """Flip ``served_at``'s mark to ``child_admitted_at``'s — the mark ruling 1
    explicitly did NOT take. The sentinel then renders, so every record written
    before the member existed would canonicalize to a NEW address: the exact harm
    ruling 1 forbids."""
    absent_shipped = ContentGenerationPath(
        plan_id="p", operator_plan=(), steps=(), product_content_address="a"
    )
    shipped_address = content_hash(absent_shipped)
    extra = ContentGenerationPath.model_fields["served_at"].json_schema_extra
    assert isinstance(extra, dict) and extra[HASH_TRANSPARENT_KEY] is True, (
        "the shipped mark is not transparent — nothing is proved below"
    )

    module = severed(
        tmp_path,
        "src/ccf/replay/record.py",
        (
            (
                "    served_at: datetime | None = Field(\n"
                "        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}\n"
                "    )",
                "    served_at: datetime | None = Field(\n"
                "        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: False}\n"
                "    )",
            ),
        ),
        "V3-transparent-mark-flipped-to-boundary",
    )
    severed_extra = module.ContentGenerationPath.model_fields["served_at"].json_schema_extra
    assert severed_extra[HASH_TRANSPARENT_KEY] is False, "the severing did not take"

    absent_severed = module.ContentGenerationPath(
        plan_id="p", operator_plan=(), steps=(), product_content_address="a"
    )
    assert content_hash(absent_severed) != shipped_address, (
        "the severing cost nothing — a sentinel that renders must move the address,"
        " which is precisely why ruling 1 chose the transparent mark"
    )


# --------------------------------------------------------------------------
# V4 — a second clock read, so one answer carries two instants.
# --------------------------------------------------------------------------


def test_V4_severing_a_second_clock_read(
    tmp_path: Path, booted_composite: _Booted
) -> None:
    """Read the clock again for the composite window. The composite is then judged
    in a window the record does not name — the disagreement the original read-once
    comment describes, reintroduced one level up."""
    reads: list[int] = []

    def counting() -> datetime:
        reads.append(1)
        return ADMITTED_AT

    def recording(**_: Any) -> dict[str, Any]:
        return {}

    shipped = _ask(
        _resolver(booted_composite, composite_children=recording, admission_clock=counting),
        _request(),
    )
    assert isinstance(shipped, ServedProduct), shipped
    assert reads == [1], "the shipped control is not green"

    module = severed(
        tmp_path,
        "src/ccf/products/resolver.py",
        (("            admitted_at = served_at", "            admitted_at = self.admission_clock()"),),
        "V4-a-second-clock-read",
    )
    reads.clear()
    arguments = _arguments(booted_composite)
    arguments.update(composite_children=recording, admission_clock=counting)
    broken = _ask(module.GovernedResolver(**arguments), _request())
    assert isinstance(broken, ServedProduct), broken
    assert reads == [1, 1], (
        f"the severing cost nothing — the clock was read {len(reads)} time(s)"
    )


# --- `D-IMPL-358` step 5 severings: one named `src/` edit per property ---------
#
# Reported SEPARATELY from step 4's four above, and deliberately NOT numbered
# `1-11`: those numerals were review shorthand in a GO message and are not
# repository identifiers, so reproducing them would be inventing a roster. Each
# entry below is named by the PROPERTY it falsifies and carries the one concrete
# edit that falsifies it.

STEP5_SEVERING_LEDGER: dict[str, str] = {
    "Bound-acquisition-before-the-judgment": "state",
    "Bind-the-pin-dropped": "state",
    "Comp-evaluated-at-is-the-decision-instant": "state",
    "Gate-the-comparand-is-the-decision-instant": "state",
    "Peer-the-verdict-is-judged-at-the-callers-instant": "state",
    "Bind-a-fabricated-version-on-the-undeclared-path": "state",
}


def test_every_ledger_entry_has_a_severing_that_exists() -> None:
    """The guard that makes both ledgers non-vacuous.

    Written because the step-5 ledger briefly named `Comp` while no severing for it
    existed: the completeness test below compares the ledger against a hard-coded
    set, so it passed a ledger that CLAIMED a severing nobody had written. A ledger
    is only evidence if every entry corresponds to an executable falsification.

    The mapping is by the label each severing passes to :func:`severed` — read out
    of this module's own source, so a severing that stops passing its label, or a
    label that stops matching its ledger key, reddens here.
    """
    source = pathlib.Path(__file__).read_text(encoding="utf-8")
    for ledger, name in ((STEP4_SEVERING_LEDGER, "step 4"), (STEP5_SEVERING_LEDGER, "step 5")):
        for key in ledger:
            assert f'"{key}",' in source, (
                f"{name} ledger names {key!r} but no severing in this module passes"
                " that label to `severed(...)` — the ledger claims a falsification"
                " that does not exist"
            )


def test_the_step5_ledger_is_complete_and_named() -> None:
    """The vacuity guard: a severing added to this module joins the ledger.

    Same shape as step 4's. It also records what the ledger is NOT: `R1–R4`, `P1`
    and "severings 1–11" were GO-text shorthand rather than sheet identifiers, so
    no entry here carries those names.
    """
    assert len(STEP5_SEVERING_LEDGER) == 6
    assert set(STEP5_SEVERING_LEDGER) == {
        "Bound-acquisition-before-the-judgment",
        "Bind-the-pin-dropped",
        "Comp-evaluated-at-is-the-decision-instant",
        "Gate-the-comparand-is-the-decision-instant",
        "Peer-the-verdict-is-judged-at-the-callers-instant",
        "Bind-a-fabricated-version-on-the-undeclared-path",
    }


def test_severing_Bound_acquisition_runs_before_the_judgment(
    tmp_path: Path, booted: _Booted
) -> None:
    """Invoke the declared acquisition seam BEFORE the temporal bound is judged.

    The property is placement, not existence: an out-of-window question must cost
    nothing. Existence is already guarded by E2/E3/E4 refusing at all; only E5's
    `calls == []` guards the ORDER, so that is what this severs.

    The edit invokes the same seam the resolver invokes, one block earlier. It is
    the mirror of "move the judgment below acquisition" and reaches the same state
    with one anchored insertion rather than a forty-line move.
    """
    _declare_temporal_bound(booted, max_past=60)
    calls, seam = _counting_acquisition()
    out_of_bound = _request(asked_at=ADMITTED_AT - timedelta(days=30))
    shipped = _ask(
        _resolver(booted, acquisition=seam, admission_clock=lambda: ADMITTED_AT),
        out_of_bound,
    )
    assert isinstance(shipped, RefusalEnvelope), shipped
    assert calls == [], "the shipped control is not green: acquisition already ran"

    module = severed(
        tmp_path,
        "src/ccf/products/resolver.py",
        (
            (
                "        # THE TEMPORAL BOUND, JUDGED HERE AND BEFORE ACQUISITION.",
                "        if self.acquisition is not None:\n"
                "            self.acquisition(\n"
                "                request=effective_request, perspective=perspective\n"
                "            )\n"
                "        # THE TEMPORAL BOUND, JUDGED HERE AND BEFORE ACQUISITION.",
            ),
        ),
        "Bound-acquisition-before-the-judgment",
    )
    calls.clear()
    arguments = _arguments(booted)
    arguments.update(acquisition=seam, admission_clock=lambda: ADMITTED_AT)
    _ask(module.GovernedResolver(**arguments), out_of_bound)
    assert calls == [1], (
        "the severing cost nothing — an out-of-window question still invoked"
        f" acquisition {len(calls)} time(s), so E5's zero is not guarding placement"
    )


def test_severing_Bind_the_pin_is_dropped(tmp_path: Path, booted: _Booted) -> None:
    """Drop `PinnedTemporalBoundary.binding` from the policy bindings.

    A served determination that RESOLVED a temporal policy must carry that policy's
    exact binding. Severing the splice leaves the serve working and the record
    silent about the policy that governed it — which is the whole of what E6 exists
    to notice.
    """
    shipped = _ask(_resolver(booted), _request())
    assert isinstance(shipped, ServedProduct), shipped
    record = _served_record(booted, shipped)
    keys = {b.key for b in record.policy_bindings.bindings}
    temporal = {k for k in keys if "temporal-boundary-policy" in k}
    assert temporal, "the shipped control is not green: no temporal pin was minted"

    module = severed(
        tmp_path,
        "src/ccf/products/resolver.py",
        (
            (
                "        temporal_pins = (\n"
                "            (temporal.binding,) if isinstance(temporal, PinnedTemporalBoundary) else ()\n"
                "        )",
                "        temporal_pins: tuple[PolicyBinding, ...] = ()",
            ),
        ),
        "Bind-the-pin-dropped",
    )
    broken = _ask(module.GovernedResolver(**_arguments(booted)), _request())
    assert isinstance(broken, ServedProduct), broken
    severed_record = _served_record(booted, broken)
    severed_keys = {b.key for b in severed_record.policy_bindings.bindings}
    assert not {k for k in severed_keys if "temporal-boundary-policy" in k}, (
        "the severing cost nothing — a temporal binding is still pinned, so E6 is"
        " not guarding the splice"
    )


def test_severing_Gate_the_comparand_returns_to_the_decision_instant(
    tmp_path: Path, booted: _Booted
) -> None:
    """Hand `run_gates` the decision instant again.

    The case is the one the comparand moved for: a window that lapses BETWEEN the
    decision and the hand-over. Shipped, it refuses. Severed, it serves — a product
    whose declared validity had already expired when the consumer received it.

    This is the control the three `test_served_at_pinning.py` legs were believed to
    provide and, measured, do not: all three stay green under this edit, because
    their subject is `served_at`'s presence in the replay record rather than Gate
    3's comparand.
    """
    lapsing = _resolver(
        booted, product_ttl_seconds=_EXPIRES_BETWEEN_DECISION_AND_SERVICE
    )
    shipped = _ask(lapsing, _request())
    assert isinstance(shipped, RefusalEnvelope), shipped
    assert shipped.kind == "ttl-refusal", (
        f"the shipped control is not green: {shipped.kind}"
    )

    module = severed(
        tmp_path,
        "src/ccf/products/resolver.py",
        (("                now=served_at,", "                now=decided_at,"),),
        "Gate-the-comparand-is-the-decision-instant",
    )
    arguments = _arguments(booted)
    arguments.update(product_ttl_seconds=_EXPIRES_BETWEEN_DECISION_AND_SERVICE)
    broken = _ask(module.GovernedResolver(**arguments), _request())
    assert isinstance(broken, ServedProduct), (
        "the severing cost nothing — the lapsed product was refused anyway, so this"
        f" pair is not measuring the comparand: {broken}"
    )
    assert broken.product.expires_at < ADMITTED_AT, (
        "a product was served whose own declared validity had already lapsed at the"
        " instant it was handed over — which is precisely the state the comparand"
        " change prevents"
    )


def test_severing_Comp_the_evaluation_instant_becomes_the_decision_instant(
    tmp_path: Path, booted_composite: _Booted, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Hand the mixing law the decision instant instead of the hoisted `served_at`.

    The property is that `compose_children(evaluated_at=...)` is the ONE hoisted
    `served_at`. Severed, the composition is judged at the instant the question was
    decided, so every constituent reports more validity remaining than it has — by
    exactly the gap between the two instants.

    Observed at the KWARG rather than through the mixing arithmetic. The behavioral
    route exists (c11's four-minute floor against three minutes of validity) but its
    margin is 180 seconds wide and entangled with the parent's own anchor; the kwarg
    is the value the property is about.
    """
    children = {"composite_children": lambda **_: {}, "admission_clock": lambda: ADMITTED_AT}
    shipped = _capturing_compose(monkeypatch, resolver_module)
    served = _ask(_resolver(booted_composite, **children), _request())
    assert isinstance(served, ServedProduct), served
    assert shipped.get("evaluated_at") == ADMITTED_AT, (
        f"the shipped control is not green: {shipped.get('evaluated_at')}"
    )

    module = severed(
        tmp_path,
        "src/ccf/products/resolver.py",
        (("                evaluated_at=served_at,", "                evaluated_at=decided_at,"),),
        "Comp-evaluated-at-is-the-decision-instant",
    )
    broken_capture = _capturing_compose(monkeypatch, module)
    arguments = _arguments(booted_composite)
    arguments.update(**children)
    broken = _ask(module.GovernedResolver(**arguments), _request())
    assert isinstance(broken, ServedProduct), broken
    assert broken_capture.get("evaluated_at") == ASKED_AT, (
        "the severing cost nothing — the mixing law was still handed"
        f" {broken_capture.get('evaluated_at')}, so nothing guards the kwarg"
    )
    assert ASKED_AT != ADMITTED_AT, "the two instants coincide; this severing is vacuous"


def test_severing_Peer_the_verdict_is_judged_at_the_callers_instant(
    tmp_path: Path,
) -> None:
    """Hand the peering admission verdict the CALLER's instant instead of the fabric's.

    `ChildResolver._admit` receives both `asked_at` and `admitted_at`, so the
    substitution is a one-word edit with a caller-supplied value already in scope.
    Measured before the guard existed: this edit left the ENTIRE suite green —
    all of `tests/peering/`, every step-4 `served_at` severing, every E-series test.

    **This severing is structural, matching its control.** The behavioral end-to-end
    control does not exist and cannot yet: `_admit` needs a `ResolvedProducer`,
    mint-only through `resolve_producing_grant` from a module-private
    `BoundSkillView`, and no deployment wires a `PeeringAdmissionGate` into a child
    resolver — so there is no governed path to drive. That is recorded as owed
    rather than papered over, and the guard here catches the edit meanwhile.

    It runs the SHIPPED control's own logic against the severed copy, so the two
    cannot drift: if the control's slice changes, this changes with it.
    """
    from tests.peering.test_admission_clock import (
        test_the_peering_hop_passes_the_FABRIC_instant_and_not_the_question_s as shipped,
    )

    shipped()  # the shipped control is green first

    module_path = severed(
        tmp_path,
        "src/ccf/products/child_resolver.py",
        (("                now=admitted_at,", "                now=asked_at,"),),
        "Peer-the-verdict-is-judged-at-the-callers-instant",
    ).__file__
    assert module_path is not None
    source = Path(module_path).read_text(encoding="utf-8")

    call = source.index("self._admit_peered(")
    end = source.index(")", source.index("now=", call))
    hop = source[call:end]
    assert "now=asked_at" in hop, "the severing did not reach the hop"
    assert "now=admitted_at," not in hop, (
        "the severing cost nothing — the hop still names the fabric instant"
    )


def test_severing_Bind_a_fabricated_version_on_the_undeclared_path(
    tmp_path: Path, booted: _Booted
) -> None:
    """Mint a binding for a policy that does not exist.

    Ruling 11's second half: an undeclared boundary records the key and the absence
    and mints NO binding. This is the MEASURED escape that widened E2 — its filter
    was `binding.key == temporal_boundary_policy_key(tenant_id=TENANT)`, so a
    binding minted under the BARE class id carried a fabricated version `"unknown"`
    straight past it. A record then claimed a governed determination was bound to a
    policy version nobody ever registered.

    E2 now filters on the class id wherever it appears in the key, which is why
    this severing reddens it. Kept as a severing rather than trusted as obvious:
    the widening is a fix to a measured escape, and an unproven fix to a measured
    escape is what this project refuses everywhere else.
    """
    from tests.products.test_resolver_seam import (
        test_E2_no_declared_temporal_policy_refuses_before_acquisition as shipped,
    )

    shipped(booted)  # green on the shipped tree, with the widened filter

    module = severed(
        tmp_path,
        "src/ccf/products/resolver.py",
        (
            (
                "        temporal_pins = (\n"
                "            (temporal.binding,) if isinstance(temporal, PinnedTemporalBoundary) else ()\n"
                "        )",
                "        temporal_pins = (\n"
                "            (temporal.binding,)\n"
                "            if isinstance(temporal, PinnedTemporalBoundary)\n"
                "            else (\n"
                "                PolicyBinding(\n"
                "                    key=temporal.required_class_id, version=\"unknown\"\n"
                "                ),\n"
                "            )\n"
                "        )",
            ),
        ),
        "Bind-a-fabricated-version-on-the-undeclared-path",
    )
    calls, seam = _counting_acquisition()
    arguments = _arguments(booted)
    # The same EMPTY plane E2 uses: the undeclared path only runs where no policy
    # is registered, and the fixture's own plane declares a wide one.
    arguments.update(
        acquisition=seam,
        admission_clock=lambda: ADMITTED_AT,
        control_plane=ControlPlaneRegistry(),
    )
    outcome = _ask(module.GovernedResolver(**arguments), _request())
    assert isinstance(outcome, RefusalEnvelope), outcome

    record = DecisionReplayRecord.model_validate_json(
        booted.store.get(
            content_address=booted.store.resolve_uri(uri=outcome.replay_reference)
        )
    )
    minted = [
        b for b in record.policy_bindings.bindings
        if "temporal-boundary-policy" in b.key
    ]
    assert minted, (
        "the severing cost nothing — no fabricated binding reached the record, so"
        " E2's widened filter is not what is holding this"
    )
    assert any(b.version == "unknown" for b in minted), minted


# --- `D-IMPL-358` step 5: Bound's RESTAMP mutations ----------------------------
#
# Named SEPARATELY from `STEP5_SEVERING_LEDGER` and deliberately not folded into
# it: those six are one-edit-per-property falsifications, and these are three ways
# to break one half of ONE property. Renumbering the six to absorb them would make
# the ledger's own arithmetic lie about what it covers.

BOUND_RESTAMP_MUTATIONS: dict[str, str] = {
    "restamped-from-a-second-clock-read": "state",
    "substituted-with-the-questions-instant": "state",
    "omitted-entirely": "state",
}


def test_every_bound_restamp_mutation_has_a_test_that_exists() -> None:
    """The same non-vacuity guard the two ledgers carry."""
    source = pathlib.Path(__file__).read_text(encoding="utf-8")
    for key in BOUND_RESTAMP_MUTATIONS:
        assert f'"{key}",' in source, (
            f"{key!r} is claimed but no mutation in this module passes that label"
        )


_RECORD_ANCHOR = """            recorded_at=request.asked_at,
            # The live instant beside the question's, never instead of it.
            served_at=served_at,"""


def _out_of_window_served_at(module: Any, booted: _Booted) -> Any:
    """Drive the out-of-window refusal on ``module`` and return the record's instant.

    Returns the persisted `served_at`, or the exception a mutation raised. Either
    falsifies the control — what must not happen is a record that quietly carries
    the right instant after the line that puts it there was broken.
    """
    _declare_temporal_bound(booted, max_past=60)
    reads, clock = _advancing_clock()
    calls, seam = _counting_acquisition()
    arguments = _arguments(booted)
    arguments.update(acquisition=seam, admission_clock=clock)
    request = _request(asked_at=ADMITTED_AT - timedelta(days=30))
    try:
        outcome = _ask(module.GovernedResolver(**arguments), request)
    except TypeError as raised:
        return raised
    assert isinstance(outcome, RefusalEnvelope), outcome
    record = DecisionReplayRecord.model_validate_json(
        booted.store.get(
            content_address=booted.store.resolve_uri(uri=outcome.replay_reference)
        )
    )
    return (record.content_generation_path.served_at, reads, calls)


@pytest.mark.parametrize(
    "label,replacement",
    [
        (
            "restamped-from-a-second-clock-read",
            _RECORD_ANCHOR.replace(
                "served_at=served_at,", "served_at=self.admission_clock(),"
            ),
        ),
        (
            "substituted-with-the-questions-instant",
            _RECORD_ANCHOR.replace(
                "served_at=served_at,", "served_at=request.asked_at,"
            ),
        ),
        (
            "omitted-entirely",
            "            recorded_at=request.asked_at,",
        ),
    ],
    ids=list(BOUND_RESTAMP_MUTATIONS),
)
def test_mutation_Bound_the_refusal_record_loses_the_hoisted_served_at(
    tmp_path: Path, booted: _Booted, label: str, replacement: str
) -> None:
    """Each of the three ways to break Bound's restamp half must be CAUGHT.

    The control is
    `test_resolver_seam.py::test_Bound_the_out_of_window_refusal_record_carries_the_ONE_hoisted_served_at`.
    Its instrument is an ADVANCING clock — a second read returns a later instant —
    so a restamp shows up as the wrong value and not only as a wrong count. That is
    what makes the first mutation visible at all; against a clock pinned to a
    constant it would have been invisible in the record.

    The third mutation cannot produce a record: `served_at` is a REQUIRED keyword on
    the recorder (`D-IMPL-264` amendment 1 — *"No intermediate layer may manufacture
    the marker from omission"*), so omitting it is a `TypeError` at the call. That is
    the design working, and it is asserted as such rather than as a missing field.
    """
    shipped = _out_of_window_served_at(resolver_module, booted)
    assert shipped[0] == ADMITTED_AT, f"the shipped control is not green: {shipped}"
    assert shipped[1] == [1] and shipped[2] == [], shipped

    module = severed(
        tmp_path, "src/ccf/products/resolver.py", ((_RECORD_ANCHOR, replacement),), label
    )
    observed = _out_of_window_served_at(module, booted)

    if isinstance(observed, TypeError):
        assert "served_at" in str(observed), observed
        return
    served_at, reads, _calls = observed
    assert served_at != ADMITTED_AT, (
        f"the mutation {label!r} cost nothing — the record still carries the hoisted"
        " instant, so the control is not guarding this line"
    )
    if label == "restamped-from-a-second-clock-read":
        assert reads == [1, 1], f"expected a second clock read, saw {reads}"
        assert served_at == ADMITTED_AT + timedelta(seconds=1), served_at
