# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""E2 (ii) (d)'s trusted-code assumption: the false-declaration counterexample, kept visible, and its boundary, measured.

``D-IMPL-378``, Dave, 2026-10-08 16:40 MST, E2 (ii), option (d), verbatim:
*"Require a positive declaration, default silence to refusal, and explicitly
limit the trusted-code assumption to deployment code callers cannot influence.
Keep the false-declaration counterexample visible."*

A class affirming ``subject_withholding: never`` is built only over a plan
factory that positively declares, in its own code, that its projection never
withholds (``ccf.products.resolver.NonWithholdingPlanFactoryProtocol``). The SDK
cannot see inside a projection before running it, so the declaration is trusted
deployment code. **The counterexample test here PASSING means the
counterexample STILL HOLDS**: a factory whose declaration is false is built, and
its withheld subject's question is refused by the serve-time defense alone — an
exception (an HTTP 500 at the door) where a nonexistent subject's is answered.
It is the measured residual of a trusted-code assumption, not a control that
SEC-020 is closed. If the SDK ever closes it, this test goes red and the
counterexample is gone. The closing test also measures every cell of it on every
run, outside the gate
(``tests/products/test_sec020_combined_proof.py::test_e2ii_limitation_the_false_declaration_cells_are_measured_not_gated``).

The assumption is limited to deployment code no caller can influence, and
:func:`test_e2ii_d_no_caller_input_supplies_selects_or_alters_the_positive_declaration`
measures that limit — statically over ``src/`` and ``runtime/``, and dynamically
at the in-process, HTTP and MCP doors — with a control in which deployment code
lets a caller in.

Fixture vocabulary only (CINV-01).
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

import pytest

from tests.products import sec020_worlds as w

#: The serve-time defense Dave retained (E2 (ii), 2026-10-08 12:29 MST), by name.
SERVE_TIME_DEFENSE = "NeverWithholdingContradicted"


def _answered(door: str, observation: w.Observation) -> bool:
    """Whether the side's one question was answered: served in process, HTTP 200 at the door, and nothing raised."""
    if observation.raised.get(w.ONLY):
        return False
    response = observation.channels.get(w.RESPONSE)
    if not isinstance(response, dict):
        return False
    if door == w.HTTP:
        return response.get("status") == 200
    return response.get("outcome") == "served"


@pytest.mark.parametrize("door", [w.IN_PROCESS, w.HTTP])
@pytest.mark.parametrize("configuration", sorted(w.NEVER_FALSE_DECLARATION_CONFIGURATIONS))
def test_e2ii_d_counterexample_a_false_positive_declaration_still_tells_the_withheld_subject_apart(
    tmp_path: pathlib.Path, configuration: str, door: str
) -> None:
    """The counterexample Dave asked to keep visible, measured in process and at the HTTP door, plain and composite.

    A class affirming ``never`` over ``sec020_worlds.FalselyDeclaringPolicyPlanFactory``
    — it positively declares that it never withholds, and its projection
    withholds the restricted subject from the asker. Construction passes, because
    the declaration is trusted. Then the withheld subject's question raises
    ``NeverWithholdingContradicted`` by name (behind HTTP, a 500), while the same
    question to a deployment that does not hold the subject, and an identifier
    nothing holds asked of the withholding deployment, are answered. The control:
    the same deployment with the policy off — whose declaration is true — serves
    the subject, so the defense is the false declaration's, not a broken build.
    """
    observed: dict[str, w.Observation] = {}
    for name, holds, subject, capable in (
        ("withheld", True, w.SUBJECT, True),
        ("nonexistent", False, w.SUBJECT, True),
        ("never-held", True, w.NEVER, True),
        ("twin", True, w.SUBJECT, False),
    ):
        deployment = w.build_never(
            tmp_path / name, configuration=configuration, anchor=w.FROM_DECISION, holds=holds, capable=capable
        )
        try:
            observed[name] = w.observe_side(w.never_shape(configuration), door, deployment, subject)
        finally:
            deployment.close()
    summary: dict[str, Any] = {
        name: observation.raised.get(w.ONLY) or observation.channels.get(w.RESPONSE)
        for name, observation in observed.items()
    }
    assert _answered(door, observed["twin"]), f"control: the truly declaring twin did not serve the subject: {summary}"
    # The counterexample: the withheld subject meets the defense alone...
    assert observed["withheld"].raised.get(w.ONLY, "").startswith(f"{SERVE_TIME_DEFENSE}:"), (
        f"the counterexample no longer holds: the withheld subject was not refused by the serve-time defense: {summary}"
    )
    if door == w.HTTP:
        withheld_response = observed["withheld"].channels.get(w.RESPONSE)
        assert isinstance(withheld_response, dict) and withheld_response.get("status") == 500, summary
    # ...while a subject nothing holds is answered, in another deployment and in the same one.
    assert _answered(door, observed["nonexistent"]) and _answered(door, observed["never-held"]), (
        f"the counterexample no longer holds: a nonexistent subject was not answered: {summary}"
    )


