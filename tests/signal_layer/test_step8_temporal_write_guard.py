"""`D-IMPL-358` step 8: the tenant-bound temporal write guard at governed ingress.

**What this guards, and where it lives.** An envelope whose ingestion instant falls
outside the tenant's declared `TemporalBoundaryPolicy` window must be refused BEFORE
L2's single writer sees it. Dave's ruling fixes the placement: the guard is a shared
admission function beside `refuse_foreign_envelope`, **not** inside
`AssemblyWorker` — the worker stays tenant-free and clock-free.

**Composition state, bound once at boot.** The function holds the composition tenant
roster and the temporal policy PINNED PER ROSTER TENANT. No `resolve_latest` per
envelope; no `datetime.now` anywhere in it. `envelope.tenant_id` is a CLAIM, not a
selector: a tenant absent from the roster is refused in the
`refuse_foreign_envelope` family, and a tenant on the roster selects the policy that
was pinned for it at boot. That is not loading a tenant from the envelope — it is
refusing a foreign one.

**The evaluation instant is handed in by the ingress caller.**

**Measured before any `src/` edit** (probe, not committed): a 10-year-out-of-window
envelope wrote 2 entities and 1 relationship straight into the graph, and a naive
`1900-01-01` ingestion instant constructed cleanly — `SignalEnvelope.ingestion_timestamp`
carries no awareness check, no ordering check and no bounds check.

**Out of scope by ruling:** `SignalEnvelope.observed_time` / claim `valid_from`. That
is VALID time — how far back a fact may have been true — not the window in which the
fabric may accept a write. Bounding it with `max_past_seconds` would refuse legitimate
back-dated valid-time. Recorded as a named residual.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.controlplane.temporal_boundary import temporal_boundary_policy_key
from ccf.signal.envelope import SignalEnvelope, SourceIdentity

TENANT = "tenant-step8"
NOW = datetime(2026, 3, 2, 12, 0, tzinfo=UTC)


def _envelope(*, tenant_id: str = TENANT, at: datetime = NOW) -> SignalEnvelope:
    return SignalEnvelope(
        tenant_id=tenant_id,
        envelope_id="env-step8",
        source=SourceIdentity(system_id="step8-source"),
        ingestion_timestamp=at,
        raw_payload={"counterparty_lei": "5493001KJTIIGC8Y1R12"},
    )


def _roster(registry: ControlPlaneRegistry, *, max_past: int = 60) -> object:
    """A composition-bound roster with the policy pinned for its one tenant."""
    from ccf.controlplane.temporal_boundary import (
        TEMPORAL_BOUNDARY_POLICY,
        TemporalBoundaryPolicy,
    )
    from ccf.signal.envelope import IngressTemporalBound
    from tests.composition import register_typed_at_composition

    register_typed_at_composition(
        registry,
        temporal_boundary_policy_key(tenant_id=TENANT),
        TemporalBoundaryPolicy(
            max_past_seconds=max_past, permitted_clock_skew_seconds=max_past
        ),
        TEMPORAL_BOUNDARY_POLICY,
    )
    return IngressTemporalBound.at_composition(
        registry=registry, tenant_ids=(TENANT,)
    )


def test_an_in_window_envelope_is_admitted() -> None:
    """The positive control. Without it a guard that refused everything would pass."""
    bound = _roster(ControlPlaneRegistry())
    bound.refuse_outside_window(_envelope(at=NOW), now=NOW)  # type: ignore[attr-defined]


def test_an_out_of_window_envelope_is_REFUSED() -> None:
    """The instant is ten years before the fabric's; the window is sixty seconds."""
    from ccf.signal.envelope import TemporalWriteRefused

    bound = _roster(ControlPlaneRegistry())
    stale = _envelope(at=NOW - timedelta(days=3650))
    with pytest.raises(TemporalWriteRefused) as raised:
        bound.refuse_outside_window(stale, now=NOW)  # type: ignore[attr-defined]
    assert raised.value.tenant_id == TENANT
    assert raised.value.instant == stale.ingestion_timestamp, (
        "the refusal restamped the instant it was handed"
    )


