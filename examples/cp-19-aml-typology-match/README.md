# AML Typology Match — the posture at the instant decides what may be proposed

`compliance.aml-typology` @ `1.0.0` · Tier 5 · SQLite (departmental) + PostgreSQL `ccf_v2` + Fluree `fibo-v2` + MongoDB `fibo_v2`, all read-only on the curated `.76` estate; nothing is written but a per-question scratch fabric · specification `spec/CP-SPEC-019_AML_Typology_Match.md`.

**The set of dispositions an analyst may propose is computed from the filing posture in force at the instant asked, before any candidate exists — and the existence of a Suspicious Activity Report is itself restricted, so one perspective is told nothing about a filing that another perspective reads in full.** An L1 analyst, an L2 reviewer and a regulatory examiner ask about the same alert at the same instant and receive three structurally different Context Products. The same alert asked at two instants across a posture boundary yields two different permitted sets.

## What this demonstrates

- **A bound computed before the thing it bounds** (`ATM-G03`, `ATM-G04`): the permitted disposition set is read from the posture and its rules at the acquisition seam, and the candidate list is *generated from that set*. A disposition the posture forbids is never constructed, and one injected anyway refuses the whole product by name rather than being quietly filtered.
- **The posture at `as_of`, not the posture now** (`ATM-G05`, `ATM-G06`): an examiner reviewing a disposition entered months ago evaluates it against the posture in force then. One alert at two instants gives two permitted sets, and the product names which posture governed.
- **Restricted existence, not merely restricted content** (`ATM-G09`, `ATM-G10`): `sar_filing_history` is not an empty member of the L1 analyst's product — it is not a member of it at all, and no byte of the vessel names the filing. A `restricted` SAR reaches the L2 reviewer and the examiner; a `confidential` one reaches the examiner alone.
- **The shape is the perspective's, never the alert's** (`ATM-G07`, `ATM-G08`): the member set is fixed per perspective, so an alert with nothing to show yields an empty member and never an absent one — which is what makes an empty member uninformative about the alert.
- **All four operator categories, Policy first** (`ATM-G01`, `ATM-G02`): Policy runs before Similarity, and the order is read off the *served* product rather than off the configuration. Reordering the configuration does not move it.
- **Residency as a formative constraint** (`ATM-G11`): a constrained resident's detail is admitted only under the declared entitlement, and no perspective in this deployment holds it — 60 of the 200 parties in the demonstration alert's network are removed before anything ranks or walks.
- **Every claim anchored** (`ATM-G12`): each typology match the examiner reads is anchored to an advisory passage carrying its document and advisory number.
- **Replay, and the existence oracle closed** (`ATM-G13`, `ATM-G14`): each adjudication rebuilds byte for byte from its own record with the posture that governed; an alert whose admissible content Policy removes entirely is indistinguishable from an alert id that was never issued.
- **Four credentials, one door** (no declared gate; see `ATM-F-14`): three grants receive three perspectives and three content addresses through the standard MCP door, and the fourth is refused with the minimal shell. Over HTTP a caller may request a perspective, and one outside its grant is refused rather than downgraded.

## Run it

```sh
make venv                                   # once; creates .venv

# READ-ONLY: the curated estate on 192.168.4.76 (v2 namespaces — never the v1 names in ccf_dataprep/.env)
export CCF_CP_19_SQLITE_PATH=/home/parkave/ccf_dataprep/data/departmental.sqlite   # opened mode=ro
export CCF_CP_19_POSTGRES_DSN=...   CCF_CP_19_POSTGRES_SCHEMA=ccf_v2
export CCF_CP_19_FLUREE_URL=...     CCF_CP_19_FLUREE_LEDGER=fibo-v2
export CCF_CP_19_MONGO_URI=...      CCF_CP_19_MONGO_DB=fibo_v2
# the four credentials the door recognizes (any strings; the fourth is granted nothing)
export CCF_CP_19_TOKEN_L1=...       CCF_CP_19_TOKEN_L2=... CCF_CP_19_TOKEN_EXAMINER=... CCF_CP_19_TOKEN_UNGRANTED=...

make -s example-cp-19                                                   # the L1 analyst, ALT-000021, posture at the decision instant
make -s example-cp-19 PRINCIPAL=--principal=PRIN-AML-L2                 # the L2 reviewer: the network, the lineage, the SAR
make -s example-cp-19 PRINCIPAL=--principal=PRIN-AML-EXAM               # the examiner: the full chain with attribution
make -s example-cp-19 AS_OF=--as-of=2025-06-01T00:00:00+00:00           # the earlier posture: a different permitted set
make -s example-cp-19 AS_OF=--as-of=2026-02-01T00:00:00+00:00           # the later posture
make -s example-cp-19 AS_OF=--as-of=2025-01-01T00:00:00+00:00           # before any posture: nothing permitted, no candidate
make -s example-cp-19 PRINCIPAL=--principal=PRIN-AML-XXX                # refused: a credential with no grant (exit 1 — correct)
make -s example-cp-19 SUBJECT=--subject=ALT-999999                      # withheld: an empty view scores D_c 1 (exit 1 — correct)
make -s example-cp-19 SUBJECT=--subject=ALT-999999 DEBT_TOLERANCE=--debt-tolerance=1.0   # served computed-empty

.venv/bin/python examples/cp-19-aml-typology-match/run.py --door   # the standard MCP door on a loopback port, four credentials
```

