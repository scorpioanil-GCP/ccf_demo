"""Legs 1 and 3 reach no model because they reach **no network at all**.

Criterion 6's default-path half, proven rather than asserted. `H-06` rules that
the default path is *"the harness invokes the registered tool"*, with no model.
The strongest available proof of that is not a claim that no model was called —
it is a process-global socket refusal the legs run *inside* and do not trip.
``mcp.client.stdio``'s ``stdio_client`` spawns its child over pipes and the
door serves over pipes, so a socket-refusing guard around either leg proves no
egress whatsoever, which is strictly stronger than "no model".

The technique is copied, deliberately, from
``archive/examples/03-harness-portability/legs/deterministic.py::install_no_model_guard``
— **copied and not imported**: that module is producer-side, imports all three
harness SDKs at module scope, and importing it here would couple this phase's
gate to an unrelated example's dependencies. Two of its disciplines are the
ones worth inheriting and both are held below: the guard is process-global and
installed before any leg runs, and it **carries its own non-vacuity control**,
because a guard nobody has watched refuse is a guard that may have stopped
patching anything and would report green forever.

Why the guard is a test and not part of the runner
--------------------------------------------------
The guard is process-global and the three clients are **child processes** of
``examples/hw1-harness-clients/runner/drive.py``. A runner cannot install a
socket guard inside a child's interpreter without the client importing
something — which would put non-harness clutter into programs whose whole claim
is how little they import (`H-11`, and the purity gate
``tests/examples/test_client_example_purity.py::reader_visible_modules``). So
the guard lives here and the two legs are driven **in-process**, by calling the
very same ``main`` coroutine their ``__main__`` block calls, with the very same
``argv`` the runner would have spawned them with.

**Leg 2 — `client_anthropic.py`, the Claude Agent SDK leg — is excluded from
this guard, by name, and this is the reason**
--------------------------------------------------------------------------
Its default path *deliberately opens a loopback TCP connection*. `H-07`
measured that ``claude_agent_sdk`` routes everything — including its own MCP
client — through the bundled ``claude`` CLI subprocess, so the leg's model
traffic is real HTTP to the copied model stand-in
``examples/hw1-harness-clients/runner/model_stub.py``, pointed at by
``ANTHROPIC_BASE_URL`` via
``examples/hw1-harness-clients/runner/model_stub.py::offline_cli_environment``.
A socket refusal is therefore the **wrong instrument** for leg 2: it would go
red on the one connection that leg is supposed to make, and a guard that fails
on declared, expected traffic measures the instrument rather than the subject.

What proves leg 2's determinism instead is the stand-in's own
fail-loud-on-drift-and-exhaustion behaviour — it declares its exchanges up
front, refuses a request that drifts from the declaration, refuses a request
past the end of it, and a passing run makes exactly the declared number of
requests. That is plan `20-04`'s controls, not this module's. An exclusion
stated is a scope boundary; an exclusion unstated is a hole, so
:func:`test_the_excluded_leg_and_its_alternative_proof_are_stated` gates this
paragraph's continued existence.

Every property takes its subject as a parameter
-----------------------------------------------
The discipline ``tests/client/test_surface.py`` states at length and this
module inherits: a control specified as *"doctor a copy and assert the test
fails"* proves nothing when the shipped assertion reads a fixed path instead of
the copy. So the ``--live`` properties below take a **parsed tree** and the
guard's controls exercise the **shipped** context manager; the shipped
assertions hand those same functions the real subjects.
"""

from __future__ import annotations

import ast
import asyncio
import contextlib
import importlib.util
import io
import json
import pathlib
import re
import socket
import sys
import tempfile
import types
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

#: The example this module guards, and the runner directory one level down —
#: down there precisely so the runner is not itself a reader-visible client
#: (`H-11`).
EXAMPLE_ROOT = REPO_ROOT / "examples" / "hw1-harness-clients"
RUNNER_DIR = EXAMPLE_ROOT / "runner"
RUNNER_PROGRAM = RUNNER_DIR / "drive.py"

#: The two legs driven inside the guard. Named here rather than discovered so
#: the split between guarded and excluded is a written decision; that the union
#: of the two still covers every discovered leg is itself asserted by
#: :func:`test_every_discovered_leg_is_guarded_or_excluded_by_name`, so a fourth
#: harness cannot join unmeasured.
GUARDED_LEGS: tuple[str, ...] = ("adk", "langgraph")

