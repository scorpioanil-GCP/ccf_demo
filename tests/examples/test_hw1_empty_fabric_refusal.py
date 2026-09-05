"""HW-1 SERVES an empty fabric, identically over both shipped transports.

The negative test ``D-IMPL-245`` (2) keeps (Dave, 2026-09-03: *"seed it so the
normal example succeeds. Keep the empty-fabric refusal as a negative test."*).
The module keeps its name for the same reason it keeps its subject: the
unseeded copy is still the negative case, and transport parity on it is still a
conformance claim rather than a teaching experience — Dave's framing, verbatim:
*"a useful conformance test, but a poor primary teaching experience."*

What moved, and under which ruling
----------------------------------
``D-IMPL-253`` Q12 with ``D-IMPL-253`` Amendment 2 (2) and ``D-IMPL-255`` (2),
ledger row ``24.6-L-06``. Until ``24.6-05`` an operator that evaluated an empty
graph was refused on the *cardinality* of what it returned, and this module
asserted that refusal by name on both legs. Dave: *"An operator successfully
evaluating an empty graph did compute something. Calling it uncomputed
conflates absence of input with absence of execution."* So the answer is now
SERVED — exit 0, a content address, the same bytes on both legs — and the
emptiness travels on the served product as a finding
(``ccf.products.contract.ComputedEmptyFinding``) rather than as a refusal.

``D-IMPL-235`` (4): a test the fix flips is rewritten under the fix, never
deleted, and its sabotage stays. The superseded refusal token is therefore
written **once** in this module, on the sabotage's own input line, carried
under plan 12's sweep marker — and nowhere else, including here. The
supersession is named by ruling above rather than by token, because a module
docstring quoting a retired vocabulary word is how a retired word comes back.

What the parity claim is now
----------------------------
Both documented commands, run against the UNSEEDED copy, must exit 0, print a
content address, print no refusal at all, and print **byte-identical** stdout —
the same standard
:func:`~tests.examples.test_hw1_two_transports.parity_violations` holds the
seeded run to, because an empty answer is an answer and agreeing on it is the
same claim as agreeing on a full one.

Why this module still cannot reuse the sibling's comparison
-----------------------------------------------------------
:func:`~tests.examples.test_hw1_two_transports.run_leg` *asserts* exit 0 and
raises on anything else, so a leg that refused would reach this module as a
fixture error rather than as a named violation. This module keeps its own leg
runner — returning the exit code rather than asserting it — and its own
comparison, with its own controls, because a comparison nobody has watched fail
is decorative. The subject fixture, the command source, the invocation splitter
and the address regex ARE the sibling's: the copy shape is its ``example``
fixture, which is the unseeded copy this claim is about.
"""

from __future__ import annotations

import os
import pathlib
import re
import shlex
import subprocess
from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal

import yaml

from ccf.client.adapters.inprocess import InProcessAdapter
from ccf.client.codec import DecodedOutcome, decode_outcome
from ccf.client.wire import WireRequest
from ccf.products.gates import DEBT_TOLERANCE_PARAMETER

from tests.examples.test_client_example_purity import documented_commands
from tests.examples.test_hw1_two_transports import (
    ADDRESS as SERVED_ADDRESS,
)
from tests.examples.test_hw1_two_transports import (
    EXAMPLE_ROOT,
    REPO_ROOT,
    TIMEOUT_SECONDS,
    example,  # noqa: F401 — the UNSEEDED copy fixture, re-exported for pytest
    invocation,
)

#: The line ``consume.py`` prints for a question that matched no companies.
#: Read off the served branch's own f-string — ``{count} of {assembled}
#: assembled`` — and anchored at both ends, so a leg that answered a *different*
#: empty-ish thing is not a match.
EMPTY_ANSWER = re.compile(r"^\s*0 of 0 assembled$", re.MULTILINE)

#: Any refusal line at all. Kept ONLY as a needle the comparison and the
#: controls point at: a refusal on either leg is now a violation, so this
#: pattern names what must be absent rather than what must be present.
ANY_REFUSAL = re.compile(r"^refused: .*$", re.MULTILINE)

