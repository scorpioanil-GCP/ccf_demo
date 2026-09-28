# 358-05 — trusted time becomes live: a temporal-bound refusal, and one instant per invocation in every governed refusal

`D-IMPL-358` Wave 2 step 5, **partially landed** — this fragment claims only what
is on the tree. Two of the step's areas are complete: the governed
`temporal-bound-refusal` vocabulary, and the refusal temporal-identity migration
across all five recorder families. The remaining areas are named in the step
record and are not claimed here.

**What is true on this tree.** A governed refusal exists for a question that
reaches outside the window a tenant declares, with a pure judgment behind it; and
every governed refusal from one invocation now carries the ONE instant that
invocation read, beside — never instead of — the question's own instant.

Two further areas have since landed. **Policy effectivity is evaluated at
`served_at` in all three layers** (`constraints_in_force`, `applicable`,
`resolve_effective_request`), claimed below. And **a deployment can now declare
its temporal boundary in its own configuration**: `ccf.temporal-boundary-policy`
is manifest-addressable and `ccf_config.yaml` gains a reserved
`temporal_boundary:` section, which is what makes ruling 11 livable — a rule that
refuses every undeclared deployment needs an authoring surface for the
declaration, and the alternative was weakening the rule.

**What is NOT true on this tree, stated so no reader infers it.** Nothing yet
CALLS the temporal-bound judgment: Gate 3's comparand is unchanged, composite
remaining validity is unchanged, and `PeeringAdmission.admit(now=)` is unchanged.
A deployment that declares the section registers a policy that **nothing reads
yet**, and a deployment that omits it is not refused yet. Those are the remainder
of step 5.

## ccf.products.refusal.TemporalBoundRefusal

- Surface: ccf.products.refusal.TemporalBoundRefusal
- Public surface: true
- Change type: added
- Before: absent — no governed refusal named a question reaching outside a declared temporal window, and no vocabulary token existed for one
- After: a `CCFContract` with a closed three-reason `Literal` (`temporal-boundary-undeclared`, `asked-at-outside-temporal-bound`, `decision-instant-outside-temporal-bound`), the canonical policy key, the trusted `served_at` it was judged at, and — for the two window reasons — the instant that fell outside and the declared bounds. The three defaulted members are declared **generation boundaries** (`HASH_TRANSPARENT_KEY: False`), because nothing predates this type: a transparent mark buys silence so that records written before a member existed keep their address, and no refusal of this kind has ever been written
- Why: `D-IMPL-358` step 5 with ruling 11. Three reasons rather than one because they are three different facts with three different remedies — an undeclared policy is the operator's to fix and the caller can do nothing about it, while an out-of-window question is the caller's. Collapsing them would send one of the two to the wrong party
- Migration: none. A new kind on a path nothing yet reaches; no existing refusal changes shape or address

## ccf.products.refusal.refuse_temporal_bound

- Surface: ccf.products.refusal.refuse_temporal_bound
- Public surface: true
- Change type: added
- Before: absent
- After: a **pure** judgment — it reads no clock and no registry — taking an already-resolved `PinnedTemporalBoundary | TemporalBoundaryUndeclared`, the trusted `served_at`, and both instants (`asked_at` and the derived decision instant), returning the refusal or `None`. `asked_at` is judged first so a question outside both is reported deterministically by the axis a caller controls most directly. The arithmetic is `ccf/peering/eligibility.py::_evidence_too_old`'s, reused rather than re-invented, which is what keeps two declared durations in this fabric meaning the same thing — and which fixes the reading of zero as the strictest bound rather than as unbounded
- Why: `D-IMPL-358` step 5. The judgment is separated from the resolution so that the instant and the policy both arrive as arguments and nothing about where they came from is decided here — the same split step 3 made between resolving a policy and pinning it
- Migration: none; no caller exists yet

## ccf.products.refusal.REFUSAL_KINDS

- Surface: ccf.products.refusal.REFUSAL_KINDS
- Public surface: true
- Change type: reshaped
- Before: twenty-seven kinds
- After: twenty-eight — `temporal-bound-refusal` joins, and `_PRE_ASSEMBLY_REFUSALS` gains the type because the judgment is pre-acquisition and pre-graph-read, so no candidate exists and no lineage is invented for it. The token was checked against all twenty-seven for the vocabulary's substring rule (no token may contain another): no collision
- Why: `D-IMPL-358` step 5. A refusal that is not in the roster cannot cross a door, be disclosed, or be given a status — the roster IS the vocabulary
- Migration: a consumer switching exhaustively on the kind gains one arm. Every structural gate over the vocabulary enumerated exactly what registration was owed and is green: the disclosure statement and minimal tables, the door's status map, the MCP parity check, and the per-kind envelope test