#: Leg 2, excluded — see the module docstring for the reason and for what
#: proves its determinism instead.
EXCLUDED_LEG = "anthropic"

#: The guard's refusal text. One constant, so a control cannot pass by matching
#: a message the guard no longer raises.
EGRESS_REFUSAL = (
    "a guarded hw1 harness leg attempted network egress; legs 1 and 3 must"
    " reach the door over pipes with no model and no socket at all (H-06)"
)

#: A host name that cannot resolve, by RFC 2606's reservation of ``.invalid``.
#: ``CONTROL 1`` needs a target whose *name resolution* would be the first thing
#: to happen, so that a half-installed guard is distinguishable from a whole
#: one; a literal IP address skips resolution entirely and hides the difference.
UNRESOLVABLE_HOST = "no-such-host.ccf-no-model-guard.invalid"

#: A served product's content address, as each client prints it on stdout. 64
#: hex characters because it is a sha256 over the product's canonical bytes.
CONTENT_ADDRESS_RE = re.compile(r"content address\s+([0-9a-f]{64})")

#: The runner's leg-driving function. Named once: a rename in the runner makes
#: :func:`driving_call_site_violations` report *zero* sites, which that function
#: refuses as vacuity rather than reporting as compliance.
LEG_DRIVING_FUNCTION = "drive_leg"

#: The flag `H-09` rules is the only live flag, and the prefix any second one
#: would have to start with to be caught.
LIVE_FLAG = "--live"
LIVE_FLAG_PREFIX = "--live"


# --- the guard, copied from example 03's technique ----------------------------


