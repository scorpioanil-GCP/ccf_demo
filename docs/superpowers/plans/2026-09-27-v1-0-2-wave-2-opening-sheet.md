# CCF SDK v1.0.2 — Wave 2 opening sheet: the fabric clock

> **Authorization.** Dave, 2026-09-27: *"WAVE 2 — OPENING-SHEET GO ONLY … This
> authorizes documentation and read-only code inspection—not implementation."*
> Nothing in this document has been implemented. No file outside `docs/` was
> written to produce it.
>
> **STATUS: ACCEPTED, 2026-09-27, with all twelve §6 choices RULED.** Recorded at
> `D-IMPL-358`. Implementation GO proceeds under that entry and under the locked
> sixteen-step sequence in §7. Two rulings amend the accepted design and say so:
> ruling 2 (D6(d)'s placement) and ruling 9 (`PeeringAdmission` joins scope).

**Baseline:** `51158a5890c120b91d30d36c96b4adf629b2ac67` (tree `0385822e`),
`origin/main`, the Wave 1 close.
**Design of record:** `docs/superpowers/specs/2026-09-25-v1-0-2-security-remediation-design.md`
§4, accepted and locked at `D-IMPL-356`. **This sheet reuses that design.** It
does not replace it and offers no menu of approaches. What it adds is the map
onto the current code, plus the measured contradictions and the unresolved
choices the design does not settle.

**Decision id:** **`D-IMPL-358`**, verified free. The spec's §10 reserves it for
"Wave 2: the fabric clock (D1–D13)". It is **not written** in `docs/DECISIONS.md`
(written: `357`, `361`; unwritten: `358`, `359`, `360`, `362`). The
`D-GATE-357` entry's closing line *"Next free decision id `D-IMPL-362`"* names
the highest **unreserved** id and does not conflict — stated here so a later
reader does not read one.

**Scope:** `SEC-008`, `SEC-010`, `SEC-011` together as **one integrated wave**
with **separate acceptance criteria and finding dispositions per SEC id**, per
Dave. The `SEC-019` rider is retained. `SEC-011` Gate 2 keeps its
assembly-path-integrity disposition; the substantive repair is Gate 3.

---

## 0. How to read this sheet

**Every line number below was resolved by SYMBOL against the baseline.** The
design's citations were written against an older commit and roughly seventy of
them are stale — in the resolver by 160–330 lines. Do not copy a line number
from the design into an implementation brief; the mapping in §2 is the current
one. Where a design claim and the code disagree, §3 states it as a measured
contradiction rather than silently correcting it, because several of them change
what the work is.

**Two prior habits this sheet is written against.** Wave 1's briefs carried six
defects that review caught — a method that did not exist, controls that were
vacuous by construction, a regex population that was measured on the wrong set.
So: every symbol named here was confirmed to exist, every count was measured on
the baseline rather than carried, and §4 states for each proposed control the
single `src/` edit that must redden it. A control whose reddening edit cannot be
named is not yet a control.

---

## 1. The defect, stated on the baseline

The design's §4.1 opens *"The served path reads no clock."* **Measured, that is
true only of the non-composite path, and the sharper statement is the one the
wave's exactly-once criterion needs:**

> The governed serve path reads **exactly one** clock, `admission_clock()` at
> `src/ccf/products/resolver.py:2633`, and that read sits **inside**
> `if registered.requires:` (`:2625`). **For every non-composite product the
> resolver reads no clock whatsoever.** Every other instant it uses derives from
> the caller.

The caller-derived instants, all resolved on the baseline:

| use | symbol | file:line | instant |
| --- | --- | --- | --- |
| decision instant | `GovernedResolver._decision_instant` | `src/ccf/products/resolver.py:2225-2247` | falls back to `request.asked_at` (`:2239-2240`, `:2242-2243`); parses a declared value at `:2244-2246` with **no awareness check and no bound** |
| as-of graph read | — | `src/ccf/products/resolver.py:2581-2583` | caller's |
| Gate 3's `now` | `run_gates(now=decided_at)` | `src/ccf/products/resolver.py:3149` | caller's |
| composite child remaining validity | `compose_children(evaluated_at=decided_at)` | `src/ccf/products/composite.py:2124`, caller at `src/ccf/products/resolver.py:2945` | caller's |
| policy effectivity | `constraints_in_force(asked_at=…)`, `applicable(asked_at=…)` | `src/ccf/products/constraints.py:1525`, `:1536`; bound at `:562-576` | caller's, half-open |
| debt | the freshness scorer | `src/ccf/halflife/decay.py:641-643` | caller's |
| record, served | `build_replay_record(recorded_at=decided_at)` | `src/ccf/products/resolver.py:3344` | caller's |
| record, refused | `_record_refusal(recorded_at=request.asked_at)` | `src/ccf/products/resolver.py:3627` | caller's |

### 1.1 Gate 3's degeneracy is worse than the design says, and not what its wording implies

**Gate 3 is already structurally two-sided.** `src/ccf/products/gates.py:1385-1386`:

```python
ceiling = now + timedelta(seconds=artifact.seconds)
if now < candidate.expires_at <= ceiling:
```

That is `(now, now + MAX_TTL]` — both sides present. `now` is already a
**required keyword** on `run_gates` (`src/ccf/products/gates.py:1017-1021`) and
`run_federated_gates` (`:1142-1148`).

So **"make Gate 3 two-sided" is not the work, and writing it into a brief would
ask for a change that is already there.** The defect is the **comparand**: on a
`from_decision` class `expires_at` and `now` derive from the same caller-supplied
instant, so the inequality cannot constrain anything absolute — back-dating moves
both operands together. One mapper put it more sharply than the design does:
this is not a reduction to a weaker temporal check but **a reduction to a pure
declaration well-formedness check**.

**D3's "required on the gate runners" therefore describes the VALUE's provenance,
not the addition of a parameter.**

### 1.2 Two things the design treats as modifications are CREATIONS

Both measured by exact-word grep on the baseline:

- **`served_at` does not exist.** Zero hits across `src/` and `runtime/`.
- **`TemporalBoundaryPolicy` does not exist.** Zero hits across `src/`,
  `runtime/`, `examples/` and `tests/`.

The second has a consequence §4.6 does not carry: *"every example tree that
declares no `TemporalBoundaryPolicy` refuses"* names **all 38 example trees**,
not the "about 25" the design estimates.

---

## 2. Where each timestamp is obtained, checked, persisted and replayed

### 2.1 Clock sites, complete, on the baseline

| site | file:line | posture |
| --- | --- | --- |
| `_utc_now` | `src/ccf/products/resolver.py:1749-1758` | the module's only wall-clock read, and it is a **default**, not a call site |
| `admission_clock` field | `src/ccf/products/resolver.py:2132` | no constructor default; wired at `build_governed_resolver` `:4222`, passed `:4846`, `:4903` |
| `admission_clock()` read | `src/ccf/products/resolver.py:2633` | **the one clock read inside `__call__`**, composite branch only |
| `OpenedProduct._clock` | `src/ccf/products/product.py:468`, `:602`, `:749` | one injected clock used **twice**: `:602` hands it to the resolver as `admission_clock`; **`:749` calls it directly** for the door's own address refusal, on a path that never enters `__call__` |
| delivery boundary | `runtime/ccf_runtime/authz/delivery_boundary.py:300` | `determined_at = entitlement_source.clock()`, read at `:386`, `:477`, `:626`, `:1007` — all **outside** `__call__` |
| client adapters | `src/ccf/client/adapters/inprocess.py:427`, `src/ccf/client/adapters/mcp_stdio.py:251` | `asked_at = request.temporal_boundary or datetime.now(UTC)` — client-side resolution of a deferred instant (`D-IMPL-159`) |
| ingress | `src/ccf/signal/acquisition.py:235`, `src/ccf/signal/mcp_source.py:66-72`, `runtime/ccf_runtime/cdc/adapter.py:155` | injected seams defaulting to `datetime.now(UTC)` |
| peered admission | `src/ccf/peering/admission.py:898-904` | `now` is a **parameter**; docstring `:911-914` declares the caller-clock posture **deliberate** |

### 2.2 Replay holds, and what it does not do

`src/ccf/replay/engine.py:78` — *"Nothing here reads a clock, and nothing here
resolves 'latest'"* — **resolves exactly and is TRUE of that module**: zero
`run_gates`, zero `datetime.now`, zero `GovernedResolver` import, store calls
limited to `get`/`resolve_uri`. Replay drives `ProjectionEngine` over a
`SnapshotReader` directly (`:1417-1440`).

Held and unmoving: `recorded_at`, `ttl_anchor_at`, `expires_at`,
`graph_snapshot_at`, the refusal's `temporal_boundary`.

`ContentGenerationPath` is dimension 5 at `src/ccf/replay/record.py:1252`, fields
`:1455-1483`. The nearest precedent for an added instant is
`ChildResolution.child_admitted_at` at `:1117-1119`.

### 2.3 The writer

`AssemblyWorker` — **four** admitting entry points, not two:

| entry point | file:line | instant it holds |
| --- | --- | --- |
| `ingest` | `src/ccf/assembly/worker.py` (see §3.6) | `envelope.ingestion_timestamp` |
| `ingest_admitted` | `src/ccf/assembly/worker.py:776` | same; **zero callers in `src/` or `runtime/`** |
| `admit_entity_claim` | `src/ccf/assembly/worker.py:622` | only `claim.observed_at` |
| `admit_relationship_claim` | `src/ccf/assembly/worker.py:638` | only `claim.observed_at` |

`refuse_foreign_envelope` (`src/ccf/signal/envelope.py:76`) is the SDK's **only** existing
check on the write stamp, and it has **zero controls**.

---

## 3. MEASURED CONTRADICTIONS against the accepted design

Each is a measurement, not an opinion. Several change the work.

### 3.1 The refusal-recorder conflation is FIVE sites, not one-plus-two

§4.3(4) says *"the only conflation site is `src/ccf/replay/record.py:2003-2005`"*
and names two refusal-recorder call sites. **Measured: five.** The conflation
itself resolves exactly — `src/ccf/replay/record.py:2002-2005`,
`boundary = product.temporal_boundary if product is not None else recorded_at`,
so for every refusal dimension 1's `temporal_boundary` **is** `recorded_at`, and
it is hashed into `graph_snapshot_id` — it is the `temporal_boundary` key of the
`content_hash` call in `src/ccf/replay/record.py::ContextFabricSnapshot.build`. **Three of the five are
unnamed by the design, and all three stamp a clock into a governed refusal's
dimension-1 identity** — two of them with the question's `asked_at` already in
hand. `govern_absence` (`runtime/ccf_runtime/authz/delivery_boundary.py:412`) and `govern_entitlement`
(`:682`) are among the unnamed.

### 3.2 The design contradicts itself on `served_at`'s hash transparency

§4.3(4) states `served_at` is marked `{HASH_TRANSPARENT_KEY: True}` **and** cites
`child_admitted_at` as "the posture O3 already chose". Measured:
`child_admitted_at` at `src/ccf/replay/record.py:1117-1119` is marked
**`{HASH_TRANSPARENT_KEY: False}`** — a declared generation boundary. **These are
two different postures with different compatibility consequences**
(transparent-at-sentinel preserves historical addresses; a generation boundary
moves every address). **RULED (ruling 1): transparent-at-sentinel** — deliberately a different mark from `child_admitted_at`.

### 3.3 §4.5's "minted by the record builder" is not what the code does

`build_replay_record` (`src/ccf/replay/record.py::build_replay_record`) **never resolves or mints a
`PolicyBinding`** — it receives the tuple and writes it (`:2032-2035`). Minting
happens at two other sites. So "the `TemporalBoundaryPolicy` key+version is
minted by the record builder" describes a builder that does not mint.

### 3.4 Option (d)'s scope is stated for two entry points; the writer has four — and it cannot see a tenant

Three measured problems with D6(d) as written:

1. **Four entry points** (§2.3). `admit_entity_claim` and
   `admit_relationship_claim` carry no `ingestion_timestamp` at all; their only
   instant is `claim.observed_at`, which is the as-of cut key.
2. **The writer never learns a tenant, so it cannot resolve a per-tenant policy
   once.** `AssemblyWorker.__init__` (`src/ccf/assembly/worker.py:595-611`) stores writer,
   resolution, registry and the pinned bundle — **nothing tenant-shaped**.
   `boot(tenant_ids=…)` (`src/ccf/boot.py:303`) holds the roster and does not pass it.
   D5 rules the policy **per-tenant**; D6(d) puts the guard in a component with
   no tenant. **This is the sheet's most load-bearing gap.**
3. **Resolving per envelope writes an audit event per envelope.**
   `ControlPlaneRegistry.resolve_latest` (`src/ccf/controlplane/registry.py:815-835`)
   calls `self._record(action="resolve_latest", …)` on **both** the miss (`:827`)
   and hit (`:832`) legs, and the paved road ingests one envelope at a time.

### 3.5 `D-IMPL-159`'s stated blocker is unenforced — and may forbid D6(d)

`docs/DECISIONS.md:492` records why the clock was not moved into the door: an
`__ccf_mode__ = "algorithmic"` module *"may not read a clock at all"*. Measured:
**no lint enforces this.** `tools/lints/algorithmic.py` has no clock rule (CINV-03
is about LLM imports), and **two algorithmic-tagged modules already call
`datetime.now(UTC)`**. `src/ccf/assembly/worker.py:61` carries that mode marker.
**RULED (ruling 2): `D-IMPL-159` REMAINS BINDING, and D6(d)'s placement is
AMENDED** — the guard moves to the governed ingress/admission boundary with an
injected fabric clock. The unenforced rule is upheld, not retired.

### 3.6 §1.3's claim that `src/ccf/assembly/worker.py` is byte-identical to v1.0.0 is false

`git diff --stat v1.0.0 -- src/ccf/signal/envelope.py` is empty; `src/ccf/assembly/worker.py` is
**not**. Every `src/ccf/assembly/worker.py` line number in the design is shifted — including
`:495`, cited as `observed_at = ingestion_timestamp`, which on the baseline is a
different statement in a different method (`SpecDrivenEntityResolution.resolve`).

### 3.7 D8 ships with no control and no sabotage, and the gap is measured

§4.9's red-when-fixed list and sabotage paragraph contain **not one entry about
the debt instant**. Measured consequence: with a plugin making
`FreshnessScorer.score` read a wall clock instead of the instant handed to it,
the suite is **153 passed / 0 failed / 0 errors** — unchanged. **The D8 ruling is
unprovable as the design stands.**

Worse, the design's own cited symbols disagree on what `now` means:
`freshness`'s docstring calls it *"The decision instant"* (`src/ccf/halflife/decay.py:641-643`)
while `AssemblyDebtScorer`'s calls it *"the as-of boundary … under
`GovernedResolver` it is the question's `asked_at`"*. And the paved road makes it
degenerate: `observed_at == asked_at` by refusal (`src/ccf/signal/envelope.py:113`,
`src/ccf/assembly/worker.py:674`), so under the default `decay_basis: observed-at` the freshness
factor is **exactly 1 for evidence of any real-world age**.

### 3.8 The example and estate premises do not hold as written

- **The living-reference roster does not exist in the record.** Exactly **one**
  tree is ruled live reference — `s1-01`, at `docs/DECISIONS.md:4705`
  (`D-IMPL-355` (2), Dave verbatim). `cp-00`…`cp-04` are ruled frozen
  (`D-IMPL-261`). **32 of 38 trees have no disposition.** `CLAUDE.md` §9's "v1
  suite" names 10 trees against 38 in the tree and omits `cp-06`…`cp-24`
  entirely.
- **No census instrument exists in-tree.** §8.2/§8.3 require before/after
  watermarks and a per-node red census; `tools/` holds no estate, watermark or
  skip-census tool. Wave 1's instruments lived in a session workspace.
- **The estate-gated run is silently partial.** Two gating idioms exist, and
  **10 modules / 173 collected nodes** use the module-level
  `pytest.mark.skipif` form that **ignores `CCF_REQUIRE_ESTATE`**.
- **The write fence is narrower than `CLAUDE.md:1035-1039` asserts.**
  `DISPOSABLE_STORE_ENV` is two names (`tests/conftest.py:265`);
  `CCF_TEST_MONGO_URI` (`:231`) is **unfenced** while eight estate-gated trees
  read curated Mongo `fibo_v2`. The guard's host test is a substring match
  (`tests/examples/estate_guard.py:81`), not parsed host equality.
- **A red-when-fixed entry cannot run.**
  `tests/examples/test_gate_two_divergence.py:261` is on §4.9's list but the
  module is `pytest.mark.archived` (`:95`) and deselected
  (`tests/conftest.py:567-574`) — **zero collected nodes**.
- **§4.6's instant census is off by two.** Measured: 17 `asked_at` literals in
  read question artifacts across 15 trees, **plus** `examples/hw1-companies-over-revenue/deployment/binding.yaml:45`
  and `examples/hw1-harness-clients/runner/question.yaml:71` = 19 across 17 trees. The
  design's total is right; its population is not.

### 3.9 Smaller, still load-bearing

- **Gate 2's NOT-A-GAP disposition holds, and the code supports a STRONGER
  statement** than the design makes on the non-composite path. But Gate 2 retains
  **one live failure mode the design does not name**: the composite widening at
  `src/ccf/products/resolver.py:3144-3145`, where `engine_resolved` becomes
  `execution.operators_invoked | composed.admitted_operators` against a claim side
  of `composed.lineage` (`:3048-3051`).
- **The SEC-019 rider understates its blast radius by one dimension.** The skip at
  `src/ccf/products/constraints.py:1092-1093` is downstream of `applied.add(_source_of(pinned))`
  (`:1050`), so an un-held constraint **still becomes a `PolicyBinding` in replay
  dimension 2** (`src/ccf/products/resolver.py:3661-3666`).
- **`EligibilityEvidencePolicy`, the artifact shape D5 copies, is itself resolved
  UNPINNED**: `src/ccf/peering/eligibility.py:431` discards the version and no
  `PolicyBinding` is minted for it anywhere.
- **A false rationale already ships.** `tests/products/test_delivery_determinism.py:265-269`
  asserts `a.recorded_at == b.recorded_at` under the reason *"the governed path
  reads no clock at all"* — false on the baseline for five refusal sites,
  independent of this wave.
- **`src/ccf/products/resolver.py:2192-2195` is already false**, claiming the serve path reads
  `admission_clock` *"exactly once per admission"*.
- **Q6's words are quoted verbatim in shipped source** at
  `src/ccf/products/constraints.py:1276-1278`. D1 amends exactly that reading, so the amendment
  has a code-comment obligation the design lists only as "prose drift".

---

## 4. Tests: what exposes the defect, what replaces it, what sabotage proves it

**The rule this section is written under:** for every control, name the single
`src/` edit that must redden it. Wave 1 shipped a control that stayed green while
the entire behavioural core was reverted; the discipline that caught it was
exactly this.

### 4.1 Controls that pin today's defective behaviour (they must be MIGRATED, red-when-fixed)

| control | what it pins | why it reddens |
| --- | --- | --- |
| `tests/products/test_delivery_determinism.py:260-269` | two runs of one question record at one instant | a trusted clock makes two serves two records; **its stated reason is also already false** (§3.9) |
| `tests/products/test_policy_constraint_resolver.py:421-440` | *"exactly the property replay would lose if effectivity were evaluated at 'now'"* | D1(a) **amends that reading** |
| `tests/products/test_d_impl_341_ttl_anchor.py:350` | mixing floor measured from the decision instant, parametrized (720s/False, 540s/True) | D8 moves mixing to `served_at` |
| `tests/products/test_refusal_envelope.py:431` | `set(envelope.fields) == {"expires_at","now","max_ttl_seconds"}` | `TTLRefusal` gaining `served_at`; **neighbouring assertions in the same block also read the roster** |
| the nine record-shape pins | the top-level record shape | a new dimension-5 field. Roster resolved so it can be edited rather than re-derived: `tests/replay/test_attestation_pin.py:339`, `tests/replay/test_adapter_pin.py:126`, and seven more |

### 4.2 Controls the wave must CREATE, each with its reddening edit

| control | reddening `src/` edit |
| --- | --- |
| the serve path reads the fabric clock **exactly once**, on the non-composite path too | delete the hoist; the read returns to `if registered.requires:` |
| effectivity is judged at `served_at`, the as-of read at `asked_at` | swap either instant for the other |
| Gate 3 refuses a back-dated question | pass `decided_at` as `now` again |
| a tenant with no `TemporalBoundaryPolicy` refuses | make undeclared mean unbounded |
| the writer refuses an out-of-window envelope **and never restamps it** | replace `envelope.ingestion_timestamp` in the guard |
| **the debt instant** — absent from §4.9 entirely | make `FreshnessScorer.score` read a wall clock. **Measured today: 153/153 green, so this control does not exist** |
| replay reads no clock and resolves no latest | add a `datetime.now` to the replay path; widen the existing control to `src/ccf/replay/environment.py:118`/`:127`, which today's `resolve_latest`-spelled check misses |
| `served_at` absent/sentinel preserves a historical address | mark the field a generation boundary |

### 4.3 Sabotage

The design's own sharpest sabotage stands: **a second clock read in the resolver**
— not anything in replay — because a carried `served_at` is reproducible while a
re-derived one is not. Add, from the mapping: the composite-branch hoist reverted;
the writer's guard reading a second clock; and the `HASH_TRANSPARENT_KEY` flip on
`served_at`.

**No lint forbids a clock read anywhere in the tree** (§3.5). §4.3(1)'s "No second
clock anywhere" therefore has **no instrument**.
`tests/authz/test_delivery_boundary.py:793-820` shows the shape one would take.

---

## 5. Live reference vs frozen, and the estate plan

**RULED (ruling 7).** `s1-01` is the only live reference (`D-IMPL-355` (2));
`cp-00`…`cp-04` are frozen (`D-IMPL-261`); **the other 32 are UNDISPOSITIONED —
neither implicitly frozen nor implicitly live.** Core Wave 2 implementation
proceeds without repairing them.

**The estate run's disposition rules, per ruling 7:**

| finding | consequence |
| --- | --- |
| a new red in `s1-01` | **BLOCKING** |
| a red in a frozen tree (`cp-00`…`cp-04`) | **ledgered** |
| a new red in an **undispositioned** tree | **stops the example-repair phase** and returns for explicit disposition |

*"Do not mass-edit examples to manufacture a green estate run."*

**Estate rules, unchanged and binding.** The curated `.76` estate stays
**read-only**. Every test that seeds, ingests, mutates or exercises a writer
refusal uses a **fresh local disposable substrate**; no test-write target may
resolve to a curated host. `estate-env.sh` stays **withheld**; no credential
reaches a report, a panel payload, published evidence or git. No credential
rotation and no estate alteration as part of this wave.

### 5.1 The census instrument, ruled IN-TREE (ruling 8)

Support machinery under `D-IMPL-276`, not production mechanism. It must: read
curated estates **only**; record **measured** before/after watermarks; classify
**exact node ids**; distinguish **pass / fail / indeterminate** evidence; refuse a
malformed or missing result artifact; redact secrets **at generation time**; and
**never contain credentials.** Dave: *"This time the qualification method must be
reviewable from the repository."*

**Before/after positions must be MEASURED** (§3.8). The plan is therefore in two parts:
(1) build or restore a census instrument that captures curated watermarks and a
per-node red/skip census by node id; (2) run it before and after, classify every
red by exact node id as base-existing / already-ledgered / new-under-Wave-2, and
treat any new red as a HOLD. Wave 1's `chunk6a` precedent is the model: the
comparison must show the red set is **identical** to base, not merely smaller.

**Second curated source set — RULED (ruling 10).** The co-lender estate (Fluree
`colender-main` on `192.168.4.76:8091`, Postgres schema `colender`;
`/home/parkave/ccf_dataprep/ccf/config.py:214`, `:250`) is included **only when a
Wave 2 close node actually reads it** — *"do not run unrelated estate merely to
increase coverage."* If read: before/after measurements and the same write fence.

**The write fence is tightened NOW (ruling 12):** `CCF_TEST_MONGO_URI` joins the
guarded disposable-store set; URIs are parsed and normalized hosts **and ports**
compared; substring host matching is eliminated.

---

## 6. THE TWELVE CHOICES — RULED by Dave, 2026-09-27

**Accepted with all twelve resolved, so Wave 2 does not reopen them during
implementation.** Recorded at `D-IMPL-358`. Two of them **amend** the accepted
design and are marked as such.

| # | ruling |
| --- | --- |
| **1** | **`served_at` is TRANSPARENT-AT-SENTINEL.** Absent preserves pre-1.0.2 addresses; populated participates in the new record's address. Its schema presence must not be a generation boundary. *Deliberately a different mark from `child_admitted_at`, which is `False` — the design cited it as precedent while asserting transparency, and this settles which posture applies.* |
| **2** | **`D-IMPL-159` REMAINS BINDING — algorithmic modules do not own the clock. AMENDS D6(d)'s placement.** The guard moves to the **governed ingress/admission boundary** with an injected fabric clock; the worker receives an already-admitted input. *"Do not weaken `D-IMPL-159` because existing code violates it."* |
| **3** | **Tenant comes from the governed ingress COMPOSITION**, not the envelope and not a caller argument. The tenant's policy is resolved and pinned there — **not** resolved-latest per envelope. |
| **4** | **All four write-capable entry points get a disposition.** `ingest`/`ingest_admitted` guarded against `ingestion_timestamp`. `admit_entity_claim`/`admit_relationship_claim` must not become bypasses: guard their `observed_at` against the same pinned policy if reachable on a supported governed path, or **prove internal-only structurally** and exclude them from the supported ingress surface. |
| **5** | **An out-of-window write is a TYPED WRITE REFUSAL.** Fails **before any write**; named typed refusal consistent with the writer seam; **no Decision Replay record fabricated** on a path that does not otherwise produce one; audited through the existing write/admission mechanism where one exists; **never restamp the envelope.** |
| **6** | **Context Debt uses the DECISION INSTANT.** D8 preserved. The explicitly resolved decision instant is passed to the reference scorer; **no wall clock inside the scorer.** `served_at` is for live enforcement, not evidence freshness. |
| **7** | **The 32 are NOT silently classified.** `s1-01` the only live reference; `cp-00`…`cp-04` frozen; **the other 32 UNDISPOSITIONED — neither implicitly frozen nor implicitly live.** Core implementation proceeds without repairing them. |
| **8** | **Build the census instrument IN-TREE**, as support machinery under `D-IMPL-276`. Seven requirements in §5.1. *"This time the qualification method must be reviewable from the repository."* |
| **9** | **`PeeringAdmission.admit(now=)` JOINS the repair. EXTENDS the accepted §4, which never named it.** Gate 3's evaluation instant comes from the fabric clock on the governed A2A inbound boundary; the inherited `asked_at` is preserved and the **live admission comparand** changes. |
| **10** | **Co-lender estate included only WHEN a Wave 2 close node reads it.** *"Do not run unrelated estate merely to increase coverage."* If read: before/after measurements and the same write fence. **No curated write anywhere.** |
| **11** | **A MISSING policy does not mint a fake binding.** Refuse and record the **required policy key/class** and the **absence reason**. Dimension 2 holds only bindings that actually resolved. A policy that resolves but whose window excludes the request yields a refusal carrying the **real pinned `PolicyBinding`.** |
| **12** | **Tighten the write fence NOW:** `CCF_TEST_MONGO_URI` joins the guarded set; URIs parsed and normalized hosts **and ports** compared; **substring host matching eliminated.** Proof infrastructure the wave's write rule requires. |

### 6.1 Two clarifications that constrain the diff

- **Gate 3:** the sheet's correction is accepted — the inequality is already
  two-sided and Wave 2 changes only the **provenance of `now`**. *"Do not rewrite
  the check merely to make the diff look substantial."*
- **The five refusal-recorder sites are ONE temporal-identity migration.** *"Do
  not fix the named two and leave three clocks leaking into refusal identity."*

## 7. The LOCKED implementation sequence

Dave, 2026-09-27. Sixteen steps, in order. The order is the ruling, not a
suggestion — step 2 comes before any production change because Wave 1's
qualification method was not reviewable from the repository.

1. Write **`D-IMPL-358`** with the twelve rulings plus D1–D13. ✔ done
2. **Build the in-tree census and write-fence support machinery FIRST.**
3. Introduce `TemporalBoundaryPolicy` and its pinning.
4. Hoist and capture `served_at` **exactly once** on every governed serve.
5. Thread `served_at` through effectivity, Gate 3, composite validity, refusals
   and **peering**.
6. Add replay `served_at` with **historical-address preservation** (ruling 1).
7. Fix the decision-instant debt control and **add its missing sabotage** — it
   has neither today, measured.
8. Build the **tenant-bound write guard OUTSIDE the algorithmic worker** and
   cover all four writer entries by **proof or guard** (rulings 2, 3, 4).
9. Migrate the red-when-fixed controls (§4.1).
10. Run focused sabotage.
11. Run the disposable writer tests.
12. Run the read-only estate census.
13. **Only then** the example disposition and repair sitting (ruling 7).
14. Freeze the candidate.
15. Codex + Cursor + Gemini close panel.
16. **STOP for `D-GATE-358`.**

### 7.1 Dependencies the code forces inside that order

- `TemporalBoundaryPolicy` (3) is a **creation** and must exist before anything
  reads it.
- The clock hoist (4) precedes every consumer of `served_at` (5, 6).
- Ruling 1 is settled, so (6) no longer blocks on a posture decision.
- The five refusal-recorder sites are rethreaded **together** in (5), per §6.1.
- (8) depends on rulings 2, 3, 4 and 5, all now ruled.
- (13) depends on ruling 7 and on (12)'s classification.

## 8. Close-time panel brief (focused, Codex + Cursor + Gemini)

Same discipline as Wave 1's close, which is the reason it is restated rather than
re-derived: the SDK is destined for a **bank**; the payload goes on **stdin**
(argv caps near 128 KB and dies rc=126 with zero bytes, which reads exactly like
a clean review); source is **inlined and line-numbered** so a sandbox that exits
0 having read nothing cannot empty the review; **every citation is checked against
the frozen SHA and a reviewer whose citations do not resolve is recorded FAILED,
not clean** — Wave 1's close recorded one reviewer FAILED and one as unverified
reading on exactly that test.

Ask them for four things: a bypass through a position the code **claims** to
cover; vacuity — the single `src/` edit that keeps a control green while the
property breaks; claim-vs-code drift; and where the defect **class** lives
elsewhere. Brief them on the known findings so budget goes to what is *adjacent*.

**Tell them the clock's threat model boundary explicitly**, and that arbitrary
code inside the same interpreter is outside it.

---

## 9. Stop conditions

- **This sheet is documentation. Implementation requires a separate GO.**
- Stop if a measured contradiction in §3 would change a **locked** D1–D13 ruling
  rather than its line numbers — that is a `D-IMPL-356` reopening, which needs
  Dave.
- Stop if any of §6's twelve choices is still unruled when the work that depends
  on it begins (§7 names which).
- Stop if a new estate red appears that is not base-existing or already ledgered.
- Stop before any merge, tag, or `D-GATE` entry.

---

## 10. The Wave 1 close is preserved

**The eight residuals are carried verbatim as known launch posture, not a cleanup
queue.** They are not Wave 2 scope and are not worked off here:

1. Value-floor punctuation: `( ) & % ' ,` and accented characters refuse.
2. A conflicted HITL gate wedges permanently; no reopen primitive.
3. The conflict population's narrowing is unproven (`S2` deletes the refusal).
4. `U4`, the estate DSN reaching a census log and junit XML — **reproduced**, and
   deferred to 1.0.3; Gemini's dissent recorded **as dissent**.
5. The printed floor pattern is unregistrable under the ReDoS shape guard.
6. The floor judges declared positions only; `freshness`, `defaults`-as-served,
   undeclared keys and non-string declared types reach the acquisition seam.
7. The ECMA-262 dialect gap on declared patterns.
8. `N9` reports as an `AttributeError` after a mint rather than as a
   missing-refusal assertion — **not cleaned, by ruling**.

**The base-existing `docs/surface/examples/RETIREMENT-COUPLINGS.md` freshness
failure is left alone**, verified red at the wave base `00fde747`.

**Not in this wave, by ruling:** no Wave 1 repair, no adapter implementation, no
HITL implementation, no erasure code, no frozen-server migration, no release
qualification, no tag.
