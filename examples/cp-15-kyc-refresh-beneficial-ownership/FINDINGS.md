# Findings — cp-15-kyc-refresh-beneficial-ownership

Built 2026-09-21 on Dave's Gate-2 GO of the same day, against `CP-SPEC-015`
with the `Q14` HITL convention, the construction boundary and the cycle ruling
folded into the spec first. Every finding was classified under
`docs/EXAMPLE-EVALUATION-CRITERIA.md` §B before any repair was considered, and
nothing in the SDK was repaired: findings are raised, not resolved
(`D-IMPL-261`). The close-report sections follow §K, in order.

**Measured at close (2026-09-21, live estate, `CCF_REQUIRE_ESTATE=1`):**
22 tests **passed**, 0 failed, 0 xfailed, 0 skipped, in four modules under
`tests/examples/test_cp_15_*.py`. 20 gates declared, 20 claimed by an
executing test; the two extra tests are positive controls. **18 of the 20 were
observed RED** under their own sabotage; `UBO-G01` and `UBO-G11` are
`unavailable` and each names its guard.

**Accepted at `D-GATE-cp-15`, 2026-09-21**, on the candidate
`cp-15-kyc @ bfdf7837`, merged `--no-ff` into `main`. **No SDK behavior
change.**

**Active SDK issue cap: 0 of 3.** None of the five stop conditions fired. In
particular **stop condition 4 did not fire**: HITL composes with the immutable
product and its replay references **without changing an SDK contract** — the
proof is §2.3.

## 1 · SDK capability proven

| launch-contract item | how this tree exercised it |
|---|---|
| define contracts as Control Plane artifacts | one `ccf_config.yaml` declares the class, four operators, a five-parameter request contract, two decay regimes, the debt profile, the policy bundle and the door |
| assemble through the single writer and the declared operators | six entity classes and five edge types enter through L2, edges first, attributed nodes last |
| apply authorization and policy before use | the residency entitlement is read from the estate's own column and applied at the acquisition seam; a person outside it is never minted (`UBO-G02`, `UBO-G03`) |
| preserve product identity and content addressing | two principals, two addresses, one class and one plan id |
| calculate Context Debt correctly | five standing classes at `supersede-only` beside one dated class on a `valid-from` curve |
| refuse correctly, as data, with a replay reference | four typed governed refusals: no jurisdiction grant, unpriced intent, floor breached, tolerance (`UBO-G07`, `UBO-G18`) |
| preserve sufficient refusal evidence | each refusal's `assembly_refusal` names its typed code and the offending value |
| replay and reconstruct | the determination rebuilds byte for byte, and a replay against a different threshold diverges (`UBO-G16`) |
| **human in the loop, audited by construction** | **the first active example to compose a HITL primitive with a Context Product** — referral, release, refusal, and a second record carrying the four links (`UBO-G09` to `UBO-G13`) |
| local and remote producer boundaries | in-process, the standard MCP door and the HTTP door over one opened product |
| prevent identity masquerading | neither the perspective nor the jurisdiction set is on the request surface |

**First on the ladder at this rung:** a governed Context Product handed to an
existing HITL workflow primitive, with the **construction boundary gated**
rather than described — and *a finding kept inside the product* rather than
dropped out of it, which is what makes the referral meaningful.

## 2 · SDK friction observed (§E)

### 2.1 Whole-tree counts

| region | physical | non-comment |
|---|---|---|
| plumbing (`produce.py`, `server/serve.py`) | 222 | 167 |
| domain (`deployment.py`, `acquisition.py`, `projection.py`) | 1,165 | 910 |
| **HITL (`review.py`)** | **210** | **—** |
| presentation (`run.py`) | 138 | 114 |
| documents (config, environment, four artifacts) | 795 | 659 |

Distinct `ccf` / `ccf_runtime` names imported: **43** — nine more than rungs
17, 18 and 19, and every one of the nine is a HITL symbol. Private SDK symbols
in the tree: **0**; in its tests: **1** (the hand-built replay environment).

