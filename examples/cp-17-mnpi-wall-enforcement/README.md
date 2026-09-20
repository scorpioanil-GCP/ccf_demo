# MNPI Wall Enforcement — one address, three credentials, three products

`cib.mnpi-wall` @ `1.0.0` · Tier 5 · SQLite (departmental) + PostgreSQL `ccf_v2` + Fluree `fibo-v2` + MongoDB `fibo_v2`, all read-only on the curated `.76` estate; nothing is written but a per-question scratch fabric · specification `spec/CP-SPEC-017_MNPI_Wall_Enforcement.md` (Gate 1 accepted with corrections, 2026-09-20).

**The product a principal receives is bounded by what its verified credential permits — never by a parameter it states — and a relationship the principal may not see does not survive into the view the fabric serves it.** A coverage banker, a research analyst and a trader ask the same question about the same issuer at the same instant through the same door and receive three structurally different Context Products with three content addresses. A fourth real principal with a credential and no grant is refused.

## What this demonstrates

- **Several credentialed principals through ONE standard door** (`MWE-G01`, `MWE-G14`, `MWE-G15`, `MWE-G18`): the SDK's `open_door` with its three typed overrides — a token source holding four credentials read from the environment by name, a perspective resolver that maps a verified `client_id` to the role the estate's principal register declares, and the tenant's three-grant entitlement policy registered after the door's own. The same opened product serves over HTTP, where a caller may *request* a role and is refused rather than downgraded when its grant does not permit it.
- **Entitlement as a formative constraint from the credential** (`MWE-G02`, `MWE-G03`): the bounding sets — which relationship classes and which classifications a principal may receive — come from the principal's own projection-plan row in `ccf_v2.projection_plan`, applied at the acquisition seam from `context.perspective`. The request surface carries no `perspective`, no `corpus_scope`, no `sections`; a request naming one is refused as an undeclared parameter.
- **Restricted relationships do not survive in the governed view** (`MWE-G05`, `MWE-G06`): engagements, notes and positions are reified entities carrying a `classification`; the Policy operator runs first with the class's whole vocabulary and its substitution plus `GQ-16` endpoint closure govern the principal-conditioned view. The claim is about the view, never about physical absence from L3.
- **Policy before Similarity is real** (`MWE-G07`): the SDK's Similarity operator ranks the analyst's published research notes from the view Policy already formed — the first domain rung to run all four operator categories.
- **Wall state on two clocks** (`MWE-G08`): the banker asking at 2026-03-10 gets no MNPI engagement with the control room's knowledge of that day, and gets it with the knowledge of 2026-03-20 — the crossing was valid from 03-07 and recorded on 03-16, an engineered nine-day lag.
- **A Reg FD supersession as a classification-member change** (`MWE-G10`, `MWE-G11`): the issuer's `reg_fd_disclosure` member is null before 2026-07-03 and carries the event after it, for every principal; the event designates no records (ccf-dataprep, 2026-09-20, outcome B), so no engagement content is admitted on the strength of the label.
- **No disclosure, and the A6 property as a load-bearing gate** (`MWE-G04`, `MWE-G16`, `MWE-G19`): the payload's member set is a function of the role and never of the subject; a subject whose admissible claims Policy removes entirely is observationally indistinguishable from a nonexistent subject; no principal's vessel or record carries a wall-decision input it is not entitled to.
- **Supersede-only beside a curve** (`MWE-G12`, `MWE-G20`): five served classes decay `supersede-only` and read freshness 1; the trader's position decays on an illustrative 24-hour half-life; debt is entitlement-neutral.

## Run it

