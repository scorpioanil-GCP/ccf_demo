# cp-20 — findings

Classified under `docs/EXAMPLE-EVALUATION-CRITERIA.md` §B **before**
remediation, and the six sections of §K are kept apart.

| id | category (§B) | disposition |
| --- | --- | --- |
| `CLD-F-01` | 4 · estate limitation | recorded and disclosed; residual `341-4` stays carried |
| `CLD-F-02` | 3 · post-launch enhancement | backlog record below |
| `CLD-F-03` | 3 · post-launch enhancement | backlog record below |
| `CLD-F-04` | **2 · launch ergonomics CANDIDATE** | **raised with the friction measured; not repaired** |
| `CLD-F-05` | 4 · estate limitation | recorded; both authorities served |
| `CLD-F-06` | 3 · post-launch enhancement | **CLOSED 2026-09-23** — `D-IMPL-347` A2; the shipped path now refuses at the child seam |
| `CLD-F-07` | — · proof-machinery defect, mine | corrected before close, recorded not swapped |
| `CLD-F-08` | — · working as designed | recorded so it is not re-derived |
| `CLD-F-09` | — · working as designed | recorded so it is not re-derived |
| `CLD-F-10` | 4 · example-contract limitation | resolved by structure, not by weakening the check |
| `CLD-F-11` | **2 · launch ergonomics CANDIDATE** | raised with the friction measured; not repaired, and not an `D-IMPL` |

**Active issue cap: 0 of 3.** `CLD-F-04` is a category-2 **candidate** and is
not a blocker until ruled one (§C). `AIA-F-01` was charged on rung 22 and does
not carry here: nothing in CP-20 depends on or reactivates it.

**SDK / runtime diff: EMPTY.** `git diff main..HEAD -- src runtime` produces no
output for this rung. No `D-IMPL` id was spent; `D-IMPL-346` remains unspent.

---

## `CLD-F-04` — a request-scoped optional child costs the whole consumer chain

**Category 2 candidate (launch ergonomics). Raised, measured, not repaired.**

`include_federated` is a request parameter. The only seam that can honor one is
child resolution, reached through `open_product(build_children=…)`. That
keyword is **refused beside a declared `agent:` or `skills:` section** —
*"a handed-in chain beside a declared one leaves the question of which
governs"* — so a composite that needs a request-scoped child may not declare
its chain at all and must rebuild what the road derives.

**Measured on this tree, 2026-09-22:**

| what | executable lines |
| --- | --- |
| the feature itself — the flag check and an empty return | **4** |
| `_registered_chain` — parse the agent and skill, derive the two pins, register | 30 |
| `FederatedChildren.factory` — grant ledger, catalog, grant request, admission gate, resolver | 87 (incl. the 4) |
| `_pinned_ref` — render content-addressed refs the road would have derived | 7 |
| `_NoApprovalSink` — the SDK's own is private and not exported | 6 |
| **total inside the fence** | **130** |
| plus `artifacts/consumer-chain.yaml` | 40 declaration lines |

Two of those rows are sharper than the total. **The SDK's `_NoApprovalSink` is
private**, so a handed-in chain must copy six lines of the SDK's own code to
supply a sink it will never consult. And **`open_product` does not register the
manifest's artifacts before calling a `build_children=` factory** — measured:
the Control Plane has *zero* audit events at that point — so the policy bundle
and debt profile the agent pins must be registered by the factory itself,
through `derive_deployment` + `register_manifest_entries`.

**§C step 1** — could the SDK ship without per-request optional-child
suppression and still honestly claim its core contract (§D)? **Yes.** §D
requires that a composite *declare the classes it requires and admit governed
children*; it does not require conditional composition. So not category 1.

**§C step 2** — would the supported alternative create enough friction or
misuse risk to materially undermine adoption? **Raised for a decision.** 130
lines of grant-ledger wiring to skip one child is substantial repeated
plumbing, and this is its **first** instance on the ladder. §J's third-instance
rule has not fired. Recorded here with the count so a second and third instance
raise the priority rather than re-deriving the measurement.