#: The flags the documented command spells, so the in-process legs below ask
#: the SAME question the subprocess legs asked rather than a question typed
#: here. The VALUES are never written down; they are read off the command.
THRESHOLD_FLAG = "--min-revenue"
AS_OF_FLAG = "--as-of"

#: ``F`` over an empty observation set: the multiplicative identity, for the
#: reason ``ccf.products.debt_scorer``'s reference scorer states — nothing was
#: observed, so nothing has decayed, and ``D_c = 1 − F·C·S`` is a product whose
#: identity element is one. An algebraic fact, not a figure about hw1's data;
#: ``C`` and ``S`` are read from the deployment's own document below.
FRESHNESS_OVER_NOTHING = Decimal(1)

#: The leading ``1`` of ``D_c = 1 − F·C·S`` (whitepaper §7.7, INV-CH7-62). The
#: arithmetic is done here rather than through the SDK's own
#: ``context_debt`` so the expectation is independent of the function under
#: observation.
_UNIT = Decimal(1)


def run_leg(command: str, *, example: pathlib.Path) -> tuple[int, str]:
    """Run one documented command against ``example``; return (rc, stdout).

    No return-code assertion here: which code is right is the comparison's
    business, so that a leg refusing on the empty copy is reported as a named
    violation rather than as a fixture error.
    """
    address, argv = invocation(command, example=example)
    completed = subprocess.run(
        argv,
        cwd=REPO_ROOT,
        env={**os.environ, "CCF_BINDING": address},
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
    )
    return completed.returncode, completed.stdout


def served_parity_violations(*, legs: Mapping[str, tuple[int, str]]) -> list[str]:
    """Every way a set of per-binding answers fails to be the same served answer.

    Five named classes: nothing was compared; a leg that did not exit 0; a leg
    that refused; a leg carrying no content address; and two legs whose stdout
    differs. Each is a distinct string so a control can name the one it
    expects, and every class is collected rather than short-circuited — a leg
    that both exited non-zero AND refused is two facts, and reporting one of
    them would let a sabotage look like a smaller failure than it is.
    """
    if len(legs) < 2:
        return [
            "fewer than two transports answered, so nothing was compared —"
            f" {sorted(legs)}"
        ]

    violations: list[str] = []
    for binding in sorted(legs):
        returncode, stdout = legs[binding]
        if returncode != 0:
            violations.append(
                f"`{binding}` exited {returncode}, not 0 — an empty fabric is"
                " SERVED computed-empty, and a served answer exits 0"
                f" (`D-IMPL-253` Q12):\n{stdout}"
            )
        refusal = ANY_REFUSAL.search(stdout)
        if refusal is not None:
            violations.append(
                f"`{binding}` refused with {refusal.group(0)!r} — an operator"
                " that evaluated an empty graph computed, so nothing about"
                " this copy is a governed no:\n" + stdout
            )
        if SERVED_ADDRESS.search(stdout) is None:
            violations.append(
                f"`{binding}` printed no content address, so its answer carries"
                f" nothing to agree about:\n{stdout}"
            )

    distinct = {stdout for _, stdout in legs.values()}
    if len(distinct) != 1:
        left, right = sorted(legs)
        violations.append(
            "the transports disagree.\n"
            f"--- {left} ---\n{legs[left][1]}\n"
            f"--- {right} ---\n{legs[right][1]}"
        )
    return violations


# ---------------------------------------------------------------------------
# Reading the copy in process: the same question, the served contract itself.
#
# `Result` exposes no accessor for the vessel and adding one is a client-surface
# change this row is fenced away from, so the adapter is driven directly through
# the one decoder — the idiom `tests/client/test_inprocess_adapter.py` already
# uses to read a served product's own fields.
# ---------------------------------------------------------------------------