### 2.2 The A2 measurement — fifth instance, and the threshold is NOT crossed

`D-GATE-cp-18` fixed the rule: keep measuring; revisit the **adopter
documentation and the pattern first** if substantially identical **generic**
glue exceeds roughly **30 lines**, or a **fifth undocumented concept**
appears. `D-IMPL-343` is not reopened and no abstraction is pre-authorized.

| dimension | cp-13c | cp-17 | cp-19 | cp-18 | **cp-15** |
|---|---|---|---|---|---|
| domain-policy LOC | 64 / 56 | 58 / 57 | 55 / 54 | 89 / 87 | **103 / 97** |
| generic plumbing LOC | 22 / 21 | 22 / 20 | 25 / 22 | 41 / 36 | **41 / 38** |
| **identical generic lines** | — | — | 15 (vs cp-17) | 23 (vs cp-19) | **18** (vs cp-18 and vs cp-19 alike) |
| concepts absent from public docs | 4 | 4 | 4 | 4, one under-stated | **4, none new** |
| hand-built runtime objects on the envelope | 0 | 0 | 0 | 0 | **0** |
| duplicated authority | 0 | 1 | 3 | 2 | **0** |
| AI-generatable from spec + public guidance | no | partly | partly | yes for the seam | **yes for the seam** |

**RULED at `D-GATE-cp-15`: B remains the disposition — documentation and
pattern, no SDK abstraction. No envelope SDK phase is opened.**

**Neither trigger fired.** Substantially identical generic glue measures
**18 lines**, below the ruled threshold of roughly 30 — and it *fell* from
cp-18's 23 rather than rising, because this rung's seam carries four typed
refusals where cp-18 carried three and the shared part is correspondingly a
smaller share. **No fifth undocumented A2 concept appeared**: the four the
adopter page documents were sufficient a fifth time, and the page's own rule
decided the request surface again, including the exclusion of `jurisdictions`.

**Duplicated authority is zero here, and that is worth naming.** This is the
only rung on the ladder whose estate already carries both halves of the
mapping the product needs — `principal.perspective` and
`principal.sees_eu_person_data` — so nothing was declared that the estate
could have said. Rungs 17, 19 and 18 each had to declare one.

### 2.3 HITL composes with no SDK contract change — stop condition 4 did not fire

Measured before the tree was written and again at close:

- `ReviewQueue(transport=…, audit=…, clock=…)` — **three objects, two of them
  concrete SDK classes** (`InMemoryHitlTransport`, `AuditLog`) and one a
  clock. Gate 0 predicted *"4 injected objects + 1 policy artifact"*; the
  measured figure is **three and no artifact** (`UBO-F-14`).
- `submit_for_review` accepts the originating record reference as
  `workflow_state_ref` and a product URI as `output_ref` unchanged.
- `release` returns a `ReviewResolution` whose record carries the event, the
  item, the submission and the verdict — **exactly the four links the ruling
  required for the second record**, with no deployment-side record type
  invented and no synthetic "review product" built.
- The TOCTOU guard refuses a wrong hash through a product exactly as it does
  in the SDK's own fixtures.

**Nothing in `ccf.hitl` was changed, extended or worked around.**

## 3 · Launch blockers

None raised.

## 4 · Findings raised

