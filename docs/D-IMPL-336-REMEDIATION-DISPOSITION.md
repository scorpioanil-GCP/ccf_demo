# D-IMPL-336 — remediation disposition

**Candidate `10553977`** on `d-impl-336-composite`. Base `main` `374a3600`.
**NOT merged. CP-14 acquisition remains HOLD.**

Register: the cross-AI panel's **F0–F18** and **V1–V3**
(`docs/D-IMPL-336-PANEL-REVIEW.md`). Rulings: `D-IMPL-336` Amendment 3.

---

## 1 · Dispositions

### Closed

| # | Finding | How it is closed | Proof |
| --- | --- | --- | --- |
| **F0** | The composite surface had no callers | `GovernedResolver.__call__` reads `requires` from the **registered class** and composes; `child_resolutions` written from execution; `requires` authorable on `ProductClassDeclaration`, forwarded by `register_product_class` and `_register` | Call sites: `resolver.py:182,184,1507,1930`; writers: `record.py:1821`, `resolver.py:2194`. **Behavioral:** `test_a_composite_records_a_child_resolution_row_from_EXECUTION`, `test_a_class_declaring_children_with_no_resolver_REFUSES`, and a non-composite control |
| **F1** | Optional governance rejection cost nothing | **Ruled**: only an honest `no-producing-skill` takes the declared absence treatment; anything invoked-and-refused refuses the composite, optional or not | `test_f1_optional_absence_is_priced_and_optional_REFUSAL_is_not` |
| **F2** | `AdmittedChild` not re-bound to its slot | It carries its requirement, `asked_at`, invocation and verified address; `_rebinding_failure` re-checks all four | `test_f2_*` (wrong slot, looser lane) |
| **F3** | Omitting `touched_entities` skipped eligibility and claimed the register ran | It moved onto `ChildProvenance` as a tuple. **The absent state has no spelling.** The shared gate's legacy `None` posture is untouched, per ruling | `test_touched_entities_has_no_absent_state`, `test_f3_*` |
| **F4** | No authorization check; caller-written skill/grant strings | `ChildInvocation` minted from the resolved catalog entry — see **open O2** for the residual | `test_provenance_and_invocation_cannot_be_authored_by_a_caller` |
| **F5** | `_tenant_id` stored, never read | Tenant check added, copying the peering precedent | `test_f5_a_foreign_tenant_child_is_refused` |
| **F6** | `ProducedHere` unverified and unauditable | Replaced by minted `LocalProvenance`; `producing_fabric` recorded on admitted **and** rejected rows — see **open O1** | `test_a_hand_built_header_cannot_become_peer_provenance`, `test_a_rebinding_failure_keeps_the_VERIFIED_identity` |
| **F7** | `checked_at` enforced nothing | Control-Plane-declared `EligibilityEvidencePolicy`, validated against **admission time**, no default, explicit refusal when undeclared; `checked_at` and the assertion address reach replay | `test_f7_*` (four tests, including the historical-`asked_at` case an ordering check would have broken) |
| **F8** | "Single-use" defence did not exist | Claim removed; the guarantee is **invocation-bound**. No spent-token registry | `test_f15_a_child_from_another_invocation_does_not_combine` |
| **F9** | Address-mismatch retained the forged address | Reported and verified addresses kept separate and labelled everywhere | `test_f9_*`, `test_a_rebinding_failure_keeps_the_VERIFIED_identity` |
| **F10** | `accepts` raised on a pre-release floor | Real semver precedence, total over every form registration accepts; `compatibility_rule()` states the rule | 10-case table in `contract.py`'s tests |
| **F11** | Governance failure collapsed on a spelling | `ChildRefusalReason` is a closed `Literal`; `_status_for` is exhaustive and **raises** | `test_f11_*` (two) |
| **F12** | Duplicates unchecked at execution | Refused in `compose_children` | `test_f12_*` |
| **F13** | Unadmitted object read as absence | Its own `unsupported-outcome` reason; covers the **optional** slot the old test missed | `test_f13_*` |
| **F14** | Three composition laws unwired | All four run; `CompositionOutcome` carries lineage and expiry; the resolver uses them | `test_f14_*` (two) |
| **F15** | One-`as_of` invariant dissolved at composition | `compose_children` takes `asked_at` and the invocation and re-binds | `test_f15_*` (two) |
| **F16** | Nothing verified a signature | `VerifiedPeerProvenance` mintable only from `AdmittedProduct`; the gate carries its **authenticated** header out, now **frozen** | `test_a_hand_built_header_cannot_become_peer_provenance`, `test_the_authenticated_header_cannot_be_mutated_after_admission` |
| **F17** | Undeclared outcome keys dropped | Refused — and the audit trace is **preserved**, not wiped | `test_f17_*`, `test_an_undeclared_outcome_key_does_not_wipe_the_audit_trace` |
| **F18** | Container transparency reinstated the ambiguity | Solved by **validation, not by changing legacy identities**, per ruling: empty-default transparency preserved so every pre-existing record keeps its address | `tests/contracts/test_hash_transparency.py` |
| **V1** | Test named one thing, measured another | All four governed absences produced, **including a real `unauthorized`**, asserted by equality. Criterion 21 discharged for the first time | `test_v1_the_four_absences_stay_distinct_INCLUDING_unauthorized` |
| **V2** | Subset check that could never fail | Rosters held to each other by **equality**, plus an assertion the fallback raises | `test_f11_the_status_map_is_exhaustive_and_raises_on_the_unknown` |
| **V3** | Vacuous expiry test | Drives the real composition; would now fail if `compose_children` were deleted | `test_f14_the_expiry_floor_is_a_property_of_THIS_path` |

