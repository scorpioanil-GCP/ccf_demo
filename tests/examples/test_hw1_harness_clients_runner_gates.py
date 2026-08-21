"""Standing sabotage controls for the four runner gates that carry Criteria 1-4.

`examples/hw1-harness-clients/runner/drive.py` holds the checks that decide
whether a harness leg actually did what this phase claims: that the declared
markers can carry a payload assertion at all, that a leg printed the Context
Product rather than merely its address, and that every leg agreed with the
reference on one content address.

**Why this module exists.** Those checks shipped with their controls run as
one-shot mutation probes, recorded as a RED->GREEN table in a plan SUMMARY.
Dave ruled (2026-08-21) that a probe recorded only in a SUMMARY does not
discharge `CLNT-12`:

    A control is something the suite can still run and that can still go red. A
    narrative measurement in a SUMMARY is evidence that someone looked once; it
    is not enforcement. [...] If the property is worth claiming, it gets a real
    control.

The close panel's B-3 named the gap and B-1 was its direct consequence: an
asymmetry between `marker_violations` (which compared whole WORDS) and
`observed_markers` (which matches raw SUBSTRINGS) let a row named `product`,
`text` or `ntex` be accepted as a payload marker and then be satisfied by
chrome alone — so an address-only leg passed the very check written to refuse
it. No standing control was positioned to see it.

Every gate below therefore appears twice: once driven with the real inputs it
sees on a default-path run, and once with the property deliberately broken and
the gate watched going red.
"""

from __future__ import annotations

import ast
import contextlib
import importlib.util
import json
import pathlib
import sys
import types

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE_DIR = REPO_ROOT / "examples" / "hw1-harness-clients"
RUNNER_DIR = EXAMPLE_DIR / "runner"
RUNNER_PROGRAM = RUNNER_DIR / "drive.py"

#: The three client programs whose printed literals the payload assertion greps.
#: `CONSOLE_VOCABULARY` must account for every one of them — B-1's root cause was
#: that it was assembled from the reference client and the runner only, and the
#: check reads the LEG's stdout.
CLIENT_PROGRAMS = ("client_adk.py", "client_anthropic.py", "client_langgraph.py")

#: A content address is 64 hex characters; the legs print one and nothing about
#: it is payload.
ADDRESS = "a" * 64


def load_runner() -> types.ModuleType:
    """Load the runner as a module, without leaving its directory on `sys.path`.

    The runner does `import model_stub` as a sibling, relying on its own
    directory heading `sys.path` when it runs as a script. Reproduced here for
    the duration of the load and undone in a `finally`, the same discipline
    `tests/examples/test_hw1_harness_clients_no_model.py::load_runner` holds.
    """
    sys.path.insert(0, str(RUNNER_DIR))
    try:
        spec = importlib.util.spec_from_file_location(
            "_hw1_runner_gates_drive", RUNNER_PROGRAM
        )
        assert spec is not None and spec.loader is not None, RUNNER_PROGRAM
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        with contextlib.suppress(ValueError):
            sys.path.remove(str(RUNNER_DIR))


@pytest.fixture(scope="module")
def drive() -> types.ModuleType:
    return load_runner()


def reference_stdout(*names: str) -> str:
    """What the reference client prints for rows carrying `names`."""
    rows = "".join(f"   {name:<30} 500\n" for name in names)
    return (
        f"\nQ: which companies have revenue over 1000000000?\n{rows}"
        f"\n   {len(names)} of 6 assembled\n   content address    {ADDRESS}\n"
    )


def leg_stdout(*names: str) -> str:
    """What a harness client prints: the address, the label, the product JSON."""
    product = json.dumps(
        {"companies": [{"name": name, "revenue": 500} for name in names]},
        indent=2,
        sort_keys=True,
    )
    return f"content address    {ADDRESS}\ncontext product\n{product}\n"


def address_only_stdout() -> str:
    """`CONTROL A`'s subject: a leg that printed its address and nothing else."""
    return f"content address    {ADDRESS}\ncontext product\n"


def printed_literals(source: str) -> list[str]:
    """Every string literal a `print(...)` call in `source` emits directly.

    Constant arguments and the constant parts of f-strings, which together are
    the CHROME a client contributes to stdout. The interpolated parts are
    payload — the content address, the product JSON — and are deliberately not
    collected: they are what the markers are supposed to match.
    """
    literals: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if not (isinstance(node, ast.Call) and getattr(node.func, "id", None) == "print"):
            continue
        for argument in node.args:
            if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                literals.append(argument.value)
            elif isinstance(argument, ast.JoinedStr):
                literals.extend(
                    value.value
                    for value in argument.values
                    if isinstance(value, ast.Constant) and isinstance(value.value, str)
                )
    return literals


# --- the shipped inputs pass -------------------------------------------------