@contextmanager
def install_no_model_guard() -> Iterator[None]:
    """Fail the run if anything opens a socket (`H-06`).

    Patches the two module-level names an outbound connection can be made
    through and restores **both** in a ``finally``, including on failure.

    **Both patches earn their place, and ``CONTROL 1`` says how.**
    ``socket.socket.connect`` is what every connection eventually reaches, so
    it alone refuses every *connection*. ``socket.create_connection`` is
    patched as well because it resolves its target before it connects: without
    that second patch a hostname target would send a DNS query and only then be
    refused, which is egress.

    **The scoping is not cosmetic.** This guard runs inside ``pytest``, in a
    process that will go on to run every other test in ``tests/examples``. An
    unscoped patch would survive the drive and refuse egress for every later
    test in the same process — a failure reporting itself somewhere unrelated
    to its cause, which is precisely the defect class a guard exists to prevent
    rather than to cause. ``CONTROL 3`` watches the restore.
    """

    def refuse(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError(EGRESS_REFUSAL)

    connect = socket.socket.connect
    create_connection = socket.create_connection
    socket.socket.connect = refuse  # type: ignore[method-assign, assignment]
    socket.create_connection = refuse  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket.connect = connect  # type: ignore[method-assign]
        socket.create_connection = create_connection


# --- loading the example's programs without making them importable packages ---


def load_program(path: pathlib.Path, name: str) -> types.ModuleType:
    """Import one standalone example program by path, under ``name``.

    The example root is not a package and must not become one: `H-11` locks it
    to ``client_*.py``, and an ``__init__.py`` there would be a reader-visible
    module that teaches nothing.
    """
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"{path} could not be loaded as a module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_runner() -> types.ModuleType:
    """Load ``examples/hw1-harness-clients/runner/drive.py`` as a module.

    The runner does ``import model_stub`` as a sibling, relying on its own
    directory heading ``sys.path`` when it runs as a script. That is reproduced
    here for the duration of the load and **undone in a ``finally``**, so this
    module does not leave the example's runner directory on the path of every
    later test in the process.
    """
    sys.path.insert(0, str(RUNNER_DIR))
    try:
        return load_program(RUNNER_PROGRAM, "_hw1_no_model_drive")
    finally:
        with contextlib.suppress(ValueError):
            sys.path.remove(str(RUNNER_DIR))


def client_program(leg: str) -> pathlib.Path:
    """The client program a leg name denotes, by the runner's own convention."""
    return EXAMPLE_ROOT / f"client_{leg}.py"


def assert_guard_is_armed() -> None:
    """Prove, in situ, that the *enclosing* guard refuses — before a leg runs.

    ``CONTROL 1`` and ``CONTROL 2`` watch the guard fire in isolation. This is
    the same observation made **inside the very context the legs are driven
    in**, which is what stops the shipped assertion from passing over a guard
    that was never installed: a drive under a dead guard proves nothing about
    egress and looks identical to a drive under a live one.
    """
    try:
        socket.create_connection(("127.0.0.1", 1), timeout=1)
    except AssertionError as refusal:
        if str(refusal) != EGRESS_REFUSAL:  # pragma: no cover - defensive
            raise
        return
    except OSError as reached:  # pragma: no cover - the dead-guard case
        raise AssertionError(
            "the guard did not refuse, so the drive it wraps would prove"
            " nothing about egress"
        ) from reached
    raise AssertionError(  # pragma: no cover - nothing listens on port 1
        "port 1 accepted a connection; this arming check is void"
    )


def drive_in_process(
    leg: str, command: str, arguments: Sequence[str], question: str
) -> str:
    """Run one leg's ``main`` in **this** process and return its stdout.

    The three flags are the client's whole contract (`H-03`) and they are built
    here exactly as ``examples/hw1-harness-clients/runner/drive.py::drive_leg``
    builds them for its subprocess — the difference is the process, not the
    invocation.

    **stdout only.** Google ADK writes ``[EXPERIMENTAL]`` warnings and the
    spawned door logs to stderr, so a reader of both streams would be reading
    the harness's chatter as if it were the client's answer.
    """
    argv = [str(client_program(leg)), "--server-command", command]
    for argument in arguments:
        argv += ["--server-arg", argument]
    argv += ["--question-json", question]

    module = load_program(client_program(leg), f"_hw1_no_model_client_{leg}")
    captured = io.StringIO()
    original = sys.argv
    sys.argv = argv
    try:
        with contextlib.redirect_stdout(captured):
            code = asyncio.run(module.main())
    finally:
        sys.argv = original
    if code != 0:
        raise AssertionError(f"leg {leg!r} exited {code}\nstdout:\n{captured.getvalue()}")
    return captured.getvalue()


def content_address(leg: str, stdout: str) -> str:
    """The one content address ``stdout`` carries, or a loud failure."""
    found = CONTENT_ADDRESS_RE.search(stdout)
    if found is None:
        raise AssertionError(f"leg {leg!r} printed no content address\n{stdout}")
    return found.group(1)


# --- the shipped assertion: both legs, one guard, one address -----------------


def test_legs_one_and_three_reach_the_door_with_no_egress_at_all() -> None:
    """Drive `adk` and `langgraph` in-process inside one socket-refusing guard.

    Both run against seeded copies built by
    ``examples/hw1-harness-clients/runner/drive.py::seeded_subject``, are handed
    the door resolved by ``…::resolve_door`` and the question assembled by
    ``…::build_question``, and must print the **same** content address. The
    guard is armed in situ before either leg runs — a probe inside the same
    context the legs run in — so this assertion cannot pass with a dead guard
    even if ``CONTROL 1`` and ``CONTROL 2`` were themselves broken.
    """
    drive = load_runner()
    addresses: dict[str, str] = {}
    with tempfile.TemporaryDirectory(prefix="ccf-hw1-no-model-") as scratch:
        for leg in GUARDED_LEGS:
            # One seeded copy per leg, the discipline the runner already holds:
            # two server children over one graph would be a single-writer
            # refusal rather than a measurement.
            with drive.seeded_subject(pathlib.Path(scratch) / leg) as root:
                command, arguments = drive.resolve_door(root)
                question = json.dumps(drive.build_question(root, drive.AS_OF))
                with install_no_model_guard():
                    assert_guard_is_armed()
                    addresses[leg] = content_address(
                        leg, drive_in_process(leg, command, arguments, question)
                    )

    assert sorted(addresses) == sorted(GUARDED_LEGS), addresses
    assert len(set(addresses.values())) == 1, (
        "the guarded legs did not agree on one content address: " f"{addresses}"
    )


def test_the_guarded_client_programs_exist() -> None:
    """Non-vacuity for the module: a rename makes it red rather than empty."""
    missing = [
        str(client_program(leg))
        for leg in GUARDED_LEGS
        if not client_program(leg).is_file()
    ]
    assert missing == [], f"guarded client programs are gone: {missing}"


def test_every_discovered_leg_is_guarded_or_excluded_by_name() -> None:
    """A fourth harness cannot join this example unguarded and unmentioned.

    The leg set is taken from
    ``examples/hw1-harness-clients/runner/drive.py::known_legs`` — the tree —
    rather than from a list written here, so the moment a ``client_*.py``
    appears it is either inside :data:`GUARDED_LEGS` or named as an exclusion
    with a reason, and this test says which is missing.
    """
    discovered = set(load_runner().known_legs())
    accounted = set(GUARDED_LEGS) | {EXCLUDED_LEG}
    assert discovered == accounted, (
        "the discovered legs and the guarded-or-excluded legs disagree;"
        f" unaccounted: {sorted(discovered - accounted)},"
        f" stale: {sorted(accounted - discovered)}"
    )


def test_the_excluded_leg_and_its_alternative_proof_are_stated() -> None:
    """`CONTROL 0` of a different kind — the written exclusion is gated.

    Not numbered with the guard's controls because it measures prose rather
    than mechanism, but deleting the paragraph that scopes this module is a
    silent widening of its apparent claim, so the paragraph is held.
    """
    text = __doc__ or ""
    for required in (f"client_{EXCLUDED_LEG}.py", "leg 2", "model_stub", "H-07"):
        assert required in text, f"the module docstring no longer states {required!r}"


# --- CONTROL 1-3: the guard fires on each patched name, and restores ----------


def test_the_guard_refuses_before_a_name_is_even_resolved() -> None:
    """CONTROL 1 — the ``socket.create_connection`` patch, made falsifiable.

    **This control was rewritten because its obvious form could not be made to
    fail, and the finding is recorded here rather than quietly fixed.** The
    obvious form is ``socket.create_connection(("127.0.0.1", 1))`` inside the
    guard: it does refuse — but it refuses *even with the*
    ``socket.create_connection`` *patch removed*, because the standard
    library's own ``create_connection`` calls ``sock.connect(sa)``, which is the
    other patched name. Neutering half the guard left this module 13/13 green.
    A control that cannot distinguish a whole guard from half a guard measures
    neither.

    What the second patch actually buys is measurable, and it is what this
    control now measures: ``create_connection`` resolves the address **before**
    it connects, so with only ``connect`` patched a *hostname* target sends a
    DNS query — real egress — and then fails with ``gaierror`` rather than with
    the guard's refusal. Patching ``create_connection`` refuses first, so not
    even a name lookup leaves the process. That is what makes the module
    docstring's "no network at all" the literal claim it says it is.
    """
    with install_no_model_guard():
        try:
            socket.create_connection((UNRESOLVABLE_HOST, 80), timeout=1)
        except AssertionError as refusal:
            assert str(refusal) == EGRESS_REFUSAL
        except OSError as leaked:  # pragma: no cover - the half-guard case
            raise AssertionError(
                "`socket.create_connection` was not patched: the call reached"
                f" name resolution and failed with {type(leaked).__name__},"
                " so a DNS query left this process before anything refused"
            ) from leaked
        else:  # pragma: no cover - the failure this control exists to catch
            raise AssertionError("the guard did not refuse `create_connection`")


def test_the_guard_refuses_socket_connect() -> None:
    """CONTROL 2 — ``socket.socket.connect`` is refused too.

    Two names are patched and a control watching only one leaves the other's
    patch unmeasured; ``mcp``, ``httpx`` and ``anyio`` do not all reach the
    network through the same one.
    """
    with install_no_model_guard():
        with socket.socket() as probe:
            try:
                probe.connect(("127.0.0.1", 1))
            except AssertionError as refusal:
                assert str(refusal) == EGRESS_REFUSAL
            else:  # pragma: no cover - the failure this control exists to catch
                raise AssertionError("the guard did not refuse `socket.connect`")


def test_the_guard_restores_both_patched_names() -> None:
    """CONTROL 3 — after the context exits, the real stack answers again.

    A **real** refused connect, not an identity check on a function object: the
    property is that later tests in this process reach the network machinery
    they expect, and ``ConnectionRefusedError`` from a closed port is what that
    looks like. An ``AssertionError`` here would be the leaked patch.
    """
    with install_no_model_guard():
        pass
    for attempt in (
        lambda: socket.create_connection(("127.0.0.1", 1), timeout=1),
        lambda: socket.socket().connect(("127.0.0.1", 1)),
    ):
        try:
            attempt()
        except AssertionError:  # pragma: no cover - the leak this control catches
            raise AssertionError("the guard leaked: a patched name survived the context")
        except OSError:
            continue
        else:  # pragma: no cover - nothing should be listening on port 1
            raise AssertionError("port 1 accepted a connection; this control is void")


# --- `--live` is one flag with one meaning (H-09), as AST properties ----------


def runner_tree() -> ast.Module:
    """The runner's source, parsed. The subject every ``--live`` property takes."""
    return ast.parse(RUNNER_PROGRAM.read_text(encoding="utf-8"))


def live_flag_declarations(tree: ast.Module) -> tuple[str, ...]:
    """Every ``--live…`` flag ``tree`` declares to ``argparse``, in source order.

    Parsed, never grepped: a flag named in a docstring, a help string or a
    comment is not a code path, and a grep cannot tell those apart from a
    declaration.
    """
    found: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute) or node.func.attr != "add_argument":
            continue
        for argument in node.args:
            if (
                isinstance(argument, ast.Constant)
                and isinstance(argument.value, str)
                and argument.value.startswith(LIVE_FLAG_PREFIX)
            ):
                found.append(argument.value)
    return tuple(found)


