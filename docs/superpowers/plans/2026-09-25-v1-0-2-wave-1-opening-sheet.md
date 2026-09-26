# v1.0.2 Wave 1 — Declared, not assumed — Opening Sheet and Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the `SEC-001` residual (a recorded rejection can be routed down the approving branch), `SEC-007` (a blank identity mints a phantom node and false edges), the subject-shape root cause of `EX-01`/`EX-02` (no shape on `ProductRequest.subject` or on `type: string` parameters), and `SEC-029` (the `0.1.0` version literal lands in dimension 2 of every replay record) — with the bookkeeping the accepted spec assigns to wave 1 — as one panelled wave on top of `main`.

**Architecture:** Four disjoint mechanisms, each *a typed refusal by name at one site, interpreted from an artifact*: a verdict→target map on the workflow artifact enforced by the factory and the engine; value admissibility at the single identity mint site, converted to a governed refusal on the canonical path; a mechanism-grammar floor judged in `GovernedResolver.__call__` before the overridable seam plus a declared per-class grammar judged in `refuse_request`; and the release version single-sourced from the git tag with a gate that fails when they differ. None reads a clock; none changes a replay-record shape; the only artifact-schema change is `gate_routes` (a generation boundary) on `WorkflowDefinition`.

**Tech Stack:** Python 3.12, Pydantic 2 (`extra=forbid` contracts, `json_schema_extra={HASH_TRANSPARENT_KEY: …}` marks), pytest (+ Hypothesis for the stateful machine), setuptools ≥ 77 + `setuptools_scm` ≥ 8, the project's own lints (`make lint`: CINV-01..06 incl. the hash-transparent-key lint), `make schemas` / `make surface` regeneration, the codex + cursor + gemini panel on stdin.

**Spec:** `docs/superpowers/specs/2026-09-25-v1-0-2-security-remediation-design.md` (accepted at `cb319661`; `D-IMPL-356`). This sheet argues from §3 (wave 1), §0.1 (the locked rulings), §2 (standing rules), §8.3 (the estate-gated run) and §9 criteria 1–4. Executors read both.

## Global Constraints

