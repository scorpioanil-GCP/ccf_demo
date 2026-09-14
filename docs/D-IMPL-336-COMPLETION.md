# D-IMPL-336 — completion package

**Candidate `1edc8fe7` on `d-impl-336-composite`. NOT merged. CP-14 acquisition
remains HOLD.**

> **A close-time cross-AI panel has run against this work** and its record is
> `docs/D-IMPL-336-CLOSE-PANEL.md` — 9 confirmed, 1 partial, 14 rejected, over
> 30 agents. It found one real defect (`CP-F-01`: **this simplification
> regressed `F3`**), one real spoof (`CP-F-02`), two measurement failures by
> the orchestrator, and two false docstrings. All are remediated at `1edc8fe7`
> and are reflected in the tables below. One advisory (`CP-F-06`) is carried.

Returned against `D-IMPL-336` **Amendment 5 §6**, which asks for one package
distinguishing **removed duplicate mechanism**, **retained control**,
**relocated responsibility** and **remaining defect**.

---

## 1 · What the simplification actually changed

Dave's challenge was that the design was more than the architecture needed:

> *"A complex context product can be made up of several other context
> products… The skill that the composite agent has knows how to acquire the
> atomic context product and roll it in. … I feel you are overcomplicating this
> somewhat simple structural architecture."*