| id | finding | class (§B) | disposition |
|---|---|---|---|
| `UBO-F-01` | **No ownership cycles exist in the curated estate.** Measured two ways — no chain in `bo_chain_hop` revisits an owner, and no hop's `owned_id` equals an earlier hop's `owner_id`. The vault specification's first counterfactual therefore has no data. | §B.4 estate limitation | **RULED, and re-affirmed at `D-GATE-cp-15`: do not engineer.** No engineered estate cycles are required. The member is kept, served honestly empty and **computed**, and the injected-cycle in-process positive control is kept — it proves the implementation can detect a cycle and that estate emptiness is not the same thing as constant-empty code |
| `UBO-F-02` | **`ReviewQueueItem.output_ref` requires a `ccf-artifact` versioned URI and refuses a bare content address**, while the ruling names the content address. Both are satisfied without changing either: the URI's version component **is** the address, so the product URI carries exactly what the ruling named. Nothing on the public surface says `output_ref` is URI-shaped. | §B.3 documentation gap | recorded; no SDK change. **Ruled at `D-GATE-cp-15`: the SDK's URI requirement is NOT to be loosened to accept a bare content address**, and the gate proving the version component equals the served address is kept |
| `UBO-F-03` | **`PendingHitlEvent.product_content_hash` is the ITEM's hash, not the product's content address.** A reader reaching for the product's address by that name gets the hash of the review item instead. The TOCTOU guard binds the item, which is correct — the name is the surprise. `CP17-F-19`'s family. | DX note | recorded |
| `UBO-F-04` | **`ReviewQueueItem.lineage` requires at least one entry**, so a finding with no supporting evidence cannot be submitted at all. That is *why* the ruling's "do not manufacture references" is expressible here as **do not refer**, and the product names such findings as not-referred rather than referring them with an empty trail. | §B.4 design consequence | recorded; the behavior is correct and the constraint is what makes it so |
| `UBO-F-05` | **A sabotage that cannot redden its gate is not a sabotage.** Replacing the cycle computation with a constant empty list left `UBO-G19` GREEN, because on an estate with no cycles the served value is `[]` either way. A positive control that injects a cycle in-process was added, and the gate now reddens. | proof-machinery defect, mine | corrected before close; recorded rather than quietly fixed |
| `UBO-F-06` | **The refresh register and the ownership chains do not join.** `kyc_refresh_state` is keyed by LEI; every chain anchor in this estate is an offshore vehicle. The two populations have no overlap at all. | §B.4 estate limitation | **ruled at `D-GATE-cp-15`: no invented join.** The `refresh_state` member is served as a **stated absence** with its reason, rather than omitted or silently empty |
| `UBO-F-07` | **`kyc_document` carries no text field**, only typed attributes, so a lexical Similarity corpus had to be composed at the acquisition seam from the document's kind, entity and owner names and jurisdiction. A one-word `kind` scores zero against any multi-word query and would empty the class at any floor above zero. | §B.4 estate limitation | disclosed at the declaration site and in the README; the floor is 0 and says why |
| `UBO-F-08` | **One chain per anchor**: 50 chains over 50 anchors, so each entity has exactly one beneficial-ownership chain and one terminal person. Assertions about *sets* of owners would be vacuous. | §B.4 estate limitation | the gates assert the threshold partition and its exhaustiveness, never a count of owners |
| `UBO-F-09` | **Every sanctions screening in the estate is in the review band** — all 19 score between 0.71 and 0.84, none clears `auto_clear` and none falls below `review_floor`. There is no auto-cleared and no auto-rejected screening to contrast against. | §B.4 estate limitation | the product's screening member is therefore always a review finding, and the gate asserts the disposition follows the policy thresholds rather than a mix that does not exist |
| `UBO-F-10` | **`kyc-refresh` is the business trigger and is not a priced intent.** No `bo_threshold` row prices it; the estate prices `onboarding`, `enhanced_due_diligence` and `sanctions_screening`. Inventing a row would have been a fixture. | §B.4 example decision | the three priced intents are declared and `kyc-refresh` is named in §A as the trigger; an unpriced intent is refused by name |
| `UBO-F-11` | **The declared gate refused a computed-empty serve** until it was guarded to require a threshold only when an entity was actually served. Unguarded, it turned the A6 comparator into a refusal and handed back the existence oracle `UBO-G17` exists to close. Same class as rung 18's. | proof-machinery defect, mine | corrected before close; recorded. Worth carrying forward: a declared gate that asserts a member's presence must ask whether the empty serve is a legitimate outcome first |
| `UBO-F-12` | The replay environment is hand-assembled in the tests (~95 lines, one private reach). `CP06C-F-01` / `CP17-F-06` / `ATM-F-12` / `IBO-F-11`, **fifth instance**. | §B.3 carried | carried; the tree itself reaches no private symbol |
| `UBO-F-13` | `CP17-F-12`'s scorer semantics apply unchanged: F is a mean over every observation in the view, so five supersede-only classes dilute the one curve class. | §B.2 carried | never re-pinned |
| `UBO-F-14` | **The ReviewQueue composition is cheaper than Gate 0 predicted**: three injected objects and no policy artifact, against the predicted four plus an artifact. Both the transport and the audit log ship as concrete classes. | measurement, favourable | recorded so the Gate-0 friction row can be corrected rather than carried forward unmeasured |