def deployment_document(example: pathlib.Path, name: str) -> dict[str, object]:
    """One of the copy's own deployment documents, parsed."""
    text = (example / "deployment" / name).read_text(encoding="utf-8")
    document = yaml.safe_load(text)
    assert isinstance(document, dict), f"{name} did not parse to a mapping"
    return document


def documented_question(example: pathlib.Path) -> tuple[dict[str, object], datetime]:
    """The parameters and boundary the documented in-process command asks under.

    Read off the command rather than restated, so the in-process read below is
    about the *same* question the two subprocess legs asked. The parameter NAME
    comes from the deployment's own request contract — the single declared
    required argument — so nothing here spells hw1's vocabulary either.
    """
    in_process = documented_commands(EXAMPLE_ROOT)[0]
    tokens = shlex.split(in_process)
    assert THRESHOLD_FLAG in tokens, (
        f"the documented in-process command spells no `{THRESHOLD_FLAG}`, so"
        f" there is no threshold to ask under: {in_process!r}"
    )
    assert AS_OF_FLAG in tokens, (
        f"the documented in-process command spells no `{AS_OF_FLAG}`; without a"
        f" pinned boundary this read would drift with the clock: {in_process!r}"
    )
    threshold = int(tokens[tokens.index(THRESHOLD_FLAG) + 1])
    as_of = datetime.fromisoformat(tokens[tokens.index(AS_OF_FLAG) + 1])

    contract = deployment_document(example, "ccf_config.yaml")["request_contract"]
    assert isinstance(contract, dict)
    required = contract["arguments"]["required"]  # type: ignore[index]
    assert isinstance(required, list) and len(required) == 1, (
        "this read asks the class's one declared required argument; the"
        f" deployment declares {required!r}"
    )
    return {str(required[0]): threshold}, as_of


def serve_in_process(example: pathlib.Path) -> DecodedOutcome:
    """Ask the copy's deployment the documented question, in this process."""
    parameters, as_of = documented_question(example)
    product_class = deployment_document(example, "ccf_config.yaml")["product_class"]
    assert isinstance(product_class, dict)
    adapter = InProcessAdapter(str(example / "deployment"))
    request = WireRequest(
        product_id=str(product_class["schema_name"]),
        parameters=parameters,
        temporal_boundary=as_of,
    )
    return decode_outcome(adapter.ask(request), sent=request)


# ---------------------------------------------------------------------------
# The claims.
# ---------------------------------------------------------------------------


def test_both_documented_transports_serve_a_computed_empty_fabric(
    example: pathlib.Path,
) -> None:
    """``D-IMPL-253`` Q12. The unseeded copy, both legs, one set of bytes.

    The two transports agree on an empty answer exactly as the sibling module's
    seeded case has them agree on a full one: same exit, same address, same
    stdout.
    """
    legs = {
        shlex.split(command)[0].partition("=")[2]: run_leg(command, example=example)
        for command in documented_commands(EXAMPLE_ROOT)
    }
    violations = served_parity_violations(legs=legs)
    assert not violations, "\n".join(violations)

    (answer,) = {stdout for _, stdout in legs.values()}
    assert EMPTY_ANSWER.search(answer), (
        "the two legs agreed, but on something other than the empty answer —"
        " a copy that quietly acquired rows would satisfy parity while proving"
        f" nothing about an empty fabric:\n{answer}"
    )