## ccf.products.resolver.RefusalRecorderProtocol

- Surface: ccf.products.resolver.RefusalRecorderProtocol
- Public surface: true
- Change type: reshaped
- Before: `record(...)` took `recorded_at` and no live instant, so a recorder had no way to state when a determination was actually made — and two of the five governed recorder families stamped live clock time into `recorded_at`, moving a refusal's dimension-1 boundary off the question
- After: a **required keyword** `served_at: datetime | None`, with no default and explicitly nullable. Required so no site can omit it; nullable so a surface that genuinely has no live instant asserts that rather than being assumed. The shape follows the ruling this module already quotes — `D-IMPL-264` amendment 1, *"No intermediate layer may manufacture the marker from omission."* `recorded_at` is untouched and is NOT a synonym: the question's instant bounds the record and the live instant travels beside it
- Why: `D-IMPL-358` step 5. One invocation reads one clock, and every refusal it produces must carry that instant rather than a fresh one — a recorder that read its own clock would put two instants in one determination
- Migration: **every conforming recorder and every caller must pass it**, which the required keyword makes a type error rather than a silent default. All five governed families are migrated: the resolver's own path, `OpenedProduct`'s address refusal, the delivery boundary's four sites, the typed raised refusal, and the entitlement refusal. The most consequential repair is the address refusal, which had `request.asked_at` in scope three lines above and stamped `recorded_at=self._clock()` anyway

## ccf.products.disclosure.EXTERNAL_STATEMENTS

- Surface: ccf.products.disclosure.EXTERNAL_STATEMENTS
- Public surface: true
- Change type: reshaped
- Before: no statement for the new kind, which the closure gate refuses
- After: one statement covering all three reasons, chosen so that it does not tell an external consumer a tenant is MISCONFIGURED — that is the operator's fact and exactly the internal state the minimal level exists to withhold. `PERMITTED_AT_MINIMAL` permits the two declared bounds and nothing else, on the `ttl-refusal` precedent: a declared ceiling is actionable, the fabric's own instants are not, and the policy key never crosses
- Why: `D-IMPL-358` step 5 with `D-IMPL-254` — what crosses a consumer boundary is the disclosure step's decision and no refusal type's
- Migration: none for existing kinds. At minimal, the undeclared reason discloses nothing actionable, correctly: nothing the caller could do would fix it

## ccf.products.constraints.constraints_in_force

- Surface: ccf.products.constraints.constraints_in_force
- Public surface: true
- Change type: reshaped
- Before: `constraints_in_force(control_plane, *, asked_at)` — the effectivity window was selected at the question's own instant
- After: `constraints_in_force(control_plane, *, served_at)`. A REQUIRED keyword with no default; the parameter is renamed rather than added beside, because its only job is the effectivity window and a retained `asked_at` would be an unused parameter inviting the two readings to diverge. `_require_aware` follows the instant — there is no implicit UTC in this fabric, and comparing a naive instant against an aware window answers for the wrong hour rather than raising
- Why: `D-IMPL-358` step 5 ruling B. A constraint that became effective after a question was asked but before it was answered now governs the answer, so a tenant that tightens a bound at noon has it in force at noon rather than from whenever the oldest in-flight question happened to be asked
- Migration: **every caller passes `served_at`, enforced as a type error rather than a silent default.** The superseded reasoning (`D-IMPL-253` Q6 — *"asked_at, absolutely. Otherwise replay of the same historical decision can resolve a different policy"*) is retained in the docstring because it names the risk that had to be answered before the instant could move; that risk is closed by a different mechanism, which is why the move is safe. Replay never re-derives effectivity: it resolves each binding at the version the record pinned, `ReplayResolver` has no `resolve_latest` to reach for, and nothing under `ccf/replay/` imports this module

## ccf.products.constraints.applicable

- Surface: ccf.products.constraints.applicable
- Public surface: true
- Change type: reshaped
- Before: `applicable(constraint, *, product_class, tenant, perspective_role, intent, asked_at)`
- After: the same four axes with `served_at` in place of `asked_at`. The four axes are unchanged; only the window reading moved, and the docstring now states which ruling amended which
- Why: `D-IMPL-358` step 5 ruling B. `applicable` and `constraints_in_force` share one `_in_window` reading precisely so the fabric cannot answer *"which policy was in force?"* two ways at two layers — so the instant had to move in both or in neither
- Migration: callers pass `served_at`. Measured: `applicable` has two executable callers and both are inside this module, so no external caller is affected