# =============================================================================
# The boundary of the assumption: no caller input reaches the declaration
# =============================================================================

#: The repository root, for the static half (this module sits at tests/products/).
_ROOT = pathlib.Path(__file__).resolve().parents[2]

#: The construction refusal of a ``never`` class whose factory does not positively declare (E2 (ii) (d)), by name.
DECLARATION_REFUSAL = "NeverWithholdingNeedsAPositiveDeclaration"

#: A threshold value the positive control's deployment code reads off a caller's question.
_CALLER_VALUE = 999


def _call_sites(*names: str) -> list[tuple[str, str, str, int, tuple[str | None, ...]]]:
    """Every call of ``<x>.<name>(...)`` or ``<name>(...)`` in ``src/`` and ``runtime/``: (name, file, scope, #args, keywords)."""
    import ast  # noqa: PLC0415

    found: list[tuple[str, str, str, int, tuple[str | None, ...]]] = []

    class _Visitor(ast.NodeVisitor):
        def __init__(self, relative: str) -> None:
            self.relative, self.scope = relative, []

        def _scoped(self, node: Any) -> None:
            self.scope.append(node.name)
            self.generic_visit(node)
            self.scope.pop()

        visit_FunctionDef = visit_AsyncFunctionDef = visit_ClassDef = _scoped

        def visit_Call(self, node: ast.Call) -> None:
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else (func.id if isinstance(func, ast.Name) else None)
            if name in names:
                found.append((name, self.relative, ".".join(self.scope), len(node.args),
                              tuple(keyword.arg for keyword in node.keywords)))
            self.generic_visit(node)

    for top in ("src", "runtime"):
        for path in sorted((_ROOT / top).rglob("*.py")):
            _Visitor(str(path.relative_to(_ROOT))).visit(ast.parse(path.read_text(encoding="utf-8")))
    return found


class _RecordingDeclaration:
    """A deployment's factory, the policy OFF, that positively declares it never withholds — and records every read.

    The declaration is TRUE (the policy-off projection never sets the withheld
    signal). ``withholds_no_subject`` accepts anything so that, if any path
    handed it something, the record would show it rather than a TypeError
    hiding it.
    """

    def __init__(self) -> None:
        from tests.deployment.test_replay_binding import PRODUCT_CLASS  # noqa: PLC0415

        self._policy = w.PolicyPlanFactory(plan_id=PRODUCT_CLASS, asker=w.ASKER, active=False)
        self.reads: list[tuple[tuple[Any, ...], dict[str, Any], Any]] = []

    def __call__(self, *, required: tuple[str, ...], request: Any) -> Any:
        return self._policy(required=required, request=request)

    def _declared(self) -> Any:
        return True

    def withholds_no_subject(self, *handed: Any, **named: Any) -> Any:
        declared = self._declared()
        self.reads.append((handed, named, declared))
        return declared


class _ReadsTheCaller(_RecordingDeclaration):
    """The CONTROL: deployment code that lets a caller in — its declaration reads the last question it built a plan for."""

    def __init__(self) -> None:
        super().__init__()
        self.last_threshold: Any = None

    def __call__(self, *, required: tuple[str, ...], request: Any) -> Any:
        from tests.deployment.test_replay_binding import THRESHOLD_PARAMETER  # noqa: PLC0415

        self.last_threshold = request.parameters.get(THRESHOLD_PARAMETER)
        return super().__call__(required=required, request=request)

    def _declared(self) -> Any:
        return self.last_threshold != _CALLER_VALUE


def _kind(call: Any) -> str:
    """The outcome's type name, a refusal envelope's reason with it, or the raised exception's type name."""
    try:
        outcome = call()
    except Exception as raised:  # noqa: BLE001 — the observation
        return type(raised).__name__
    reason = getattr(outcome, "reason", None)
    return f"{type(outcome).__name__}:{reason}" if reason else type(outcome).__name__