`-s` silences `make`'s own echo so the program's output is what you read. Every request parameter is optional; omitted, the program asks the demonstration question in `artifacts/question.yaml`. The instants are pinned because the estate is a snapshot; nothing moves `asked_at` to get an answer. A refusal exits non-zero — that is the SDK working, not a crash.

## The story

### 0. The envelope is read before the fabric exists

Acquisition reads the departmental store *first*, before any enterprise source is opened. Which SARs this perspective may know exist is not a filter applied to an assembled product; it is the bound that decides what is assembled. A SAR the perspective may not know about is never minted as a claim, so nothing downstream can serve it by mistake.

Then the perspective's own projection plan, then the posture effective at `as_of` and the disposition rules that posture carries, then the alert and its network, then the advisory passages. Only admissible claims are emitted — edges first, attributed nodes last.

### 1. The bound comes before the candidates

The permitted disposition set is computed from the posture and the subject's matched typologies before any candidate exists, and it rides on the alert claim because the asking perspective is entitled to know what it may propose. The rule *set* that produced it does not ride along: it is an envelope input, consumed at the seam. Π then builds the candidate list by iterating the permitted set. Containment is by construction, and the declared gate is the proof that the construction held.

### 2. Policy runs first, then the rest

Every served thing is a reified entity carrying a `classification`, reached from the alert by a typed edge. The Policy operator runs first with the class's whole vocabulary and removes anything outside it, taking every edge to a removed entity with it. Similarity ranks the advisory passages that survived; the temporal cut keeps what was valid at the instant; the walk starts from the alert. The per-perspective narrowing is not the walk's — the walk sees only what acquisition put in the per-request fabric.

### 3. Three shapes, one plan

One projection plan branches on the perspective. The L1 analyst's product carries typology matches, disposition candidates and sanctions screening; the L2 reviewer's carries the counterparty network, the ownership chain, the prior-alert lineage and the SAR history; the examiner's carries all of it plus policy-version attribution and the reasoning trail. The member set is fixed per perspective, so the shape carries no information about the alert.

## Artifact-by-artifact

| file | role |
|---|---|
| `spec/CP-SPEC-019_AML_Typology_Match.md` | the specification, written before this code existed; §G.1 is the acceptance authority for every gate |
| `ccf_config.yaml` | the Control Plane document: product class, the four operators, the request contract (`as_of`, `network_depth`, `debt_tolerance`), resolution rules, the λ_c table with its illustrative row, the debt profile, the policy bundle, the default perspective, TTL, replay, the door |
| `ccf_environment.yaml` | the NAMES the four sources and the four credentials are read from, and the remedy each raises with when unset; never a value |
| `artifacts/question.yaml` | the demonstration question, the pinned instants, the comparator alerts |
| `artifacts/perspectives.yaml` | the product's declared shape per perspective, its SAR visibility, and the classification vocabulary the declared gate holds it to |
| `artifacts/source-vocabulary.yaml` | every table, predicate, collection and field name this deployment reads, and the classification each class is assigned |
| `artifacts/gates.yaml` | the fourteen declared gates, each with its statement, executing test, sabotage and the red it was observed at |
| `acquisition.py` | the estate half: four readers, the envelope computed in one order, dated claims out |
| `deployment.py` | the deployment half: claims as envelopes, the debt assessment, the declared gate |
| `projection.py` | Π: one plan, three perspective branches, the candidate list built from the permitted set |
| `produce.py` | the paved producer road — two marker regions and nothing domain-specific |
| `server/serve.py` | the standard door with its three typed overrides, and the HTTP door over the same opened product |
| `run.py` | presentation only; the one module that writes to a terminal |
| `FINDINGS.md` | what this rung measured about the SDK, classified under `docs/EXAMPLE-EVALUATION-CRITERIA.md`, including the mandatory A2 third-instance measurement |