- **The rulings are locked** (`D-IMPL-356`): A1 = (a) `gate_routes` on `WorkflowDefinition`; A2 = (a) `HASH_TRANSPARENT_KEY: False`, factory refuses an undeclared routed gate; A3 = (a) `decision` stays a double-entry that must equal the artifact's route; A4 = refuse when qualifying submissions carry more than one distinct verdict; A5 = gate branch only, the escalation sibling is a row. B1 = the widest refusal set (`None`, empty/whitespace, `bool`, `float`, `Mapping`, non-`str` `Sequence`, `bytes`); B2 = positional-string coercion for `int`/`Decimal` (every existing URI byte-identical); B3 = raise, and the SDK converts its own seam class by mechanism under cause `nonexistent` (amends `D-IMPL-347` B2 for SDK-raised seam classes only); B4 = omit a `None` attribute after measuring the population; B5 = dispose under the `D-IMPL-243` precedent. C1 = the SDK floor; C1a = `^[A-Za-z0-9][A-Za-z0-9:/._~@+=-]{0,511}$` (512 ASCII characters); C2 = judged in `GovernedResolver.__call__` beside `refuse_intent`, before the overridable `constraint_resolver` seam; C3 = every `type: string` parameter too; C4 = `ArgumentDomain.pattern` as a third exclusive shape + `ProductRequestContract.subject_domain` (amends `D-IMPL-264` D-03); C5 = both new fields hash-transparent `True`; C6 = `EX-01` regraded, `cp-16` named. `SEC-029` ships in this wave. Reopen one only on implementation evidence that directly contradicts the accepted design, and then stop for Dave.
- **No clock anywhere in this wave.** `grep -n 'datetime.now\|utcnow\|time.time' <changed files>` must be empty on the diff.
- **No values in `src/`:** `GATE_ACTIONS` is mechanism vocabulary; the floor grammar and its length are mechanism constants in the register of `CANONICAL_DECIMAL` (`src/ccf/products/request.py:1847`) and `MAX_REFERENCE_BYTES`; the SDK-owned seam class map holds the SDK's own exception only.
- **Examples are frozen** (`D-IMPL-261`, §0 L2): no file under `examples/` or `archive/` changes. A red example is a gap-ledger row.
- **"Nothing has shipped"** (§0 #4): the three migrated fixtures go to `schema_version: "2.0.0"`; nothing is deprecated in place; no historical record byte moves.
- **Every new marked field declares its key** (`HASH_TRANSPARENT_KEY: True|False`); the CINV-06 lint and `tests/contracts/test_hash_transparency.py::test_the_marked_fields_in_the_tree_are_exactly_the_ticked_table` are red by design until the ticked table names the field — the base roster `tools/lints/hash_transparent_base_roster.json` is never edited.
- **Red-when-fixed tests are rewritten, never deleted** (§2 rule 1). Their rewritten form is in Part IV.
- **Commit at deliverable boundaries** with the `D-IMPL-357` id in the message; branch `wave-1-357`, cut from `main` after `v1.0.2-spec` merges (docs only) — Dave's merge GO, not the executor's.
- **Three states, never two** (§2 rule 8): every count reported names `passed` / `failed` / `errors` / `skipped`.
- Run tests as `PYTHONPATH=src:runtime .venv/bin/python -m pytest …` from the repo root (the editable finder can otherwise import `main`'s tree in a worktree).

---

## Part I — Implementation boundaries

| In wave 1 | Out of wave 1 (where it lives) |
|---|---|
| `gate_routes` on `WorkflowDefinition` + local validators; factory coverage check; engine route compare **after** the declared-target check; conflicting-verdict refusal in `_gate_authority`; the three fixtures migrated to `2.0.0`; `docs/schemas/ccf.workflow-definition.json` regenerated | Removing `decision` from `resume` (A3(b), §7.4); the escalation sibling (`runtime/ccf_runtime/workflow/engine.py:1083-1087`, §7.4); a workflow-definition hash on the replay record (§7.4) |
| `IdentityRefused` at the single mint site; positional-string coercion; the `None`-attribute omission (after measurement); mechanism conversion on the canonical path (the `D-IMPL-347` B2 amendment); the `*_ref: True` rule note | L2 partial admission (one transaction per claim, §7.4); durable L2 refusal recording on the CDC/federated doors (§7.4); plugin strategies (declined) |
| `SUBJECT_FLOOR_V1` + `refuse_floor` judged in `__call__`; `ArgumentDomain.pattern`; `ProductRequestContract.subject_domain`; `_refuse_subject` inside `refuse_request`; schema render + disclosure; the `src/ccf/products/request.py:281-285` docstring; the read-only probe; the SDK door page's stdio disclosure | The stdio composition control (1.0.3, §7.3); `TemporalBoundRefusal` and every clock item (wave 2) |
| `setuptools_scm` single-sourcing; `tools/check_version_stamp.py`; a tag-triggered CI job; `SDK_DISTRIBUTION` untouched unless the PyPI rename lands (§3.4 item 3) | The tag text and the qualification recipe (release mechanics, §8) |
| `SEC353-G-09` ledger row; `D-IMPL-357` (wave record) and `D-IMPL-361` (adapters HIGH, the release condition, the 1.0.3 sheet) entries; surface fragment `357-01`; `make schemas`, `make surface`; the two published-page edits | Anything under `examples/`, `archive/`, waves 2–4 |

**The threat-model boundary this wave states in its entry:** the routes, the mint site and the floor are controls on the governed served surfaces (HTTP, MCP, the in-process door through `GovernedResolver.__call__`, and `WorkflowEngine.resume` through its capability); a direct in-process caller of `SpecDrivenEntityResolution.resolve` or of `refuse_request` is outside the model (`D-IMPL-354` ruling 1). The controls are nonetheless placed so that the in-process paths hit them too.

## Part II — Expected changed surfaces

| Surface | Change | Bookkeeping it forces |
|---|---|---|
| `src/ccf/workflow/definitions.py` | `gate_routes: Mapping[str, Mapping[str, str]]`, default `{}`, `{HASH_TRANSPARENT_KEY: False}`; one new model validator | `docs/schemas/ccf.workflow-definition.json` (`make schemas`); `tests/cli/test_schema_export.py:124/:130` red until then; the hash-transparency ticked table; fragment `357-01` |
| `src/ccf/workflow/factory.py` | routed `hitl-gate` steps must carry a complete map | none |
| `runtime/ccf_runtime/workflow/engine.py` | `_gate_authority` returns every qualifying submission; `resume` refuses on >1 distinct verdict and on `decision != route`; the D-IMPL-350 residual paragraph rewritten | `docs/surface/v0.2-surface.json` unchanged (private names) |
| `tests/fixtures/banking/workflows/covenant_review_workflow.yaml`, `payment_release_workflow.yaml`, `perf/synth/artifacts/workflow.yaml` | `gate_routes` + `schema_version: "2.0.0"` | every test that builds them goes green again |
| `src/ccf/assembly/worker.py` | `IdentityRefused` (public, in `__all__`), `_identity_text`, the attribute omission; rule docstring | fragment `357-01`; `make surface` |
| `src/ccf/products/resolver.py` | `SDK_SEAM_REFUSALS` and the mechanism branch in `_declared_seam_refusal`; `refuse_floor` judged after `refuse_intent` | fragment; `make surface` |
| `src/ccf/products/request.py` | `SUBJECT_FLOOR_V1`, `SUBJECT_FLOOR_VERSION`, `refuse_floor`, `_refuse_subject`; `ArgumentDomain.pattern`; `ProductRequestContract.subject_domain`; reason `malformed-value` appended last; docstring at `:281-285` | roster pin rewritten to 10; `docs/schemas/ccf.product-request-contract.json` (`make schemas`); ticked table; `make surface` |
| `src/ccf/products/request_schema.py` | `pattern` derived and refused-if-planted | `tests/products/test_request_schema_render.py:291` tuple |
| `pyproject.toml`, `.github/workflows/release-stamp.yml`, `tools/check_version_stamp.py`, `tests/test_version_stamp.py` | `dynamic = ["version"]` + `setuptools_scm`; the gate; a tag-triggered job | the venv is reinstalled (`pip install -e .`) so metadata carries the derived version |
| `docs/D-IMPL-353-EXAMPLES-GAP-LEDGER.md` | row `SEC353-G-09` | none |
| `docs/DECISIONS.md` | `D-IMPL-357`, `D-IMPL-361` | next free id `D-IMPL-362` stays reserved for the release record per the spec's §10 |
| `docs/surface-changes/357-01-declared-not-assumed.md` | the fragment claiming every new public name | `tests/test_surface_drift.py` green after `make surface` |
| `public/how-to/compose-a-workflow-with-hitl.md:138`; `public/reference/artifacts/workflow-definitions.md:18`; the page documenting `ProductDoor` (locate with `grep -rln 'serve_stdio' public/`) | the agreement clause; the dated pre-`gate_routes` note; the stdio single-identity disclosure | `make docs-strict` |
| `tools/probe_subject_floor.py` | read-only probe of every subject / string-parameter literal in the tree against the floor | its report is attached to the `D-IMPL-357` entry |

---

## Part III — Tasks

Lanes A (verdict→target), B (identity), C (subject shape) and D (version stamp) are independent and may run in four worktrees; lane E (bookkeeping) runs after A–D merge. Inside a lane the tasks are sequential.

### Task A1: `gate_routes` on `WorkflowDefinition`, validated locally

**Files:**
- Modify: `src/ccf/workflow/definitions.py:126-135` (the field block) and `:255-290` (add a validator after `_bindings_key_declared_nonterminal_nodes`)
- Test: `tests/workflow/test_definitions.py`

**Interfaces:**
- Consumes: `GATE_ACTIONS` (`src/ccf/hitl/approval_gate.py:114`, `frozenset({"approve", "reject"})`); `HASH_TRANSPARENT_KEY` (`ccf.contracts.canonical`).
- Produces: `WorkflowDefinition.gate_routes: Mapping[str, Mapping[str, str]]` (gate step name → verdict → declared target), default `{}`, marked `False`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/workflow/test_definitions.py  (append)
import pytest
from pydantic import ValidationError

from ccf.workflow.definitions import WorkflowDefinition


def _base(**overrides):
    document = {
        "schema_version": "2.0.0",
        "artifact_version": "1.0.0",
        "name": "w",
        "tenant": "acme-bank",
        "task_definition_ref": "ccf-artifact://acme-bank/ccf.task-definition/t@1.0.0",
        "start": "fetch",
        "transitions": [
            {"source": "fetch", "target": "gate"},
            {"source": "gate", "target": "approved"},
            {"source": "gate", "target": "rejected"},
        ],
        "terminal_states": ["approved", "rejected"],
        "gate_routes": {"gate": {"approve": "approved", "reject": "rejected"}},
    }
    document.update(overrides)
    return document


def test_gate_routes_maps_each_verdict_to_a_declared_target_from_that_gate() -> None:
    definition = WorkflowDefinition.model_validate(_base())
    assert definition.gate_routes["gate"]["reject"] == "rejected"


def test_a_route_to_a_target_not_declared_from_that_gate_is_refused() -> None:
    with pytest.raises(ValidationError, match="not a declared transition target from"):
        WorkflowDefinition.model_validate(
            _base(gate_routes={"gate": {"approve": "approved", "reject": "fetch"}})
        )


def test_a_verdict_outside_GATE_ACTIONS_is_refused() -> None:
    with pytest.raises(ValidationError, match="GATE_ACTIONS"):
        WorkflowDefinition.model_validate(
            _base(gate_routes={"gate": {"approve": "approved", "escalate": "rejected"}})
        )


def test_a_route_keyed_by_an_undeclared_node_is_refused() -> None:
    with pytest.raises(ValidationError, match="appear nowhere"):
        WorkflowDefinition.model_validate(
            _base(gate_routes={"phantom": {"approve": "approved"}})
        )


def test_gate_routes_is_a_generation_boundary_not_a_transparent_default() -> None:
    from ccf.contracts.canonical import HASH_TRANSPARENT_KEY

    field = WorkflowDefinition.model_fields["gate_routes"]
    assert (field.json_schema_extra or {}).get(HASH_TRANSPARENT_KEY) is False
```

- [ ] **Step 2: Run them to verify they fail**

Run: `PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/workflow/test_definitions.py -k gate_routes -v`
Expected: FAIL — `ValidationError: Extra inputs are not permitted` on `gate_routes` (the contract is `extra=forbid`).

- [ ] **Step 3: Add the field and the validator**

```python
# src/ccf/workflow/definitions.py — imports
from ccf.contracts.canonical import HASH_TRANSPARENT_KEY
from ccf.hitl.approval_gate import GATE_ACTIONS

# inside class WorkflowDefinition, after `gate_policies: Mapping[str, str] = {}`
    #: Per-gate verdict→target routing (D-IMPL-357 A1): which declared
    #: transition target each GATE_ACTIONS verdict may take from that gate.
    #: A GENERATION BOUNDARY (D-IMPL-351(a); D-IMPL-243 amendment 1): a
    #: document lacking it is of an earlier generation, and the factory
    #: refuses a routed gate that declares no complete map. Routing values,
    #: never code (CINV-01): the SDK supplies only the verdict vocabulary.
    gate_routes: Mapping[str, Mapping[str, str]] = Field(
        default={}, json_schema_extra={HASH_TRANSPARENT_KEY: False}
    )

    @model_validator(mode="after")
    def _routes_map_verdicts_onto_declared_targets(self) -> "WorkflowDefinition":
        declared = self._declared_nodes()
        outgoing: dict[str, set[str]] = {}
        for transition in self.transitions:
            outgoing.setdefault(transition.source, set()).add(transition.target)
        stray = sorted(set(self.gate_routes) - declared)
        if stray:
            raise ValueError(
                f"gate route key(s) {stray!r} appear nowhere in the wrapper's"
                " declared transition graph (D-IMPL-357 A1; CLAUDE.md §8.1)"
            )
        for gate, routes in sorted(self.gate_routes.items()):
            unknown = sorted(set(routes) - GATE_ACTIONS)
            if unknown:
                raise ValueError(
                    f"gate {gate!r} routes verdict(s) {unknown!r}, which are"
                    f" not in GATE_ACTIONS {sorted(GATE_ACTIONS)}; a route is"
                    " keyed by the gate's own verdict vocabulary (D-IMPL-357 A1)"
                )
            for verdict, target in sorted(routes.items()):
                if target not in outgoing.get(gate, set()):
                    raise ValueError(
                        f"gate {gate!r} routes verdict {verdict!r} to"
                        f" {target!r}, which is not a declared transition"
                        f" target from {gate!r}; a route names one of the"
                        " gate's own declared targets (D-IMPL-357 A1)"
                    )
        return self
```

Confirm no import cycle: `PYTHONPATH=src:runtime .venv/bin/python -c "import ccf.workflow.definitions"` must succeed. If `ccf.hitl.approval_gate` transitively imports `ccf.workflow`, move `GATE_ACTIONS` into a new leaf module `src/ccf/hitl/vocabulary.py` re-exported by `approval_gate` — and record that in the fragment.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/workflow/test_definitions.py -v`
Expected: PASS for the five new tests and every existing one.

- [ ] **Step 5: Regenerate the schema and re-run the drift gate**

Run: `make schemas && PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/cli/test_schema_export.py -q`
Expected: `docs/schemas/ccf.workflow-definition.json` gains `gate_routes` with `"ccf_hash_transparent": false`; the drift tests pass.

- [ ] **Step 6: Tick the hash-transparency table and commit**

Add `ccf.workflow.definitions.WorkflowDefinition.gate_routes` (marked `False`) to the ticked table `tests/contracts/test_hash_transparency.py` consumes (the table lives beside `:625`; follow the existing row form). Run: `PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/contracts/test_hash_transparency.py -q` → PASS. Then:

```bash
git add src/ccf/workflow/definitions.py tests/workflow/test_definitions.py docs/schemas/ccf.workflow-definition.json tests/contracts/test_hash_transparency.py
git commit -m "feat(357-A1): gate_routes on WorkflowDefinition — verdict→target as a generation boundary"
```

### Task A2: The factory refuses a routed gate without a complete map; the three fixtures migrate

**Files:**
- Modify: `src/ccf/workflow/factory.py:348-359` (inside the `gate_policies` loop's neighbourhood)
- Modify: `tests/fixtures/banking/workflows/covenant_review_workflow.yaml`, `tests/fixtures/banking/workflows/payment_release_workflow.yaml`, `perf/synth/artifacts/workflow.yaml`
- Test: `tests/workflow/test_factory.py`

**Interfaces:**
- Consumes: `WorkflowDefinition.gate_routes` (A1); `step_kinds` and `routable` computed at `src/ccf/workflow/factory.py:325-345`.
- Produces: `WorkflowConstructionError` for a routed `hitl-gate` step whose `gate_routes` entry does not cover every member of `GATE_ACTIONS`.

- [ ] **Step 1: Write the failing test**

```python
# tests/workflow/test_factory.py  (append; `_workflow_fixture`, `_construct` and the
# `registry` fixture with the covenant closure already exist in this module)
import pytest

from ccf.workflow.definitions import WorkflowDefinition
from ccf.workflow.factory import WorkflowConstructionError


def test_a_routed_gate_without_a_complete_route_map_is_refused_at_construction(
    registry, tmp_path
) -> None:
    """D-IMPL-357 A2: silence must not mean unconstrained. A gate the wrapper
    routes to must say where each verdict goes, or the workflow is not built."""
    document = _workflow_fixture()["workflow_definition"]      # the module's own loader
    definition = WorkflowDefinition.model_validate(
        {**document, "gate_routes": {"credit-officer-approval": {"approve": "approved"}}}
    )
    with pytest.raises(WorkflowConstructionError, match="does not route verdict"):
        _construct(registry, definition)   # tests/workflow/test_factory.py:138 — registers, then constructs
```

- [ ] **Step 2: Run it to verify it fails**

Run: `PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/workflow/test_factory.py -k complete_route_map -v`
Expected: FAIL — the workflow constructs (no refusal).

- [ ] **Step 3: Add the coverage check**

```python
# src/ccf/workflow/factory.py — after the gate_policies loop (~:359)
        # D-IMPL-357 A2 — every ROUTED hitl-gate step declares where each
        # verdict goes. Scoped to the nodes the wrapper routes to
        # (`routable`), the same population the phantom check above walks.
        for gate_name in routable:
            if step_kinds.get(gate_name) != "hitl-gate":
                continue
            missing = sorted(GATE_ACTIONS - set(definition.gate_routes.get(gate_name, {})))
            if missing:
                raise WorkflowConstructionError(
                    f"hitl-gate step {gate_name!r} does not route verdict(s)"
                    f" {missing!r}; a routed gate declares a target for every"
                    " GATE_ACTIONS verdict, because an undeclared route is"
                    " the route the engine must refuse, not guess"
                    " (D-IMPL-357 A2; D-IMPL-351(a); CLAUDE.md §6.4)"
                )
```
with `from ccf.hitl.approval_gate import GATE_ACTIONS` at the module head.

- [ ] **Step 4: Migrate the three fixtures**

```yaml
# tests/fixtures/banking/workflows/covenant_review_workflow.yaml
workflow_definition:
  schema_version: "2.0.0"      # was "1.0.0" — the gate_routes generation (D-IMPL-357)
  # … unchanged …
  gate_routes:
    credit-officer-approval:
      approve: approved
      reject: rejected
```
```yaml
# tests/fixtures/banking/workflows/payment_release_workflow.yaml
  schema_version: "2.0.0"
  gate_routes:
    treasury-approval:
      approve: released
      reject: rejected
```
```yaml
# perf/synth/artifacts/workflow.yaml
  schema_version: "2.0.0"
  gate_routes:
    panel-review:
      approve: accepted
      reject: declined
```

- [ ] **Step 5: Run the workflow suites**

Run: `PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/workflow tests/conformance/test_orchestration.py tests/http_api/test_routes.py tests/cli/test_cli.py -q -p no:randomly`
Expected: the new test PASSES; every previously green test is green again (the fixtures now carry the map); exactly two tests are RED — `tests/workflow/test_engine.py::test_a_rejection_authorizes_resumption_but_does_not_bind_the_target` is still green at this point (the engine does not compare yet), so expect **zero** reds here and record that the pin flips in A3.

- [ ] **Step 6: Commit**

```bash
git add src/ccf/workflow/factory.py tests/workflow/test_factory.py tests/fixtures/banking/workflows perf/synth/artifacts/workflow.yaml
git commit -m "feat(357-A2): the factory refuses a routed gate without a complete verdict map; fixtures to 2.0.0"
```

### Task A3: The engine holds the caller's `decision` to the artifact's route for the recorded verdict

**Files:**
- Modify: `runtime/ccf_runtime/workflow/engine.py:540-556` (after the declared-target check) and the `_gate_authority` docstring paragraph "Known residual (D-IMPL-350)" (`:1004-1013`)
- Test: `tests/workflow/test_engine.py:856-895` (rewrite), `tests/workflow/test_engine_stateful.py:169-195` (rewrite)

**Interfaces:**
- Consumes: `authority.action` (a `GATE_ACTIONS` member), `workflow.definition.gate_routes`, `self._refuse(authorized, workflow, *, execution_id, reason)`.
- Produces: a `WorkflowResumeRefused` whose `reason` names neither the verdict nor the expected target.

- [ ] **Step 1: Rewrite the pin so it asserts the closed residual**

```python
# tests/workflow/test_engine.py — replaces test_a_rejection_authorizes_resumption_but_does_not_bind_the_target
def test_a_recorded_rejection_cannot_be_routed_down_the_approving_branch(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """SEC-001 residual, CLOSED (D-IMPL-357 A3). The artifact declares where
    each verdict goes; the caller's decision must agree with it."""
    engine, transport, _ = _engine(registry, tmp_path)
    workflow = _covenant(registry)
    suspended = asyncio.run(engine.execute(execute_as(workflow), workflow, execution_id="exec-1"))
    assert isinstance(suspended, WorkflowSuspended)
    _resolve_gate(
        registry, transport,
        tenant=workflow.definition.tenant,
        event_key=suspended.event_key,
        action="reject", subject_id="officer-2",
    )
    refused = asyncio.run(
        engine.resume(resume_as(workflow), workflow, execution_id="exec-1", decision="approved")
    )
    assert isinstance(refused, WorkflowResumeRefused)
    assert "reject" not in refused.reason and "rejected" not in refused.reason
    resumed = [e for e in registry.audit_log.events() if e.action == "workflow_resumed"]
    assert resumed[-1].resolved is False and resumed[-1].actor is None
    # The gate is still open, and the declared route for the verdict works.
    completed = asyncio.run(
        engine.resume(resume_as(workflow), workflow, execution_id="exec-1", decision="rejected")
    )
    assert isinstance(completed, WorkflowCompleted)
    assert completed.terminal_state == "rejected"
```

```python
# tests/workflow/test_engine_stateful.py — the rule, rewritten to draw the VERDICT
    @precondition(lambda self: bool(self._keys_in("suspended")))
    @rule(data=st.data(), verdict=st.sampled_from(["approve", "reject"]))
    def resume_suspended(self, data: st.DataObject, verdict: str) -> None:
        key = data.draw(st.sampled_from(self._keys_in("suspended")))
        tenant, shape = self._shapes[key]
        workflow = self.workflows[(tenant, shape)]
        _resolve_gate(
            self.registry, self.transport, tenant=tenant,
            event_key=f"{key}/credit-officer-approval", action=verdict,
        )
        decision = workflow.definition.gate_routes["credit-officer-approval"][verdict]
        outcome = asyncio.run(
            self.engine.resume(
                resume_as(workflow), workflow,
                execution_id=key.split("/", 1)[1], decision=decision,
            )
        )
        assert isinstance(outcome, WorkflowCompleted)
        assert outcome.terminal_state == decision
        self.observed[key] = "terminal"
```

- [ ] **Step 2: Run them to verify the pin fails**

Run: `PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/workflow/test_engine.py::test_a_recorded_rejection_cannot_be_routed_down_the_approving_branch -v`
Expected: FAIL — `assert isinstance(refused, WorkflowResumeRefused)` (it is a `WorkflowCompleted`: the residual, visible one last time).

- [ ] **Step 3: Add the route compare, after the declared-target check**

```python
# runtime/ccf_runtime/workflow/engine.py — inside resume(), directly after the
# `if decision not in targets:` refusal (:542-553)
            route = workflow.definition.gate_routes.get(record.current_state, {}).get(
                authority.action
            )
            if route is None or decision != route:
                # D-IMPL-357 A3/A4: the artifact declares where the recorded
                # verdict goes; the caller's decision is a double-entry that
                # must agree. Names NEITHER the verdict nor the route (remedy 3:
                # the refusal never answers the caller's question for them).
                return self._refuse(
                    authorized,
                    workflow,
                    execution_id=execution_id,
                    reason=(
                        f"decision {decision!r} does not agree with the route"
                        " the workflow definition declares for the verdict"
                        " the HITL authority path recorded on"
                        f" {record.current_state!r}; routing is interpreted"
                        " from the artifact only (CINV-01; D-IMPL-357)"
                    ),
                )
```
Rewrite the `_gate_authority` docstring's "Known residual (D-IMPL-350)" paragraph to: *"The verdict→target binding: declared on the artifact as `gate_routes` (D-IMPL-357 A1) and enforced in `resume` after the declared-target check; the D-IMPL-350 residual is closed, pinned by `test_a_recorded_rejection_cannot_be_routed_down_the_approving_branch`."*

- [ ] **Step 4: Run the suites**

Run: `PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/workflow tests/http_api/test_routes.py -q -p no:randomly`
Expected: PASS, including `test_a_refused_gate_resume_does_not_enumerate_the_declared_targets` (:793), `test_workflow_resume_with_an_undeclared_decision_is_refused` (`tests/http_api/test_routes.py:631`, "declared transition" still in the reason because the new check is ordered after it) and the stateful machine.

- [ ] **Step 5: Commit**

```bash
git add runtime/ccf_runtime/workflow/engine.py tests/workflow/test_engine.py tests/workflow/test_engine_stateful.py
git commit -m "fix(357-A3): resume holds the caller's decision to the artifact's route for the recorded verdict — SEC-001 residual closed"
```

### Task A4: Conflicting verdicts on one suspension refuse

**Files:**
- Modify: `runtime/ccf_runtime/workflow/engine.py:931-1054` (`_gate_authority` returns every qualifying submission; `resume` refuses on more than one distinct verdict)
- Test: `tests/workflow/test_engine.py` (in-process, through the submit-only path) and `tests/http_api/test_routes.py` (through `POST /hitl/actions` twice)

**Interfaces:**
- Consumes: `HitlActionSubmission` (`src/ccf/hitl/transport.py:377`), `transport.submit(authorized, submission=…)`, `submit_capability(...)` and `_binding(hash, subject_id=…)` from the test modules.
- Produces: `_gate_authority(...) -> tuple[HitlActionSubmission, ...]`; `resume` refuses (typed, audited `resolved=False, actor=None`) when `{s.action for s in qualifying}` has more than one member.

- [ ] **Step 1: Write the failing tests**

```python
# tests/workflow/test_engine.py  (append)
from ccf.hitl.transport import HitlActionSubmission


def test_two_officers_conflicting_verdicts_on_one_suspension_refuse_to_route(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """D-IMPL-357 A4. The submit-only door records N submissions per event;
    once the verdict routes, first-writer-wins would let the order of arrival
    decide a bank approval. Two distinct verdicts refuse, naming neither."""
    engine, transport, _ = _engine(registry, tmp_path)
    workflow = _covenant(registry)
    suspended = asyncio.run(engine.execute(execute_as(workflow), workflow, execution_id="exec-1"))
    assert isinstance(suspended, WorkflowSuspended)
    tenant = workflow.definition.tenant
    pending = next(e for e in transport.pending(tenant=tenant) if e.event_key == suspended.event_key)
    for subject, action in (("officer-1", "reject"), ("officer-2", "approve")):
        transport.submit(
            submit_capability(tenant=tenant, principal=subject, event_key=suspended.event_key),
            submission=HitlActionSubmission(
                event_key=suspended.event_key,
                action=action,
                principal=_binding(pending.product_content_hash, subject_id=subject),
            ),
        )
    outcome = asyncio.run(
        engine.resume(resume_as(workflow), workflow, execution_id="exec-1", decision="approved")
    )
    assert isinstance(outcome, WorkflowResumeRefused)
    assert "conflicting" in outcome.reason
    assert "approve" not in outcome.reason and "reject" not in outcome.reason  # neither verdict named
```

```python
# tests/http_api/test_routes.py  (append; `_bound_submission` and `_suspend_over_http` exist)
def test_conflicting_verdicts_through_the_action_door_refuse_the_resumption(
    app: Any, fabric: Fabric
) -> None:
    key, version = fabric.covenant
    body = _suspend_over_http(app, fabric, "http-covenant-conflict")
    pending = next(e for e in fabric.hitl.pending(tenant=body["tenant"]) if e.event_key == body["event_key"])
    for action in ("reject", "approve"):
        submission = _bound_submission(body["event_key"])
        submission["product_content_hash"] = pending.product_content_hash
        submission["action"] = action
        assert call(app, "POST", "/hitl/actions", json=submission).status_code == 200
    response = call(
        app, "POST", "/workflow/resumptions",
        json={"definition_key": key, "definition_version": version,
              "execution_id": "http-covenant-conflict", "decision": "approved"},
    )
    assert response.status_code == 409
    assert "conflicting" in response.json()["reason"]
```
If `_bound_submission` fixes the approver subject, both submissions come from one principal; that is still two distinct verdicts and the test stands. If the door's principal must differ per call, use the two-token fixture the module already carries for "two-approver distinguishability (D-23)".

- [ ] **Step 2: Run them to verify they fail**

Run: `PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/workflow/test_engine.py::test_two_officers_conflicting_verdicts_on_one_suspension_refuse_to_route tests/http_api/test_routes.py::test_conflicting_verdicts_through_the_action_door_refuse_the_resumption -v`
Expected: FAIL — the first submission (`reject`) is taken by `next(...)`, the route compare refuses with the A3 reason (not "conflicting") or, if the test's first action is `approve`, the workflow completes.

- [ ] **Step 3: Return every qualifying submission; refuse on conflict**

```python
# runtime/ccf_runtime/workflow/engine.py — _gate_authority: replace `return next((…), None)` with
        return tuple(
            submission
            for submission in self._hitl_transport.submissions(tenant=tenant)
            if submission.event_key == event_key
            and submission.principal.product_content_hash == suspension
            and submission.action in GATE_ACTIONS
            and (
                submission.answered_event_class == GATE_EVENT_CLASS
                and submission.answered_workflow_state_ref == key
                if submission.answered_event_class is not None
                else gate_still_pending
            )
        )
```
(and its return annotation to `tuple[HitlActionSubmission, ...]`), then in `resume`:
```python
            qualifying = self._gate_authority(tenant=tenant, key=key, gate=record.current_state, record=record)
            if not qualifying:
                return self._refuse(...)   # the existing authority refusal, unchanged
            if len({submission.action for submission in qualifying}) > 1:
                # D-IMPL-357 A4: two distinct verdicts on one suspension. Names
                # neither verdict; an audit event carries the fact.
                return self._refuse(
                    authorized, workflow, execution_id=execution_id,
                    reason=(
                        f"execution {key!r} carries conflicting human verdicts"
                        f" on gate {record.current_state!r}; a gate routes on"
                        " one recorded verdict, and the authority path must"
                        " be reconciled by a human before it resumes"
                        " (D-IMPL-357 A4; CLAUDE.md §8.2)"
                    ),
                )
            authority = qualifying[0]
```
The conflict set is computed over every capability-qualified submission in 1.0.2 (spec §3.1 item 5); wave 3 narrows it to eligibility-filtered submissions.

- [ ] **Step 4: Run the suites**

Run: `PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/workflow tests/http_api/test_routes.py tests/conformance/test_orchestration.py -q -p no:randomly`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add runtime/ccf_runtime/workflow/engine.py tests/workflow/test_engine.py tests/http_api/test_routes.py
git commit -m "fix(357-A4): conflicting verdicts on one suspension refuse to route"
```

### Task A5: Published pages for the routing change

**Files:**
- Modify: `public/how-to/compose-a-workflow-with-hitl.md:138`; `public/reference/artifacts/workflow-definitions.md:18`

- [ ] **Step 1: Add the agreement clause** at `:138` after "the decision string names the route and never supplies the permission": *"— and, since `D-IMPL-357`, it must agree with the route the definition's `gate_routes` declares for the verdict the human recorded; a decision that names another declared target is refused without the refusal naming the verdict or the route."*
- [ ] **Step 2: Add the dated note** above the transclusion at `public/reference/artifacts/workflow-definitions.md:18`: *"(Pre-`gate_routes` shape, archived under `D-IMPL-351`: this document declares no verdict routes and would be refused by the factory since `D-IMPL-357`. The current shape is `tests/fixtures/banking/workflows/covenant_review_workflow.yaml`.)"*
- [ ] **Step 3: Build docs strict and commit**

Run: `make docs-strict` → exit 0.
```bash
git add public/how-to/compose-a-workflow-with-hitl.md public/reference/artifacts/workflow-definitions.md
git commit -m "docs(357-A5): the decision agrees with the declared route; the archived example is pre-gate_routes"
```

### Task B1: An identity component is admissible or refused, by name, at the single mint site

**Files:**
- Modify: `src/ccf/assembly/worker.py:59-70` (`__all__`), `:340-372` (`SpecDrivenEntityResolution.resolve`), a new `IdentityRefused` class and `_identity_text` helper beside the strategy
- Test: `tests/assembly/test_worker.py`

**Interfaces:**
- Consumes: `envelope(payload=…)` helper (`tests/assembly/test_worker.py:41`); `spec_fabric` fixture and `_positional_spec`/`_OWNS` (`:877-896` neighbourhood); `content_hash`.
- Produces: `class IdentityRefused(ValueError)` with attributes `envelope_id`, `entity_class`, `key`, `field`, `reason` (`reason ∈ {"null", "empty", "bool", "float", "non-scalar"}`); `_identity_text(value) -> tuple[str | None, str]` (the positional-string text, or `None` with the refusal reason).

- [ ] **Step 1: Write the failing tests**

```python
# tests/assembly/test_worker.py  (append)
from decimal import Decimal

import pytest

from ccf.assembly.worker import IdentityRefused


def _lei_rule() -> EntityResolutionSpec:
    return EntityResolutionSpec(
        semver="1.0.0",
        entity_rules=(
            EntityResolutionRule(match_key="lei", entity_class="company", identity_keys=("lei",)),
        ),
    )


@pytest.mark.parametrize(
    ("value", "reason"),
    [
        (None, "null"),
        ("", "empty"),
        ("   ", "empty"),
        (True, "bool"),
        (1.5, "float"),
        ({"lei": "x"}, "non-scalar"),
        (["x"], "non-scalar"),
        (b"x", "non-scalar"),
    ],
)
def test_an_inadmissible_identity_value_is_refused_by_name(value: object, reason: str) -> None:
    """D-IMPL-357 B1 (SEC-007): presence is not admissibility."""
    strategy = SpecDrivenEntityResolution(spec=_lei_rule())
    with pytest.raises(IdentityRefused) as caught:
        strategy.resolve(envelope=envelope(payload={"lei": value}))
    assert caught.value.reason == reason
    assert caught.value.key == "lei" and caught.value.entity_class == "company"


def test_int_and_decimal_identities_keep_their_positional_string_uris() -> None:
    """D-IMPL-357 B2 / D-IMPL-316: the coercion is what bare str() did, so no
    existing URI moves."""
    strategy = SpecDrivenEntityResolution(spec=_lei_rule())
    for value, text in ((7, "7"), (Decimal("1.50"), "1.50")):
        (resolved,) = strategy.resolve(envelope=envelope(payload={"lei": value}))
        assert resolved.entity_uri == f"company://{content_hash({'lei': text})}"


def test_two_null_identity_envelopes_mint_nothing_and_no_edge(
    spec_fabric: Callable[[EntityResolutionSpec], "FabricHandle"],
) -> None:
    """THE NEGATIVE CONTROL (SEC-007). Before B1, both envelopes minted ONE
    phantom node (`company://<hash of {"lei": "None"}>`) and the owns rule
    minted a real edge onto it. Re-enable bare str() and this reddens on both
    counts — the second assertion is the one that proves the false edge."""
    handle = spec_fabric(_positional_spec(remap=True, rules=(_OWNS,)))
    for envelope_id, payload in (
        ("e1", {"parent_lei": None, "lei": LEI}),
        ("e2", {"parent_lei": None, "lei": PARENT_LEI}),
    ):
        with pytest.raises(IdentityRefused):
            handle.worker.ingest(envelope(envelope_id=envelope_id, payload=payload))
    view = handle.reader.as_of(tenant_id=TENANT, at=INGESTED_AT)
    assert len(view.entities) == 0
    assert len(view.relationships) == 0
```
(Add `from ccf.contracts.canonical import content_hash` to the module; `LEI`, `PARENT_LEI`, `_positional_spec(*, remap, rules)` and `_OWNS` exist at `tests/assembly/test_worker.py:317-318`, `:765`, `:794`.)

- [ ] **Step 2: Run them to verify they fail**

Run: `PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/assembly/test_worker.py -k "inadmissible or positional_string or two_null" -v`
Expected: FAIL — `ImportError: cannot import name 'IdentityRefused'`.

- [ ] **Step 3: Implement the refusal and the coercion**

```python
# src/ccf/assembly/worker.py — beside SpecDrivenEntityResolution
from decimal import Decimal


class IdentityRefused(ValueError):
    """An identity component's value cannot name an entity (D-IMPL-357 B1; SEC-007).

    Raised, never swallowed, at the ONE mint site: a null, blank, boolean,
    float or non-scalar value would render through ``str()`` into a string
    every such record shares, minting one phantom node and, through the
    relationship rules, false edges onto it. The reason is named so an
    operator can tell which it was. Presence is checked before this
    (partial identity), admissibility here.
    """

    def __init__(self, *, envelope_id: str, entity_class: str, key: str, field: str, reason: str) -> None:
        self.envelope_id, self.entity_class, self.key, self.field, self.reason = (
            envelope_id, entity_class, key, field, reason
        )
        super().__init__(
            f"envelope {envelope_id!r} presents an inadmissible identity value"
            f" ({reason}) for {entity_class!r} key {key!r} read from payload"
            f" field {field!r}; the fabric refuses to mint a URI from a value"
            " that names no entity (D-IMPL-357 B1)"
        )


def _identity_text(value: object) -> tuple[str | None, str]:
    """The positional-string form of an admissible identity value, or the refusal reason.

    ``int`` and ``Decimal`` render exactly as ``str()`` rendered them before
    D-IMPL-357, so every URI minted from a numeric identifier is byte-identical
    (D-IMPL-316: the global hashing model is untouched); a ``str`` is taken as
    is — untrimmed, unfolded. ``bool`` is checked before ``int`` because it is
    an ``int``; ``float`` is refused here because ``str()`` ran before the
    canonical form's own float refusal and would have minted ``"1.5"``.
    """
    if value is None:
        return None, "null"
    if isinstance(value, bool):
        return None, "bool"
    if isinstance(value, float):
        return None, "float"
    if isinstance(value, str):
        return (value, "") if value.strip() else (None, "empty")
    if isinstance(value, int):
        return str(value), ""
    if isinstance(value, Decimal) and value.is_finite():
        return str(value), ""
    return None, "non-scalar"
```
and in `resolve`, replace the `identity = {key: str(payload[field]) …}` comprehension (`:361-363`) with:
```python
            identity: dict[str, str] = {}
            for key, field in source_of.items():
                text, reason = _identity_text(payload[field])
                if text is None:
                    raise IdentityRefused(
                        envelope_id=envelope.envelope_id, entity_class=rule.entity_class,
                        key=key, field=field, reason=reason,
                    )
                identity[key] = text
```
Add `"IdentityRefused"` to `__all__`. Add to `EntityResolutionRule`'s docstring: *"A `*_ref: True` presence-flag `match_key` (the SDK's own acquisition idiom) cannot also be an identity key: a boolean identity value is refused at the mint (D-IMPL-357 B1)."*

- [ ] **Step 4: Run the assembly suite**

Run: `PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/assembly -q -p no:randomly`
Expected: PASS; the existing `partial identity` test (`:201`) stays green (presence is still checked first).

- [ ] **Step 5: Commit**

```bash
git add src/ccf/assembly/worker.py tests/assembly/test_worker.py
git commit -m "fix(357-B1): an inadmissible identity value is refused by name at the mint site — SEC-007"
```

### Task B2: Measure the null-attribute population, then omit a `None` attribute

**Files:**
- Create: `tools/measure_null_attributes.py` (read-only)
- Modify: `src/ccf/assembly/worker.py:369` (the attribute comprehension)
- Test: `tests/assembly/test_worker.py`

- [ ] **Step 1: Measure** — the script walks `tests/fixtures/**/*.jsonl`, `tests/signal_layer/fixtures/*.json` and every `examples/**/deployment.py`/`acquisition.py` for `or ""` sites, and prints: fixture rows with a `null` under a declared `attribute_keys` name (by loading each `EntityResolutionSpec` found in `tests/fixtures/**/*.yaml`), plus the 95 `or ""` sites. Attach the printed table to the `D-IMPL-357` entry (B4). Expected from the recon: 0 fixture nulls on attribute keys; 95 sites in 32 files across 21 trees.
- [ ] **Step 2: Write the failing test**

```python
def test_a_null_attribute_is_absent_not_the_string_none() -> None:
    """D-IMPL-357 B4: absent-not-null (cp-01's own posture); PolicyFilter keys
    off attributes, and "None" is an answered value."""
    strategy = SpecDrivenEntityResolution(
        spec=EntityResolutionSpec(
            semver="1.0.0",
            entity_rules=(
                EntityResolutionRule(
                    match_key="lei", entity_class="company",
                    identity_keys=("lei",), attribute_keys=("jurisdiction",),
                ),
            ),
        )
    )
    (resolved,) = strategy.resolve(envelope=envelope(payload={"lei": "L1", "jurisdiction": None}))
    assert "jurisdiction" not in resolved.attributes
```
- [ ] **Step 3: Run to verify it fails** — Expected: FAIL, `resolved.attributes == {"jurisdiction": "None"}`.
- [ ] **Step 4: Implement** — at `:369`: `attributes={key: str(payload[key]) for key in rule.attribute_keys if key in payload and payload[key] is not None}` with a comment citing D-IMPL-357 B4.
- [ ] **Step 5: Run `tests/assembly` and the write-path suites** — `PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/assembly tests/products/test_paved_road.py tests/signal_layer -q -p no:randomly` → PASS (the measured population has no null attribute on a declared key).
- [ ] **Step 6: Commit** — `git commit -m "fix(357-B4): a null attribute is absent, not the string 'None'; population measured"` (include `tools/measure_null_attributes.py` and its output under `docs/superpowers/plans/evidence/357-B4-null-attributes.txt`).

### Task B3: The canonical path converts the SDK's own seam class by mechanism (the `D-IMPL-347` B2 amendment)

**Files:**
- Modify: `src/ccf/products/resolver.py:3197-3216` (`_declared_seam_refusal`) and a module constant beside it
- Test: `tests/products/test_d_impl_347_seam_refusals.py` (reuse `_write_tree`, `_open`, `_question`, `_config`, imported there from `tests.products.test_paved_road`, and the module's own `_seam_of`; the record is read as `opened.record_of(outcome)` at `:58`/`:219`)

**Interfaces:**
- Consumes: `SeamRefusalBinding` (`src/ccf/controlplane/artifacts.py:1305`), `RefusalCause` `"nonexistent"`, `IdentityRefused` (B1).
- Produces: `SDK_SEAM_REFUSALS: Mapping[str, SeamRefusalBinding]` = `{"ccf.assembly.worker.IdentityRefused": SeamRefusalBinding(exception=…, cause="nonexistent", error_code="identity-refused")}`; `_declared_seam_refusal` consults it before the class's declared map.

- [ ] **Step 1: Write the failing tests**

```python
# tests/products/test_d_impl_347_seam_refusals.py  (append)
from ccf.assembly.worker import IdentityRefused


def test_the_sdks_own_identity_refusal_is_a_governed_refusal_without_a_declaration(
    tmp_path: pathlib.Path,
) -> None:
    """D-IMPL-357 B3 — amends D-IMPL-347 B2 for SDK-raised seam classes only:
    the SDK knows what its own IdentityRefused means (a record naming no
    entity), so the paved road converts it under cause `nonexistent` even
    though no product class declares it. Before: an HTTP 500 with no record."""
    root = _write_tree(tmp_path / "b3", config=_config())   # declares NO seam_refusals
    scratch = tmp_path / "b3" / "scratch"

    def _null_identity(**_: Any) -> Any:
        raise IdentityRefused(
            envelope_id="env-null", entity_class="company", key="lei", field="lei", reason="null"
        )

    with _open(root, scratch, project=_null_identity) as opened:
        outcome = opened.answer(_question(opened))
        assert isinstance(outcome, RefusalEnvelope), outcome
        block = str(opened.record_of(outcome).content_generation_path.assembly_refusal)
        assert "identity-refused" in block and "nonexistent" in block


def test_a_deployment_cannot_widen_the_sdk_seam_map_and_its_own_undeclared_types_still_propagate(
    tmp_path: pathlib.Path,
) -> None:
    """The control that keeps the amendment narrow: only the SDK's own class
    converts by mechanism; `test_an_UNdeclared_domain_exception_still_propagates`
    above keeps proving the deployment half."""
    from ccf.products.resolver import SDK_SEAM_REFUSALS

    assert set(SDK_SEAM_REFUSALS) == {"ccf.assembly.worker.IdentityRefused"}
```
- [ ] **Step 2: Run to verify it fails** — Expected: the first test FAILS with `IdentityRefused` propagating out of `opened.answer(...)`; the second with `ImportError`.
- [ ] **Step 3: Implement**

```python
# src/ccf/products/resolver.py — module level, beside the seam helpers
#: D-IMPL-357 B3 (amends D-IMPL-347 B2 for SDK-RAISED seam classes only): the
#: seam exceptions the SDK itself raises and therefore knows the meaning of.
#: A deployment's own types stay declared-or-re-raised (B2); nothing here can
#: be widened from a declaration (`binder.refuse_seam_refusal_widening`).
SDK_SEAM_REFUSALS: Final[Mapping[str, SeamRefusalBinding]] = {
    "ccf.assembly.worker.IdentityRefused": SeamRefusalBinding(
        exception="ccf.assembly.worker.IdentityRefused",
        cause="nonexistent",
        error_code="identity-refused",
    ),
}
```
and in `_declared_seam_refusal`, before the declared loop: `if (mechanism := SDK_SEAM_REFUSALS.get(raised)) is not None: return mechanism`. Update the method docstring: exact type, never a subclass walk, still holds; the SDK map is consulted first because the SDK owns the meaning.
- [ ] **Step 4: Run** — `PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/products/test_d_impl_347_seam_refusals.py tests/deployment/test_binder.py -q` → PASS (the binder is untouched: the SDK class is not in any deployment map, so nothing is widened).
- [ ] **Step 5: Commit** — `git commit -m "fix(357-B3): the paved road converts the SDK's own IdentityRefused by mechanism — D-IMPL-347 B2 amended for SDK-raised seam classes"`.

### Task C1: The mechanism floor — `SUBJECT_FLOOR_V1` and `refuse_floor`

**Files:**
- Modify: `src/ccf/products/request.py:232-242` (append the reason), `:1847` neighbourhood (the constants), a new `refuse_floor` beside `refuse_intent` (`:2009`)
- Test: `tests/products/test_request_contract.py:1011-1016` (roster pin rewrite) and new tests

**Interfaces:**
- Consumes: `ProductRequestViolation` (`src/ccf/products/request.py:1503`), `ProductRequestContract.arguments.properties` (`SkillArgumentProperty.type`).
- Produces: `SUBJECT_FLOOR_V1 = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:/._~@+=-]{0,511}$")`, `SUBJECT_FLOOR_VERSION: Final[str] = "SUBJECT_FLOOR_V1"`, `refuse_floor(*, request, declared) -> ProductRequestViolation | None` (subject first, then every declared `type: "string"` parameter in sorted order), reason `"malformed-value"` appended **last** to `ProductRequestViolationReason`.

- [ ] **Step 1: Rewrite the roster pin and write the failing tests**

```python
# tests/products/test_request_contract.py — replaces test_the_reason_vocabulary_has_nine_members_…
def test_the_reason_vocabulary_has_ten_members_and_malformed_value_is_last() -> None:
    import typing
    from ccf.products.request import ProductRequestViolationReason
    members = typing.get_args(ProductRequestViolationReason)
    assert len(members) == 10
    assert members[-6] == "not-supported-at-tier"
    assert members[-5] == "not-a-proportion"
    assert members[-4:-2] == ("below-minimum", "above-maximum")
    assert members[-2] == "not-in-domain"
    assert members[-1] == "malformed-value"          # D-IMPL-357 C1, appended LAST


@pytest.mark.parametrize(
    "subject",
    ['x"y', "o'brien", "a b", "a\tb", "50%", "a;b", "a#b", "<x>", "", "é", "x" * 513],
)
def test_a_subject_outside_the_floor_is_a_malformed_value(subject: str) -> None:
    from ccf.products.request import SUBJECT_FLOOR_VERSION, refuse_floor
    violation = refuse_floor(request=_request(subject=subject), declared=_contract())
    assert violation is not None and violation.reason == "malformed-value"
    assert violation.key == "subject" and SUBJECT_FLOOR_VERSION in violation.detail


@pytest.mark.parametrize(
    "subject",
    ["5493001KJTIIGC8Y1R12", "urn:fixture:a/b", "http://example.org/fibo/GammaBank",
     "ALT-999999", "fixture:subject/one", "x" * 512],
)
def test_every_measured_subject_form_passes_the_floor(subject: str) -> None:
    from ccf.products.request import refuse_floor
    assert refuse_floor(request=_request(subject=subject), declared=_contract()) is None


def test_a_declared_string_parameter_is_held_to_the_floor_too() -> None:
    """C3: the floor closes the PARAMETER splices (cp-04-canonical `lei`), not only the subject."""
    from ccf.products.request import refuse_floor
    contract = _contract(arguments={"properties": {"lei": {"type": "string"}}})   # the module's _contract(**overrides), :145
    violation = refuse_floor(
        request=_request(parameters={"lei": 'x" . ?s ?p ?o . "'}), declared=contract
    )
    assert violation is not None and violation.key == "lei" and violation.reason == "malformed-value"
```
(`_request(**overrides)` and `_contract(**overrides)` are the module's builders at `tests/products/test_request_contract.py:156` and `:145`; the `arguments` override takes the same shape the module's `argument_domains` tests pass.)

- [ ] **Step 2: Run to verify they fail** — Expected: `ImportError: cannot import name 'refuse_floor'`; the roster pin fails at `len(members) == 10`.
- [ ] **Step 3: Implement**

```python
# src/ccf/products/request.py — the roster
ProductRequestViolationReason = Literal[
    "undeclared-parameter", "missing-required-parameter", "type-mismatch", "class-mismatch",
    "not-supported-at-tier", "not-a-proportion", "below-minimum", "above-maximum",
    "not-in-domain",
    "malformed-value",   # D-IMPL-357 C1 — appended LAST, never inserted
]

#: The mechanism floor (D-IMPL-357 C1/C1a; SEC-002/EX-01/EX-02 root cause). What
#: the fabric can place in a URL path segment (whitepaper §6.3's
#: `{counterparty-id}` slot), a SPARQL IRI position and a quoted literal:
#: 512 ASCII characters from an ALLOWLIST. Not a denylist — a denylist that
#: admitted `'` would leave a single-quoted literal splice open. In the same
#: register as CANONICAL_DECIMAL and MAX_REFERENCE_BYTES: a grammar the
#: mechanism owns, not a domain value. Versioned by name; a change is a new
#: name, and the name rides on every refusal it decides (`detail`).
SUBJECT_FLOOR_V1: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:/._~@+=-]{0,511}$")
SUBJECT_FLOOR_VERSION: Final[str] = "SUBJECT_FLOOR_V1"


def refuse_floor(
    *, request: ProductRequest, declared: ProductRequestContract
) -> ProductRequestViolation | None:
    """Does the subject, and every declared string parameter, lie inside the floor?

    Judged by `GovernedResolver.__call__` beside `refuse_intent` and BEFORE the
    overridable constraint-resolver seam (D-IMPL-357 C2), so no
    `PolicyConstraintResolver` override can remove it and no request reaches
    the acquisition seam carrying text the seam might splice. Pure: no clock,
    no registry, no I/O. Subject first, then declared `string` parameters in
    sorted order, so the first verdict is the same verdict on every run.
    A declared `subject_domain` / `pattern` (C4) is judged AFTER this, inside
    `refuse_request`, and cannot widen past it by construction.
    """
    def _violation(key: str, presented: object) -> ProductRequestViolation:
        return ProductRequestViolation(
            reason="malformed-value",
            key=key,
            declared_type="string",
            presented_type=type(presented).__name__,
            declared_keys=frozenset(declared.arguments.properties),
            presented_keys=frozenset(request.parameters),
            detail=(
                f"{key}: the presented text lies outside the fabric's identifier"
                f" floor {SUBJECT_FLOOR_VERSION} ({SUBJECT_FLOOR_V1.pattern}) —"
                " what can be placed in a URL segment, an IRI position and a"
                " quoted literal; refused by name, never rewritten (D-IMPL-357 C1)"
            ),
        )

    if not SUBJECT_FLOOR_V1.fullmatch(request.subject):
        return _violation("subject", request.subject)
    for name in sorted(declared.arguments.properties):
        property_ = declared.arguments.properties[name]
        if property_.type != "string" or name not in request.parameters:
            continue
        presented = request.parameters[name]
        if isinstance(presented, str) and not SUBJECT_FLOOR_V1.fullmatch(presented):
            return _violation(name, presented)
    return None
```
Correct the class docstring at `:281-285`: *"…validates its **shape**: the mechanism floor `SUBJECT_FLOOR_V1` always, and a declared `subject_domain` when the class declares one (D-IMPL-357)."*
- [ ] **Step 4: Run** — `PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/products/test_request_contract.py -q` → PASS.
- [ ] **Step 5: Commit** — `git commit -m "feat(357-C1): SUBJECT_FLOOR_V1 and refuse_floor — the mechanism floor for the subject and every string parameter"`.

### Task C2: The floor is judged in `GovernedResolver.__call__` before the overridable seam

**Files:**
- Modify: `src/ccf/products/resolver.py:2203-2235` (after the `refuse_intent` branch, before `self.constraint_resolver.resolve(...)`)
- Test: `tests/products/test_resolver_seam.py` (the module's `_resolver(...)` / `_ask(...)` helpers and a stub constraint resolver)

- [ ] **Step 1: Write the failing tests**

```python
# tests/products/test_resolver_seam.py  (append)
def test_a_malformed_subject_is_refused_before_the_acquisition_seam_and_before_the_constraint_resolver() -> None:
    """D-IMPL-357 C2. The seam must be invoked ZERO times, and a
    PolicyConstraintResolver override must not be able to remove the floor."""
    seam_calls: list[object] = []

    def _seam(*, request, perspective):
        seam_calls.append(request)
        return ()

    class _Override:  # a stub that skips every judgment
        def resolve(self, **kwargs):
            raise AssertionError("the overridable seam ran before the floor")

    resolver = _resolver(booted, acquisition=_seam, constraint_resolver=_Override())
    outcome = _ask(resolver, _request(subject='x" . ?s ?p ?o . "'))
    assert isinstance(outcome, RefusalEnvelope)
    assert seam_calls == []
    assert outcome.replay_reference != NO_REPLAY_REFERENCE
    address = booted.store.resolve_uri(uri=outcome.replay_reference)
    record = DecisionReplayRecord.model_validate_json(booted.store.get(content_address=address))
    assert "malformed-value" in str(record.content_generation_path.assembly_refusal)
```
(The module's helpers: `_resolver(booted, **overrides)` at `tests/products/test_resolver_seam.py:540`, `_request(**overrides)` at `:556`, `_ask(resolver, request)` at `:570`, the `booted` fixture, and the record read exactly as `:594-612` performs it; `acquisition=` and `constraint_resolver=` are `GovernedResolver` constructor fields, `src/ccf/products/resolver.py:1999` and `:2235`.)
- [ ] **Step 2: Run to verify it fails** — Expected: FAIL — `AssertionError: the overridable seam ran before the floor` (or the seam is called).
- [ ] **Step 3: Implement** — in `__call__`, immediately after the `refuse_intent` branch returns (`:2203-2229`) and before `declared = self._request_contract(declaration)` is consumed by the constraint resolver, hoist `declared = self._request_contract(declaration)` up and add:
```python
        floor = refuse_floor(request=request, declared=declared)
        if floor is not None:
            # D-IMPL-357 C2: a mechanism floor, judged before the overridable
            # seam and before any acquisition; the deciding declaration is the
            # class (pinned as for intent) and the floor's version rides in
            # `detail`, which is what pins the floor on the record.
            return self._record_refusal(
                envelope=envelope_for(floor, request=identity),
                execution=None,
                request=request,
                perspective=perspective,
                policy_bindings=(
                    PolicyBinding(key=self.product_class_key, version=content_hash(declaration)),
                ),
                resolution=ResolutionNotApplicable(reason="refused-before-resolution"),
            )
```
- [ ] **Step 4: Run** — `PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/products/test_resolver_seam.py tests/products/test_delivery_determinism.py tests/http_api/test_product_refusal_statuses.py tests/mcp/test_egress_refusal_channels.py -q -p no:randomly` → PASS; the disclosure controls at `tests/products/test_disclosure.py:724-727`/`:798-801` stay green (`detail` withheld at minimal; `malformed-value` is a `ProductRequestViolation`, an existing kind).
- [ ] **Step 5: Commit** — `git commit -m "fix(357-C2): the floor is judged in GovernedResolver.__call__ before the overridable seam"`.

### Task C3: `ArgumentDomain.pattern` (a third exclusive shape) and `ProductRequestContract.subject_domain`

**Files:**
- Modify: `src/ccf/products/request.py:435-491` (`ArgumentDomain`), the `ProductRequestContract` field block (`:793-807` neighbourhood), `refuse_request` (`:1920`, a `_refuse_subject` step after `_refuse_address`), `src/ccf/products/request_schema.py:88-112`
- Test: `tests/products/test_request_contract.py`, `tests/products/test_request_schema_render.py:291`

**Interfaces:**
- Produces: `ArgumentDomain.pattern: str | None` (hash-transparent `True`; exactly one of numeric / members / pattern; compiled with `re.fullmatch` at construction; a non-compiling pattern refused by name); `ArgumentDomain.refuses(value)` returns `"not-in-domain"` for a string outside the pattern; `ProductRequestContract.subject_domain: ArgumentDomain | None` (hash-transparent `True`; numeric shape refused); `_refuse_subject` returns a `ProductRequestViolation(reason="not-in-domain", key="subject", …)` with the pattern text in `detail` only.

- [ ] **Step 1: Write the failing tests**

```python
def test_pattern_is_a_third_exclusive_shape_and_amends_D03() -> None:
    from ccf.products.request import ArgumentDomain
    domain = ArgumentDomain(pattern=r"[A-Z]{2}[0-9]{4}")
    assert domain.refuses("GB1234") is None
    assert domain.refuses("gb1234") == "not-in-domain"
    with pytest.raises(ValidationError, match="exactly one shape"):
        ArgumentDomain(pattern=r"x", members=("x",))
    with pytest.raises(ValidationError, match="does not compile"):
        ArgumentDomain(pattern=r"(")


def test_a_declared_subject_domain_is_judged_after_the_address_step() -> None:
    from ccf.products.request import ArgumentDomain, refuse_request
    contract = _contract(subject_domain=ArgumentDomain(pattern=r"[0-9A-Z]{20}"))
    violation = refuse_request(request=_request(subject="short"), declared=contract)
    assert violation is not None
    assert violation.reason == "not-in-domain" and violation.key == "subject"
    assert "[0-9A-Z]{20}" in violation.detail and violation.declared_type == "string"


def test_a_subject_domain_cannot_be_numeric() -> None:
    from ccf.products.request import ArgumentDomain, ProductRequestContract
    with pytest.raises(ValidationError, match="subject_domain"):
        _contract(subject_domain=ArgumentDomain(minimum=Decimal(1)))


def test_the_render_advertises_pattern_and_refuses_a_planted_one() -> None:
    from ccf.products.request_schema import render_request_input_schema   # src/ccf/products/request_schema.py:55
    contract = _contract(argument_domains={"lei": ArgumentDomain(pattern=r"[0-9A-Z]{20}")},
                         arguments={"properties": {"lei": {"type": "string"}}})
    rendered = render_request_input_schema(contract)
    assert rendered["properties"]["lei"]["pattern"] == r"[0-9A-Z]{20}"
```
and extend the planted-key tuple at `tests/products/test_request_schema_render.py:291` with `"pattern"`.
- [ ] **Step 2: Run to verify they fail** — Expected: `ValidationError: Extra inputs are not permitted` for `pattern` / `subject_domain`.
- [ ] **Step 3: Implement**

```python
# ArgumentDomain
    pattern: str | None = Field(default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True})

    @model_validator(mode="after")
    def _at_least_one_end_and_in_order(self) -> "ArgumentDomain":
        numeric = self.minimum is not None or self.maximum is not None
        shapes = int(numeric) + int(self.members is not None) + int(self.pattern is not None)
        if shapes != 1:
            raise ValueError(
                "an argument domain declares exactly one shape — numeric bounds"
                " (minimum and/or maximum), OR an enumerated member set (members),"
                " OR a grammar (pattern) — and this one declares"
                f" {shapes} (D-IMPL-264 D-03 as amended by D-IMPL-357 C4, D-IMPL-259)"
            )
        if self.pattern is not None:
            try:
                re.compile(self.pattern)
            except re.error as error:
                raise ValueError(
                    f"an argument domain's pattern does not compile: {error}"
                    " (D-IMPL-357 C4)"
                ) from error
            return self
        # … the existing members / numeric branches unchanged …

    def refuses(self, value: object) -> ProductRequestViolationReason | None:
        if self.pattern is not None:
            if isinstance(value, str) and re.fullmatch(self.pattern, value):
                return None
            return "not-in-domain"
        # … unchanged …