def test_a_tenant_off_the_roster_is_REFUSED_as_foreign() -> None:
    """`envelope.tenant_id` is a CLAIM. An unknown one is refused, never adopted."""
    from ccf.signal.envelope import TemporalWriteRefused

    bound = _roster(ControlPlaneRegistry())
    with pytest.raises(TemporalWriteRefused) as raised:
        bound.refuse_outside_window(  # type: ignore[attr-defined]
            _envelope(tenant_id="tenant-not-on-the-roster"), now=NOW
        )
    assert "roster" in str(raised.value)


def test_a_missing_policy_REFUSES_and_names_the_key_and_the_absence() -> None:
    """Undeclared refuses, and says which key it looked under and what was absent.

    Ruling 11 admits no default and no fabricated binding. An operator reading this
    refusal must be able to act on it, which means the key and the reason — not
    merely "refused".
    """
    from ccf.signal.envelope import IngressTemporalBound, TemporalWriteRefused

    bound = IngressTemporalBound.at_composition(
        registry=ControlPlaneRegistry(), tenant_ids=(TENANT,)
    )
    with pytest.raises(TemporalWriteRefused) as raised:
        bound.refuse_outside_window(_envelope(), now=NOW)
    assert raised.value.policy_key == temporal_boundary_policy_key(tenant_id=TENANT)
    assert raised.value.reason, "the absence reason is empty"
    assert temporal_boundary_policy_key(tenant_id=TENANT) in str(raised.value)


def test_the_roster_pins_each_policy_ONCE_at_composition() -> None:
    """No `resolve_latest` per envelope: the registry is not consulted on the path.

    Asserted by counting. A roster that re-resolved would show reads growing with the
    number of envelopes judged, which is the state the pinning exists to prevent.
    """
    from ccf.signal.envelope import IngressTemporalBound

    registry = ControlPlaneRegistry()
    bound = _roster(registry)
    assert isinstance(bound, IngressTemporalBound)

    reads: list[str] = []
    real = registry.resolve_latest

    def counting(key: str) -> object:
        reads.append(key)
        return real(key)

    registry.resolve_latest = counting  # type: ignore[method-assign]
    for _ in range(5):
        bound.refuse_outside_window(_envelope(), now=NOW)
    assert reads == [], (
        f"the roster consulted the registry {len(reads)} time(s) while judging"
        " envelopes; the policy is pinned at composition"
    )


# --- the guard is ON the production ingress path, before the writer -------------


def test_on_the_paved_road_an_out_of_window_write_is_UNREACHABLE(
    tmp_path: "object",
) -> None:
    """The paved road refuses earlier, and the measurement says where.

    This began as an end-to-end control asserting the write guard FIRES on the paved
    road. It does not, and the reason is structural rather than a wiring defect —
    which is worth recording, because a reader would otherwise expect this path to
    exercise the guard:

    1. step 5's resolver bound judges `asked_at` against the SAME tenant policy and
       refuses the question BEFORE acquisition runs, so no envelope is ever produced;
    2. and if a question is in-window, `refuse_foreign_envelope` requires
       `ingestion_timestamp == asked_at` on this road, so an in-window question can
       only produce an in-window envelope.

    So on the paved road the write guard is belt-and-braces: it cannot fire because
    two earlier refusals already cover the ground. Its value is on ingress paths that
    do NOT sit behind the resolver's bound. That is asserted here rather than
    described, so a later change that removes either earlier refusal is visible.
    """
    import pathlib as _pathlib

    from ccf.products.refusal import RefusalEnvelope
    from tests.products import paved_fixture as fixture
    from tests.products.test_paved_road import _open, _question, _write_tree

    root = _pathlib.Path(str(tmp_path))
    config = fixture.producer_config()
    config["temporal_boundary"] = {
        "max_past_seconds": 60,
        "permitted_clock_skew_seconds": 60,
    }
    tree = _write_tree(root, config=config)
    opened = _open(tree, root / "scratch", clock=lambda: fixture.ASKED_AT)

    outcome = opened.answer(
        _question(opened).model_copy(
            update={"asked_at": fixture.ASKED_AT - timedelta(days=3650)}
        )
    )

    assert isinstance(outcome, RefusalEnvelope), outcome
    assert outcome.kind == "temporal-bound-refusal", (
        "the paved road no longer refuses an out-of-window question at the resolver,"
        " so the write guard is now the only thing standing between that question and"
        " a write — re-read this test's reasoning before changing it"
    )
    # ...and the acquisition never ran, which is the property either refusal must
    # preserve: the refusal is reached before any envelope is produced, so there is
    # nothing for the writer to have written.
    assert opened._acquire.contexts == [], (
        f"acquisition ran {len(opened._acquire.contexts)} time(s) for a question that"
        " was refused out of window — the refusal is on the wrong side of the seam"
    )