## ccf.products.constraints.resolve_effective_request

- Surface: ccf.products.constraints.resolve_effective_request
- Public surface: true
- Change type: reshaped
- Before: no instant parameter — the function took `request` and re-checked applicability at `request.asked_at` on its own
- After: a REQUIRED keyword-only `served_at: datetime`. **This is the parameter whose absence would have made the whole change cosmetic.** The function independently RE-EVALUATES applicability, so a constraint set selected at `served_at` upstream would have been silently re-filtered at `request.asked_at` here — the selection undone with no error and no test red. A default would have let exactly that pass
- Why: `D-IMPL-358` step 5 ruling B, which names all three layers for this reason. The function stays pure: the instant arrives as an argument and no clock is read
- Migration: every caller passes `served_at`, including `ReferencePolicyConstraintResolver.resolve` and the `PolicyConstraintResolver` Protocol, which gain the same required keyword. A deployment substituting its own resolver conforms to the new signature or fails the Protocol check

## ccf.controlplane.artifacts.TEMPORAL_BOUNDARY_POLICY

- Surface: ccf.controlplane.artifacts.TEMPORAL_BOUNDARY_POLICY
- Public surface: true
- Change type: added
- Before: the constant existed only in `ccf.controlplane.temporal_boundary` (step 3) and was absent from the module that exposes the SDK's artifact-class catalog, so `SDK_ARTIFACT_CLASSES` named a class no reader of `ccf.controlplane.artifacts` could see
- After: the constant is re-exposed here and listed in `__all__`. The contract, the canonical key helper and the resolution/pinning machinery all stay in `ccf.controlplane.temporal_boundary`; **only the constant is re-exposed**, and that module imports `ccf.controlplane.artifact_base` rather than this one, so the direction stays acyclic. This follows `RESOLUTION_SPEC`, whose contract likewise lives in another module (`ccf.assembly.worker`)
- Why: `D-IMPL-358` step 5 section A1 makes the class manifest-addressable, and `tests/deployment/test_class_lookup.py` takes this module as its source of truth for *"the real constant"* when it asserts object identity against `SDK_ARTIFACT_CLASSES`. Exposing the constant satisfies that identity assertion with the real object. The rejected alternative was widening the control to walk the whole `ccf.controlplane` package: measured, that pulls in `ccf.entity-invalidation-register`, which is in neither SDK mapping, and turns a green control red on code this step does not own
- Migration: none. An additive export; no existing name changes, and the class's own module is unchanged

## ccf.controlplane.artifacts.DeploymentConfig

- Surface: ccf.controlplane.artifacts.DeploymentConfig
- Public surface: true
- Change type: reshaped
- Before: no way to declare a temporal boundary in configuration, so every config-driven deployment was undeclared under ruling 11 with no authoring surface to fix it
- After: an optional reserved section `temporal_boundary: Mapping[str, Any] | None = None`, marked `HASH_TRANSPARENT_KEY: True`. Transparent at its `None` sentinel, so **a config that omits the section keeps its pre-change content identity byte-for-byte** — measured on the existing reserved sections, which still derive exactly as before. Absence means *undeclared*; it does not mean unbounded and it synthesizes no policy. The body is the step-3 contract verbatim: no `semver` is injected, no tenant or key or registration metadata is accepted inside it, and the SDK supplies no duration default
- Why: `D-IMPL-358` step 5 section A. Ruling 11 admits no exception, so the declaration needs a home in the document an operator actually edits
- Migration: none required of an existing config — the field is optional and transparent at absence. A deployment that wants a bound adds the section; once enforcement lands (the remainder of step 5), a config-driven deployment without one will refuse

## ccf.deployment.keys.DeploymentKeys

- Surface: ccf.deployment.keys.DeploymentKeys
- Public surface: true
- Change type: reshaped
- Before: no field naming the derived temporal-boundary key
- After: `temporal_boundary: str | None` — the canonical key the derivation minted, or `None` when the config declared no section. The key is always `temporal_boundary_policy_key(tenant_id=config.tenant_id)`; an author cannot override it, and stating `key`, `class_id`, `role` or `registration` inside the section is **refused by name** rather than ignored or honored. A section present with no top-level `tenant_id` is refused rather than keyed class-only or given an invented tenant
- Why: `D-IMPL-358` step 5 section A7. A caller that booted a deployment needs the address the policy was registered under without re-deriving it, and re-derivation at the call site is how two spellings of one key appear in one fabric
- Migration: additive; a reader that ignores the field is unaffected
