"""CINV-04: the replay-by-construction harness, with honest deferrals.

CLAUDE.md §11 ("Decision Replay is enforced at write time, not retrofitted") and
§3.1 (the Phase I review reads the CI invariants); 04-RESEARCH.md Open Question 3.

CINV-04 is not one check. It is the claim that *every* path producing a
decision writes its replay record by construction, and CLAUDE.md names five
such paths: served Context Products, HITL actions (§8.2), workflow traces
(§8.1), skill grants and revocations, and the skill-set in force at decision
time (§6.2). Two of those five paths do not exist yet — the pillars that
produce them (HITL, workflows) land in I.4; skill-set capture went active
with the I.2 skilling wave (D-10).

That leaves a reporting problem, and the way it is usually solved is wrong. A
suite that asserted only what exists would pass, and "CINV-04: green" would then
mean "the checks we wrote all pass", which reads identically to "the invariant
holds". This module refuses that reading: the deferred checks are *emitted*, as
pytest skips carrying the phase that will activate them. ``pytest -rs`` prints
them, so the gate review reads a status that distinguishes "verified" from "not
yet verifiable" without having to know which pillars have shipped.

The registry below is the machine-readable form of that status. Each entry
names the invariant, its state, and — for active checks — the test that
actually asserts it, because the assertion belongs with the subject and
duplicating it here would produce two checks that could disagree.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Literal, NamedTuple

import pytest

from ccf.replay.serve import CapabilityForgeryError, DeliveryCapability

if TYPE_CHECKING:
    from ccf.boot import FabricHandle

TESTS_ROOT = Path(__file__).resolve().parents[1]

CheckStatus = Literal["active", "not-yet-applicable"]

#: Phrase every deferred skip reason carries. Named so the CI grep and the
#: reason strings cannot drift apart.
DEFERRAL_PHRASE = "not-yet-applicable"


class Check(NamedTuple):
    """One CINV-04 check, and where it stands.

    Attributes:
        name: Stable identifier, for the gate checklist.
        invariant: What must hold, in one sentence.
        status: Whether this check is asserted today.
        owning_test: ``path::function`` of the test that asserts it, for active
            checks. ``None`` for deferred ones — there is nothing to point at,
            and inventing a placeholder test would be the false green again.
        phase: The milestone that activates a deferred check.
    """

    name: str
    invariant: str
    status: CheckStatus
    owning_test: str | None = None
    phase: str | None = None


#: The CINV-04 status, in full. Read by the D-17 gate checklist.
CINV_04_CHECKS: tuple[Check, ...] = (
    Check(
        name="replay-write-precedes-delivery",
        invariant=(
            "no Context Product reaches a caller without its Decision Replay "
            "record having been appended first"
        ),
        status="active",
        owning_test=(
            "replay/test_serve_writes_replay.py::"
            "test_a_failing_store_yields_no_delivery"
        ),
    ),
    Check(
        name="single-writer-at-boot",
        invariant=(
            "exactly one writer per graph, refused at boot rather than "
            "discovered when the second writer writes"
        ),
        status="active",
        owning_test=(
            "invariants/test_single_writer_boot.py::"
            "test_booting_the_same_graph_twice_raises"
        ),
    ),
    Check(
        name="hash-verified-re-hydration",
        invariant=(
            "a recorded decision reproduces its product at the recorded "
            "content address, after the graph has moved on"
        ),
        status="active",
        owning_test=(
            "replay/test_engine_rehydration.py::"
            "test_the_product_replays_exactly_after_the_graph_has_moved_on"
        ),
    ),
    Check(
        name="hitl-action-capture",
        invariant=(
            "every HITL action — approval, escalation, override, review — "
            "lands in replay dimension 2 by construction (CLAUDE.md §8.2)"
        ),
        status="not-yet-applicable",
        phase="I.4",
    ),
    Check(
        name="workflow-trace-capture",
        invariant=(
            "every workflow execution trace lands in replay dimensions 4 and 5 "
            "by construction (CLAUDE.md §8.1)"
        ),
        status="not-yet-applicable",
        phase="I.4",
    ),
    Check(
        name="skill-set-capture",
        invariant=(
            "every skill grant and revocation, and the skill-set in force at "
            "decision time, land in replay dimension 4 by construction "
            "(CLAUDE.md §6.2)"
        ),
        status="active",
        owning_test=(
            "integration/test_agent_slice.py::"
            "test_a_granted_decision_captures_the_grant_set_hash_in_dimension_4"
        ),
    ),
)

ACTIVE = tuple(check for check in CINV_04_CHECKS if check.status == "active")
DEFERRED = tuple(
    check for check in CINV_04_CHECKS if check.status == "not-yet-applicable"
)


# --- the registry itself ---------------------------------------------------


def test_every_check_is_either_asserted_somewhere_or_explicitly_deferred() -> None:
    """No entry may be neither. That third state is where a false green lives."""
    for check in CINV_04_CHECKS:
        if check.status == "active":
            assert check.owning_test, check.name
            assert check.phase is None, check.name
        else:
            assert check.phase, check.name
            assert check.owning_test is None, check.name


@pytest.mark.parametrize("check", ACTIVE, ids=lambda check: check.name)
def test_an_active_check_points_at_a_test_that_exists(check: Check) -> None:
    """The registry is load-bearing only if its references resolve.

    A status table naming tests that were renamed away would report green about
    assertions nobody runs — which is exactly the failure mode this module
    exists to prevent, arriving through the back door.
    """
    assert check.owning_test is not None
    module_path, _, function = check.owning_test.partition("::")
    source_path = TESTS_ROOT / module_path
    assert source_path.is_file(), check.owning_test
    source = source_path.read_text(encoding="utf-8")
    assert re.search(rf"^def {re.escape(function)}\(", source, re.MULTILINE), (
        check.owning_test
    )


@pytest.mark.parametrize("check", DEFERRED, ids=lambda check: check.name)
def test_a_deferred_check_is_reported_as_a_skip_not_as_a_pass(check: Check) -> None:
    """Emitted, never silently absent (04-RESEARCH.md Open Question 3).

    ``pytest -rs`` lists these with their reasons, so a reader of the gate
    checklist sees three named invariants awaiting their pillar rather than a
    suite that passed and a claim they cannot check.
    """
    pytest.skip(
        f"{check.name}: {DEFERRAL_PHRASE} until Phase {check.phase} — "
        f"{check.invariant}"
    )


# --- the active checks, asserted locally where the assertion is cheap ------
#
# The owning tests above carry the full versions. These are the structural
# statements, restated here so the harness is not purely bibliographic: a
# registry whose every entry was a pointer would pass with the fabric deleted.


def test_the_delivery_capability_cannot_be_constructed() -> None:
    """The only mint is a completed replay append (whitepaper §7.10, T-04-10)."""
    with pytest.raises(CapabilityForgeryError):
        DeliveryCapability(None, object())  # type: ignore[arg-type]


def test_a_second_writer_over_one_graph_is_refused_at_boot(
    fabric_boot: Callable[..., "FabricHandle"], tmp_path: Path
) -> None:
    """CINV-04's single-writer leg, restated (DESIGN.md §2A.5.3 layer 4)."""
    from ccf.graph._writer import SingleWriterViolation

    database_path = tmp_path / "cinv04.sqlite3"
    fabric_boot(database_path=database_path)
    with pytest.raises(SingleWriterViolation):
        fabric_boot(database_path=database_path)