def live_flag_violations(tree: ast.Module) -> list[str]:
    """`H-09`: exactly one live flag is declared, and it is ``--live``.

    Vacuity is a violation in its own right and comes first: a tree declaring
    **no** live flag would otherwise yield an empty finding set, and "found
    nothing wrong" would be indistinguishable from "criterion 6's opt-in does
    not exist".
    """
    declarations = live_flag_declarations(tree)
    if not declarations:
        return [
            f"no {LIVE_FLAG!r} flag is declared at all, so criterion 6's opt-in"
            " does not exist and a count over it would pass vacuously"
        ]
    violations: list[str] = []
    exact = [name for name in declarations if name == LIVE_FLAG]
    if len(exact) != 1:
        violations.append(
            f"{LIVE_FLAG!r} is declared {len(exact)} times; it must be declared"
            " exactly once"
        )
    extra = sorted({name for name in declarations if name != LIVE_FLAG})
    if extra:
        violations.append(
            f"a second live flag is declared: {extra}. `H-09` rejected"
            " `--live-deployment`/`--live-model` because two orthogonal flags"
            " are four combinations per harness of which CI runs one, leaving"
            " three paths documented and never run"
        )
    return violations


def live_branches(tree: ast.Module) -> list[ast.If | ast.IfExp]:
    """Every branch in ``tree`` whose condition consults the live value.

    Both spellings the runner can use: the parsed ``args.live`` attribute and
    the ``live`` keyword parameter it is threaded through as.
    """
    found: list[ast.If | ast.IfExp] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.If, ast.IfExp)):
            continue
        for inner in ast.walk(node.test):
            if isinstance(inner, ast.Attribute) and inner.attr == "live":
                found.append(node)
                break
            if isinstance(inner, ast.Name) and inner.id == "live":
                found.append(node)
                break
    return found


