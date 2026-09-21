# Findings — cp-18-ib-opportunity-synthesis

Built 2026-09-21 on Dave's Gate-2 GO of the same day, against `CP-SPEC-018`
with the §F.4 composition ruling folded in first. Every finding below was
classified under `docs/EXAMPLE-EVALUATION-CRITERIA.md` §B before any repair
was considered, and nothing in the SDK was repaired: findings are raised, not
resolved (`D-IMPL-261`). The close-report sections follow §K, in order.

**Measured at close (2026-09-21, live estate, `CCF_REQUIRE_ESTATE=1`):**
18 gate tests **passed**, 0 failed, 0 xfailed, 0 skipped, in three modules
under `tests/examples/test_cp_18_*.py`. 18 gates declared, 18 claimed by an
executing test. **17 of the 18 were observed RED** under their own sabotage;
`IBO-G01` is `unavailable` with its guard named.

**Accepted at `D-GATE-cp-18`, 2026-09-21**, on the candidate
`cp-18-ib @ 03ebeb34`, merged `--no-ff` into `main`. **No SDK behavior
change.**

**Active SDK issue cap: 0 of 3.** No launch blocker, no missing IB-required
capability, no incorrect SDK behavior and no security or governance defect.
**The §F.4.2 complexity stop DID fire**, and it was resolved exactly as the
ruling directs — child count zero, rung completed on the governed envelope
alone — so it is a recorded outcome rather than an open question.

## 1 · SDK capability proven

| launch-contract item | how this tree exercised it |
|---|---|
| define contracts as Control Plane artifacts | one `ccf_config.yaml` declares the class, four operators, a five-parameter request contract including an **array** parameter, two λ_c decay regimes, the debt profile, the policy bundle and the door |
| assemble through the single writer and the declared operators | five entity classes and four edge types enter through L2, edges first, attributed nodes last |
| apply authorization and policy before use | the envelope is computed at the acquisition seam from `context.perspective`: the coverage portfolio, the projection plan, the weight vector and the restricted state, all before anything ranks (`IBO-G09`, `IBO-G10`) |
| preserve product identity and content addressing | three perspectives, three content addresses, one class and one plan id (`IBO-G02`) |
| calculate Context Debt correctly | two decay regimes side by side — a `valid-from` curve on dated signals and `supersede-only` on four standing classes — with C over the perspective's own required classes |
| refuse correctly, as data, with a replay reference | four distinct governed refusals: no projection plan, no coverage portfolio, a signal type outside the plan, and the tolerance (`IBO-G14`, `IBO-G15`) |
| preserve sufficient refusal evidence | each refusal's `assembly_refusal` names its typed code and the offending value |
| replay and reconstruct | a ranking rebuilds byte for byte from its own record under the weight version that served it, and a replay against a different vector **diverges** (`IBO-G06`, `IBO-G07`) |
| local and remote producer boundaries | in-process, the standard MCP door and the HTTP door over one opened product |
| prevent identity masquerading | neither the perspective nor the weight version is on the request surface; both are resolved from the credential and the Control Plane |

**First on the ladder at this rung:** a **consumer-anchored** product — the
subject is the banker, so there is no principal-independent version of the
answer to filter; and a **policy-versioned ranking function** pinned inside the
fabric, so a ranking replays under the weights that were in force when it was
served rather than under today's.

## 2 · SDK friction observed (§E), and the A2 measurement

### 2.1 Whole-tree counts

Physical lines / non-comment non-blank, measured 2026-09-21.

| region | physical | non-comment |
|---|---|---|
| plumbing (`produce.py`, `server/serve.py`) | 216 | 167 |
| domain (`deployment.py`, `acquisition.py`, `projection.py`) | 1,355 | 1,082 |
| presentation (`run.py`) | 138 | 116 |
| documents (config, environment, four artifacts) | 868 | 658 |

Distinct `ccf` / `ccf_runtime` names imported by the tree: **34**. Private
(underscore) SDK symbols in the tree: **0**; in its tests: **1**
(`GovernedResolver._operator_parameters`, inside the hand-built replay
environment — `CP06C-F-01`, fourth instance).

### 2.2 The A2 measurement — MEASURED AGAIN, NOT RECONSIDERED

`D-GATE-cp-19` closed A2 at **B**: adopter documentation, no SDK abstraction.
That ruling stands. This section is the fourth instance's count on the same
seven dimensions, recorded so the trend is visible, and it does **not** reopen
the decision.