**Current supported path:** exactly what this tree does. **Scope/risk of a
fix:** a way to compose a request-scoped decision *over* the derived chain
rather than instead of it — no new seam, but it touches `open_product`'s
refusal matrix. **Recommended release:** post-launch unless a second rung meets
it.

---

## `CLD-F-06` — a governed refusal raised from the child seam escapes as an exception

**Category 3 (post-launch enhancement).** `GovernedResolver` catches
`GovernedRefusalRaised` around the acquisition seam and **nowhere else** —
`src/ccf/products/resolver.py`, and the comment there is explicit: *"Only this
type; any other exception the seam raises propagates exactly as before."* The
child-resolution call site has no such handler.

Measured 2026-09-22: raising `GovernedRefusalRaised` from a `build_children=`
resolver produces a traceback, not a `RefusalEnvelope`.

**The workaround, preserved as history:** the check ran at the **acquisition
seam**, which runs strictly before child resolution. The envelope was read
there in the same pass, so the check cost nothing extra and no peer had been
called. It worked — and it put a dispatch decision in the seam that reads
sources, which is not where it belongs.

---

### `CLD-F-06` — CLOSED 2026-09-23

**The shipped CP-20 path now exercises governed refusal at the
child-resolution seam end to end.** `D-IMPL-347` A2 wrapped all four
deployment-supplied seams, so a `GovernedRefusalRaised` from the child resolver
becomes a `RefusalEnvelope` recorded as a **composite** refusal — Dave's
ruling: *"there is no child outcome to attach it to."*

**Proven against the live estate**, in `test_an_out_of_envelope_ask_is_refused_before_any_peer_is_called`
(`CLD-G10`'s own gate, strengthened rather than a new one):

| # | proof | result |
|---|---|---|
| 1 | Citibank remains outside the request envelope | unchanged; no estate retuning |
| 2–3 | the child resolver raises; the SDK converts it | `RefusalEnvelope`, `reason = subject-unavailable` |
| 4 | `refusal_seam` | **`build_children`** |
| 5 | `child_resolutions` | **`()`** — a composite refusal, no child row |
| 6 | no peer dispatch | the refusal KIND proves it: a post-dispatch refusal is `child_admission`, which the `unattested` case still produces, and the two must differ |
| 7 | no band-derived point estimate | `CLD-G13` unchanged and green |
| 8 | externally equivalent to the workaround | the whole 20-test suite passes unchanged |

**The second read, measured.** The child seam receives no source handles, so
it reads the envelope rows itself through `acquisition.envelopes_in_force` —
**3 source calls against a full acquire's 9** (one member-id→LEI query, two
scope passes plus the envelope rows). It costs **no** environment resolution:
`FederatedChildren.bind()` already held the road-resolved settings from open,
retained by an earlier pass for exactly this. Latency **25 ms median against
the live estate, versus 35 ms for a full acquire — 71%**, and that ratio is
honest rather than flattering: by *calls* the read is narrow, by *wall time*
connection setup dominates a small query. It is not a second acquisition; no
second answer to the question is produced, and no peer is called before the
decision.

The friction that remains is `CLD-F-11`.

---

## `CLD-F-11` — the child seam may refuse, but cannot see the deployment's sources

**Category 2 (launch ergonomics CANDIDATE), raised 2026-09-23 with the friction
measured. Not a missing capability**, and deliberately **not** a `D-IMPL`:
Dave, 2026-09-23 — *"The SDK can already express the correct behavior; the cost
is that the child resolver must perform a narrow second read... That is real
friction, but it is not yet evidence that the SDK cannot ship honestly."*

**Measured.** `D-IMPL-347` A2 lets the per-question child seam raise a governed
refusal. Neither surface it is handed carries the deployment's source handles:

| seam | receives | reaches this deployment's two legs? |
| --- | --- | --- |
| `acquire(context)` | `AcquisitionContext`, with `context.sources` | **yes** |
| the `build_children=` factory | `ConsumerContext` — `artifact_store`, `clock`, `control_plane`, `mcp_skills`, `tenant_id` | **no** |
| `resolve_for(...)` | `requirements`, `request`, `asked_at`, `admitted_at`, `composition_invocation`, `consumer_lineage` | **no** |