def driving_call_site_violations(tree: ast.Module, function_name: str) -> list[str]:
    """One leg-driving call site, and it does not sit inside a live branch.

    `H-09` rules ``--live`` selects the subject root and nothing else, so the
    code path that drives a leg is reached identically either way. A **second**
    driving call site inside ``if args.live:`` is exactly criterion 6's
    *documented but never run* failure mode, one level in.

    Zero call sites is a violation, not a pass: it means the function was
    renamed or removed and this property has stopped looking at anything.
    """
    sites = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == function_name
    ]
    if not sites:
        return [
            f"no call to {function_name!r} was found, so this property read"
            " nothing; the runner's leg-driving function was renamed or removed"
        ]
    violations: list[str] = []
    if len(sites) > 1:
        violations.append(
            f"{function_name!r} is called from {len(sites)} sites; one driving"
            " path is what makes the `--live` and default runs the same run"
        )
    guarded = {id(node) for branch in live_branches(tree) for node in ast.walk(branch)}
    inside = [node for node in sites if id(node) in guarded]
    if inside:
        violations.append(
            f"{len(inside)} call(s) to {function_name!r} sit inside a branch on"
            " the `--live` value, so a leg-driving path exists that CI never"
            " exercises"
        )
    return violations


def live_leg_coverage_violations(tree: ast.Module, legs: Sequence[str]) -> list[str]:
    """No discovered leg is filtered out of the live path.

    Asserted over the **discovered** leg set rather than a list written here,
    so a fourth harness cannot join unreachable. A leg name appearing inside a
    branch on the live value is the shape that would do it — ``if args.live and
    leg != "adk"`` and its relatives — and it is refused whatever it is doing
    there, because a live path that can name one leg can exclude it.

    Two vacuity guards, because this property has two ways to read nothing: an
    empty leg set, and a ``--live`` flag that is declared and never consulted.
    """
    if not legs:
        return [
            "no legs were discovered, so a coverage assertion over them would"
            " pass for a runner that drives nothing"
        ]
    branches = live_branches(tree)
    if not branches:
        return [
            "the live value is declared but never consulted in any branch, so"
            " either the flag does nothing or this property stopped finding it"
        ]
    violations: list[str] = []
    for branch in branches:
        named = sorted(
            {
                node.value
                for node in ast.walk(branch)
                if isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and node.value in set(legs)
            }
        )
        if named:
            violations.append(
                f"a branch on the `--live` value names leg(s) {named}; `H-09`"
                " rules `--live` is the choice of subject root and nothing"
                " else, so no leg may be reachable in one mode and not the"
                " other"
            )
    return violations


