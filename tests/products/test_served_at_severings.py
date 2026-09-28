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
import sys
import types
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from ccf.contracts.canonical import HASH_TRANSPARENT_KEY
from ccf.controlplane.registry import content_hash
from ccf.replay.record import ContentGenerationPath, DecisionReplayRecord
from ccf.replay.serve import ServedProduct
from tests.products.test_resolver_seam import (  # noqa: F401 — fixtures
    ADMITTED_AT,
    ASKED_AT,
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