```
```python
# ProductRequestContract
    subject_domain: ArgumentDomain | None = Field(default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True})

    @model_validator(mode="after")
    def _subject_domain_is_a_grammar_or_a_set(self) -> "ProductRequestContract":
        if self.subject_domain is not None and (
            self.subject_domain.minimum is not None or self.subject_domain.maximum is not None
        ):
            raise ValueError("subject_domain declares a numeric shape; a subject is an identifier and is held to a pattern or a member set (D-IMPL-357 C4)")
        return self
```
```python
# refuse_request — after `address = _refuse_address(...)`
    subject = _refuse_subject(request=request, declared=declared)
    if subject is not None:
        return subject

def _refuse_subject(*, request, declared) -> ProductRequestViolation | None:
    if declared.subject_domain is None:
        return None
    reason = declared.subject_domain.refuses(request.subject)
    if reason is None:
        return None
    grammar = declared.subject_domain.pattern
    stated = (f"pattern {grammar}" if grammar is not None
              else f"declared set [{', '.join(repr(m) for m in sorted(declared.subject_domain.members or ()))}]")
    return ProductRequestViolation(
        reason=reason, key="subject", declared_type="string",
        presented_type=type(request.subject).__name__,
        declared_keys=frozenset(declared.arguments.properties),
        presented_keys=frozenset(request.parameters),
        detail=f"subject: the presented identifier is not in this class's {stated} (D-IMPL-357 C4)",
    )
