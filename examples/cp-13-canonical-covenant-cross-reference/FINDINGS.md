# Findings — cp-13-canonical

Findings raised while building the canonical rung-13 successor on the paved producer
road (`CP-SPEC-013C`, written and committed before its implementation under the CP-14
completion GO of 2026-09-17). Classified under `docs/EXAMPLE-EVALUATION-CRITERIA.md` §B
before any repair; each says whether the behavior is legitimate SDK semantics or a
mismatch, with the basis stated. Findings are raised, not resolved: every one below is
Dave's to rule on. The close-report sections follow §K.

## 1 · SDK capability proven

| §D item | how this tree exercised it |
|---|---|
| define / assemble | two documents, four callables, two regions; both operators, Π, the three L6 gates, the declared lineage obligations and the product's own gate run on the road |
| preserve product identity | **the lane, measured** (`CXRC-G14`): the four demonstration sources at the specimen's instant hash to the specimen's payload `5e87490c…`, zero field-level differences, the debt assessment equal member for member including its three scorer pins → `1.0.0` |
| calculate Context Debt correctly | the SDK's assembly scorer over the governed view: `F` by the reference freshness scorer over the view's observations with the booted λ_c table, `C` and `S` declared to it off the admitted anchors' own chains (`CXRC-G15`); equal to the specimen's to the last digit |
| refuse correctly | a tolerance below the measured debt withholds with the debt block (`G11`); an unknown intent refuses on the declared set (`G21`); a question admitting no evidence node refuses on the declared lineage obligation (`G23`); wrong producer id and wrong tenant refuse independently at the consumer (`G19`); the walk's own two exceptions propagate exactly as the specimen raises them (`G04`, `G07`) |
| replay and reconstruct | `replay()` reproduces the served bytes from the recorded snapshot and the dimension-2 effective request with no acquisition object alive, and the debt reading over the replayed view re-derives both declared factors; the tolerance refusal reconstructs through `replay_refusal()` with no product rehydrated (`D-IMPL-344`, `G25`) |
| local and remote boundaries | the CP-14-shaped question through the standard door in another process, admitted `provider-controls` (`G18`); the door and the in-process run serve one address (`G20`) |
| identity confusion prevented | the expected producer identity and tenant come from the registration (`G19`); the door serves every caller as the declared credit officer and no request parameter names a principal (`G22`) |

## 2 · SDK friction observed (§E)

Measured with the counter `docs/PAVED-ROAD-LOC-REPORT.md` uses (physical lines / code
lines excluding comments and docstrings); "relocated" means the work now happens in the
SDK or a document, not that it vanished.

| measure | specimen (low road) | successor (paved) |
|---|---|---|
| plumbing (`produce.py` + `server/serve.py`), physical / code | 152 / 88 (no door at all) | **170 / 61** (103 / 34 + 67 / 27) — and a door exists |
| domain (`deployment` / `acquisition` / `projection`), code | 897 (265 / 451 / 181) | 836 (198 / 439 / 199) |
| `run.py`, code | 130 | 110 (a `--door` flag; presentation only) |
| documents, physical / non-comment | 2 documents, 256 / 167 | 2 documents, 320 / 201 |
| distinct `ccf.` names imported | 19 | 20 |
| duplicated authorities | the perspective, the TTL and the plan-id prefix stated in code and in documents; the estate names read straight off `os.environ` | 0 measured — the perspective, the TTL, the door identity, the discovery set and the class lane are each stated once, and the sources are named in one document |

**Relocated, not eliminated:** the effective-request derivation, the ingest loop with
its order assertion, the resolver's fourteen keyword arguments and the record readback
moved into the SDK; `backends.yaml` became `ccf_environment.yaml`. Documents grew by
34 non-comment lines: `discovery:`, `replay:`, `ttl:` and `door:` are declarations the
specimen kept in code or did not make.

**Friction named, none worked around:**