def test_the_six_declared_names_are_accepted(drive: types.ModuleType) -> None:
    """Non-vacuity for every control below: the real markers are not refused.

    Without this, a `marker_violations` that refused everything would make each
    control below pass for the wrong reason.
    """
    names = drive.declared_markers(
        drive.declared_rows(
            drive.DECLARED_ROWS_DOCUMENT,
            {"reference": "reference", "name": "name", "revenue": "revenue"},
        ),
        {"reference": "reference", "name": "name", "revenue": "revenue"},
    )
    assert len(names) == 6, names
    assert drive.marker_violations(names, sorted(drive.CONSOLE_VOCABULARY)) == []


def test_a_leg_that_printed_the_product_passes_every_gate(
    drive: types.ModuleType,
) -> None:
    """The default-path shape: same names, same address, product printed."""
    names = ("Kestrelmark Industries", "Volanti Logistics")
    assert drive.payload_violations(
        reference_stdout(*names), leg_stdout(*names), list(names)
    ) == []
    assert drive.printed_product_violations(leg_stdout(*names)) == []
    assert drive.compare_addresses(ADDRESS, {"adk": ADDRESS, "langgraph": ADDRESS}) == []


# --- CONTROL 1-3: marker_violations, watched refusing ------------------------


@pytest.mark.parametrize("name", ["product", "text", "ntex", "Product", "CONTEXT"])
def test_control_1_a_marker_chrome_can_satisfy_is_refused(
    drive: types.ModuleType, name: str
) -> None:
    """CONTROL 1 — B-1's escape, as a standing control.

    Each of these is a substring of something the runner, the reference client
    or the three harness clients print themselves. Accepting any of them makes
    "stdout carries a declared company name" true of a run that printed no
    payload at all, which is exactly what `payload_violations` exists to refuse.
    `product` is the one that matters most: all three clients print the literal
    line `context product`, and the vocabulary originally omitted the word.
    """
    violations = drive.marker_violations(
        [name, "Volanti Logistics"], sorted(drive.CONSOLE_VOCABULARY)
    )
    assert violations, f"{name!r} was accepted as a payload marker"


def test_control_2_an_empty_marker_set_is_refused(drive: types.ModuleType) -> None:
    """CONTROL 2 — the vacuity floor. A search over no markers passes on anything."""
    assert drive.marker_violations([], sorted(drive.CONSOLE_VOCABULARY))


@pytest.mark.parametrize(
    ("names", "why"),
    [
        (["Ab", "Volanti Logistics"], "shorter than the minimum marker length"),
        (["dead beef", "Volanti Logistics"], "hex digits and spaces only"),
        (["Volanti", "Volanti Logistics"], "a substring of another marker"),
        (["Volanti Logistics", "Volanti Logistics"], "declared twice"),
    ],
)
def test_control_3_each_stated_marker_property_goes_red(
    drive: types.ModuleType, names: list[str], why: str
) -> None:
    """CONTROL 3 — the properties `scenario-rows.yaml` states, each watched firing."""
    assert drive.marker_violations(names, sorted(drive.CONSOLE_VOCABULARY)), why


# --- CONTROL 4-6: payload_violations, watched refusing -----------------------


def test_control_4_an_address_only_leg_is_refused(drive: types.ModuleType) -> None:
    """CONTROL 4 — `CONTROL A`'s subject, now a test rather than a SUMMARY row."""
    names = ("Kestrelmark Industries",)
    assert drive.payload_violations(
        reference_stdout(*names), address_only_stdout(), list(names)
    )


def test_control_5_a_truncating_leg_is_refused(drive: types.ModuleType) -> None:
    """CONTROL 5 — same address, fewer rows printed.

    The set comparison is the only thing that sees this: the leg printed *a*
    product, and an equal content address does not make it the same product.
    """
    assert drive.payload_violations(
        reference_stdout("Kestrelmark Industries", "Volanti Logistics"),
        leg_stdout("Kestrelmark Industries"),
        ["Kestrelmark Industries", "Volanti Logistics"],
    )


def test_control_6_an_empty_marker_list_cannot_reach_a_vacuous_pass(
    drive: types.ModuleType,
) -> None:
    """CONTROL 6 — the floor beneath CONTROL 2, reached by a direct caller."""
    assert drive.payload_violations(reference_stdout(), address_only_stdout(), [])


# --- CONTROL 7-8: printed_product_violations, the `--live` condition ---------


def test_control_7_the_live_condition_refuses_an_address_only_leg(
    drive: types.ModuleType,
) -> None:
    """CONTROL 7 — the check that carries Criteria 1-3 when no seed exists.

    Under `--live` the subject is an operator's own populated deployment, so the
    six seeded names are not in it. This is the gate that still refuses a client
    that printed its address and nothing else, with no vocabulary at all.
    """
    assert drive.printed_product_violations(address_only_stdout())


