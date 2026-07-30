"""CINV-04: the replay-by-construction harness — fully active as of I.4.

CLAUDE.md §11 ("Decision Replay is enforced at write time, not retrofitted") and
§3.1 (the Phase I review reads the CI invariants); 04-RESEARCH.md Open Question 3.

CINV-04 is not one check. It is the claim that *every* path producing a
decision writes its replay record by construction, and CLAUDE.md names five
such paths: served Context Products, HITL actions (§8.2), workflow traces
(§8.1), skill grants and revocations, and the skill-set in force at decision
time (§6.2). Through I.3 the two paths whose pillars had not shipped (HITL,
workflows) were carried as *emitted deferrals* — pytest skips naming the
phase that would activate them — so that "CINV-04: green" never read as
"the invariant holds" while two of its legs were unverifiable.

As of 07-07 both deferrals are discharged: the D-01 vertical slice
(``tests/workflow/test_slice.py``) exercises the real ApprovalGate and the
workflow engine end to end, and the two formerly deferred checks now carry
owning tests demonstrated to fail under a severed capture (D-25 — the red
outputs are recorded in the 07-07 SUMMARY). The registry below is the
machine-readable status. Each entry names the invariant, its state, and the
test that actually asserts it, because the assertion belongs with the
subject and duplicating it here would produce two checks that could
disagree.

**D-22 scope statement:** these checks guard *capture on exercised paths* —
each owning test fails when the capture is severed, and each activated
family carries an adversarial case proving the check guards the path, not
just the happy case. They are lint/CI-style verification, not a type-level
proof that no unexercised path could exist; the type-unrepresentable legs
(e.g. an unbound HITL submission) are documented on the primitives that own
them.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

import pytest

from ccf.replay.serve import CapabilityForgeryError, DeliveryCapability

if TYPE_CHECKING:
    from ccf.boot import FabricHandle

TESTS_ROOT = Path(__file__).resolve().parents[1]


class Check(NamedTuple):
    """One CINV-04 check, and the test that asserts it.

    Attributes:
        name: Stable identifier, for the gate checklist.
        invariant: What must hold, in one sentence.
        owning_test: ``path::function`` of the test that asserts it. Every
            check is active as of I.4 — the deferral machinery this registry
            carried through I.3 is discharged, not merely hidden.
    """

    name: str
    invariant: str
    owning_test: str


#: The CINV-04 status, in full. Read by the D-17 gate checklist.
CINV_04_CHECKS: tuple[Check, ...] = (
    Check(
        name="replay-write-precedes-delivery",
        invariant=(
            "no Context Product reaches a caller without its Decision Replay "
            "record having been appended first"
        ),
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
        owning_test=(
            "workflow/test_slice.py::"
            "test_the_human_action_lands_on_dimension_2_verbatim"
        ),
    ),
    Check(
        name="workflow-trace-capture",
        invariant=(
            "every workflow execution trace lands in replay dimensions 4 and 5 "
            "by construction (CLAUDE.md §8.1)"
        ),
        owning_test=(
            "workflow/test_slice.py::"
            "test_the_step_sequence_lands_on_dimension_5_verbatim"
        ),
    ),
    Check(
        name="skill-set-capture",
        invariant=(
            "every skill grant and revocation, and the skill-set in force at "
            "decision time, land in replay dimension 4 by construction "
            "(CLAUDE.md §6.2)"
        ),
        owning_test=(
            "integration/test_agent_slice.py::"
            "test_a_granted_decision_captures_the_grant_set_hash_in_dimension_4"
        ),
    ),
)

#: The adversarial companions of the two I.4-activated families (Cursor
#: suggestion 6, 07-07): each proves its check guards the *path*, not just
#: the happy case — an attempted resolution/completion engineered to skip
#: the replay landing is detectable against the positive sentinel.
ADVERSARIAL_CASES: tuple[tuple[str, str], ...] = (
    (
        "hitl-action-capture",
        "workflow/test_slice.py::"
        "test_a_resolution_that_skips_the_dim_2_landing_is_detectable",
    ),
    (
        "workflow-trace-capture",
        "workflow/test_slice.py::"
        "test_a_completion_that_skips_the_dim_5_landing_is_detectable",
    ),
)


# --- the registry itself ---------------------------------------------------


def _test_exists(reference: str) -> bool:
    module_path, _, function = reference.partition("::")
    source_path = TESTS_ROOT / module_path
    if not source_path.is_file():
        return False
    source = source_path.read_text(encoding="utf-8")
    return bool(
        re.search(rf"^def {re.escape(function)}\(", source, re.MULTILINE)
    )


def test_every_check_names_an_owning_test() -> None:
    """No entry may be unowned. That state is where a false green lives."""
    for check in CINV_04_CHECKS:
        assert check.owning_test, check.name


@pytest.mark.parametrize("check", CINV_04_CHECKS, ids=lambda check: check.name)
def test_an_active_check_points_at_a_test_that_exists(check: Check) -> None:
    """The registry is load-bearing only if its references resolve.

    A status table naming tests that were renamed away would report green about
    assertions nobody runs — which is exactly the failure mode this module
    exists to prevent, arriving through the back door.
    """
    assert _test_exists(check.owning_test), check.owning_test


@pytest.mark.parametrize(
    ("family", "reference"),
    ADVERSARIAL_CASES,
    ids=[family for family, _ in ADVERSARIAL_CASES],
)
def test_each_activated_family_carries_a_resolving_adversarial_case(
    family: str, reference: str
) -> None:
    """The I.4 activations guard the path, not just the happy case."""
    assert family in {check.name for check in CINV_04_CHECKS}
    assert _test_exists(reference), reference


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