So a refusal decided on the deployment's **own** facts — exactly what an
envelope check is — requires the deployment to carry the sources across the
seam boundary itself. This rung does it with `FederatedChildren.bind()`, eight
lines, called once at open from `produce.product`.

**Why it is a candidate and not a blocker.** The correct behavior is fully
expressible today with no SDK change, the carry is small and local, and the
second read is narrow by call count (3 against 9). The one figure that is
*not* flattering is latency: 25 ms against a full acquire's 35 ms, because
connection setup dominates a small query. That is recorded rather than
smoothed.

**Revisit only if** a second credible product independently needs the same
source-reach pattern; or the second read creates material correctness or
temporal-consistency problems; or the measured glue or latency makes the paved
path impractical. **Do not open a `D-IMPL` for this on one instance.**

**A second, smaller instance of the same shape, recorded here rather than
given its own id:** `ccf.deployment.environment.resolve_values` is public at
its submodule and not re-exported at the package, so a seam resolving
environment values itself would have to write the `A-1` submodule import that
`D-IMPL-346` just closed elsewhere. This rung does not need it — `bind()`
already holds resolved settings — but the next tree that does will meet it.

---

## `CLD-F-02` — a product's TTL is a class constant, and the peer's is per-row

**Category 3 (post-launch enhancement).** `peer_product_declaration` declares
`declared_ttl_seconds` **per (counterparty, facility)** — 21600 / 10800 / 7200
on this estate. A Context Product class carries **one** `max_ttl_seconds`.

The peer therefore declares 21600, the value for the one facility this rung
ever serves, and `CLD-G05` asserts the served lifetime against the row read
**live** rather than against the constant — so the coincidence is checkable
instead of assumed, and the gate reddens if the estate moves. Adjacent to the
dual-TTL work already ruled post-launch. **Current supported path:** one class
per TTL regime, or the class ceiling plus a served declaration, as here.

---

## `CLD-F-03` — the projection cannot see `eligibility_basis`

**Category 3 (post-launch enhancement).** `ChildContractView` is a mapping from
product class to contract. The admission authority that actually governed the
read — `eligibility_basis`, one of `local-register` / `producer-attested` /
`provider-controls` — lives on the **replay record's** child rows and is not
reachable from the plan.

So `CLD-G15`'s payload marking is derived from the admitted child's **tenant**
against the deployment's own, which is admission evidence the plan *can* see
and is exactly as structural. The record carries the authority; `CLD-G16`
asserts it there. **Current supported path:** the tenant comparison.
**Adoption impact:** a product wanting to serve *which authority* admitted each
claim must read its own replay record back.

---

## `CLD-F-01` — residual `341-4` does not go live on this rung

**Category 4 (engineered-estate limitation).** Gate 0 predicted CP-20 would be
the first live carrier of `341-4` — an admitted child's expiry becoming the
composite's binding TTL floor — and the Gate-1 report repeated it. **Both are
wrong**, and the correction is recorded rather than left in conversation.

Measured: the class ceiling is 4 h; the three peer declarations are 6 h
(`FAC-6F4065`, attested, in envelope), 3 h (`FAC-405B7A`, Citibank, **out of
envelope** under `Q1`(b)) and 2 h (`FAC-A4A5EE`, **unattested**, refused under
`Q2`). The only two short enough to floor the composite are precisely the two
the governance rules refuse, and Bank of America holds product declarations on
only two of its six facilities, so there is no fourth candidate.

`CLD-G04` is therefore **`unavailable` with its guard named** (`Q4`, Dave,
2026-09-22), its test is a **tripwire** that reddens if the estate ever gains
an admissible short declaration, and **nothing is manufactured to retire the
residual**. The floor rule itself is proven on its ceiling-binding arm by
`CLD-G05`.

---

## `CLD-F-05` — two commitment authorities disagree

**Category 4 (engineered-estate limitation).** The filed participations on
`FAC-6F4065` sum to **$950,000,000**; `ccf_v2.facility.commitment_amount` says
**$500,000,000**. The EX-10 covers `FAC-6F4065` and `FAC-A4A5EE` ($300 m
together $800 m), which still does not reconcile.

