# Developer Video Source Plan

The videos derive from the approved/release documentation. They do not become a second source of SDK truth.

**Qualified SDK:** `drcastillo/ccf_code/main@ff470d400976815e9a1e49176ca51f97e4e691b1`

## Video 1 — CCF SDK: Consumer vs Producer

**Audience:** application developers, agent developers, data engineers  
**Length target:** 8–10 minutes

Story:
1. CCF in one minute
2. two primary roles
3. Hello World consumer
4. governed Result/refusal
5. producer: completed spec → config/code → product
6. where to go next

Sources:
- `05-reference/01-client-developer/`
- `05-reference/02-context-product-producer/README.md`
- `05-reference/05-technical-reference/SDK_OVERVIEW.md`

Demo:
- HW-1
- canonical CP-03

## Video 2 — Read a Context Product Spec and Trace It to Code

**Audience:** data engineers / Python developers  
**Length target:** 12–15 minutes

Story:
1. open the example README
2. read the completed spec first
3. §A–§G
4. map contract/source/assembly/debt/gates to files
5. run
6. vary
7. validate

Demo:
- CP-00 for smallest full spec
- CP-03 canonical for paved road

## Video 3 — Create a New Context Product with Cowork

**Audience:** SME + data engineer + developer  
**Length target:** 15–20 minutes

Story:
1. start from the decision
2. build evidence packet
3. AI drafts Standard v0.3 spec
4. authority-owned TBCs remain explicit
5. Gate 1
6. AI generates code from the approved spec
7. independent validation
8. Gate 2

Sources:
- `05-reference/04-create-your-own/`

## Video 4 — Prove the Product: Gates, Refusal, Debt

**Audience:** engineers, reviewers, controls  
**Length target:** 12–15 minutes

Story:
1. green is not enough
2. governed refusal vs exception
3. freshness / TTL
4. Context Debt
5. deliberately make a gate RED
6. restore
7. evidence / closeout

Sources:
- `05-reference/05-technical-reference/HALFLIFE_AND_DEBT.md`
- `05-reference/05-technical-reference/CONTEXT_PRODUCTS.md`

Demo:
- CP-05
- canonical CP-03

## Video 5 — Compose and Federate Context Products

**Audience:** advanced developers / architects  
**Length target:** 12–18 minutes

Story:
1. composite is a consumer
2. child requirements/questions
3. child admission/refusal
4. preserve provenance/debt/validity
5. federation / peer

Demo:
- CP-14
- CP-20

## Video 6 — Decision Replay and Assembly Mode 2

**Audience:** developers, controls, architects  
**Length target:** 18–22 minutes

Story:
1. why replay is more than logging
2. five-dimension record
3. record address vs product address
4. DR-01 served reconstruction
5. DR-01 refusal reconstruction
6. `RecordedEnvironment`
7. exact-version/snapshot/content-address holds
8. DR-02: algorithmic product → model packaging → governed claims
9. packaging trace
10. smoothing gate catches unsupported prose
11. model output remains derivative, substrate remains artifact-of-record

Sources:
- `05-reference/03-decision-replay/README.md`
- `05-reference/03-decision-replay/DR01_REPLAY_A_GOVERNED_DETERMINATION.md`
- `05-reference/03-decision-replay/DR02_PACKAGE_A_CONTEXT_PRODUCT.md`
- `05-reference/05-technical-reference/DECISION_REPLAY.md`

Demo:
- DR-01 served and `--refuse`
- DR-02 deterministic packager and smoothing-gate refusal

## Publication rule

Record demos against the same qualified SDK baseline as the written documentation. If the SDK baseline changes, revalidate the commands and visible outputs before publishing the video.
