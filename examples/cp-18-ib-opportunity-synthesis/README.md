# IB Opportunity Synthesis — the perspective is a dimension of the product

`cib.opportunity-synthesis` @ `1.0.0` · Tier 5 · SQLite (departmental) + PostgreSQL `ccf_v2` + Fluree `fibo-v2` + MongoDB `fibo_v2`, all read-only on the curated `.76` estate; nothing is written but a per-question scratch fabric · specification `spec/CP-SPEC-018_IB_Opportunity_Synthesis.md`.

**The only product on this ladder anchored on the consumer rather than on the subject.** A banker asks what to work on this week. The coverage portfolio decides which prospects are candidates, and the verified perspective decides what the ranking optimizes for — so three bankers receive three different orderings of the same governed signals, not three sorts of one list. The weight vector that produced an ordering is pinned inside the fabric, so a ranking entered months ago replays under the weights that were in force then.

## What this demonstrates

- **Π as a dimension of the product** (`IBO-G02`, `IBO-G03`, `IBO-G04`): one banker, one instant, three perspectives, three content addresses. The three projection plans in the estate permit *identical* signal types, so the plan is not the discriminator — the weight vector is. A maturity wall is priced at 1.0 for the DCM banker and 0.05 for the M&A originator, and that is why one prospect sits in one perspective's top third and the other's bottom half from the same evidence.
- **A pinned, policy-versioned weight vector** (`IBO-G05`, `IBO-G06`, `IBO-G07`): the version is resolved at the decision instant and never stated by the caller, because a banker choosing which vector ranks its own book could choose the one that flatters it. The vector rides inside the hash-bound fabric, so replay reproduces the historical ranking after the Control Plane has moved on — and a replay against a different vector diverges rather than quietly agreeing.
- **Restriction as classification, not deletion** (`IBO-G08`): a restricted prospect remains a candidate and is ranked with its restriction disclosed. What the restriction bounds is the evidence admitted for it — no banker-local note contributes to a restricted prospect's score, because a private note may encode exactly what the restriction exists to contain.
- **The banker's own notebook, reaching the ranking** (`IBO-G10`, `IBO-G11`): the departmental notes of the asking banker and no other's, and removing them observably moves a ranked row.
- **Optional context that stays optional** (`IBO-G17`, `IBO-G18`): the CP-17 wall child is absent by ruling, recorded as named debt rather than as a refusal, and every ranked row states that it rests on the narrower evidence base rather than leaving a consumer to assume otherwise.
- **A ranking that can justify itself** (`IBO-G13`): every row carries the signals that put it there with their weights, ages and evidence. The arithmetic is the explanation.
- **Refusals that are answers** (`IBO-G14`, `IBO-G15`, `IBO-G16`): a signal type outside the plan is refused by name rather than silently dropped; a banker with no coverage is refused rather than served an empty list; a banker id that was never issued is indistinguishable from one whose candidates Policy removed.

## Run it

```sh
make venv                                   # once; creates .venv

# READ-ONLY: the curated estate on 192.168.4.76 (v2 namespaces — never the v1 names in ccf_dataprep/.env)
export CCF_CP_18_SQLITE_PATH=/home/parkave/ccf_dataprep/data/departmental.sqlite   # opened mode=ro
export CCF_CP_18_POSTGRES_DSN=...   CCF_CP_18_POSTGRES_SCHEMA=ccf_v2
export CCF_CP_18_FLUREE_URL=...     CCF_CP_18_FLUREE_LEDGER=fibo-v2
export CCF_CP_18_MONGO_URI=...      CCF_CP_18_MONGO_DB=fibo_v2
# the four credentials the door recognizes (any strings; the fourth is granted nothing)
export CCF_CP_18_TOKEN_MA=...       CCF_CP_18_TOKEN_DCM=... CCF_CP_18_TOKEN_SECTOR=... CCF_CP_18_TOKEN_UNGRANTED=...

make -s example-cp-18                                        # the M&A originator's book
make -s example-cp-18 BANKER=--banker=BKR006                 # the DCM banker: a different ordering of the same signals
make -s example-cp-18 BANKER=--banker=BKR027                 # the sector strategist
make -s example-cp-18 LIMIT=--limit=5                        # fewer rows; the caller can only ask for less
make -s example-cp-18 SIGNAL_TYPES=--signal-types=ma_event_8k             # narrowing inside the plan
make -s example-cp-18 SIGNAL_TYPES=--signal-types=not_a_signal_type       # refused by name (exit 1 — correct)
make -s example-cp-18 BANKER=--banker=BKR999                 # refused: a credential with no grant (exit 1 — correct)
make -s example-cp-18 BANKER=--banker=BKR998                 # withheld: a banker id nobody issued (exit 1 — correct)

.venv/bin/python examples/cp-18-ib-opportunity-synthesis/run.py --door   # the standard MCP door, four credentials
```

