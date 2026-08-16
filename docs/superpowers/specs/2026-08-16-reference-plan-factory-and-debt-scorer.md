# Reference `ProjectionPlanFactory` and `AssemblyDebtScorer` — honouring §11 so a deployment can be pure configuration

- **Date:** 2026-08-16
- **Status:** Approved by Dave, 2026-08-16
- **Supersedes:** the `D-IMPL-141` proposal as written (`module:attribute`
  factories in `binding.yaml`) — **rejected**, see §2
- **Blocks:** Phase 17 waves 6 and 7. The first example cannot land until this
  does.

---

## 1. The problem

`~ccf.products.resolver.GovernedResolver` takes thirteen constructor
arguments. Measured on the tree, 2026-08-16:

| Source | Count | Arguments |
|---|---:|---|
| The booted fabric | 3 | `fabric`, `control_plane`, `artifact_store` |
| Plain data | 8 | `product_class_key`, `request_contract_key`, `operator_parameter_keys`, `policy_bundle_key`, `replay_record_class`, `query_pin_class`, `max_ttl_seconds`, `product_ttl_seconds` |
| **Behavioral** | **2** | **`plan_factory`, `debt_scorer`** |

Eleven of thirteen are fabric-supplied or declarable. The two behavioral
arguments are the whole problem: **`ProjectionPlanFactoryProtocol` and
`AssemblyDebtScorerProtocol` are declared in `src/ccf/products/resolver.py` and
nothing in `src/` or `runtime/` implements them.**

So every deployment must supply both in Python. The Phase 17 test fixture
demonstrates the cost: `tests/client/fixtures/deployment/resolver.py` is **295
lines**, and its content is a projection, a plan factory and a debt scorer —
not domain material, but mechanism the SDK declined to ship.

**This violates CLAUDE.md §11 in its own words:** *"Reference implementations
ship alongside Protocols. For every pluggable substrate, the SDK ships a
working reference impl."* Two Protocols have none, and they are exactly the two
that force producer Python back into `deployment/`.

**It is also the 722-line example wearing a smaller suit.** Wave 2 moved
assemble → gate → serve into the SDK (`D-29`) and the example shrank
dramatically. But behavior the SDK declared and did not implement stayed the
deployment's problem, so the folder a reader is told to ignore still contains
code they will feel obliged to read.

## 2. What was rejected, and why

`D-IMPL-141` proposed that `binding.yaml` carry `resolver:` and `question:` as
`<module-path>:<attribute>` references — factories the loader imports and calls.

**Rejected by Dave, 2026-08-16.** That reintroduces precisely the shape
declined during the 2026-08-15 brainstorm, where the chosen option was *"the
SDK ships one generic resolver — the deployment folder stays pure
configuration, no Python in it, nothing to discover,"* and the declined option
carried the recorded cost: *producer Python comes back into `deployment/`, so a
reader opening that folder sees a hook they think they must understand.*

**The tension the proposal identified was real**, and measurement confirms half
of it: a fully generic resolver cannot invent domain vocabulary. But
measurement also dissolves the other half — see §3. The resolution is not an
exception to the no-Python rule; it is the SDK honouring §11.

## 3. What measurement settled

**Nothing in the request path requires computation.**

- `~ccf.projection.plan.Perspective` is **two plain strings** —
  `principal_id: str`, `role: str`. Fully declarable.
- `~ccf.products.request.ProductRequest` carries `schema_name`,
  `schema_version`, `subject`, `intent`, `freshness`, `asked_at`, `parameters`.
  `schema_name`/`schema_version` come off the request's product id;
  `subject`/`intent`/`freshness` are **plain `str`** and declarable;
  `asked_at` is a `datetime` the SDK already owns through `as_of` (`D-04`);
  `parameters` come from the client.

So `question:` and `perspective:` do **not** need factories. The only genuine
gap is the two unimplemented Protocols.

## 4. Goal

**`GovernedResolver` is fully usable with zero Python in `deployment/`.**

After this work the first example's deployment directory contains exactly:

```
deployment/
  ccf_config.yaml
  binding.yaml        # pure data
```

## 5. Scope — deliberately narrow

| Item | Action |
|---|---|
| `ProjectionPlanFactoryProtocol` | Ship one reference implementation in `src/` |
| `AssemblyDebtScorerProtocol` | Ship one reference implementation in `src/` |
| Selection / defaulting | The two become the **defaults** inside `GovernedResolver` (or a thin `build_governed_resolver(...)` helper). A deployment is never required to name them. |
| `binding.yaml` | Stays **data-only**. May later gain optional keys to override the defaults; not required for v0. |
| Domain logic | **Forbidden.** Both reference implementations stay pure mechanism. |

