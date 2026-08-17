# Deferred items — phase 16

Out-of-scope discoveries logged rather than fixed, per the executor's scope
boundary. Each entry names the plan that found it and the plan that should own
it.

## Two `tests/products/` docstrings cross-reference the retired ERGO-03 audit module

- **Found during:** plan 16-01, Task 2, when
  `tests/examples/test_surface_audit.py` was deleted under `D-IMPL-94` / `D-15`.
- **What:** two modules name that file in prose as a live exemplar of the
  "assemble the probe body at runtime so this module's own source is not what a
  scan trips over" discipline. Both statements are present-tense and both became
  false the moment the module was deleted:
  - `tests/products/test_gate_two_call_shape.py`, in the docstring of the
    binder-scan non-vacuity test — *"the discipline
    `test_required_operators_guard.py::test_the_guard_detects_the_shortcut_it_exists_to_refuse`
    and `tests/examples/test_surface_audit.py` both use"*.
  - `tests/products/test_required_operators_guard.py`, in the in-body comment
    above the assembled probe sources — *"the same discipline
    `tests/examples/test_surface_audit.py` uses for the figures it forbids"*.
- **Why it was not fixed in 16-01:** the plan's Task 2 `<files>` list does not
  include either module, and both are owned by later plans in this phase —
  16-15 (limb 2, retiring
  `test_the_plan_recognition_refuses_an_unrelated_required_keyword`) and 16-18
  (limb 1, re-flooring the four non-vacuity constants). Editing them from a
  wave-1 worktree would collide with those plans in a later wave for no benefit.
  Neither reference is a *citation* in the `tools/lints/citations.py` sense —
  both are bare backticked paths with no `:NNN` and no `::symbol` — so nothing
  goes red today; `python -m tools.lints --all` exits 0 with the module gone.
- **Where it belongs:** plan 16-15 and plan 16-18, each correcting the module it
  already has open. The correct redirect is
  `docs/surface/examples/ERGO-03-FROZEN.md`, which records the same discipline
  and states why the module that practised it retired. Both edits are docstring
  prose, not detection logic, so neither is touched by `D-14`'s carry-forward.

## `docs/SURFACE-CHANGES.md` and `docs/surface-changes/15-03-audit-baseline.md` name the retired module

- **Found during:** plan 16-01, Task 2.
- **What:** both name `tests/examples/test_surface_audit.py` as a live module.
  `docs/surface-changes/15-03-audit-baseline.md` is the per-plan fragment that
  recorded its creation; `docs/SURFACE-CHANGES.md:2964` is the assembled mirror
  of that fragment.
- **Why it was not fixed:** these are **dated per-plan records of what a plan
  did at the time**, which is the same class `deferred-items.md` for Phase 15.1
  repeatedly declined to rewrite — correcting them would falsify the record of
  what plan 15-03 built. Whether such records are *corrected* or *annotated* is
  the open editorial judgment `docs/SURFACE-AUDIT.md` §5.4 already carries, and
  `D-IMPL-94`'s Q-6 disposition settles only whether `SURFACE-CHANGES.md`
  publishes, not how its dated fragments age.
- **Where it belongs:** plan 16-20 or 16-21, alongside whatever standing gate
  `DOCS-17` builds for stale prose paths — which is the mechanism that will have
  to decide the general rule, not this one file.

## Client-chosen `subject` on the egress product tool is not entitlement-scoped

- **Found during:** plan 16-23, Task 1 (security analysis of the new door).
- **Status:** **RULED — `D-IMPL-128` limb 2** (RESOLVED, Dave, 2026-08-13).
  This is a **named residual under an existing ruling**, not an open question
  and not a candidate for one.
- **Owner:** **unassigned by ruling.** The trigger for opening it is a concrete
  harm or an authorised scoped-assembly workstream.
- **What:** `runtime/ccf_runtime/authz/product_entitlement.py::entitled_perspective`
  decides on `(grant, tenant, product_class, resolved role)` and
  carries **no subject dimension**, while `subject` becomes the traversal seed
  (`ccf.products.request.request_seeds`, `D-IMPL-111` limb (a)) and therefore
  selects what is assembled.