| id | finding | class | disposition |
|---|---|---|---|
| `CP13C-F-01` | **The road hands Π the effective request and nothing from the side — and the honest shape was fabric state, again.** The specimen's Π and both measured debt factors closed over the whole acquisition result; the road offers no seam for that. Carrying each anchor's chain, the envelope and the governing register as claims on the anchor node (`source_json`, `envelope_json`, `governing_json`) made the evidence replayable from the snapshot AND made a source the caller may not read count for nothing in the debt. Recorded as the measurement `CP06C-F-02` asked for a second time: for this document-backed product it is the correct shape, not friction | not a finding against the SDK | the ruling stands; second data point |
| `CP13C-F-02` | **A replay environment for a paved product is still assembled by hand** — the same ~40 lines `CP06C-F-01` recorded (`_FreshEnvironment` in this tree's tests is the third copy) | 3 · post-launch enhancement | recorded under `CP06C-F-01`'s backlog item; the third copy is the case for generalization the item named |
| `CP13C-F-03` | **The specimen's two walk exceptions propagate through `opened.answer`** — `UnknownCovenantSource` and `ScopeNotEntitled` are raised by the acquisition and the road re-raises them, exactly as the specimen did (`CXRC-G04`, `G07`). Through the standard door they reach a consumer as an opaque `ccf-runtime-failure` rather than a governed refusal (`D-IMPL-304`, the pre-resolution carry; `CP14-F-21`). Preserved as the specimen's contract under the GO's "preserve … entitlement behavior"; converting them into governed refusals is a business-meaning change that needs a ruling | 4 · frozen-contract limitation, disclosed | not changed |
| `CP13C-F-05` | **Close-review repairs (2026-09-17).** (a) Π took the declared seed from a module constant through the plan factory while the anchor carried it as a claim; Π now reads `seeded_on`, the envelope and the governing register off the admitted anchors and refuses a view whose anchors disagree on any of them rather than picking a winner by sort order. (b) `C` over an empty admitted view read 1 (the specimen's estate-side figure); it now reads 0 — nothing admitted is a coverage shortfall — and reaches only the refusal's record. Payload unchanged on every served question (the lane measurement still holds) | repaired in the candidate | recorded |
| `CP13C-F-04` | **A fabricated citation cannot be served at all.** Sabotage S02 (a citation invented for a point anchor) did not turn `CXRC-G02` red in isolation: the tree refused to serve any question, so every served-fixture test errored. The product's own gate and the contract refuse the fabrication before a gate could observe it — the right behavior, and a sabotage that cannot isolate its gate | not a finding | recorded on the roster as `observed_red: null` with the reason |

## 3 · Launch blockers

None raised by this tree. `ttl_anchor: from_decision` is the specimen's own, so `D-IMPL-341`
has no subject here; `D-IMPL-342` is a consumer-side carry.

## 4 · Backlog candidates (§I)

No new item. `CP13C-F-02` adds the third copy to `CP06C-F-01`'s reference-replay-environment
item.

## 5 · Estate / example limitations

Inherited from the specimen unchanged: 48 of 49 covenant definitions carry offsets and no
hash (`span-unverifiable`); 158 defined terms are point anchors; `ex:governedBy` is asserted
nowhere; 18 of 40 memoranda carry no embedding; the `filed` scope permits no memorandum, so
the credit officer's retrieval examines zero candidates. The entitlement register keys on
three role names, which is why the perspective's role is the principal.

## 6 · Product result

At `2026-09-13T00:00:00+00:00`, principal `credit-officer`, scope `filed`, depth 3, the four
demonstration sources: 21 chain nodes, **4 checked citations**, 17 explained absences (13
point anchors, 4 unverifiable spans), 36 documents in force, `D_c` 0.8095 `forced_llm`
(`F` 1, `C` 0.1905, `S` 1). The control room under `filed-and-internal` is served a different
address with 22 candidates examined and 18 memoranda `not-evaluable`. For CP-14: BGC Group's
facility document carries two evidence anchors (`INTEREST_COVERAGE`, `LEVERAGE`); the
CP-14-shaped question is admitted through the door at the diagnostic tolerance, and at the
governed 0.25 this producer WITHHOLDS (measured debt 0.81), which the memo must report
rather than tune around. A consumer can rely on: every served citation re-hashed, the
reason for every absence, the retrieval bound stated. A consumer cannot rely on: a
citation for a covenant definition (none is checkable on this estate).

## Sabotage record

Run by hand on the candidate after the build, restored by copy and verified with `diff -r`
before the next; nine mutations, one suite run each (26 tests).

| sabotage | applied to | red | green |
|---|---|---|---|
| S02 — a citation fabricated for a point anchor | `projection.py` | every served fixture ERRORED (the tree will not serve the fabrication); `G19`, `G25` failed on the same | 7 estate-free tests — `G02` not isolated (`CP13C-F-04`) |
| S06 — `seeded_on` dropped from the payload | `projection.py` | `CXRC-G06`; `G14` (the payload moved) | the other 24 |
| S09 — `governedBy` reported present | `projection.py` | `CXRC-G09`; `G14` | the other 24 |
| S13 — a `door.yaml` naming a script path added | `server/` | `CXRC-G13` alone | the other 25 |
| S15 — `C` read off a constant, not the view | `deployment.py` | `CXRC-G15` alone (the constant equals today's measurement, so `G14` and `G25` stay green — which is why `G15` moves the view) | the other 25 |
| S17 — one specimen file edited | the specimen's README | `CXRC-G17` alone | the other 25 |
| S21 — the discovery set removed (the specimen's shape) | `ccf_config.yaml` | `CXRC-G21` alone | the other 25 |
| S22 — the principal read off a request parameter | `deployment.py` | `CXRC-G22`; `G03`, `G04` (every role became the credit officer) | the other 23 |
| S23 — the lineage obligations removed | `ccf_config.yaml` | `CXRC-G23` alone (the product's own gate then refuses the empty view, on a different reason) | the other 25 |

Restored tree after the sweep: 26 passed; the specimen diff-empty. Not individually
sabotaged: `G01`, `G03`, `G04`, `G05`, `G07`, `G08`, `G10`, `G11`, `G12`, `G14`, `G16`,
`G18`, `G19`, `G20`, `G24`, `G25` — each asserted, its described sabotage recorded on the
roster with `observed_red: null`.