| dimension | cp-13c (1st) | cp-17 (2nd) | cp-19 (3rd) | **cp-18 (4th)** |
|---|---|---|---|---|
| domain-policy LOC | 64 / 56 | 58 / 57 | 55 / 54 | **89 / 87** |
| generic plumbing LOC (`deployment.acquire`) | 22 / 21 | 22 / 20 | 25 / 22 | **41 / 36** |
| concepts absent from public docs | 4 | 4 | 4 | **0 new; one under-stated — see 2.3** |
| hand-built runtime objects on the envelope | 0 | 0 | 0 | **0** |
| duplicated authority | 0 | 1 | 3 | **2** |
| structural similarity of the seam | — | — | 0.71 vs cp-17, 15 of 22 identical | **0.66 vs cp-19, 23 of 36 identical** |
| AI-generatable from spec plus public guidance | no | partly | partly | **yes for the seam — see 2.3** |

**The domain half is bigger here, and it is not duplication.** 89 lines against
cp-19's 55, because this envelope does four things where cp-19's did two: the
projection plan, the weight vector in force, the restricted-state read, and the
element-wise containment of a set-valued request parameter. Cross-rung
similarity on the domain half stays low (`plan_for` at 0.36 against cp-19's).

**The seam grew, and the growth has one cause worth naming.**
`deployment.acquire` is 41 physical lines against cp-19's 25, with 23 of 36
code lines identical to cp-19's. The growth is **three** exception-to-governed-
refusal conversions instead of one — each a six-line block of the same shape,
repeated *within one tree* rather than across trees.

**RULED at `D-GATE-cp-18`: B remains the disposition** — adopter
documentation, no SDK abstraction. The growth from 15 to approximately 23
repeated lines is **attributable to a domain-specific refusal idiom rather
than to a new generic seam**, and `D-IMPL-343` is not reopened.

**The threshold carried forward to KYC**, restated as ruled: continue
measuring; if substantially identical **generic** glue exceeds approximately
**30 lines**, or a **fifth undocumented concept** appears, **revisit the
adopter documentation and the pattern first** — not an SDK abstraction, which
is not pre-authorized.

### 2.3 Did the adopter page remove the private-knowledge cost? Mostly — and the gap it left is measured

This rung was written against
`public/how-to/condition-acquisition-on-the-verified-credential.md` rather
than against the prior trees' source, which is the experiment
`CP-SPEC-018` §G.2 set. The result:

- **The seam itself needed no prior tree.** All four concepts the page
  documents were sufficient, and the page's own rule — *if changing the value
  could give the caller more than its credential permits, it is envelope
  input* — decided the request surface directly, including the exclusion of
  `weight_version` that `IBO-G06` then depends on.
- **No FIFTH undocumented concept was required.** Dave's second reopen trigger
  did not fire.
- **But concept 3 was UNDER-STATED, and the build proved it.** The page said a
  `valid-from` class reads `observed_time` as its freshness clock and that an
  undated claim *"has no age the curve can measure"*. The actual behavior is a
  hard refusal at serve time (`MissingDecayInstant`), which this rung hit when
  it modeled a maturity wall — a standing state with no event date — inside
  the dated `signal` class. **The page has been corrected** with the
  consequence and the modeling rule it implies: a standing state and a dated
  event are different observation types and need different classes. Recorded
  as `IBO-F-04`.

**The SDK's refusal here was the best possible behavior**, and is worth
recording as a positive: it refused loudly, named the class and the field, and
explained *why* a fallback would be wrong. It taught the correct model rather
than silently reporting a fresh figure for an observation with no known age.

## 3 · Launch blockers

None raised.

## 4 · Findings raised

| id | finding | class (§B) | disposition |
|---|---|---|---|
| `IBO-F-01` | **The estate holds no SC 13D data at all** — no table, view or column anywhere in `ccf_v2` names a 13D or an activist stake. The vault specification calls this *"one of the highest-signal, freely available, timestamped events for M&A origination"* and the weight vector prices it at the M&A originator's **top** weight (1.0 against DCM's 0.1). The single sharpest M&A discriminator is priced and unsupplied. | §B.4 estate limitation | declared `unsourced` in `artifacts/source-vocabulary.yaml` with the reason, never simulated. The counterfactual is carried by `maturity_wall` instead, which the estate does supply |
| `IBO-F-02` | **Four of the eleven priced signal types reach no product.** `activist_stake_13d` (no source), `merger_proxy` and `registration_s4` (passages only, no typed signal row), and `institutional_positioning_13f` (the estate's latest 13F report period precedes the demonstration window, so the quarterly cadence puts it outside every 90-day window ending at the pinned instant). A weight priced for a signal the estate cannot supply contributes zero, honestly. | §B.4 estate limitation | disclosed in the vocabulary artifact and the spec; the gates assert relationships and never a count of admitted types |
| `IBO-F-03` | **The signal-type vocabulary is a deployment mapping, not an estate column.** `perspective_weight` and `ib_signal_class` name eleven types; no table stores a signal under those names, and `signal_event` uses a different vocabulary entirely (CP-11's). The type-to-source map is this deployment's, declared in one artifact. | §B.4 example decision | declared and cited; a reader consults one artifact to know where `maturity_wall` comes from |
| `IBO-F-04` | **A `decay_basis: valid-from` class REFUSES an undated claim, and the public page understated that.** Modeling a maturity wall — a standing state with no event date — inside the dated `signal` class produced `MissingDecayInstant` at serve time. The correct model is a second observation type with `decay: supersede-only`. **The adopter page has been corrected** with the consequence and the rule. | §B.3 documentation gap, found by building against the page | page corrected; **NO SDK DEFECT** (`D-GATE-cp-18`). A class declaring `valid-from` decay requires an actual temporal observation: an undated standing state cannot be placed in it and silently anchored to decision or ingestion time. The SDK refusing the incorrect model is `D-IMPL-332` working as designed |
| `IBO-F-05` | **The three projection plans permit identical signal types**, so the plan is not the perspective discriminator — the weight vector is. An implementation keying the perspective's shape on `permitted_signal_types` would find the three perspectives indistinguishable while the counterfactual silently stopped being demonstrated. `IBO-G03` holds the two apart and asserts the estate's plans are still identical, so the trap cannot quietly disappear. | §B.4 estate property | gated |
| `IBO-F-06` | **A sabotage of Π's `perspective` argument could not redden the perspective gate.** The perspective reaches the *ranking* through the **acquisition seam** — the weight vector written onto the banker claim — not through Π's argument, so forcing Π's role left all three orderings intact. The sabotage was moved to the vector lookup. A useful fact about where the perspective actually enters. | **measured architectural fact**, not a failed product control (`D-GATE-cp-18`) | the discriminator flows *verified perspective → acquisition → versioned weight vector on the banker claim → ranking*, so a sabotage of Π's argument leaving the gate green is the architecture reporting itself. The sabotage was moved to the vector lookup |
| `IBO-F-07` | **Two more sabotages could not redden their gate for want of data.** The restricted-evidence bound could not fire because this banker holds no note on a restricted prospect, and the evidence-free-candidate filter could not fire because every prospect in the estate carries at least one signal. Both were restated to break the property the gate actually guards. | proof-machinery defect, mine | corrected before close; both recorded |
| `IBO-F-08` | **The weight version in force is resolved as the highest version, not temporally.** `perspective_weight` carries two versions and **no effective date**, so "the vector in force at `as_of`" cannot be resolved from time. This deployment takes the highest version and says so. A later estate carrying effective dates would resolve it temporally with no change to the mechanism. | §B.4 estate limitation | disclosed at the resolution site; `IBO-G06` replays whatever version the snapshot carries, so the gate is unaffected |
| `IBO-F-09` | **The weight version does not reach `policy_bundle_versions`.** It rides on the banker claim inside the hash-bound fabric — which is what makes replay reproduce the historical ranking — but the lineage pin names the policy bundle, not the vector. Gate-0 predicted the correct route is a weight table inside the policy bundle read through a late-bound Control Plane closure; this rung did not take it, because the snapshot route is sufficient for replay and the bundle route was unproven by any rung. | §B.3 backlog | recorded with the alternative named; no SDK change sought |
| `IBO-F-10` | **ACCEPTED ARCHITECTURE DECISION (`D-GATE-cp-18`), not an SDK deficiency.** `CP-SPEC-018` §F.4.2's complexity stop fired. The paved child seam is `Callable[[ChildRequirement, ProductRequest], ChildQuestion]` — one requirement, one question — and the SDK refuses a duplicate `product_class` in `requires` by name (`D-IMPL-336`). Composing CP-17 over the MNPI-bearing subset would require reopening that rule, a fan-out helper, or a hand-rolled resolver. Child count set to **zero**, rung completed on the governed envelope alone, exactly as the ruling authorizes. **One ceiling recorded and not acted on:** the seam can carry **one** child with no new machinery. | accepted architecture decision for this rung | ruled at `D-GATE-cp-18`: **not an SDK deficiency requiring remediation, and no future work.** `IBO-G17` and `IBO-G18` survive the stop and hold the product to *stating* the narrower evidence base. The one technically expressible child is a **ceiling observation only** |
| `IBO-F-11` | The replay environment is hand-assembled in the tests (~95 lines, one private reach). `CP06C-F-01` / `CP17-F-06` / `ATM-F-12`, fourth instance. | §B.3 carried | carried; the tree itself reaches no private symbol |
| `IBO-F-12` | `CP17-F-12`'s scorer semantics apply unchanged: F is a mean over every observation in the view, so four supersede-only classes dilute the one curve class. | §B.2 carried | never re-pinned; no debt figure is asserted as a number |
| `IBO-F-13` | **The estate maps no banker to a perspective.** `banker` carries `desk` and `role`; `ccf_v2.principal` holds CP-17's four principals whose perspectives are none of the three IB ones. Resolved by deployment declaration, the same shape as `ATM-F-03`. | §B.4 estate limitation | declared in `ccf_environment.yaml` and `server/serve.py`; the perspective-to-plan and perspective-to-weights halves are read from the estate |

## 5 · Estate / example limitations (§B.4)

Disclosed where the reader meets them: no SC 13D source (`IBO-F-01`); four of
eleven priced signal types unsupplied (`IBO-F-02`); the type-to-source map is
the deployment's (`IBO-F-03`); the three plans are identical (`IBO-F-05`); the
weight versions carry no effective date (`IBO-F-08`); no banker-to-perspective
row (`IBO-F-13`); every banker covers exactly twenty-five prospects, so the
empty-portfolio state is unreachable from the data and `IBO-G15` constructs it.

## 6 · Product result

At `asked_at = 2026-08-25T00:00:00Z`, banker `BKR014` (Priya Okafor, Treasury
Services) over a portfolio of twenty-five prospects: the M&A originator, the
DCM banker and the sector strategist receive three different orderings of the
same governed signals, at three content addresses, under one class and one
plan id. The divergence prospect sits in the M&A originator's top third and
the DCM banker's bottom half, because a maturity wall is priced at 1.0 for DCM
and 0.05 for M&A. A restricted prospect is ranked with its restriction shown
and without any banker-local evidence. Every ranked row names the signals that
put it there, with weights, ages and evidence.

A ranking served under one weight version replays to its served bytes; the
same record replayed against an inverted vector diverges. A signal type
outside the plan is refused by name; a banker with no coverage is refused; a
banker id nobody issued is indistinguishable from one whose candidates Policy
removed.

**What a consumer can rely on:** the member set of its perspective, fixed for
every banker and every request; every ranked prospect inside the banker's own
portfolio; the weight version that produced the ordering, named on the
product; an explanation for every row. **What it cannot rely on:** activist-
stake, merger-proxy, registration or 13F signal (none reaches the product in
this estate — `IBO-F-02`); the weight version as a lineage pin (`IBO-F-09`);
the freshness factor as a per-class number (`IBO-F-12`); any contribution from
the optional MNPI wall child, which is absent by ruling and says so.

## Sabotage record

Every gate's sabotage and the red it was observed at are in
`artifacts/gates.yaml`. Summary: 18 declared; **17 observed RED** — twelve by a
single reverting edit to the tree with only that gate's test executed, and
five (`IBO-G07`, `IBO-G11`, `IBO-G14`, `IBO-G15`, `IBO-G16`) carrying the
sabotage inside the test. One (`IBO-G01`) is `unavailable`: the four operator
keys were reordered in the configuration and the served order did not move,
because `CATEGORY_ORDER` decides it.

**Three sabotages left their gate green on the first attempt.** One was a fact
about the product worth knowing (`IBO-F-06`: the perspective enters the
ranking at the acquisition seam, not at Π); two were want of data
(`IBO-F-07`). All three were restated to break the property the gate actually
guards, and all three are recorded rather than quietly swapped out — a
sabotage that cannot redden its gate is a defect in the proof machinery, and
this rung found three.