def test_e2ii_d_no_caller_input_supplies_selects_or_alters_the_positive_declaration(tmp_path: pathlib.Path) -> None:
    """Dave's (d): *"explicitly limit the trusted-code assumption to deployment code callers cannot influence."*

    **Static (``src/`` and ``runtime/``, by AST).** The SDK reads the declaration
    in ONE place, with no argument:
    ``ccf.products.resolver._refuse_a_never_class_without_a_positive_declaration``,
    called once, from ``GovernedResolver.__post_init__``, on the resolver's own
    ``plan_factory`` — a constructor field; the resolver holds no question. A
    resolver is built only through ``build_governed_resolver``, from three
    places: the paved road's ``OpenedProduct.answer`` (the factory is the
    ``project`` the deployment opened the product with), the in-process client's
    ``_boot`` (the ``plan:`` reference of ``binding.yaml`` inside the deployment
    root it boots, whose Python the process then runs — threat ``T-17-19``,
    accepted as the deployment's own trust boundary) and the replay environment
    (the paved road's own arguments). The only dynamic loads are that reference
    and the graph backends' registry. No door (``runtime/``) builds a resolver or
    loads a factory, and no harness adapter names any of these.

    **Dynamic (the paved road, which builds a resolver per question).** A
    deployment's recording factory is read once per question, at the in-process
    door, over HTTP — with query parameters named like the declaration and a
    factory reference added — and over MCP, every time with nothing handed to
    it, and it returns its own value. A question whose parameters name the
    declaration or a factory is refused by the request contract
    (``undeclared-parameter``), and the read stays the factory's. A silent
    factory's class is refused at construction whatever such parameter the
    question carries. The wire model refuses a question naming either.

    **The control.** A deployment factory whose declaration reads a value off
    the caller's previous question (deployment code letting a caller in): the
    caller's value flips the declaration, and the next question is refused at
    construction — so this measure sees a caller's influence where deployment
    code creates it, which is exactly what the trusted-code assumption does not
    cover.
    """
    import dataclasses  # noqa: PLC0415

    from pydantic import ValidationError  # noqa: PLC0415

    from ccf.products.door import WireRequest  # noqa: PLC0415
    from ccf.products.resolver import GovernedResolver  # noqa: PLC0415
    from tests.deployment.test_replay_binding import PRODUCT_CLASS, THRESHOLD_PARAMETER  # noqa: PLC0415

    # --- static -------------------------------------------------------------------
    sites = _call_sites(
        "withholds_no_subject", "_refuse_a_never_class_without_a_positive_declaration", "GovernedResolver",
        "build_governed_resolver", "load_reference", "spec_from_file_location", "import_module", "__import__",
    )
    by_name: dict[str, list[tuple[str, str, int, tuple[str | None, ...]]]] = {}
    for name, relative, scope, args, keywords in sites:
        by_name.setdefault(name, []).append((relative, scope, args, keywords))
    resolver_py = "src/ccf/products/resolver.py"
    assert by_name.get("withholds_no_subject") == [
        (resolver_py, "_refuse_a_never_class_without_a_positive_declaration", 0, ())
    ], by_name.get("withholds_no_subject")
    assert by_name.get("_refuse_a_never_class_without_a_positive_declaration") == [
        (resolver_py, "GovernedResolver.__post_init__", 0, ("declaration", "plan_factory"))
    ], by_name.get("_refuse_a_never_class_without_a_positive_declaration")
    assert {(relative, scope) for relative, scope, _a, _k in by_name.get("GovernedResolver", [])} == {
        (resolver_py, "build_governed_resolver")
    }, by_name.get("GovernedResolver")
    assert {(relative, scope) for relative, scope, _a, _k in by_name.get("build_governed_resolver", [])} == {
        ("src/ccf/products/product.py", "OpenedProduct.answer"),
        ("src/ccf/client/adapters/inprocess.py", "_boot"),
        ("src/ccf/replay/environment.py", "RecordedEnvironment.__init__"),
    }, by_name.get("build_governed_resolver")
    assert {(relative, scope) for relative, scope, _a, _k in
            by_name.get("load_reference", []) + by_name.get("spec_from_file_location", [])
            + by_name.get("import_module", []) + by_name.get("__import__", [])} == {
        ("src/ccf/client/adapters/inprocess.py", "_boot"),
        ("src/ccf/client/adapters/binding_document.py", "load_reference"),
        ("src/ccf/graph/registry.py", "_load_builtin"),
    }, sites
    fields = {field.name: str(field.type) for field in dataclasses.fields(GovernedResolver)}
    assert "plan_factory" in fields and "request" not in fields, sorted(fields)
    assert not [name for name, kind in fields.items() if "ProductRequest" in kind], fields
    adapters = _ROOT / "runtime" / "ccf_runtime" / "adapters"
    named = {
        str(path.relative_to(_ROOT)) for path in adapters.rglob("*.py")
        for token in ("GovernedResolver", "build_governed_resolver", "open_product", "plan_factory",
                      "withholds_no_subject", "load_reference", "binding_document")
        if token in path.read_text(encoding="utf-8")
    }
    assert not named, f"a harness adapter names the resolver, a plan factory or its declaration: {sorted(named)}"

    # --- dynamic: what each door hands the declaration ------------------------------
    holding = {w.SUBJECT: w.subject_holding()}
    recording = _RecordingDeclaration()
    deployment = w.open_paved(
        tmp_path / "recording", anchor=w.FROM_DECISION, acquire=w.SubjectKeyedSource(holding), project=recording,
        never=True,
    )
    injected = {THRESHOLD_PARAMETER: 1000, "withholds_no_subject": False, "plan_factory": "module:attribute"}
    try:
        outcomes = {
            "in-process, the subject": _kind(lambda: deployment.ask(w.SUBJECT, None)),
            "in-process, an identifier nothing holds, another threshold": _kind(
                lambda: deployment.ask(w.NEVER, {THRESHOLD_PARAMETER: 5})
            ),
            "in-process, parameters naming the declaration and a factory": _kind(
                lambda: deployment.ask(w.SUBJECT, injected)
            ),
        }
        app = w.http_app(deployment)
        response = w.http_call(
            app, "GET", f"/product/{deployment.tenant}/{deployment.product_class}/{deployment.version}",
            token=w.ASKER_TOKEN,
            params={
                "subject": w.SUBJECT, "intent": w.INTENT, "freshness": w.FRESHNESS,
                "asked_at": w.asked_at().isoformat(), "parameters": json.dumps(w.default_parameters()),
                "withholds_no_subject": "false", "plan_factory": "module:attribute",
            },
        )
        outcomes["http, query naming the declaration and a factory"] = f"HTTP {response.status_code}"
        mcp = w.observe_side(w.SUBJECT_KEYED, w.MCP, deployment, w.SUBJECT, parameters=injected)
        refusal = mcp.channels.get(w.REFUSAL) or {}
        outcomes["mcp, parameters naming the declaration and a factory"] = (
            mcp.raised.get(w.ONLY) or f"{refusal.get('outcome')}:{refusal.get('reason')}"
        )
    finally:
        deployment.close()
    assert outcomes == {
        "in-process, the subject": "ServedProduct",
        "in-process, an identifier nothing holds, another threshold": "ServedProduct",
        "in-process, parameters naming the declaration and a factory": "RefusalEnvelope:undeclared-parameter",
        "http, query naming the declaration and a factory": "HTTP 200",
        "mcp, parameters naming the declaration and a factory": "refused:undeclared-parameter",
    }, outcomes
    assert len(recording.reads) == len(outcomes), f"not one read per question: {recording.reads}"
    assert all(handed == () and named == {} and declared is True for handed, named, declared in recording.reads), (
        f"a read of the declaration was handed something, or returned another value: {recording.reads}"
    )

    silent = w.open_paved(
        tmp_path / "silent", anchor=w.FROM_DECISION, acquire=w.SubjectKeyedSource(holding),
        project=w.SilentPolicyPlanFactory(plan_id=PRODUCT_CLASS, asker=w.ASKER, active=False), never=True,
    )
    try:
        silenced = {
            "valid": _kind(lambda: silent.ask(w.SUBJECT, None)),
            "claiming the declaration": _kind(
                lambda: silent.ask(w.SUBJECT, {THRESHOLD_PARAMETER: 1000, "withholds_no_subject": True})
            ),
        }
    finally:
        silent.close()
    assert silenced == {"valid": DECLARATION_REFUSAL, "claiming the declaration": DECLARATION_REFUSAL}, silenced

    for extra in ({"withholds_no_subject": True}, {"plan_factory": "module:attribute"}):
        with pytest.raises(ValidationError, match=next(iter(extra))):
            WireRequest.model_validate({"product_id": PRODUCT_CLASS, "parameters": {}, "temporal_boundary": None, **extra})

    # --- the control: deployment code that lets the caller in ------------------------
    control = _ReadsTheCaller()
    leaky = w.open_paved(
        tmp_path / "control", anchor=w.FROM_DECISION, acquire=w.SubjectKeyedSource(holding), project=control,
        never=True,
    )
    try:
        first = _kind(lambda: leaky.ask(w.SUBJECT, {THRESHOLD_PARAMETER: _CALLER_VALUE}))
        second = _kind(lambda: leaky.ask(w.SUBJECT, None))
    finally:
        leaky.close()
    assert (first, second) == ("ServedProduct", DECLARATION_REFUSAL), (
        f"control: a declaration reading the caller's value did not change with it ({first}, {second},"
        f" reads {control.reads}), so this measure could not see a caller's influence at all"
    )
    assert [declared for _h, _n, declared in control.reads] == [True, False], control.reads