Not repaired, and neither figure is dropped. The consent arithmetic uses the
**filed commitment schedule's own total** — Required Lenders is a percentage of
commitments held by lenders, which is what the schedule enumerates — and the
payload's `findings` names the disagreement, both figures and the denominator
selected. Rung 21's `LEX-G11` pattern.

---

## `CLD-F-07` — a gate of mine that its own sabotage could not redden

**A proof-machinery defect, mine, corrected before close and recorded rather
than quietly swapped.**

`CLD-G17` forbids `Federate` and `Enrich` in `operators_invoked`. The first
version checked **exact set membership**. Operator keys are
`<category>.<name>`, so a key named `federate.peer-position` would have sailed
straight past it — and the sabotage that should have reddened the gate left it
green, which is how the defect surfaced.

The check now matches as a **substring over each member**, and the sabotage
bites. Recorded because the class recurs: an instrument that cannot fail when
the thing it measures is broken is not evidence.

---

## `CLD-F-08` — `omissible_outcomes` governs the payload, never admission

**Working as designed; recorded so it is not re-derived.** The first sabotage
of `CLD-G07` added `refused` to the requirement's `omissible_outcomes` and the
gate **stayed green** — correctly. That field decides what may be omitted from
the served payload; it has no bearing on whether a refused child refuses the
composite. `D-IMPL-336` F1 holds regardless of it.

The sabotage that does bite is a deployment one: the `build_children` wrapper
swallowing the refusal and reporting no outcome, which the composite would then
price as an honest absence. That is the failure the gate exists to catch.

---

## `CLD-F-09` — a door cannot misdeclare its own tenant

**Working as designed; recorded because it changed a test's construction.**
`derive_deployment` refuses at the **producer's own boot** when a `door`
section asserts a `producer_tenant` its deployment does not declare
(`D-IMPL-343` R-6). So the tenant-mismatch impostor for `CLD-G03` could not be
a mislabelled door — it had to be a genuinely different deployment.

Defense in depth ahead of the consumer's admission check, and worth knowing:
the consumer's registration is the second line, not the only one.

---

## `CLD-F-10` — one `examples/cp-*` tree is one deployment, and this rung is two

**Category 4 (example-contract limitation), resolved by structure.**

`tests/examples/test_spine_separation.py` holds every `examples/cp-*` tree to
*exactly one module opening canonical regions* and *exactly one fabric-facing
module printing*. A cross-organizational rung has two deployments — the
consumer's and the co-lender's — each with a legitimate spine and a legitimate
runner. The first build nested the peer at
`examples/cp-20-syndicated-lending-co-lender/peer/` and produced **four new
failures** against the baseline.

**The check is right and the layout was wrong.** The co-lender is a different
institution; making it a subdirectory of ours said otherwise. It now lives at
`examples/peer-cp-20-co-lender/`, outside the `cp-*` ladder glob — the place
`door-cp-05-credit-exposure-rollup` already occupies, and for the same reason:
a supporting producer tree is not a rung.

**Nothing in the contract was changed to accommodate this example.** Measured
after the move: 12 failed on the candidate against 12 failed on the baseline,
the identical pre-existing set — **zero new failures**.

---

## Product result (§K.6)

On `FAC-6F4065` at `participant`, with the boundary crossed: 18 filed members
totalling $950 m; our own $61.5 m at `BBB-`/`performing`; Bank of America's
attested $187 m admitted under tenant `cp-20-peer-demo` and marked
`remote-attested`; filed and declared figures **agree** (divergence $0);
Required Lenders 50 % against known consent of **26.16 %** — **not reachable**;
`D_c = 0`; expiry at the 4 h class ceiling against the peer's declared 6 h.

Without the boundary: the same syndicate, known consent **6.47 %**,
`D_c = 0.50` — the declared cost of the absent child.

**What a consumer can rely on:** which claims are reconstructible and which are
merely attested; that no figure in the payload was derived from a band; that an
out-of-envelope ask never reached a peer; and that the answer's validity never
outlives what it was composed from. **What it cannot:** that the consent
denominator is the facility's stated commitment — it is the filed schedule's,
and the two disagree (`CLD-F-05`).