## Whitepaper / CLAUDE.md sections exercised

| section | how |
|---|---|
| Whitepaper §7.4(c) — **policy-before-similarity** | the four-operator composition, served as an operator-plan fact rather than asserted in prose |
| Whitepaper §7.5 — Projection | three perspectives differing in what is ASSEMBLED, not merely in what is shown |
| Whitepaper §7.6 — Context Product Contract | `extra=forbid`; a filing posture in force at a past `as_of` |
| Whitepaper §7.7 — half-life and Context Debt | supersede-only classes, and what that does to the freshness mean (`ATM-F-04`) |
| Whitepaper §7.10 — Decision Replay | the posture, the bound and the plan all reconstructible from the record |
| CLAUDE.md §6.4 — No-Hardcoding | the typology vocabulary and the posture windows are artifacts and estate data |
| CLAUDE.md §7.1/§7.3 — MCP egress | the standard door, four credentials, the fourth granted nothing |
| CLAUDE.md §9 — estate discipline | reads `.76` only; seeds nothing; asserts relationships, never estate counts |

## What to change first

Replace `artifacts/source-vocabulary.yaml` with your own estate's names and `artifacts/perspectives.yaml` with your own audience shapes; rewrite the readers in `acquisition.py` against your stores. `produce.py` names no domain value and does not change. The declared gate in `deployment.py` is where a product-specific invariant goes — a containment rule, a shape rule, a visibility rule — and the SDK runs it after its own universal gates and before the tolerance check.

### Illustrative calibration

This example runs against a point-in-time demonstration estate rather than continuously refreshed production data. Freshness half-lives and related thresholds are calibrated to make the governed behavior observable in that snapshot. They demonstrate how the SDK applies these controls and should not be interpreted as recommended production coverage-policy thresholds.

Two values here are demonstration values, each labeled where it is declared and each chosen from a measurement rather than a preference:

- the `transaction` half-life of 86,400 seconds, because value dates in the estate are date-grained and an hourly curve reads the same for every alert at any 2026 instant;
- the Similarity floor of 1 percent, because the reference index scores integer token overlap between a seven-token query and passages of about ninety unique tokens, and the whole seventy-two-passage corpus therefore scores in a four-value band. `ccf_config.yaml` carries the measured distribution and the reason 1 is the smallest floor at which the operator still discriminates.

The observations, the decay curve and the decision instant stay the SDK's and the estate's. Only the declared thresholds are demonstration values.

## What would fail

**Similarity running before Policy.** The whole rung is §7.4(c): the permitted
set is computed first and the ranking happens inside it. An implementation that
ranked first and filtered after would serve the same rows and a different
guarantee — which is why the gate reads the EXECUTED plan from replay
dimension 5 rather than `operators_invoked`, an unordered `frozenset`.

**An L1 analyst learning that a SAR exists.** The silence is doubly enforced
and **either guard alone suffices** — breaking the departmental audience filter
is not enough to leak it (`ATM-F-08`). That is recorded as a measured property
of the rung, not as redundancy to trim.

**Fourteen declared gates**, each claimed by an executing test. `ATM-G08`'s
first sabotage could not redden it — making a member conditional on the alert
did not mutate the claim the gate asserts — and was corrected rather than
swapped (`ATM-F-07`).

### What this rung does NOT prove

The vector path. **0 of 72 advisory passages carry an embedding or a
`sha256`**, so ranking uses the SDK's lexical operator and anchoring uses the
passage id (`ATM-F-01`). The reference index's usable score band also collapses
for a short query over long passages (`ATM-F-05`). No alert's subject party has
a sanctions-screening row anywhere in the estate (`ATM-F-06`), and jurisdiction
is spelled three different ways across three sources (`ATM-F-02`).