# --- named severings: one `src/` edit per control -------------------------------

STEP8_GUARD_MUTATIONS: dict[str, str] = {
    "the-roster-check-removed": "state",
    "the-judged-instant-becomes-the-fabric-clock": "state",
    "the-undeclared-policy-becomes-no-constraint": "state",
}


def test_every_step8_mutation_has_a_test_that_exists() -> None:
    """The non-vacuity guard, and it did not catch what it should have.

    An earlier ledger carried `the-window-judgment-removed`, whose mutation rewrote
    `refusal = refuse_temporal_bound(` to `refusal = None or refuse_temporal_bound(`.
    Those are the same expression — `None or X` IS `X` — so the entry named a
    falsification that cost nothing, and this guard passed it because the label was
    genuinely present in the source. **A guard that checks a label exists cannot
    check that the mutation bites.** The entry is gone and the two that remain each
    take a property away; nothing here is a reachability check wearing a severing's
    name.
    """
    import pathlib as _p

    source = _p.Path(__file__).read_text(encoding="utf-8")
    for key in STEP8_GUARD_MUTATIONS:
        assert f'"{key}",' in source, f"{key!r} is claimed but no mutation exists"


def test_severing_the_roster_check_is_removed(tmp_path: "object") -> None:
    """Without the roster check a foreign tenant is not refused — it CRASHES.

    Stronger than predicted and reported as measured: the guard reaches
    `self.pinned[claimed]` for a tenant that was never pinned and raises `KeyError`,
    an untyped crash where a governed refusal belongs.
    """
    import pathlib as _p

    from tests.products.test_served_at_severings import severed

    module = severed(
        _p.Path(str(tmp_path)),
        "src/ccf/signal/envelope.py",
        (("        if claimed not in self.pinned:", "        if False:"),),
        "the-roster-check-removed",
    )
    bound = module.IngressTemporalBound.at_composition(
        registry=ControlPlaneRegistry(), tenant_ids=(TENANT,)
    )
    with pytest.raises(KeyError):
        bound.refuse_outside_window(
            _envelope(tenant_id="tenant-not-on-the-roster"), now=NOW
        )


def test_severing_the_judged_instant_becomes_the_fabric_clock(
    tmp_path: "object",
) -> None:
    """Judge the fabric's own instant instead of the envelope's. The guard goes blind.

    **The falsification the opening sheet asked for** — *"replace
    `envelope.ingestion_timestamp` in the guard"* — and the one an earlier ledger
    entry only pretended to be.

    The severed guard judges `now` against itself, so the age is always ZERO and
    every envelope is in window however stale it is. The envelope still carries its
    real old timestamp; nothing is restamped in production, and only the scratch copy
    shows what this mistake would cost.

    Both halves of the property are asserted on the SHIPPED implementation first —
    that the envelope's own instant is what is judged, and that the refusal REPORTS
    that same instant rather than a restamped one — so the severing is measured
    against a control known to be green and known to be about the right value.
    """
    import pathlib as _p

    from ccf.signal.envelope import TemporalWriteRefused
    from tests.products.test_served_at_severings import severed

    stale = _envelope(at=NOW - timedelta(days=3650))

    # (1) SHIPPED: refuses, and reports the instant it was handed — not a restamp.
    shipped = _roster(ControlPlaneRegistry())
    with pytest.raises(TemporalWriteRefused) as raised:
        shipped.refuse_outside_window(stale, now=NOW)  # type: ignore[attr-defined]
    assert raised.value.instant == stale.ingestion_timestamp, (
        "the shipped refusal reports an instant other than the envelope's own"
    )
    assert raised.value.instant != NOW, (
        "the shipped guard reports the fabric's instant, so this severing could not"
        " tell the two apart"
    )

    # (2) SEVERED: the same stale envelope is admitted.
    module = severed(
        _p.Path(str(tmp_path)),
        "src/ccf/signal/envelope.py",
        (
            (
                "        instant = envelope.ingestion_timestamp",
                "        instant = now",
            ),
        ),
        "the-judged-instant-becomes-the-fabric-clock",
    )
    registry = ControlPlaneRegistry()
    _roster(registry)
    bound = module.IngressTemporalBound.at_composition(
        registry=registry, tenant_ids=(TENANT,)
    )
    bound.refuse_outside_window(stale, now=NOW)  # must NOT raise
    # ...and the envelope was never rewritten: the severing changed what the guard
    # READ, not what the caller supplied.
    assert stale.ingestion_timestamp == NOW - timedelta(days=3650)