**Measured before the ruling.** `src/ccf/products/composite.py` stood at 1,910
lines: the pre-ruled composition content (`D-IMPL-31`'s four laws,
`D-IMPL-104`'s per-factor debt) was **25%**; a trust apparatus was **~40%**. A
deployment acquiring one child wrote **45 lines of non-comment code** and
constructed **five intermediate typed objects**.

**Measured after.**

| | before | after |
| --- | --- | --- |
| deployment code to acquire a child | 45 lines | **16** |
| evidence objects a deployment constructs | 5 | **0** |
| `composite.py` | 1,910 lines | **1,666** |
| unit-test fixture | boots a fabric + artifact store | **a bare `ControlPlaneRegistry`** |

**The root cause, and it was mine.** The outcomes map was treated as a hostile
input, so a second authorization layer was built on top of the one that
already existed. **The grant is the authorization.** Every panel finding that
drove the token layer was real *given that design*; the design choice that made
them real was making acquisition a loose seam rather than a granted skill
dispatch.

---

## 2 · The register, by disposition

### Removed — duplicate mechanism

| What | Why it was duplicate |
| --- | --- |
| `LocalFabricAttestor`, `_ATTESTOR_TOKEN` | Asked a second time whether a locally dispatched child was authorized. The grant already said so. |
| `LocalProvenance`, `_LOCAL_PROVENANCE_TOKEN` | A minted "this fabric produced it" label over an invocation the fabric itself had dispatched. |
| `VerifiedPeerProvenance`, `_PEER_PROVENANCE_TOKEN`, `peer_provenance_from_admitted` | Re-carried a peering verdict the peering gate already returns as `AdmittedProduct`. |
| `ChildProvenance` base | The axis it modelled (*who produced this*) is the **dispatch result's type**, and is now read rather than declared. |
| `FabricHandle.local_attestor` | Boot no longer mints a composite-specific capability. |
| `ChildCandidate.provenance` | Replaced by `invocation` + (peered only) `admission`. |

**What removing it cost, found by the panel and not by me.** Deleting
`ChildProvenance` made `touched_entities` optional — necessary, because Dave
ruled a consumer must not be required to read a remote provider's replay store.
It also left the **local** leg admitting `None` while still recording
`local-register` as the authority: `CP-F-01`, the `F3` regression. The property
`ChildProvenance` had enforced by making the field mandatory is enforced now by
the local leg **refusing** when it is absent. That is the one row in this table
where "relocated, not dropped" was not true when it was written.

**Verified absent** from `src/` and `runtime/` by grep; the only surviving
mentions are docstrings recording what was removed and why.

### Retained — controls that stayed, at the surface they belong to

| Control | Where it lives now |
| --- | --- |
| A child invocation cannot be authored by a caller | `ChildInvocation`, token-minted by `invocation_from_dispatch` |
| Producer identity comes from the ledger, not a string | `ResolvedProducer` + `BoundSkillView.grant_hash_for` (**O2**) |
| A revoked or ungranted producer cannot initiate | `resolve_producing_grant` reads the live view |
| The provider relationship cannot be relabelled | read off the dispatch result's **type**; `invocation_from_dispatch` takes no `acquisition` argument |
| Touched entities cannot be claimed for a remote child | refused, not ignored (**F3**, closed the other way — see §3) |
| A LOCAL child with no execution record cannot be admitted | `_establish_eligibility`, refusing `eligibility-evidence-missing` (**CP-F-01**) |
| A remote entry cannot be relabelled as a local dispatch | `invocation_from_dispatch` holds three facts to each other: the dispatch result's type, the granted entry's `skill_type`, and the `skill_type` the dispatch stamped on its own result (**CP-F-02**) |
| Fit checks: class, version, tenant, one `as_of`, address, assessable debt | `CompositeAdmissionGate` |
| Slot-to-child reconciliation | `_rebinding_failure` (**F2**/**F15**) |
| The four composition laws | `compose_children` (`D-IMPL-31`, `D-IMPL-104`) |
| Gate 2 strictness, with the parent's own declaration unmaskable | **R4** — the union widens the operand, never the parent's half |
| An invoked child's refusal refuses the composite | **F1** — only `no-producing-skill` takes the declared absence |
| Admission time from the trusted runtime clock | **O3** — required, injectable, read once per composition |

### Relocated — responsibility moved, verification did not

| What | From | To |
| --- | --- | --- |
| `EligibilityEvidencePolicy`, its key, `EligibilityEvidence` | `ccf.products.composite` | `ccf.peering.eligibility` |
| The five equality bindings + the declared age bound | a copy inside `CompositeAdmissionGate` | `verify_child_eligibility`, one call composition consumes |
| The **F7** control suite | `tests/products/test_composite.py` | `tests/peering/test_child_eligibility.py` — **and strengthened**: all five bindings are now moved individually, where the original moved one |

### Remaining defect

| # | What | Status |
| --- | --- | --- |
| — | An over-bound protected header surfaces as `SignatureInvalid`, because `ExceededSizeError` is a `JoseError` and the identity provider maps the family. **Nothing is admitted**, so the direction is safe, but an operator debugging an oversized envelope is told the wrong thing. | **OPEN, recorded not repaired.** Changing that mapping widens what the verify path distinguishes and was not R1's subject. |
| `CP-F-06` | On the mixing-refusal path `ChildAdmissionRefusal.product_class` is set from `child.verified_content_address`, so the field carries a content address where every other refusal in the module puts a requirement class name. | **OPEN, advisory.** Confirmed by the close panel. Not repaired here: what that field holds has readers outside this module, and changing it on one path is a wider change than this work's scope. |

Nothing else from the two panels or the R-series is open. `R1`–`R6`, `F0`–`F18`,
`V1`–`V3`, `O1`–`O3`, `CMP-R-01`, `CMP-R-02`, `INT-01a` and `INT-01b` are all
closed or superseded; §4 lists each with the test that proves it.

---

## 3 · Two closures that went the opposite way from Amendment 3

Recorded because a later reader will otherwise think a control was dropped.

**`F3` — `touched_entities`.** Amendment 3 closed it by making the value
**always present**, so there was no "I did not look" state. Amendment 5 closes
it **the other way**, because Dave ruled that a consumer must not be required
to reach a remote provider's replay store. For an `mcp` or `peered` child the
value is `None`, the local register is **not consulted**, and the recorded
`eligibility_basis` says which authority *did* apply. What is now impossible is
**claiming** entities for a child whose execution record this fabric does not
hold — that is refused, not ignored.

**`O1` — the attestor.** Amendment 4 required it minted through the real
`BootedFabric` lifecycle; it was, at `bd66f1f0`. Amendment 5 **removed the
requirement along with the class**, because the thing it established was
already established by the grant and the dispatch. The controls it carried did
not disappear: they are the "Retained" rows above.

---

## 4 · Verification

```
make lint                                                            clean
make typecheck                        222 source files (src + runtime), clean
```

**`make typecheck` is the prescribed target.** Earlier reports in this workstream
said `mypy src/ccf`, which is narrower and never covered `runtime/`.

### Sabotage — every new control, reverted, watched to fail

| Reverted | Goes red |
| --- | --- |
| `R4`'s union operand | `INT-01a`, with the Gate 2 collision |
| `R4`'s own-declaration guard | `test_r4_the_union_CANNOT_mask_the_parents_own_declaration_drifting` |
| The declared header bound, moved below the honest header | the same envelope refuses — proving the bound is **read at verification**, not merely present |
| `child_operators_invoked` / `child_expires_at` | `CMP-R-02` cannot re-derive the union or the floor |
| The local leg's missing-record refusal (`CP-F-01`) | a superseded child is ADMITTED with `basis=local-register`, measured, with the control beside it |
| Any one of `invocation_from_dispatch`'s three facts (`CP-F-02`) | an MCP-granted entry records as `local-dispatch` with caller-chosen entities |

---

## 4a · A discovered dependency, NOT remediation scope: `D-IMPL-337`

`D-IMPL-336`'s two close panels each found one instance of the same shape — a
value whose authority comes from a guarded construction path, reaching a
consumer that never verifies it received the guarded type. Each was repaired
individually. An AST census then measured the population those panels had been
sampling: **7 guarded types, 15 consumer sites, 1 verifying, 6 publicly
reachable** — and **five of the six exposed sites are in Replay, Peering,
Assembly and the Control Plane**, none of which this branch touches.

**Dave's ruling (2026-09-14): that is a cross-cutting SDK invariant gap, and it
gets its own decision rather than being smuggled into the phase that discovered
it.** It is recorded at `D-IMPL-337` — OPEN, design required, with the six sites
as its initial census, severity distinguished by consequence rather than
flattened because one instrument finds them all.

**Why it is not fixed here.** A four-subsystem correction inside this branch
would destroy the ability to answer *"did `D-IMPL-336` correctly implement
composite Context Products?"* — the composite work would become inseparable from
unrelated replay, peering, assembly and Control Plane repairs.

**What IS this branch's obligation, and it is discharged.** 336's own guarded
consumers must be correct and the branch must introduce no new bypass. Audited
at `64d4ae4a`:

| consumer | reachability | verifies? |
| --- | --- | --- |
| `invocation_from_dispatch(producer)` | **exported** | **yes** — `ProvenanceForgeryError` on a non-`ResolvedProducer` |
| `compose_children(outcomes)` | **exported** | **yes** — `isinstance(outcome, AdmittedChild)` |
| `_admit`, `_rebinding_failure`, `_row_for_admitted` | module-private | n/a — unreachable across the module boundary |

No publicly reachable consumer of a guarded type in `composite.py` or
`child_resolver.py` infers authority from shape alone.

---

## 4b · MERGE PACKAGE — the four ruled items, each cited to its implementation

Not carried forward from a checklist: each row names the symbol and the tests
that close it, measured against candidate `29d1885a`.

### R1 — the peering path · **DISCHARGED**

`joserfc`'s `JWSRegistry` defaults `max_header_length` to **512** and
`_registry_declaring` never set it; an honest protected header carrying a
child-eligibility assertion is **621 bytes**, so the peered composite path was
**unreachable**, not merely untested.

- **Implementation:** `src/ccf/peering/identity.py:204`,
  `MAX_PROTECTED_HEADER_BYTES: Final = 2048`, set on the registry **instance**
  so no other `joserfc` user in the process is affected.
- **Tests:** `tests/peering/test_peered_child_envelope.py`, **5 tests** — the
  honest header exceeding the library default (so the constant cannot outlive
  its reason); an honest signed envelope reaching composition through the real
  `PeeringAdmissionGate`; **the bound moved BELOW the honest header and the
  same envelope refusing**, which proves it is read at verification rather
  than merely present; a tampered signature still refused; a stale producer
  check still refused on the genuine envelope.

### CMP-R-01 — refused-composite child evidence · **DISCHARGED**

`compose_children` always built a row per declared requirement; those rows
reached the persisted record on the **served** path only.

- **Implementation:** `src/ccf/products/resolver.py:710`
  (`RefusalRecorderProtocol.record`) and `:963` (`ReplayRefusalRecorder.record`)
  take `child_resolutions: tuple[ChildResolution, ...] = ()`; the composition
  refusal branch passes `composed.resolutions`. Surface recorded **before**
  implementation in its own commit, as ruled (`docs/surface-changes/336-04-*`).
- **Tests:** `test_cmpr01_a_REFUSED_composite_records_which_children_it_tried`
  reads the rows back **off the store**;
  `test_cmpr01_a_NON_composite_refusal_records_no_rows_and_is_unchanged` is the
  control — `()` is hash-transparent, so no existing record's address moves.

### `GrantBoundChildResolver` in `src/` · **DISCHARGED**

- **Implementation:** `src/ccf/products/child_resolver.py:91`. The supported
  local path is **effective grant → actual dispatch → the child's governed door
  → fit checks → compose**, with the duplicate local attestor stack removed and
  verified absent from `src/` and `runtime/`.
- **Measured effect:** acquiring one child went from **45 lines of deployment
  code and five hand-constructed evidence objects to 16 lines and none**.
- **Surface:** `docs/surface-changes/336-05-the-reference-child-resolver.md`,
  written after the D-15 drift gate caught its absence.
- **Tests:** `test_int01a_one_governed_question_through_the_whole_machinery`
  plus the no-grant and revoked-grant negative controls; the cross-process
  proof drives the **same** `build_composite` with only the binding changed.

### The replay-record binding · **FIXED at `23c296af`**

`_touched_entities` took dependency evidence from whatever record the producer
named. The binding is now between the referenced record's
`product_content_address` and the child's **recomputed** `content_hash(contract)`,
established **before** the record's entities are read. Raised as
`ChildRecordMismatch` rather than refused: evidence about another product is
not a fact about this child's eligibility.

- **Implementation:** `src/ccf/products/child_resolver.py::_touched_entities`;
  surface entry in `336-05`.
- **Tests:** `test_a_child_naming_ANOTHER_products_replay_record_is_refused` —
  valid-foreign-record rejection, honest-record positive control, and the
  binding-removal sabotage (RED, restored byte-identically).
- **Follow-on from the focused repair review, fixed:** `ChildRecordMismatch`
  was a `RuntimeError`, and the MCP egress door wraps only
  `(ValueError, TypeError, LookupError, OSError)` into an opaque
  `ccf-runtime-failure` id (`D-IMPL-253` Q20 — *no message, no type name, no
  traceback*). It escaped that wrap and would have delivered a replay-reference
  URI and two content addresses to a client. Now a `ValueError`, matching
  `ccf.replay.serve.ProductRecordMismatch`, which is the same defect class one
  layer up and a `ValueError` for the same reason. Pinned by
  `test_the_record_mismatch_is_wrapped_OPAQUE_at_the_delivery_doors`, which
  reads the door's own except tuple rather than restating it.

### INT-01b · **CLOSED** (see `docs/DECISIONS.md`, 2026-09-14)

**Scope, preserved exactly and not enlarged.** INT-01b is closed for: real L2
supersession → the child's governed delivery refuses → the middle and higher
composites propagate that refusal. It does **not** prove the composite
admission check itself — the `F3` regressions own that check, and a mutation
disabling `composite.py`'s local-leg register consult leaves INT-01b green
while both `F3` tests go red. It does **not** re-prove same-age unrelated-product
selectivity — the existing `D-IMPL-334`/`D-IMPL-335` regression owns that.
**Not enlarged merely to make an unrelated mutation turn it red.**

> `INT-01b` proves nested dependency propagation through historical
> reconstruction. After a real L2 supersession at `T_WORLD > T0`, the same
> child question asked again at `T0` is refused by the child's own governed
> delivery path. The middle and higher composites refuse because the governed
> child they acquire refuses. No parent invalidation boundary is separately
> written or synthesized.

**The failed first proof, kept:** the original cached-child test was invalid as
evidence for `D-IMPL-334`/`D-IMPL-335` because `F15`'s one-`as_of` rule produced
`as-of-mismatch` before dependency invalidation could be exercised. **Sabotage 2
remaining green exposed the false proof.**

Measured facts: real boot-bound L2 ingest; boundary at **13:00 world time, not
the June ingestion time**; no direct register write; no direct sink invocation;
no manual dependency copying into the composites; all three targeted sabotages
RED and restored byte-identically; post-change re-derivation serves again
through the nested chain.

**What it does not prove:** the single-entity fixture cannot express an
*"equally old unrelated product still serves"* control. **Dependency
selectivity remains covered by the existing `D-IMPL-334`/`D-IMPL-335`
regression** at `tests/products/test_dependency_invalidation.py`. INT-01b
proves nested propagation and re-derivation.

- **Tests:** `tests/products/test_composite_integration.py`, **4 `int01b`
  tests** — the nested chain; the transitive expiry floor; the L2 supersession
  proof; and the inherited-composition-state regression.

---

## 5 · Limitations, stated plainly

- **The full estate tour remains CP-14 work**, per Amendment 5. No composite
  has been run against `.76`, so nothing is measured about real debt factors,
  real lineage sizes or real expiry spreads.
- **The MCP demonstration uses one logical resource served by one child
  process.** It is a real process boundary, a real HTTP transport and a real
  MCP client; it is not a multi-provider topology.
- **The peered branch of `GrantBoundChildResolver` selects the first inbound
  product that passes admission and matches the class.** A peer returning
  several candidates for one requirement is not disambiguated, and that is a
  gap rather than a policy.
- **A `local_callable` whose callable proxies a product produced elsewhere is
  recorded as `local-dispatch`, and the SDK cannot tell.** Raised by fable at
  close panel 2, and it is Dave's verbatim hazard — *"a local skill fetching a
  remote product must not relabel that product as locally produced"* — in the
  one form that is **structurally invisible**: all three cross-checks in
  `invocation_from_dispatch` pass, because the entry genuinely is a
  `local_callable` and the dispatch genuinely ran locally. What the SDK cannot
  see is what the deployment's own callable did inside.

  **Not repairable here, and the reason is the architecture rather than the
  effort.** A callable is opaque by construction — that is what makes
  in-process, MCP, A2A and another-agent acquisition interchangeable behind one
  skill. Inspecting it would require the composite to know how its provider
  works, which is precisely what Amendment 5 forbids.

  What bounds it: the child still crosses `door_answer`, so its content address
  is the producer's own; the local leg now **refuses** without an execution
  record, so a proxied child that cannot produce one is not admitted at all;
  and the grant is per-agent, so binding such a skill is a governed,
  audited act. It is a deployment-integrity property, not a fabric one, and it
  belongs in adopter guidance.
- The over-bound-header reporting defect in §2, and `CP-F-06`.
- **`AmbiguousProducerError` is a `RuntimeError` reaching the same MCP door
  from the same resolver**, so it escapes the opaque wrap exactly as
  `ChildRecordMismatch` did. **Pre-existing and NOT fixed here**: it predates
  this work, and widening the door's except tuple would change a runtime
  door's posture for a condition `D-IMPL-336` did not introduce. Recorded so
  the next owner of that door has the measurement.
- **Two of the six close-panel findings were measurement failures by the
  orchestrator, not design defects** — a surface gate that was red on this
  branch and green on `main` and never run, and a test whose comment promised
  an assertion the code did not carry. Both are fixed; both are recorded here
  because the pattern (running the generator, not the gate) is the one worth
  remembering.