- **Why it ships anyway, and it is a measurement rather than an argument:** the
  delta this tool introduces is **zero**. Anything reachable as
  `call_tool(subject=S)` is already reachable as
  `GET /product/{tenant}/{class}/{version}?subject=S&…` on the same grant,
  through the same decision, on a door shipped since `D-IMPL-108`
  (`runtime/ccf_runtime/http_api/routes/product.py::build_router`). The
  tool widens the vocabulary of doors, not the set of reachable state.
- **What closing it would need:** a perspective-scoped assembly path that does
  not exist. `D-IMPL-119` limb 2 measured the entitled-versus-assembled delta as
  *empty on the shipped path* and put the scoped view out of scope; `D-IMPL-124`
  Shape D was **blocked** on the same absence.
- **Standing constraint, carried verbatim from `D-IMPL-128` limb 2:** *no plan
  may cite the tool's shipping as evidence that subject-scoping is
  unnecessary.*

## A product class declaring any required request parameter is unreachable through either parameterised door

- **Found during:** plan 16-23, Task 1 (measured, not inferred).
- **Status:** **CORRECTED AND RULED — `D-IMPL-133`** (Dave, 2026-08-14):
  *"We will need to support parameters in mcp from the Client. That was a miss."*
  **The "blocked" reasoning below is WRONG and is left standing only as a
  corrected entry, never silently deleted.** A door never validates, so a door
  never needs the `RegisteredProductClass`: `ccf.products.request.refuse_request`
  is *"called by the deployment's own resolver, not by any door"*
  (`D-IMPL-121`, extending `D-IMPL-113`), and is called from **nowhere** in
  `runtime/` — only three docstring cross-references. Both doors therefore carry
  the mapping through to the resolver, which holds the class. Two lines, not a
  seam widening.
- **Owner:** **the HW-1 plan** (`D-IMPL-127`). It is a design constraint on that
  plan rather than a defect in 16-23.
- **What:** both parameterised doors send `parameters={}`. Measured at
  `753a21d` against the committed `examples/s1-01` request contract, a
  `ProductRequest` carrying the four §6.3 axes and `parameters={}` is refused:
  `reason='missing-required-parameter' key='decision_instant'`. The HTTP door
  has the identical property today.
- **Why the obvious repair is blocked:** carrying the class's declared
  parameters requires validating them against the `RegisteredProductClass`,
  which **the door never holds** — it is resolved *behind* the resolver seam.
  That is exactly the boundary `D-IMPL-113` records, and the SDK cannot call a
  comparison whose second operand it does not have. A declared-parameter surface
  on the tool would also make it wider than the HTTP door beside it.
- **Consequence for `D-IMPL-127`:** HW-2 is required to change only the
  *client*, so HW-1's product class must declare **no required** request
  parameters, or `decision_instant` must stop being one. Optional parameters are
  unaffected.

## `get_context` on the Experience MCP server is authenticated but not entitled

- **Found during:** plan 16-23's security analysis (recorded here as a
  **cross-reference**, because 16-23's tool is named under `D-IMPL-128`'s
  **Governs** as the door that deliberately does not copy this shape).
- **Status:** **RULED — `D-IMPL-128` limb 1** (RESOLVED, Dave, 2026-08-13):
  *"fix it in this phase."* Not unruled, not unowned, and no candidate
  `D-IMPL` id is filed for it.
- **Owner:** plan **`16-24`**, assigned by **`D-IMPL-129`**, whose
  `files_modified` includes `runtime/ccf_runtime/mcp/experience.py`.
- **What:** `runtime/ccf_runtime/mcp/experience.py::build_experience_server`'s
  `get_context` takes both arguments from the client and
  calls neither `verified_grant()` nor `entitled_perspective(...)`, while the
  `context_product` **resource on the same server** calls both.
- **Why 16-23 does not fix it:** it is another plan's file in an adjacent wave,
  and editing it here would collide with the plan that owns the repair. What
  16-23 owes the record instead is the reason it did not copy the shape: the
  precedent `D-IMPL-126` cites proves a parameterised MCP tool is *buildable*,
  not that it is *governed*. `D-IMPL-128` records that framing, and records that
  16-23's own security analysis is how the defect surfaced — *"no audit and no
  lint found it."*