## 5 · Estate / example limitations (§B.4)

No ownership cycles (`UBO-F-01`); the refresh register does not join the
chains (`UBO-F-06`); KYC documents carry no text (`UBO-F-07`); one chain per
anchor (`UBO-F-08`); every screening in the review band (`UBO-F-09`);
`kyc-refresh` unpriced (`UBO-F-10`). Every registered principal holds at least
one jurisdiction grant, so `UBO-G18`'s ungranted state is unreachable from the
data and the test constructs it.

## 6 · Product result

At `asked_at = 2026-08-25T00:00:00Z`, entity `ICJ-SPV-027` (Redstone Ventures
S.A., Panama), chain depth 3 through Ireland to a Bulgarian EU resident at
12.59% effective ownership, under `onboarding` with a 25% threshold set by the
strictest priced jurisdiction on the chain's own path:

The KYC analyst receives the chain, the person with a carried resolution
confidence, one sub-threshold finding, one resolution finding and one
sanctions finding in the review band, the declarations beside the computed
figure, and an empty cycle member. **Two findings are referred** to the review
queue — the sub-threshold owner and the sanctions hit — each naming the
originating replay-record reference and the product's content address. The
coverage banker, who holds no residency entitlement, receives the same
question's product with the person absent entirely and no indication that
anything was withheld.

The same entity under `enhanced-due-diligence` would bind at a lower
threshold; on `ICJ-SPV-149` that is demonstrated live, where a 17.75% owner is
a referred finding under one intent and a reportable owner under the other.

**What a consumer can rely on:** the member set of its perspective; a
resolution confidence on every person; every reportable owner at or above the
applicable threshold and every sub-threshold finding below it; a referral for
every finding backed by evidence; the product's immutability under human
review. **What it cannot rely on:** any cycle detection demonstrated against
real cycles (there are none — `UBO-F-01`); a refresh-cycle state for these
anchors (`UBO-F-06`); an auto-cleared sanctions screening (`UBO-F-09`); the
freshness factor as a per-class number (`UBO-F-13`).

## Sabotage record

Every gate's sabotage and the red it was observed at are in
`artifacts/gates.yaml`. Summary: 20 declared; **18 observed RED** — twelve by
a single reverting edit with only that gate's test executed, and six
(`UBO-G07`, `UBO-G12`, `UBO-G13`, `UBO-G16`, `UBO-G17`, `UBO-G18`) carrying
the sabotage inside the test. **Two are `unavailable`**, each naming its
guard: `UBO-G01` because `CATEGORY_ORDER` decides the executed order, and
`UBO-G11` because the `NO_HITL_ACTIONS` sentinel is written by the SDK's own
record builder and no deployment seam can set it — `open_product` takes no
such argument and the resolver passes none.

**One sabotage left its gate green on the first attempt** (`UBO-F-05`), and it
was the interesting one: on an estate with no cycles, the cycle member reads
`[]` whether it was computed or hard-coded, so the gate could not tell a
measurement from a constant. The fix was a positive control that injects a
cycle in-process, which is also what makes Dave's "no cycle is invented" limb
two-sided rather than a tautology.