def test_control_8_the_live_condition_refuses_an_empty_product(
    drive: types.ModuleType,
) -> None:
    """CONTROL 8 — an address computed over nothing is not evidence of assembly."""
    assert drive.printed_product_violations(
        f"content address    {ADDRESS}\ncontext product\n{{}}\n"
    )


def test_the_live_condition_does_not_depend_on_the_seed(
    drive: types.ModuleType,
) -> None:
    """The CR-01 regression: a live leg printing rows nobody seeded still passes.

    This is the property whose absence made every `--live` leg fail. The names
    below appear in no declared document; the check must not care.
    """
    assert drive.printed_product_violations(leg_stdout("Nordvale Freight")) == []


# --- CONTROL 9: compare_addresses, watched refusing --------------------------


def test_control_9_a_diverging_leg_is_refused(drive: types.ModuleType) -> None:
    """CONTROL 9 — Criterion 4, watched failing."""
    assert drive.compare_addresses(ADDRESS, {"adk": ADDRESS, "langgraph": "b" * 64})


def test_control_9b_no_legs_is_not_a_silent_pass(drive: types.ModuleType) -> None:
    """CONTROL 9b — an agreement assertion over zero legs agrees vacuously."""
    assert drive.compare_addresses(ADDRESS, {})


# --- the mechanism that keeps B-1 from recurring -----------------------------


def test_the_console_vocabulary_covers_what_the_clients_print(
    drive: types.ModuleType,
) -> None:
    """Every word the three clients print as a literal is chrome the guard knows.

    B-1's root cause was not the matching asymmetry alone — it was that
    `CONSOLE_VOCABULARY` was assembled from `consume.py` and the runner while
    the check greps the LEG's stdout, so `product` was missing entirely. This
    turns "remember to include the clients' output" from a rule into a
    mechanism: add a printed word to a client and this goes red until the
    vocabulary accounts for it.
    """
    missing: dict[str, list[str]] = {}
    for program in CLIENT_PROGRAMS:
        source = (EXAMPLE_DIR / program).read_text(encoding="utf-8")
        printed = printed_literals(source)
        unknown = sorted(
            word
            for literal in printed
            for word in drive._words(literal)
            if len(word) >= drive.MINIMUM_MARKER_CHARS
            and word not in drive.CONSOLE_VOCABULARY
        )
        if unknown:
            missing[program] = unknown
    assert missing == {}, (
        "these words are printed by a client but absent from CONSOLE_VOCABULARY,"
        f" so a row named for one would be satisfied by chrome: {missing}"
    )


# --- the CR-01 end-to-end proof: --live against rows nobody declared ---------


ALTERNATE_ROWS = """\
semver: "1.0.0"
tenant_id: hw1-demo
observed_at: "2026-07-01T00:00:00+00:00"
companies:
  - reference: OP-0001
    name: Nordvale Freight
    revenue: 2100000000
  - reference: OP-0002
    name: Sablewood Optics
    revenue: 1300000000
  - reference: OP-0003
    name: Tarnhelm Provisions
    revenue: 640000000
"""


def test_live_drives_a_deployment_holding_rows_the_declared_document_never_names(
    tmp_path: pathlib.Path,
) -> None:
    """`--live` succeeds against an operator's OWN data. The CR-01 regression.

    This is the property whose absence made every `--live` target fail. The
    runner read the six payload markers from `runner/scenario-rows.yaml`
    unconditionally and asserted them against whatever subject `--live` pointed
    at — but `--live` points at a deployment an operator populated themselves,
    per `D-32` and this example's README. The six names could never appear, so
    the leg was refused, and the message blamed the client for printing "a
    content address rather than the Context Product" when it had printed the
    whole product.

    The proof has to be end-to-end rather than a unit call, because the defect
    was in the WIRING — every individual check was correct. So: seed a subject
    from a document declaring three companies that appear in no tracked file,
    restore the real declared document so nothing about it is in scope, point
    `--live` at the seeded deployment, and drive a real leg.
    """
    drive = load_runner()
    rows_document = tmp_path / "operator-rows.yaml"
    rows_document.write_text(ALTERNATE_ROWS, encoding="utf-8")

    declared = drive.DECLARED_ROWS_DOCUMENT
    drive.DECLARED_ROWS_DOCUMENT = rows_document
    try:
        with drive.seeded_subject(tmp_path / "operator") as root:
            # The declared document is out of scope from here on: a `--live` run
            # must not consult it, and restoring it before `main()` is what
            # makes that a measurement rather than an assumption.
            drive.DECLARED_ROWS_DOCUMENT = declared
            source_deployment = drive.SOURCE_DEPLOYMENT
            argv = sys.argv
            drive.SOURCE_DEPLOYMENT = root
            sys.argv = ["drive.py", "--live", "--legs", "adk"]
            try:
                assert drive.main() == 0
            finally:
                drive.SOURCE_DEPLOYMENT = source_deployment
                sys.argv = argv
    finally:
        drive.DECLARED_ROWS_DOCUMENT = declared