```sh
make venv                                   # once; creates .venv

# READ-ONLY: the curated estate on 192.168.4.76 (v2 namespaces — never the v1 names in ccf_dataprep/.env)
export CCF_CP_17_SQLITE_PATH=/home/parkave/ccf_dataprep/data/departmental.sqlite   # opened mode=ro
export CCF_CP_17_POSTGRES_DSN=...   CCF_CP_17_POSTGRES_SCHEMA=ccf_v2
export CCF_CP_17_FLUREE_URL=...     CCF_CP_17_FLUREE_LEDGER=fibo-v2
export CCF_CP_17_MONGO_URI=...      CCF_CP_17_MONGO_DB=fibo_v2
# the four credentials the door recognizes (any strings; the fourth is granted nothing)
export CCF_CP_17_TOKEN_COVERAGE=... CCF_CP_17_TOKEN_RESEARCH=... CCF_CP_17_TOKEN_TRADER=... CCF_CP_17_TOKEN_KYC=...

make -s example-cp-17                                        # the coverage banker, SP Plus, 2026-08-17 (T1)
make -s example-cp-17 PRINCIPAL=--principal=PRIN-RES-002     # the research analyst: published research only
make -s example-cp-17 PRINCIPAL=--principal=PRIN-TRD-003     # the trader: positions only
make -s example-cp-17 ASKED_AT=--asked-at=2026-03-10T00:00:00+00:00                                              # TW: no MNPI — not yet recorded
make -s example-cp-17 ASKED_AT=--asked-at=2026-03-10T00:00:00+00:00 KNOWN_AS_OF=--known-as-of=2026-03-20T00:00:00+00:00   # TW as known later: MNPI present
make -s example-cp-17 PRINCIPAL=--principal=PRIN-RES-002 ASKED_AT=--asked-at=2026-07-01T00:00:00+00:00          # T0: reg_fd_disclosure null
make -s example-cp-17 PRINCIPAL=--principal=PRIN-KYC-004     # refused: no plan, no grant (exit 1 — correct)
make -s example-cp-17 SUBJECT=--subject=0000000000000000NOPE                       # withheld: an empty view scores D_c 1 (exit 1 — correct)
make -s example-cp-17 SUBJECT=--subject=0000000000000000NOPE DEBT_TOLERANCE=--debt-tolerance=1.0   # served computed-empty

.venv/bin/python examples/cp-17-mnpi-wall-enforcement/run.py --door   # the standard MCP door on a loopback port, four credentials
```

`-s` silences `make`'s own echo so the program's output is what you read. Every request parameter is optional; omitted, the program asks the demonstration question in `artifacts/question.yaml`. The three instants are pinned because the estate is a snapshot; nothing moves `asked_at` to get an answer. A refusal exits non-zero — that is the SDK working, not a crash.

## The story

### 0. One address

Three principals hold three credentials. Over MCP the door resolves the perspective from the verified credential and nothing else; over HTTP a caller may ask for a role, and a role its grant does not permit is refused by typed code, never downgraded. The fourth principal in the estate, the EU KYC analyst, holds a credential and no grant: refused as unconfigured, with the deny audited, and what crosses the wire is the same minimal shell a nonexistent product would get.

### 1. The envelope comes from the credential

Acquisition reads the control room's restricted list first — mandatory for every principal — then the issuer, then the principal's own plan row, then the wall crossings on two clocks and the Reg FD event. The plan's edge vocabulary decides which relationship classes exist in the principal's fabric; the plan's classification envelope bounds the document and MNPI-tagged classes; the walled classification is admitted for an issuer only when a crossing is valid at `asked_at` and had been asserted by `known_as_of`. Only admissible claims are emitted — edges first, attributed nodes last.

### 2. Policy runs first, then the walk

Every reified claim carries a `classification`. The Policy operator runs first with the class's whole vocabulary and removes anything outside it; endpoint closure takes every edge to a removed entity with it. Similarity ranks the research notes that survived; the temporal cut keeps what was valid at the instant; the walk starts from the issuer. The per-principal narrowing is not the walk's: the walk sees only what acquisition put in the per-request fabric.

### 3. Three shapes, one plan

One projection plan branches on the role. The banker's product carries deal engagements and interactions; the analyst's, published research; the trader's, positions. The member set is fixed per role, so an issuer with nothing to show yields empty lists, never an absent member, and never a count of what was withheld.

## Artifact-by-artifact