## 6. Design decisions to lock

**Defaulting strategy.** `GovernedResolver` — or a thin
`build_governed_resolver(...)` helper — supplies the two reference
implementations automatically when the caller does not pass them. **A
deployment that provides only data never has to know the Protocols exist.**

**Location.** Both live under `src/ccf/` beside the Protocols they implement,
or in a clearly named package. They are **part of the public mechanism
surface**, not hidden test fixtures.

**What each must do, and its boundary:**

- **Plan factory** — construct the projection plan from the already-loaded
  Control Plane artifacts plus the request. **No domain thresholds, no business
  rules.**
- **Debt scorer** — perform the standard debt assessment from the assembly
  result and the half-life / debt-profile artifacts already in the Control
  Plane. **Pure mechanism.**

The No-Hardcoding Rule (CLAUDE.md §6.4) is the sharpest exposure here, exactly
as it was for `D-29`'s composition: a reference implementation that bakes in a
threshold, a role, or a product class is the defect this work exists to remove,
reappearing one layer down.

**No new discovery or registration machinery in this change.** Simple defaults
are sufficient for v0. Optional override keys in `binding.yaml` may be added
later if a real need appears; they are out of scope now.

**`binding.yaml` remains data-only.** This work is what *makes* the data-only
path viable; it does not itself introduce `module:attribute` factories.

## 7. Out of scope for this pause

- Multiple alternative implementations, or a general plugin registry
- Pluggable registration / entry-point discovery
- Any change to the client surface, `WireOutcome`, or the refusal envelope
- Perspective / request vocabulary — already confirmed declarable as data (§3)
- Example work — **wave 7 stays blocked until this lands**

## 8. Success criteria

1. `GovernedResolver` can be constructed and used with **only fabric objects
   plus plain data**.
2. A deployment directory containing only `ccf_config.yaml` and a data-only
   `binding.yaml` produces a **working gated product**.
3. **No Python files remain under the first example's `deployment/`.**
4. Existing tests stay green, and **new tests prove the reference
   implementations are actually used as defaults** — not merely that they
   exist. (A default nothing exercises is the phase's signature defect: a check
   that stops checking without going red.)
5. CLAUDE.md §11 is no longer violated for these two Protocols.

## 9. Suggested plan shape

- **`17-11`** — reference `ProjectionPlanFactory`
- **`17-12`** — reference `AssemblyDebtScorer`
- **`17-13`** — wire both as defaults into `GovernedResolver` (or the helper),
  plus tests proving a data-only deployment works end to end

After `17-13` is green, waves 6 and 7 may resume.

## 9a. Risks and watch items

Three, each of which has a precedent in this phase rather than being
hypothetical:

1. **The reference plan factory must not hard-code any domain plan shape.** It
   stays driven by Control Plane artifacts plus the request. This is the same
   exposure `D-29`'s composition carried, one layer down — and the reason that
   plan required a per-constant justification.
2. **The reference debt scorer must use the existing half-life / debt-profile
   machinery**, not invent new scoring rules. `D-IMPL-47` already rules the
   scorer surface (versioned scorers, Control-Plane-updatable class bindings,
   replay pinning the scorer version in force); a reference implementation
   *implements* that, it does not re-decide it.
3. **Defaulting must be explicit and testable**, so a future override path does
   not silently break. This is the phase's signature defect waiting to happen:
   a default that nothing exercises is a check that stops checking without
   going red. Success criterion 4 exists for exactly this — the tests must
   prove the defaults are *selected and used*, not merely that they exist.

## 10. Consequence for `D-IMPL-141`

The entry in `docs/DECISIONS.md` is **rejected as proposed** and must be
rewritten to record: the rejection and its reason, the measurement that
dissolved the `question:`/`perspective:` half of the argument, and the
data-only `binding.yaml` shape that replaces it. `binding.yaml` survives — as a
**data document**, retaining the parts of the proposal that were sound: not a
Control Plane artifact (unregistered, not content-hashed, no `semver`, never
reaching Decision Replay dimension 2), a strict loader that refuses an unknown
key by name, and path containment that refuses absolute paths, `..` segments,
and plain names resolving outside the root.