def test_severing_an_undeclared_policy_becomes_no_constraint(
    tmp_path: "object",
) -> None:
    """Ruling 11's INGRESS half, and the line no other ledger entry's edit touches.

    Added at step 10 as reconciliation, not as a new campaign: ruling 11 admits no
    default and no fabricated binding, and
    `test_a_missing_policy_REFUSES_and_names_the_key_and_the_absence` above asserts
    it — but nothing in any of the six ledgers took that property away, so the
    control's force was asserted rather than measured.

    **The property rests on TWO lines, and only one of them was covered.**

    1. `temporal_boundary.py` returning an ABSENCE rather than a default. That line
       is `T3-missing-means-default` in `STEP3_SEVERING_LEDGER`. Measured at step 10:
       substituting T3's behaviour in process does admit this envelope, so the line
       is genuinely load-bearing here — but T3's asserted red is step 3's pin control
       on a scratch copy of `temporal_boundary.py`, which the guard never imports.
    2. The guard's own undeclared branch, HERE: the pinned absence is handed to
       `refuse_temporal_bound` rather than being read as "nothing to enforce". No
       ledger entry's edit touches it. This severing does.

    The severing is the realistic wrong implementation for this line — *no declared
    policy means no window, so there is nothing to refuse* — and it is the exact
    inversion of the ruling: an undeclared tenant would write freely, which is the
    default ruling 11 forbids arriving by omission instead of by declaration.
    """
    import pathlib as _p

    from ccf.signal.envelope import IngressTemporalBound, TemporalWriteRefused
    from tests.products.test_served_at_severings import severed

    # (1) SHIPPED: undeclared refuses, and the refusal names the key and the absence.
    shipped = IngressTemporalBound.at_composition(
        registry=ControlPlaneRegistry(), tenant_ids=(TENANT,)
    )
    with pytest.raises(TemporalWriteRefused) as raised:
        shipped.refuse_outside_window(_envelope(), now=NOW)
    assert raised.value.policy_key == temporal_boundary_policy_key(tenant_id=TENANT), (
        "the shipped control is not green — nothing below proves anything"
    )
    assert raised.value.reason == "temporal-boundary-undeclared", raised.value.reason

    # (2) SEVERED: the same envelope is ADMITTED, cleanly. A crash would redden the
    # control for the wrong reason; this returns `None`, which is what a fabric would
    # actually do with a tenant nobody declared a window for.
    module = severed(
        _p.Path(str(tmp_path)),
        "src/ccf/signal/envelope.py",
        (
            (
                "        bound = self.pinned[claimed]",
                "        bound = self.pinned[claimed]\n"
                "        if isinstance(bound, TemporalBoundaryUndeclared):  # severed\n"
                "            return",
            ),
        ),
        "the-undeclared-policy-becomes-no-constraint",
    )
    broken = module.IngressTemporalBound.at_composition(
        registry=ControlPlaneRegistry(), tenant_ids=(TENANT,)
    )
    assert broken.refuse_outside_window(_envelope(), now=NOW) is None, (
        "the severing cost nothing — the undeclared policy still refuses, so this"
        " ledger entry would be naming a falsification that does not bite"
    )

    # (3) ...and a DECLARED tenant still refuses under the same severed copy, so the
    # entry is about the undeclared branch and not about the window arithmetic.
    registry = ControlPlaneRegistry()
    _roster(registry)
    declared = module.IngressTemporalBound.at_composition(
        registry=registry, tenant_ids=(TENANT,)
    )
    with pytest.raises(module.TemporalWriteRefused):
        declared.refuse_outside_window(
            _envelope(at=NOW - timedelta(days=3650)), now=NOW
        )