| file | role |
|---|---|
| `spec/CP-SPEC-017_MNPI_Wall_Enforcement.md` | the specification, written and accepted before this code existed; §G.1 is the acceptance authority for every gate |
| `ccf_config.yaml` | the Control Plane document: product class, the four operators, the request contract (`known_as_of`, `debt_tolerance`), resolution rules, the λ_c table with its illustrative row, the debt profile, the policy bundle, the default perspective, TTL, replay, the door |
| `ccf_environment.yaml` | the NAMES the five sources and the four credentials are read from, and the remedy each raises with when unset; never a value |
| `artifacts/question.yaml` | the demonstration question and the three pinned instants |
| `artifacts/source-vocabulary.yaml` | every table, collection, predicate, classification rule and minted edge name the source legs use |
| `artifacts/perspectives.yaml` | the product's shape per role — which members each role carries, which members the classification envelope bounds |
| `artifacts/gates.yaml` | the declared gates `MWE-G01`–`MWE-G21` with the test that claims each |
| `produce.py` | the paved road: `boot` and `answer`, one `open_product`, no domain vocabulary |
| `deployment.py` | `acquire` (the envelope from the credential, edges first), `assess` (C over the principal's own required classes), `wall_gate` (the declared gate) |
| `acquisition.py` | the source legs — reads only, no `ccf` import |
| `projection.py` | Π: one plan, three role branches; the view-side completeness reader |
| `server/serve.py` | the standard door with its three overrides; the tenant policy registered after it; the HTTP door over the same opened product |
| `run.py` | presentation only — the one module that prints; `--door` serves the MCP door on a loopback port |
| `FINDINGS.md` | the six-section close report, the sabotage record and the DX rubric |

## Whitepaper / CLAUDE.md sections exercised

Whitepaper §6.1 (project-then-retrieve), §6.5 (entitlements determine what the context is allowed to be), §7.3 (the Context Graph and the single writer), §7.4 (the four operator categories, Policy first), §7.5 (Π conditioned by perspective), §7.7 (half-life and Context Debt), §7.8 (the Control Plane as the audit plane), §7.10 (Decision Replay), §8.7.2 (MNPI governance via Policy-before-Similarity). CLAUDE.md §6.4 (the No-Hardcoding Rule — every domain value lives in the two documents and `artifacts/`), §7.1 (MCP as egress), §8.3 (the HTTP front door), §9 (the estate is evidence; tests read it and seed nothing; the illustrative-calibration rule), §10 (single writer). Rulings relied on: `D-IMPL-343` (the paved road), `D-IMPL-323` (illustrative calibration), `D-IMPL-326` (gate acceptance authority), `D-IMPL-242` amendment 1 (computed-empty served with its search), `D-IMPL-253` Q27 (unauthorized equals nonexistent at the boundary), `D-IMPL-334`/`D-IMPL-335` (invalidation boundaries), Dave's CP-17 rulings of 2026-09-20 in `docs/DECISIONS.md`.

## What to change first

**The two documents, and the two artifacts beside them.** `ccf_config.yaml` declares the class, the four operators, the request contract, the λ_c rows and the door identity; `ccf_environment.yaml` names where the stores and the credentials are read from. `artifacts/source-vocabulary.yaml` is how a different estate's tables, predicates and classification rules are bound; `artifacts/perspectives.yaml` is how a different set of roles gets its shape. The Python is the interpreter of those documents: `acquisition.py` for your own systems of record, `deployment.py` for your own claim builders, `projection.py` for your own payload — none of them should need a domain value that is not already in a document.

**Illustrative calibration:** This example runs against a point-in-time demonstration estate rather than continuously refreshed production data. Freshness half-lives and related thresholds are calibrated to make the governed behavior observable in that snapshot. They demonstrate how the SDK applies these controls and should not be interpreted as recommended production coverage-policy thresholds. The `position` half-life of 86,400 s (the vault's ~1 hour is unobservable on a date-grained `as_of`), the Similarity query and floor, the tolerance default and the debt profile are the values to revisit first for your own data.

## What would fail

Serve the banker's view to the research credential (`MWE-G01`, `MWE-G02`); mint an edge outside the principal's plan vocabulary (`MWE-G03`); add a member because data exists or drop one because it does not (`MWE-G04`); reorder the operators so Similarity ranks before Policy (`MWE-G05`, `MWE-G07`); inject a claim outside the classification vocabulary and let it reach the product (`MWE-G06`); admit an MNPI engagement before the control room recorded the crossing (`MWE-G08`); skip the restricted list or serve when it is unreachable (`MWE-G09`); infer disclosed content from the Reg FD label (`MWE-G10`); serve a determination whose snapshot precedes a recorded boundary (`MWE-G11`); give a supersede-only class a curve or the position class no clock (`MWE-G12`); mint a plan per role (`MWE-G13`); serve the ungranted credential, or tell it more than a nonexistent product would (`MWE-G14`); downgrade a requested role instead of refusing it (`MWE-G15`); refuse a nonexistent subject while serving an emptied one (`MWE-G16`); re-derive a debt factor in replay (`MWE-G17`); let two runs or the two doors disagree (`MWE-G18`); write a crossing id, a restriction row or another principal's plan into a vessel or record (`MWE-G19`); raise the analyst's debt for the MNPI it may not see (`MWE-G20`); make the wall a display filter (`MWE-G21`).