def test_the_served_empty_product_carries_its_search_as_evidence(
    example: pathlib.Path,
) -> None:
    """``D-IMPL-255`` (2). The emptiness travels with what produced it.

    Read off the served contract itself, over the same unseeded copy the two
    legs ran against. The Debt is compared against the figure the deployment's
    OWN declared factors give — read from ``binding.yaml`` here rather than
    typed — so a scorer that replaced the retired cardinality branch with a
    different constant fails even where that constant happens to coincide.
    """
    decoded = serve_in_process(example)
    assert decoded.outcome.refusal is None, (
        "the unseeded copy was refused in process while both subprocess legs"
        f" served it: {decoded.outcome.refusal}"
    )
    vessel = decoded.vessel
    assert vessel is not None

    finding = vessel.computed_empty
    assert finding is not None, (
        "an empty answer was served with no record of the search behind it —"
        " the finding is what makes zero results legible as a search rather"
        " than as silence (24.6-L-06)"
    )
    assert finding.emptiness == "attested", (
        "the search behind the empty answer classified as"
        f" {finding.emptiness!r}: a query issued against a source attesting"
        " coverage is what `attested` means, and hw1's SQLite deployment does"
        " both"
    )
    assert finding.operators_returned_empty, (
        "the finding names no operator that returned empty, which the contract"
        " refuses at construction — so this assertion is a check that the"
        " finding describes THIS execution rather than a default"
    )
    assert finding.operators_returned_empty <= finding.operators_invoked
    assert finding.plan_id == vessel.plan_id

    declared = deployment_document(example, "binding.yaml")["debt"]
    assert isinstance(declared, dict)
    completeness = Decimal(str(declared["completeness"]))
    semantic_consistency = Decimal(str(declared["semantic_consistency"]))
    expected = _UNIT - (
        FRESHNESS_OVER_NOTHING * completeness * semantic_consistency
    )

    assert vessel.debt is not None, (
        "the served product carries no debt assessment, so there is no measured"
        " figure to hold to the declared factors"
    )
    assert vessel.debt.factors.freshness == FRESHNESS_OVER_NOTHING, (
        "freshness over an empty observation set is not the multiplicative"
        f" identity but {vessel.debt.factors.freshness} — the figure below"
        " would then be measuring something else"
    )
    assert vessel.debt.factors.completeness == completeness
    assert vessel.debt.factors.semantic_consistency == semantic_consistency
    assert vessel.debt.debt == expected, (
        f"the empty answer was assembled at D_c {vessel.debt.debt}, and the"
        f" deployment's declared C={completeness} and S={semantic_consistency}"
        f" over an empty observation set give {expected}. Cardinality never"
        " determines Context Debt (`D-IMPL-255` (2))"
    )


def test_no_tolerance_is_declared_so_no_shell(example: pathlib.Path) -> None:
    """``D-IMPL-253`` Amendment 2 (2). A shell needs a tolerance, and hw1 has none.

    Dave's amendment ends *"an applicable tolerance may subsequently cause a
    shell response"* — MAY, and only where one is declared. Both places a
    tolerance could be declared for this deployment are read, so this test
    reports which one acquired a value rather than only that the answer changed.
    """
    config = deployment_document(example, "ccf_config.yaml")
    product_class = config["product_class"]
    request_contract = config["request_contract"]
    assert isinstance(product_class, dict) and isinstance(request_contract, dict)

    assert "default_debt_tolerance" not in product_class, (
        "the product class now declares a default debt tolerance"
        f" ({product_class['default_debt_tolerance']!r}), so the served empty"
        " answer below may be a shell rather than the product — this test's"
        " subject moved"
    )
    properties = request_contract["arguments"]["properties"]  # type: ignore[index]
    assert DEBT_TOLERANCE_PARAMETER not in properties, (
        f"the request contract now declares `{DEBT_TOLERANCE_PARAMETER}`, so a"
        " caller can put a tolerance on the question and this deployment's"
        " empty answer is no longer unconditionally the product"
    )

    decoded = serve_in_process(example)
    assert decoded.outcome.refusal is None, (
        "no tolerance is declared anywhere in this deployment and the answer"
        f" was still refused: {decoded.outcome.refusal}"
    )
    assert decoded.vessel is not None


def test_the_two_transports_are_actually_different() -> None:
    """Non-vacuity. Two runs of one transport agreeing proves nothing."""
    schemes = {
        shlex.split(command)[0].partition("=")[2].partition(":")[0]
        for command in documented_commands(EXAMPLE_ROOT)
    }
    assert schemes == {"inprocess", "mcp+stdio"}, (
        "the example documents commands for"
        f" {sorted(schemes)}; the served-parity claim is about those two"
    )