```
```python
# request_schema.py
    for name, spec in properties.items():
        planted = [key for key in ("enum", "minimum", "maximum", "pattern") if key in spec]
        …
def _derived_keys(domain: ArgumentDomain) -> dict[str, Any]:
    if domain.pattern is not None:
        return {"pattern": domain.pattern}
    …
```
- [ ] **Step 4: Run** — `PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/products/test_request_contract.py tests/products/test_request_schema_render.py tests/products/test_disclosure.py -q` → PASS; then `make schemas` (regenerates `docs/schemas/ccf.product-request-contract.json`), tick `ArgumentDomain.pattern` and `ProductRequestContract.subject_domain` in the hash-transparency table, `make lint` → CINV-06 green.
- [ ] **Step 5: Commit** — `git commit -m "feat(357-C4): ArgumentDomain.pattern and ProductRequestContract.subject_domain — the declared grammar (amends D-IMPL-264 D-03)"`.

### Task C5: The read-only probe and the stdio disclosure

**Files:**
- Create: `tools/probe_subject_floor.py`
- Modify: the `public/` page documenting `ProductDoor` (`grep -rln 'serve_stdio' public/`)

- [ ] **Step 1: Write the probe** — it imports `SUBJECT_FLOOR_V1`, walks `examples/**/*.yaml` for `subject:` values and every `parameters:` string value, `tests/examples/*.py` for `QUESTION[...]["subject"]` literals, and prints `path:line value → pass|REFUSE`. If the estate variables (`CCF_CP_*`) are exported it additionally runs each example's own question against the floor after the example resolves its subject from the estate (the example's `run.py --dry-run` where one exists; otherwise the literal only, and it says so). Expected from the recon: zero literal refusals.
- [ ] **Step 2: Run it against the tree** and, at the estate-gated run (Part VI), against `.76`; attach both outputs under `docs/superpowers/plans/evidence/357-C1a-probe.txt`.
- [ ] **Step 3: Disclose on the door page**: *"`ProductDoor.serve_stdio` serves one pre-set identity for every caller of the process (`ambient_stdio_identity`); a multi-principal deployment uses `serve_loopback` or composes its own transport. The composition control is designed with the harness adapters in 1.0.3 (`D-IMPL-361`)."*
- [ ] **Step 4: `make docs-strict`; commit** — `git commit -m "docs(357-C5): the subject-floor probe; the stdio single-identity disclosure"`.

### Task D1: The version is the tag's — `setuptools_scm`, a gate, a tag-triggered job

**Files:**
- Modify: `pyproject.toml:1-7` (`[build-system]`, `[project]`)
- Create: `tools/check_version_stamp.py`, `.github/workflows/release-stamp.yml`, `tests/test_version_stamp.py`
- Test: `tests/test_version_stamp.py`

**Interfaces:**
- Consumes: `src/ccf/graph/registry.py:474-484` `_sdk_version()` → `importlib.metadata.version(SDK_DISTRIBUTION)`; `SDK_DISTRIBUTION = "ccf"` (`:188`).
- Produces: `importlib.metadata.version("ccf")` derived from git (`1.0.2` at the `v1.0.2` tag; `1.0.1.devN+g…` on a branch past `v1.0.1`); `tools/check_version_stamp.py` exits non-zero when `HEAD` is an exact `v*` tag and the installed metadata differs from it.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_version_stamp.py
"""D-IMPL-357 §D (SEC-029): the version the replay record carries is the tag's."""
import importlib.metadata
import re
import subprocess

from ccf.graph.registry import SDK_DISTRIBUTION, _sdk_version


def test_the_installed_version_is_not_the_stale_literal_and_is_git_derived() -> None:
    version = importlib.metadata.version(SDK_DISTRIBUTION)
    assert version != "0.1.0"
    assert re.match(r"^\d+\.\d+\.\d+", version), version
    assert _sdk_version() == version


def test_on_an_exact_tag_the_stamp_equals_the_tag() -> None:
    described = subprocess.run(
        ["git", "describe", "--tags", "--exact-match"], capture_output=True, text=True
    )
    if described.returncode != 0:
        import pytest
        pytest.skip("HEAD is not an exact tag; the gate binds at release only")
    assert importlib.metadata.version(SDK_DISTRIBUTION) == described.stdout.strip().lstrip("v")
```

- [ ] **Step 2: Run to verify it fails**

Run: `PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/test_version_stamp.py -v`
Expected: FAIL — `assert '0.1.0' != '0.1.0'`.

- [ ] **Step 3: Single-source the version**

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=77", "setuptools_scm>=8"]
build-backend = "setuptools.build_meta"

[project]
name = "ccf"
dynamic = ["version"]          # was: version = "0.1.0"  (SEC-029; D-IMPL-357 §D)
# … unchanged …

[tool.setuptools_scm]
# The tag is the single source: `v1.0.2` → "1.0.2"; a commit past a tag renders
# `1.0.2.devN+gSHA`, which is the honest stamp for a record produced by
# unreleased code. A checkout with no git history builds as the fallback and
# says so, rather than as a plausible release number.
fallback_version = "0.0.0+no-git-metadata"
```
Then reinstall so the metadata is regenerated: `.venv/bin/pip install -e ".[dev]" -q` (the wheel `setuptools_scm-10.3.4` is already downloadable on this host).

- [ ] **Step 4: Write the gate and the job**

```python
# tools/check_version_stamp.py
"""Fail when HEAD is an exact v* tag and the installed stamp is not that tag's (D-IMPL-357 §D)."""
from __future__ import annotations

import importlib.metadata
import subprocess
import sys

DISTRIBUTION = "ccf"


def main() -> int:
    described = subprocess.run(
        ["git", "describe", "--tags", "--exact-match"], capture_output=True, text=True
    )
    if described.returncode != 0:
        print("check_version_stamp: HEAD is not an exact tag; nothing to hold")
        return 0
    tag = described.stdout.strip()
    stamped = importlib.metadata.version(DISTRIBUTION)
    if stamped != tag.lstrip("v"):
        print(f"check_version_stamp: tag {tag} but installed {DISTRIBUTION} is {stamped}")
        return 1
    print(f"check_version_stamp: {tag} == {stamped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```
```yaml
# .github/workflows/release-stamp.yml
name: release-stamp
on:
  push:
    tags: ["v*"]
jobs:
  stamp:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0        # setuptools_scm and `git describe` need the tags
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: python -m pip install -e "."
      - run: python tools/check_version_stamp.py
```
Add `check-version-stamp:` to the `Makefile` as `$(ENV) $(PYTHON) tools/check_version_stamp.py` and reference it from the qualification recipe in `D-IMPL-357`'s entry (release mechanics stay §8's).

- [ ] **Step 5: Run**

Run: `PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/test_version_stamp.py -v && .venv/bin/python tools/check_version_stamp.py`
Expected: the first test PASSES with a `1.0.1.devN+g…` stamp; the second SKIPS off-tag; the gate prints "not an exact tag; nothing to hold".

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml tools/check_version_stamp.py .github/workflows/release-stamp.yml tests/test_version_stamp.py Makefile
git commit -m "feat(357-D): the version is derived from the tag (setuptools_scm) and gated at release — SEC-029"
```
Note for the entry: the derived stamp now differs per commit on a branch, so any test that pinned `graph_adapter_version == "0.1.0"` goes red — `git grep -n '"0.1.0"' tests/` is the roster to rewrite (expected: none beyond fixtures that carry the literal in prose).

### Task E1: Bookkeeping — the ledger row, the two entries, the fragment, the regenerations

**Files:**
- Modify: `docs/D-IMPL-353-EXAMPLES-GAP-LEDGER.md` (row `SEC353-G-09`), `docs/DECISIONS.md` (`D-IMPL-357`, `D-IMPL-361`), `docs/surface/v0.2-surface.json` (via `make surface`), `docs/schemas/*.json` (via `make schemas`)
- Create: `docs/surface-changes/357-01-declared-not-assumed.md`

- [ ] **Step 1: The ledger row** (the table at `docs/D-IMPL-353-EXAMPLES-GAP-LEDGER.md:70`'s shape):

```
| `SEC353-G-09` | Eight frozen custom doors call `open_door(token_verifier=…)`, a keyword `ba946df1` removed (`examples/cp-15-kyc-refresh-beneficial-ownership/server/serve.py:128`, `examples/cp-16-abs-securitization-surveillance/server/serve.py:121`, `examples/cp-17-mnpi-wall-enforcement/server/serve.py:109`, `examples/cp-18-ib-opportunity-synthesis/server/serve.py:121`, `examples/cp-19-aml-typology-match/server/serve.py:135`, `examples/cp-21-large-exposure/server/serve.py:123`, `examples/cp-23-portfolio-early-warning/server/serve.py:119`, `examples/cp-24-portfolio-what-if/server/serve.py:119`); every one raises `TypeError` at construction; zero examples use the migration target `open_door_with_verifier` | `runtime/ccf_runtime/mcp/product_door.py:320-327` — `open_door(product, *, environ, perspective_resolver, entitlement_source)`; the verifier-bearing composition is `open_door_with_verifier` (`:384-421`), per `353-05` | the wave-1 opening sheet, 2026-09-25 (recorded, not repaired — `D-IMPL-356` L2) | **OPEN** — a `TypeError` at construction, by name; estate-gated so never observed in a census-posture run | post-1.0.2 example rerun; not unfrozen in waves 1–3 |
```

- [ ] **Step 2: `D-IMPL-357`** — one entry in the ledger's paragraph style recording: the wave's scope; A1–A5, B1–B5, C1–C6+C1a as locked at `D-IMPL-356` and as implemented (with the two declared amendments: `D-IMPL-347` B2 for SDK-raised seam classes; `D-IMPL-264` D-03 for the third shape); `SEC-029`; the measurements attached (B4 population, C1a probe); the red-when-fixed tests and their rewrites (Part IV); the sabotage results (Part V); the estate-gated run's census (Part VI); the threat-model boundary sentence (Part I); the rows opened (§7.4: the escalation sibling, removing `decision`, L2 partial admission, durable L2 refusal recording, the workflow-definition hash); next free id `D-IMPL-362` reserved.
- [ ] **Step 3: `D-IMPL-361`** — the adapter entry: `TP-01`…`TP-05` rated HIGH by ruling (§0 #1) with the recon's severities beside it; the `D-IMPL-356` release condition verbatim; the three statuses each finding must take in the release record; the seven verified facts (spec §7.1); the 1.0.3 ruling sheet; the stdio composition control; "this authorizes no adapter implementation in 1.0.2 and creates no fourth code wave".
- [ ] **Step 4: The fragment** `docs/surface-changes/357-01-declared-not-assumed.md`, in the `353-08` form: what did NOT change first (no action id, no handle signature, no HTTP wire shape, no MCP tool schema); then the new public names it claims — `ccf.workflow.definitions.WorkflowDefinition.gate_routes`, `ccf.assembly.worker.IdentityRefused`, `ccf.products.request.SUBJECT_FLOOR_V1`, `SUBJECT_FLOOR_VERSION`, `refuse_floor`, `ArgumentDomain.pattern`, `ProductRequestContract.subject_domain`, the reason `malformed-value`, `ccf.products.resolver.SDK_SEAM_REFUSALS`; the `2.0.0` lane on the three fixtures (declarative — the generation boundary is `gate_routes`).
- [ ] **Step 5: Regenerate and check** — `make schemas && make surface && .venv/bin/python tools/dump_surface.py --check && make lint && PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/test_surface_drift.py tests/cli/test_schema_export.py tests/contracts/test_hash_transparency.py -q` → all green.
- [ ] **Step 6: Commit** — `git commit -m "docs(357-E1): SEC353-G-09; D-IMPL-357 and D-IMPL-361; surface fragment 357-01; schemas and surface regenerated"`.

---

## Part IV — Red-when-fixed roster (rewrite, never delete)

| Test (node) | What it pins today | What it becomes |
|---|---|---|
| `tests/workflow/test_engine.py::test_a_rejection_authorizes_resumption_but_does_not_bind_the_target` (`:856-895`) | `WorkflowCompleted` after a recorded `reject` + `decision="approved"`; `actor == "officer-2"` | `test_a_recorded_rejection_cannot_be_routed_down_the_approving_branch` (A3 step 1): `WorkflowResumeRefused`, audit `resolved=False, actor=None`, then the declared route completes |
| `tests/workflow/test_engine_stateful.py::TestWorkflowEngineStateful.resume_suspended` (`:169-195`) | draws `decision ∈ {approved, rejected}` after an always-approve resolve | draws the **verdict**, resolves the gate with it, derives `decision` from `gate_routes` (A3 step 1) |
| Every test constructing the three fixtures (`tests/workflow/*`, `tests/http_api/conftest.py` → `tests/http_api/test_routes.py:573/606/631`, `tests/cli/test_cli.py::test_workflow_invoke_status_resume`, `tests/conformance/test_orchestration.py`, `perf/suites/micro/test_factory.py`) | green on `1.0.0` documents with no `gate_routes` | red at the factory between A2 step 3 and step 4; green again once the YAML migrates (fixed by data, not by test edits) |
| `tests/http_api/test_routes.py::test_workflow_resume_with_an_undeclared_decision_is_refused` (`:631`, asserts "declared transition" at `:650`) | ordering-sensitive | stays green because the route compare is placed **after** the declared-target check |
| `tests/cli/test_schema_export.py::test_the_committed_schemas_match_what_the_classes_emit` (`:124`) and `::test_each_committed_schema_is_its_class_byte_for_byte` (`:130`) | committed schemas | red until `make schemas` after A1 and C3 |
| `tests/contracts/test_hash_transparency.py::test_the_marked_fields_in_the_tree_are_exactly_the_ticked_table` | the ticked roster of marked fields | red until `gate_routes` (`False`), `pattern` (`True`), `subject_domain` (`True`) are ticked |
| `tests/products/test_request_contract.py::test_the_reason_vocabulary_has_nine_members_tier_proportion_domain_then_membership` (`:1011-1016`) | nine members, `not-in-domain` last | ten members, `malformed-value` last (C1 step 1) |
| `tests/products/test_request_schema_render.py` planted-key tuple (`:291`) and its refusal control | `("enum", "minimum", "maximum")` | gains `"pattern"` (C3) |
| `tests/products/test_d_impl_347_seam_refusals.py::test_an_UNdeclared_domain_exception_still_propagates` (`:273`) | undeclared types re-raise | **stays green** — it is the control that keeps B3 narrow |
| `tests/assembly/test_worker.py::test_…partial identity` (`:201`) | presence refusal | stays green (presence still first) |
| `tools/lints` CINV-06, `tools/dump_surface.py --check`, `tests/test_surface_drift.py` | the committed manifest | red until the fragment and `make surface` |
| any test asserting `graph_adapter_version == "0.1.0"` (`git grep -n '"0.1.0"' tests/`) | the stale literal | rewritten to `!= "0.1.0"` / git-derived |

## Part V — Sabotage plan (each severing on the merged tree, in a detached worktree; restore from saved bytes, never `git checkout --`)

| # | Severing | Control that must redden | Guard it proves |
|---|---|---|---|
| S1 | delete the route compare in `resume` | `test_a_recorded_rejection_cannot_be_routed_down_the_approving_branch` | A3 |
| S2 | delete the `len({…action…}) > 1` refusal | `test_two_officers_conflicting_verdicts_…` and the HTTP twin | A4 |
| S3 | move the route compare **ahead** of the declared-target check | `tests/http_api/test_routes.py::test_workflow_resume_with_an_undeclared_decision_is_refused` (`:650`) | ordering |
| S4 | put the expected target into the A3 refusal reason | `test_a_refused_gate_resume_does_not_enumerate_the_declared_targets` and `tests/http_api/test_routes.py:606` | remedy 3 |
| S5 | delete the factory coverage check | `test_a_routed_gate_without_a_complete_route_map_is_refused_at_construction` | A2 |
| S6 | in `_routes_map_verdicts_onto_declared_targets`, drop the target-membership check | `test_a_route_to_a_target_not_declared_from_that_gate_is_refused` | A1 |
| S7 | restore bare `str()` at the mint site | `test_an_inadmissible_identity_value_is_refused_by_name[…]` and `test_two_null_identity_envelopes_mint_nothing_and_no_edge` (both assertions) | B1 |
| S8 | make `_identity_text` accept `float` | the `[1.5-float]` parametrization only | B1's float name |
| S9 | delete the `SDK_SEAM_REFUSALS` lookup | `test_the_sdks_own_identity_refusal_is_a_governed_refusal_without_a_declaration` | B3 |
| S10 | add a deployment type to `SDK_SEAM_REFUSALS` | `test_a_deployment_cannot_widen_the_sdk_seam_map_…` | B3's narrowness |
| S11 | move `refuse_floor` inside `refuse_request` (after the overridable seam) | `test_a_malformed_subject_is_refused_before_the_acquisition_seam_and_before_the_constraint_resolver` | C2 |
| S12 | admit `'` in `SUBJECT_FLOOR_V1` | `test_a_subject_outside_the_floor_is_a_malformed_value["o'brien"]` | C1a |
| S13 | raise the bound to `{0,1023}` | `["x" * 513]` | C1a length |
| S14 | let `refuse_floor` skip string parameters | `test_a_declared_string_parameter_is_held_to_the_floor_too` | C3 |
| S15 | let a `pattern` domain be judged **instead of** the floor | a new control: a `pattern` admitting `'` still refuses `o'brien` as `malformed-value` | "cannot widen past the floor" |
| S16 | restore `version = "0.1.0"` | `test_the_installed_version_is_not_the_stale_literal…` after reinstall; `tools/check_version_stamp.py` at a throwaway local tag `v9.9.9-sabotage` (deleted after) | §D |

Every severing is recorded as observed RED then restored byte-for-byte to the freeze hash (`git rev-parse HEAD^{tree}` equal before and after), in `docs/superpowers/plans/evidence/357-sabotage.md`.

## Part VI — Estate-gated validation (read-only against `.76`)

1. **At the wave base** (main at the wave-1 fork) and **at close** (the merged tree): export the `ccf_dataprep` connection material and the **v2** namespaces (`fibo-v2` / `ccf_v2` / `fibo_v2` on `192.168.4.76`; the `.env` names the v1 ones — derive the `CCF_CP_*` values from `ccf_dataprep/ccf/config.py`, never from `.env` alone); no `CCF_TEST_*` seeding; `estate_guard` refuses a curated host on either leg.
2. Record the watermarks before and after (`ccf:main t=…`, `fibo-v2 t=…`, ledger count) — zero movement is a pass condition.
3. Run: `PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/examples -q -rs -p no:randomly --junitxml=evidence/357-estate-<base|close>.xml` (foreground, split into chunks under ten minutes each).
4. Report `passed / failed / errors / skipped` and the exact failing node ids; classify each red as **pre-existing at the base** (the R10 census plus the eight `SEC353-G-09` doors) / **new under wave 1** / **already ledgered**. A new red is an SDK finding or a gap-ledger row before it is anything else (`D-IMPL-261`); no example file changes.
5. Expected from the design: **zero new reds** — wave 1 changes no served wire shape; the only example-reachable changes are the floor (every measured literal passes; the probe reports the estate-sourced values) and the identity refusal (fixture scan: zero nulls on declared identity keys). A new red here is evidence, and stops the close.

## Part VII — Panel brief (codex + cursor + gemini, after sabotage, before Dave)

- **Payload, on stdin, one bundle ≤ 190 KB:** the `D-IMPL-357` entry draft; the full diff against the wave base; numbered (`cat -n`) excerpts of `src/ccf/workflow/definitions.py` (whole), `src/ccf/workflow/factory.py:300-385`, `runtime/ccf_runtime/workflow/engine.py:495-575` and `:925-1060`, `src/ccf/assembly/worker.py:300-400` and `:540-600`, `src/ccf/products/resolver.py:2190-2300` and `:3190-3270`, `src/ccf/products/request.py:225-250`, `:430-520`, `:1840-1860`, `:1915-2080`, `src/ccf/products/request_schema.py:80-115`, `src/ccf/controlplane/artifacts.py:1300-1345` and `:1550-1565`, `src/ccf/deployment/binder.py:318-338`, `pyproject.toml:1-12`, `tools/check_version_stamp.py`; the three migrated fixtures; every new or rewritten test; Part V's results.
- **Told:** the SDK is destined for a **bank**; the executing model is excluded; every citation must resolve and every quotation must exist; findings carry `path:line` + quoted line + a concrete failure; BLOCKING only for a factual error, an undeclared ruling contradiction, a violated invariant or a plan-diverging ambiguity.
- **Known and not to be re-derived:** A1–A5, B1–B5, C1–C6+C1a are locked (`D-IMPL-356`); the escalation sibling, `decision`'s removal, L2 partial admission, durable L2 refusal recording and the workflow-definition hash are named rows; `SEC353-G-09` is ledgered; wave 2's clock is out of scope.
- **The questions, in priority order:** (1) Can a recorded `reject` still reach a non-reject target through any door — HTTP `POST /workflow/resumptions`, the CLI verb, the four orchestration drivers, the harness tool schema? (2) Can a caller make the identity refusal inapplicable — a `str` subclass, a `Decimal` that is not finite, a value that reaches `ingest_admitted` (`src/ccf/assembly/worker.py:684-712`) by another path, an `EntityResolutionStrategy` plugin? (3) Does any served path reach the acquisition seam with a subject or string parameter outside the floor — the in-process door (`src/ccf/products/door.py`), the MCP resource path, a composite child question (`src/ccf/products/child_resolver.py:771`), the `dispatch.py` peer forwarding? (4) Does the floor's placement change what any existing refusal test observes (the refusal order at `src/ccf/products/resolver.py:2203-2235`)? (5) Does `SDK_SEAM_REFUSALS` open any conversion for a deployment-raised type, and can the binder be made to widen it? (6) Does the version stamp read anything but installed metadata, and does the derived dev stamp break a record-shape pin? (7) What is adjacent: the same defect class next to each fix.
- **Dispositions** in `docs/V1.0.2-CLOSE-REVIEWS.md` (wave 1 section): every finding and every retraction verified against the tree; rejections recorded as rejections.

## Part VIII — Exit criteria for wave 1 (spec §9 items 1–4, made concrete)

1. `test_a_recorded_rejection_cannot_be_routed_down_the_approving_branch` and the conflicting-verdict pair pass; S1–S6 observed red.
2. `test_two_null_identity_envelopes_mint_nothing_and_no_edge` passes on both assertions; the paved-road conversion test passes with `identity-refused` / `nonexistent` in the record; S7–S10 observed red.
3. A subject carrying `"` or `'`, a 513-character subject, and a `type: string` argument carrying `<` refuse as `malformed-value` at the in-process door, over MCP and over HTTP before any acquisition, with a replay record; the override control passes; S11–S15 observed red; the probe reports zero literal refusals and names every estate-sourced value it checked.
4. `importlib.metadata.version("ccf")` is git-derived in the reinstalled venv; `tools/check_version_stamp.py` holds at a throwaway tag; S16 observed red.
5. `make lint`, `make schemas`, `make surface`, `tools/dump_surface.py --check`, `make docs-strict`, the workflow / assembly / products / http_api / mcp / conformance suites green, reported as four numbers.
6. Estate-gated run at base and close: zero new reds, watermarks unchanged, every red classified by node id.
7. Panel run and dispositioned; blocking findings fixed in-wave; then STOP for Dave with the `D-IMPL-357` entry, the changed-surface inventory, the sabotage table, the estate census and the panel dispositions. `D-GATE-357` and the `--no-ff` merge to `main` are Dave's.

## Part IX — What this sheet does not do

No wave-2 or wave-3 code (no clock, no `TemporalBoundRefusal`, no HITL claim set). No release or tag work beyond the stamp mechanism and its gate. No new reconnaissance: every citation above was read on `main` @ `a5b0f691` during the spec's two reviews. No example or `archive/` edit. No merge: the wave-1 branch forks from `main` after `v1.0.2-spec` merges, on Dave's GO.

---

**Execution handoff.** Two options once this sheet is accepted: **(1) subagent-driven** — one fresh subagent per task in four parallel worktrees (lanes A–D), two-stage review between tasks, lane E after the join; **(2) inline** — tasks executed in this session with checkpoints after each lane. Either way the sequence per §2 rule 1 holds: build → red-when-fixed rewrites → sabotage on the merged tree → the estate-gated run → the panel → verify → STOP for Dave.
