# D-IMPL-343 — close-time cross-AI review of the consumer half

**Subject:** the shipped code of the consumer paved road at candidate `d-impl-343-dx @ 5abfe4bb`
(the diff against the accepted producer-half candidate `c12320d6`, plus the facade module
`src/ccf/products/product.py` in full), inlined into the payload and fed to each reviewer on
stdin (CLAUDE.md §3.1: inline the source; a single argv string caps at 128 KB and the payload
was 210 KB). The payload carried the seven attack questions Dave set, the rulings the code must
honor, seven known findings marked "do not re-derive", and the citation rule: a finding that
cites nothing that resolves is recorded as rejected.

**Panel:** codex (`codex exec`, API-key auth; 69,166 tokens) and cursor (`cursor agent -p --mode
ask`). Both produced findings whose cited symbols resolve against the inlined text; both are
counted as reviewers. The executing model is excluded for independence and did not review.

**Fixes landed in the follow-up commit on the same branch, before Dave's merge ruling**, per
§3.1 ("fix all blocking findings in-phase"). Every disposition below was verified against the
tree, not accepted on the reviewer's word.

## Findings and dispositions

| # | reviewer | claim (as cited) | verified? | disposition |
|---|---|---|---|---|
| C-1 | codex F-1 | `config.py::_complete_skill_entry` refused an offer floor BELOW the requirement's floor within one major; a same-major producer serving above both would be admitted by the low road, so the refusal was a semantic divergence (attack 3) | **CONFIRMED** — `requirement.accepts(child_version=offer.versions_from)` is a "same major AND at or above" test; the correct open-time guard is "same major" only, admission holding the served lane | **FIXED**: `_same_major` (via the one floor rule, `version_satisfies_floor` in both directions); regression `tests/deployment/test_paved_sections.py::test_the_two_floors_must_open_one_major_lane_and_may_differ_within_it`; the admission boundary is now reachable through the paved road and proven: `tests/products/test_paved_consumer.py::test_a_served_lane_below_the_composites_floor_is_refused_at_admission_with_the_reason` |
| C-2 | codex F-2 | `config.py::_complete_agent` accepted any stated agent `consumes` lane inside the requirement's lane; nothing on the composite path reads the agent's lane, so a differing lane was a second statement admission never consults (attack 2) | **CONFIRMED** — `Agent.consume` (`agents/agent.py`) is the only reader and is not on the composite path; the ledger's tier-1 reads classes only | **FIXED**: the stated lane is held EQUAL to `compatible_from` (fill-or-hold-equal, like every other derived value); the parametrized hold-equal test now carries the `1.4.0` case |
| C-3 | codex F-3 + cursor F-2 | `product.py::open_product` registered `producers:` on the facade's registry but a `children=` resolver built before open could not receive it; the docstring claimed the hatch composes over the SDK's registrations while the hatch test registered producers a second time (attack 7) | **CONFIRMED** — `_low_road_children` built its own `McpSkillRegistry`; two registries, one unused | **FIXED**: the hatch now has two forms — `children=` (fully external; refused beside `producers:` by name) and `build_children=` (a `ChildResolverFactory` handed a `ConsumerContext`: the facade's one Control Plane, store, `mcp_skills`, tenant, clock); the hatch test builds the low road over the context and registers nothing; `test_a_hatch_beside_a_declared_chain_a_mapping_or_declared_producers_is_refused_at_open` covers every mixed state |
| C-4 | codex F-4 | `product.py::_derive_consumer_chain` collapses a structured `GrantRefusal` into `ValueError` at open (attack 6) | verified as described | **REJECTED as blocking; recorded as advisory.** A grant the deployment's OWN regime refuses for a skill the deployment DECLARED is a configuration fact known before any question is asked — `D-IMPL-340` ruling 1's boundary (deployment facts are exceptions; governed determinations are values). `open_product` returns an opened product or raises; the raised error names the refusal's type and carries its detail. Returning a refusal object from open would give the facade a second return shape for a state in which nothing was asked. |
| U-1 | cursor F-1 | `config.py::_complete_agent` did not hold a STATED `policy_regime`/`halflife_debt_profile` ref to the deployment's section when that section's key was bare; two regimes could stand (attack 2) | **CONFIRMED** — the `len(key.split("/")) == 3` guard on the hold-equal branch let a stated ref pass beside an unreferenceable section | **FIXED**: whenever the section exists, the derived reference is formed (the bare-key remedy applies to a stated ref too) and a stated ref is held equal; regression `test_a_stated_regime_ref_beside_an_unreferenceable_policy_key_is_refused_with_the_remedy`; the producer-half agent tests now declare a referenceable policy key |
| U-2 | cursor F-3 | `product.py::_derive_consumer_chain` skipped the grant request when `entry.name in bound`, ignoring a bumped `artifact_version` (attack 3) | **CONFIRMED** — over a shared plane an edited `skills:` entry would leave the old grant in force and the new entry unbound, silently | **FIXED**: the in-force entry's content hash is held equal to the declared entry's; a difference is refused at open naming both versions — revocation is a Control Plane action, never a side effect of an edit; regression `test_a_bumped_skill_beside_a_grant_in_force_is_refused_at_open_naming_both_versions` |
| U-3 | cursor F-4 | `OpenedProduct.resolve` normalized a floor-bearing request to the served lane; `answer` passed the request through, so the two public verbs diverged on the same request (attack 3) | **CONFIRMED** | **FIXED**: one `_admit_lane` method holds a class-and-floor address for both verbs; regression `test_answer_admits_a_floor_bearing_request_the_way_resolve_admits_an_address` |
| U-4 | cursor (adjacent to K3/K4/K5) | observations only; no additional finding | — | recorded |

**Attack-question verdicts, both reviewers, after verification.** (1) Removes, does not relocate:
what the adopter still writes is the declaration (R-7/R-2 statements) and the one domain
mapping — no finding. (2) Two hidden second authorities found (C-2, U-1), both closed. (3) Three
divergence branches found (C-1, U-2, U-3), all closed; the door-floor vs admission-lane
boundary difference is R-13 by design and disclosed. (4) No identity change beyond the known
request-lane normalization (K5); child content address, registration address and question
identity equal to the low road in dogfood B. (5) No bypass through the public surface; the
hatch returning an unadmitted contract is refused by provenance (D-IMPL-337 visible). (6) No
coarsened classification; C-4 recorded as the deliberate boundary. (7) One double-wired hatch
found (C-3), closed with the factory form.

**What the panel did not find, and the tree's own proofs cover:** the R-6 tenant check
(`producer-tenant-mismatch` through the public surface), the `no-producing-skill` path after a
revocation, the `producer-unavailable` path, the open-time refusals by name. The panel found
what the suite could not: three of the seven confirmed findings were in code paths the first
suite exercised only in the direction that passed.