# ---------------------------------------------------------------------------
# Controls. The comparison must be watched refusing, or it is decorative.
# ---------------------------------------------------------------------------

#: A served leg's stdout, for the controls that need one half to be healthy.
#: Not a captured run: a control's input is data it states, so that what makes
#: it fail is visible in the control itself.
_SERVED = "\n   0 of 0 assembled\n   content address    " + "a" * 64 + "\n"


def test_the_comparison_refuses_a_leg_that_refused() -> None:
    """A governed no on either leg is a violation, whatever its exit code.

    The planted refusal is a DIFFERENT kind from the one this row retired, on
    purpose: the comparison rejects refusals as a class, and a control spelling
    the retired token would be testing a string rather than the rule.
    """
    violations = served_parity_violations(
        legs={
            "inprocess:x": (0, _SERVED),
            "mcp+stdio:y": (0, "refused: tolerance-exceeded\n"),
        }
    )
    assert violations, "a refusing leg was reported as a served answer"
    assert any("refused with" in entry for entry in violations), violations


def test_the_comparison_refuses_two_legs_that_disagree() -> None:
    """A one-character divergence in the content address is a disagreement."""
    violations = served_parity_violations(
        legs={
            "inprocess:x": (0, _SERVED),
            "mcp+stdio:y": (0, _SERVED.replace("a" * 64, "b" + "a" * 63)),
        }
    )
    assert violations, "two different answers were reported as agreement"
    assert any("disagree" in entry for entry in violations), violations


def test_the_comparison_refuses_a_single_transport() -> None:
    """**Vacuity control.** One leg that served is not two legs that agreed."""
    violations = served_parity_violations(legs={"inprocess:x": (0, _SERVED)})
    assert violations, "one answer was reported as a parity result"
    assert any("nothing was compared" in entry for entry in violations), violations


def test_the_comparison_refuses_a_nonzero_exit() -> None:
    """A leg that printed the right bytes and exited 1 did not serve them."""
    violations = served_parity_violations(
        legs={"inprocess:x": (0, _SERVED), "mcp+stdio:y": (1, _SERVED)}
    )
    assert violations, "a leg that exited 1 was reported as a served answer"
    assert any("exited 1, not 0" in entry for entry in violations), violations


def test_the_comparison_refuses_a_leg_without_an_address() -> None:
    """**Vacuity control.** Two legs that printed nothing agreed on nothing."""
    violations = served_parity_violations(
        legs={"inprocess:x": (0, ""), "mcp+stdio:y": (0, "")}
    )
    assert violations, "two empty outputs were reported as agreement"
    assert any("no content address" in entry for entry in violations), violations


# ---------------------------------------------------------------------------
# Sabotage. `D-IMPL-235` (4): the flipped test keeps its sabotage, inverted.
#
# The SDK source is not copied and mutated here, because what this module
# observes is a pair of subprocess ANSWERS — so the sabotage lives on the
# comparison's INPUT, in the shape the retired behavior actually produced:
# exit 1 and the retired token. It is the mirror of the control this module
# carried in the other direction before `24.6-05`.
# ---------------------------------------------------------------------------


def test_sabotage_reverting_the_served_leg_to_a_refusal_is_red() -> None:
    """The retired behavior, fed to the shipped comparison, is reported by name.

    Both facts are asserted — the exit code AND the refusal — because a
    comparison that reported only the first would go green the day a leg
    refused while exiting 0, which is precisely the shape of a governed refusal
    reaching a consumer as a success.
    """
    reverted = (1, "refused: empty-operator-result\n")  # sweep-exempt: sabotage input
    violations = served_parity_violations(
        legs={"inprocess:x": (0, _SERVED), "mcp+stdio:y": reverted}
    )
    assert violations, (
        "the retired refusal was reported as a served answer — the comparison"
        " would pass on the behavior this row removed"
    )
    assert any("exited 1, not 0" in entry for entry in violations), violations
    assert any("refused with" in entry for entry in violations), violations