def test_the_runner_declares_exactly_one_live_flag() -> None:
    """`H-09`, shipped: one flag, one meaning."""
    violations = live_flag_violations(runner_tree())
    assert violations == [], "\n".join(violations)


def test_the_runner_has_one_leg_driving_call_site_outside_any_live_branch() -> None:
    """`H-09`, shipped: ``--live`` does not fork the path that drives a leg.

    No test in this module passes ``--live`` to anything. `H-09`'s live meaning
    is *point at a real populated deployment*, which CI does not have; the
    claim under test is structural.
    """
    violations = driving_call_site_violations(runner_tree(), LEG_DRIVING_FUNCTION)
    assert violations == [], "\n".join(violations)


def test_every_discovered_leg_is_reachable_under_live() -> None:
    """`H-09`, shipped: no leg is filtered out of the live path."""
    violations = live_leg_coverage_violations(runner_tree(), load_runner().known_legs())
    assert violations == [], "\n".join(violations)


# --- CONTROL 4-6: the `--live` properties, watched failing --------------------


def test_a_second_live_flag_is_a_violation() -> None:
    """CONTROL 4 — a tree declaring ``--live-model`` beside ``--live`` goes red.

    The doctored tree is handed to the SAME function the shipped assertion
    calls, so this control cannot pass by reading something else.
    """
    doctored = ast.parse(
        "parser.add_argument('--live', action='store_true')\n"
        "parser.add_argument('--live-model', action='store_true')\n"
    )
    violations = live_flag_violations(doctored)
    assert violations
    assert "--live-model" in violations[0]


def test_a_second_driving_call_site_inside_a_live_branch_is_a_violation() -> None:
    """CONTROL 5 — the forked path `H-09` rejects, scored."""
    doctored = ast.parse(
        "if args.live:\n"
        f"    {LEG_DRIVING_FUNCTION}(leg, root, as_of, environment)\n"
        "else:\n"
        f"    {LEG_DRIVING_FUNCTION}(leg, root, as_of, environment)\n"
    )
    violations = driving_call_site_violations(doctored, LEG_DRIVING_FUNCTION)
    assert len(violations) == 2, violations
    assert "2 sites" in violations[0]
    assert "never exercises" in violations[1]


def test_no_live_flag_at_all_is_a_violation_rather_than_an_empty_finding() -> None:
    """CONTROL 6 — vacuity is named, never reported as compliance.

    Without this the properties above would report a clean tree for a runner
    that had lost criterion 6's opt-in entirely.
    """
    doctored = ast.parse("parser.add_argument('--legs', default='adk')\n")
    assert live_flag_declarations(doctored) == ()
    violations = live_flag_violations(doctored)
    assert violations
    assert "does not exist" in violations[0]


def test_a_leg_named_inside_a_live_branch_is_a_violation() -> None:
    """CONTROL 7 — the coverage property, watched firing.

    Not in the plan's numbering; added because
    :func:`live_leg_coverage_violations` would otherwise be a property nobody
    has ever seen report anything, which is the same standing as a guard nobody
    has watched refuse. Both of its vacuity guards are exercised too — an empty
    leg set and a tree that never consults the live value — because a coverage
    assertion has two ways to read nothing.
    """
    filtered = ast.parse("if args.live and leg != 'adk':\n    continue\n")
    violations = live_leg_coverage_violations(filtered, ("adk", "langgraph"))
    assert violations
    assert "'adk'" in violations[0] or "adk" in violations[0]

    assert "no legs were discovered" in live_leg_coverage_violations(filtered, ())[0]

    unconsulted = ast.parse("if leg in LEGS_DRIVING_A_MODEL:\n    pass\n")
    violations = live_leg_coverage_violations(unconsulted, ("adk",))
    assert violations
    assert "never consulted" in violations[0]