### Open — named, not excluded

| # | Finding | Status |
| --- | --- | --- |
| **O1** | `LocalFabricAttestor` is publicly constructible with a caller-chosen `attestor_id`. "Boot-bound" is a convention, not enforcement | **Confirmed by execution.** Raised by codex against the repair. This is a *"declaration is not a door"* instance in my own fix and should be closed by constructing the attestor from a `BootedFabric` and deriving its id |
| **O2** | `invocation_from_dispatch` accepts any `SkillCatalogEntry` plus a caller's `grant_hash`; nothing binds it to an actual `resolve_producing_grant` result | **Confirmed by execution.** The token replaced free strings but did not bind them |
| **O3** | `admitted_at` is `decided_at`, which a declared historical decision instant could move | **Confirmed by reading.** Current behavior is conservative — the skew check refuses rather than admits — but the clock is wrong in principle |
| **CMP-R-01** | `child_resolutions` do not reach a **refused** composite's persisted record | **Confirmed.** The refusal path records through `RefusalRecorderProtocol.record`, a public seam with no such parameter. I added a parameter and **backed it out**: one accepted and ignored would be the exact defect class this phase repairs. Closing it is a protocol change |
| **INT-01** | The integration proof through **cp-04-canonical, cp-05, cp-13** and the nested leaf→composite→higher-composite supersession chain | **Not built.** Named rather than excluded, per the instruction. See §3 |

---

## 2 · Verification

Run sequentially against the clean candidate, nothing else touching the tree.

```
make lint                                             clean
mypy src/ccf                          149 source files, no issues
pytest tests/products/test_composite.py            33 passed
pytest tests/products tests/replay tests/contracts tests/peering
       tests/projection tests/deployment tests/cli tests/skills
       tests/agents tests/controlplane      2,444 passed, 1 skipped, 5 failed
```

**Failure-set comparison against the pinned base.** The 5 are exactly `main`'s,
measured with this work stashed and the FAILED lists diffed — not counted:

- `tests/cli/test_schema_export.py` ×3 — `ccf.half-life-table` drift and an
  uncommitted `ccf.entity-invalidation-register.json`
- `tests/peering/test_admission_record.py` — the `claims.py` pin, stale since
  `da14c544`
- `tests/deployment/test_class_lookup.py` — unclaimed `ccf.halflife.decay.*`

**None absorbed.** The nine surface names still unclaimed by any fragment are
byte-identical to `main`'s list.

---

## 3 · What INT-01 would establish that the current tests do not

Stated concretely, because "an integration gap" is not a risk assessment.

The current proof drives the **real** `GovernedResolver`, the **real**
`run_gates` delivery path and the **real** persisted replay record. What it
does **not** drive is a `CompositeChildResolverProtocol` implementation that
resolves an actual grant, dispatches an actual skill and delivers an actual
child — the tests supply the outcomes map directly. So the residual risk is
specifically:

1. **The seam between dispatch and admission is unexercised.** Nothing proves a
   real dispatch result can be turned into a `ChildCandidate` at all — which is
   where **O2** lives, and why O2 matters more than its severity suggests.
2. **No nested chain has run.** `compose_expiry` and `compose_lineage` are
   proven over one level. A composite serving as another's child is
   type-legal and untested.
3. **Supersession through the boot-bound writer is unexercised at the composite
   level.** Invalidation is proven against a directly-recorded register entry,
   not against a real graph write propagating to a dependent chain.
4. **No estate data has passed through the surface**, so nothing has been
   measured about real debt factors, real lineage sizes or real expiry spreads.

None of these is a correctness argument against the repair; they are the
things the repair has not yet been shown to survive.

---

## 4 · Remaining limitations

- **Signature verification and integration are NOT excluded** — per the
  instruction, both were done and both are reviewed above (F16, F0). What
  remains is INT-01's *example-level* proof.
- `AdmittedChild`'s construction token is unforgeable through the supported
  interfaces and not against `object.__new__` — unchanged, and stated in the
  module.
- O1–O3 and CMP-R-01 above.