`-s` silences `make`'s own echo so the program's output is what you read. Every request parameter is optional; omitted, the program asks the demonstration question in `artifacts/question.yaml`. A refusal exits non-zero — that is the SDK working, not a crash.

## The story

### 0. The candidate universe is the consumer's

Acquisition reads the banker and the coverage portfolio first. There is no principal-independent version of this product to filter: the portfolio decides the candidates and the perspective decides the ranking function, which is what makes Π a dimension of the product rather than of the presentation layer.

A banker who covers nothing is refused by name. An empty ranking would read as *"nothing worth working on this week"* — a different answer, and a false one.

### 1. The restricted state classifies; it does not delete

The departmental read comes next. A restricted prospect stays in the candidate universe and is ranked with its restriction shown, because the banker needs to know not to act on it. What the restriction bounds is the evidence: the banker's private notes do not contribute to a restricted prospect's score.

### 2. The weight vector is resolved, not requested

The version in force is read from the estate at the decision instant and written onto the banker claim, inside the hash-bound fabric. The caller cannot name a version, and replay does not resolve one — it reads the one the snapshot carries.

### 3. Policy first, then the rest, then the arithmetic

Every claim carries a classification; Policy runs first and removes anything outside the product's vocabulary, taking edges to removed entities with it. Similarity ranks the filing passages that survived; the temporal cut keeps what was valid at the instant; the walk starts from the banker. Then Π scores each candidate: each admitted signal contributes its weight decayed by its own half-life, summed, ordered, truncated. No inference, no LLM — the ranking is arithmetic over a policy-versioned vector, which is what makes it replayable and defensible.

**A standing state and a dated event are different observation types.** A maturity wall is true *as of now* and has no event date; an 8-K happened on a day. They live in different classes with different decay, and the SDK's refusal of an undated claim in a `valid-from` class is what taught that distinction here.

## Artifact-by-artifact

| file | role |
|---|---|
| `spec/CP-SPEC-018_IB_Opportunity_Synthesis.md` | the specification, written and ruled before this code existed; §G.1 is the acceptance authority for every gate, and §F.4 carries the composition ruling |
| `ccf_config.yaml` | the Control Plane document: product class, the four operators, the request contract, resolution rules, the λ_c table, the debt profile, the policy bundle, TTL, replay, the door |
| `ccf_environment.yaml` | the NAMES the four sources and four credentials are read from, and the remedy each raises with when unset; never a value |
| `artifacts/question.yaml` | the demonstration question, the pinned instants, the divergence prospect |
| `artifacts/perspectives.yaml` | the product's declared shape per perspective, and the classification vocabulary the gate holds it to |
| `artifacts/source-vocabulary.yaml` | every table, collection and field this deployment reads — including the **type-to-source map**, which is this deployment's because no table stores a signal under the eleven declared names |
| `artifacts/gates.yaml` | the eighteen declared gates with their sabotages and the red each was observed at |
| `acquisition.py` | the estate half: four readers, the envelope computed in one order, dated claims out |
| `deployment.py` | the deployment half: claims as envelopes, the debt assessment, the declared gate |
| `projection.py` | Π: one plan, three perspective branches, and the ranking arithmetic |
| `produce.py` | the paved producer road — two marker regions and nothing domain-specific |
| `server/serve.py` | the standard door with its three typed overrides, and the HTTP door over the same opened product |
| `run.py` | presentation only; the one module that writes to a terminal |
| `FINDINGS.md` | what this rung measured about the SDK, classified under `docs/EXAMPLE-EVALUATION-CRITERIA.md` |

## What to change first to adapt it

Replace `artifacts/source-vocabulary.yaml` with your own estate's names and its type-to-source map, and `artifacts/perspectives.yaml` with your own audience shapes. Rewrite the readers in `acquisition.py` against your stores and the scoring rule in `projection.py` against your domain. `produce.py` names no domain value and does not change. The seam that derives the envelope from the verified credential is documented at `public/how-to/condition-acquisition-on-the-verified-credential.md`, and this tree was written against that page rather than against another example's source.

## Illustrative calibration

This example runs against a point-in-time demonstration estate rather than continuously refreshed production data. Freshness half-lives and related thresholds are calibrated to make the governed behavior observable in that snapshot. They demonstrate how the SDK applies these controls and should not be interpreted as recommended production coverage-policy thresholds.

Two values here are demonstration values, each labeled where it is declared. The fabric's `signal` half-life is the median of the estate's eleven declared per-type half-lives, so the fabric-level freshness term still discriminates at the pinned instant; the per-type half-lives the *ranking* uses are the estate's own and are not calibrated. The Similarity floor over the filing corpus is chosen by the same measured rule rung 19 recorded. The observations, the decay curve and the decision instant stay the SDK's and the estate's.
