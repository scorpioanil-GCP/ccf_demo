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

import ast
import importlib
import inspect
import re
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

import pytest

from ccf.replay.serve import CapabilityForgeryError, DeliveryCapability
from tests.invariants.test_mcp_role_separation import PRODUCT_DOOR_MODULES

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
#:
#: D-22 scope marking (Phase I.4 gate review): where an ``invariant``
#: sentence reads "every ... by construction (CLAUDE.md §n.n)", it is a
#: **quotation of the cited CLAUDE.md commitment**, not this suite's own
#: claim at that strength. The strength each check enforces is exactly its
#: ``owning_test`` (plus the adversarial cases below), each observed red
#: under a severed capture. For ``hitl-action-capture`` specifically: the
#: owning test drives the ApprovalGate slice end to end; the other three
#: primitives are covered compositionally — per-primitive byte-equality of
#: the produced ``hitl_actions_block`` against the canonical action record
#: (tests/hitl/) composed with the builder's verbatim-landing guarantee
#: (tests/replay/test_dimension_extensions.py) — not by a per-primitive
#: end-to-end replay drive.
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
    Check(
        name="debt-delivery",
        invariant=(
            "each of the three enumerated Context Product doors serializes the "
            "whole vessel, so no door can drop the Context Debt the vessel "
            "carries, and the debt a decision was made with lands on replay "
            "dimension 5 by construction (D-IMPL-100)"
        ),
        owning_test=(
            "invariants/test_replay_by_construction.py::"
            "test_no_enumerated_door_can_drop_the_debt_the_vessel_carries"
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
    (
        "debt-delivery",
        "invariants/test_replay_by_construction.py::"
        "test_a_door_that_serialized_around_the_vessel_would_be_detected",
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


# --- the debt-delivery leg (15.5-11, D-IMPL-100) ---------------------------
#
# Criterion 1 says "no delivery path exists that drops it", and a claim about
# delivery paths checked at one of them is the defect this phase exists to
# correct: its first plans covered two doors and missed the external front
# door. So this check ranges over `PRODUCT_DOOR_MODULES` — plan 15.5-06's
# enumeration, whose own companion test proves it exhaustive over `runtime/`'s
# product-serving handlers. There is one list of doors in this suite, and
# `test_this_module_declares_no_second_door_enumeration` is what keeps it one.

#: The two canonical serializers a door hands the vessel to.
_VESSEL_SERIALIZERS: frozenset[str] = frozenset(
    {"canonical_bytes", "canonical_response"}
)


def _serializes_the_whole_vessel(source: str) -> bool:
    """Whether ``source`` hands a served product's ``.product`` to a serializer.

    The detector both the owning test and its adversarial companion run, so
    the adversarial case exercises the *check* rather than a paraphrase of it.
    It looks for the one shape all three shipped doors have — a canonical
    serializer called on ``<something>.product`` — because that is what makes
    debt reach a consumer: the field is on the vessel, so a door that
    serializes the vessel carries it and a door that reaches around the vessel
    does not.
    """
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        function = node.func
        name = (
            function.id
            if isinstance(function, ast.Name)
            else function.attr
            if isinstance(function, ast.Attribute)
            else None
        )
        if name not in _VESSEL_SERIALIZERS:
            continue
        argument = node.args[0]
        if isinstance(argument, ast.Attribute) and argument.attr == "product":
            return True
    return False


@pytest.mark.parametrize("door", PRODUCT_DOOR_MODULES)
def test_no_enumerated_door_can_drop_the_debt_the_vessel_carries(
    door: str,
) -> None:
    """CINV-04's debt-delivery leg, at the strength the mechanism supports.

    Two assertions, and the conjunction is the whole claim. The vessel carries
    ``debt`` — so debt is inside the bytes rather than beside them — and every
    enumerated door serializes the *whole* vessel rather than picking fields
    off it. A door therefore cannot drop debt without ceasing to serve a
    Context Product at all.

    **The strength is deliberately not higher.** This does not claim that every
    product carries an assessment: ``debt`` is optional, because a product
    assembled without one must still be constructible and every product written
    before D-IMPL-100 was in exactly that posture. The claim is *carried debt
    cannot be dropped at a door*, which is what criterion 1 asks and what the
    shipped mechanism supports. The declined placement — debt as a third field
    on ``ServedProduct`` — would have failed this test at all three doors, since
    none of them reads ``servable.replay_ref``.
    """
    from ccf.products.contract import ContextProductContract

    assert "debt" in ContextProductContract.model_fields

    module = importlib.import_module(door)
    source = Path(inspect.getsourcefile(module) or "").read_text(encoding="utf-8")

    assert _serializes_the_whole_vessel(source), door


def test_a_door_that_serialized_around_the_vessel_would_be_detected() -> None:
    """The adversarial companion: the check guards the path, not the happy case.

    A door engineered to skip the debt landing — serializing the replay
    reference, or reaching past the vessel for the payload alone — is detected
    by the same predicate the owning test runs. A check with only a happy-path
    witness is the false green this registry exists to prevent.
    """
    assert not _serializes_the_whole_vessel(
        "def context_product(tenant, product_class, version):\n"
        "    servable = resolver.resolve(tenant=tenant)\n"
        "    return canonical_bytes(servable.replay_ref).decode('utf-8')\n"
    )
    assert not _serializes_the_whole_vessel(
        "def retrieve(request):\n"
        "    servable = resolver.resolve()\n"
        "    return canonical_response(servable.product.payload)\n"
    )
    # The control: the shape the three shipped doors actually have.
    assert _serializes_the_whole_vessel(
        "def context_product(tenant, product_class, version):\n"
        "    servable = resolver.resolve(tenant=tenant)\n"
        "    return canonical_bytes(servable.product).decode('utf-8')\n"
    )


def test_this_module_declares_no_second_door_enumeration() -> None:
    """One list of doors in the invariant suite, asserted on the source.

    Two lists are two answers to "how many doors are there", and this phase
    began because nobody had counted. The enumeration is
    ``tests/invariants/test_mcp_role_separation.py``'s, whose own companion
    test proves it exhaustive over ``runtime/``; this module imports it and
    names no door itself.
    """
    # Derived from the enumeration rather than written out, so this assertion
    # cannot match its own prefix literal — and so the runtime package name
    # appears nowhere in this module, which is the property being asserted.
    prefix = PRODUCT_DOOR_MODULES[0].split(".")[0] + "."
    source = Path(__file__).read_text(encoding="utf-8")
    door_literals = [
        node.value
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and node.value.startswith(prefix)
    ]

    assert not door_literals, door_literals
    assert len(PRODUCT_DOOR_MODULES) == len(set(PRODUCT_DOOR_MODULES))
