# KYC Refresh / Beneficial Ownership — a finding is not an absence

`compliance.beneficial-ownership` @ `1.0.0` · Tier 4 · PostgreSQL `ccf_v2` + MongoDB `fibo_v2` + Fluree `fibo-v2`, all read-only on the curated `.76` estate; nothing is written but a per-question scratch fabric · specification `spec/CP-SPEC-015_KYC_Refresh_Beneficial_Ownership.md`.

**Who are the natural persons behind this entity — and what do you do with the ones you are not sure about?** Ownership walked to person level across jurisdictions, with a resolution confidence carried per person, and the findings that fall below a reporting threshold or below a confidence floor kept **inside** the product and handed to the SDK's review queue rather than dropped out of it.

**This is the first example on the ladder to compose a HITL primitive with a Context Product.** What makes it a coverage probe rather than a feature is the boundary: the product is complete, governed, assessed and immutable *before* anything is referred, and the review queue consumes its references and can never reach back into it.

## What this demonstrates

- **A finding is not an absence** (`UBO-G08`): a person below the reporting threshold and a resolution below the confidence floor both stay in the product, named. Raising the confidence floor turns resolutions *into* findings; it does not remove them.
- **A governed product handed to a HITL queue** (`UBO-G09`, `UBO-G10`): each finding is referred with the originating **replay-record** reference as its workflow state and the product's **content address** as its output reference. Not the address for both: identical product bytes can participate in different governed determinations, so an address alone cannot say which one referred the finding.
- **The construction boundary, gated** (`UBO-G20`): assembling with the review queue never opened produces byte-identical output, and the construction modules import no HITL symbol at all — checked against the import graph, because every one of them explains in prose that it does not.
- **The product is immutable and the verdict is its own record** (`UBO-G11`, `UBO-G12`, `UBO-G13`): the product's record carries the no-HITL-actions sentinel by construction, a human release leaves the product and its record byte-unchanged, the verdict lands on a second record linked by the originating reference and the output reference, and a reviewer echoing the wrong hash is refused.
- **Residency as a formative constraint** (`UBO-G02`, `UBO-G03`): a person record outside the principal's entitlement is never materialized, and no member, count or marker says how many were withheld — a count of what was withheld is itself disclosure. The entitled principal's person set is a strict superset of the unentitled one's.
- **The intent selects the threshold** (`UBO-G06`): one entity under two intents yields two thresholds, and the same person moves from a sub-threshold finding to a reportable owner.
- **Absence represented honestly** (`UBO-G19`): no ownership cycles exist in this estate and none were engineered. The cycle member is present, empty, and *computed* — a test that injects a cycle in-process proves the member reports one when one exists, so its emptiness elsewhere is a measurement rather than a default.
- **A contradiction served as a contradiction** (`UBO-G15`): a KYC declaration that disagrees with the computed chain carries both figures and says it disagrees. The computed figure is never overwritten.

## Run it

```sh
make venv                                   # once; creates .venv

# READ-ONLY: the curated estate on 192.168.4.76 (v2 namespaces — never the v1 names in ccf_dataprep/.env)
export CCF_CP_15_POSTGRES_DSN=...   CCF_CP_15_POSTGRES_SCHEMA=ccf_v2
export CCF_CP_15_FLUREE_URL=...     CCF_CP_15_FLUREE_LEDGER=fibo-v2
export CCF_CP_15_MONGO_URI=...      CCF_CP_15_MONGO_DB=fibo_v2
export CCF_CP_15_TOKEN_KYC=...      CCF_CP_15_TOKEN_COVERAGE=... CCF_CP_15_TOKEN_RESEARCH=... CCF_CP_15_TOKEN_UNGRANTED=...

make -s example-cp-15                                              # the KYC analyst; a sub-threshold finding and a sanctions hit, both referred
make -s example-cp-15 PRINCIPAL=--principal=PRIN-COV-001           # no residency entitlement: the person is not there at all
make -s example-cp-15 ENTITY=--entity=ICJ-SPV-149                  # the intent contrast, under onboarding
make -s example-cp-15 ENTITY=--entity=ICJ-SPV-149 INTENT=--intent=enhanced-due-diligence   # the same person, now reportable
make -s example-cp-15 ENTITY=--entity=ICJ-SPV-026                  # an above-threshold owner
make -s example-cp-15 MIN_CONFIDENCE=--min-confidence=0.1          # refused by name: a floor may be raised, never lowered (exit 1 — correct)
make -s example-cp-15 ENTITY=--entity=ICJ-SPV-999999               # withheld: no chain (exit 1 — correct)

.venv/bin/python examples/cp-15-kyc-refresh-beneficial-ownership/run.py --door   # the standard MCP door
```

`-s` silences `make`'s own echo. A refusal exits non-zero — that is the SDK working, not a crash.

## The story

### 0. The entitlement is read first

A person record outside the principal's residency entitlement is never minted. Not filtered afterwards, never minted — and the product never says how many were withheld, because that count would be the disclosure the entitlement exists to prevent. Unusually for this ladder, the estate itself carries the axis: `principal.sees_eu_person_data` is the estate's column, not this deployment's declaration.

### 1. The threshold is the intent's

`bo_threshold` is keyed by jurisdiction **and** intent, and the strictest applicable jurisdiction on the chain's path governs. The product states which jurisdictions decided it, and whether it fell back to the intent's strictest declared value because none of the chain's own jurisdictions was priced.

### 2. A finding stays inside the product

Persons at or above the threshold are reportable. Persons below it, and resolutions below the confidence floor, are **findings** — served, named, and carried in the payload. The estate makes this the common case rather than a corner: most chains fall below the reporting threshold, and every sanctions screening it holds is in the review band.

### 3. Only then is anything referred

The product is complete. Its bytes are fixed and its record is written. **Now** the review queue opens, takes the content address and the record reference, and enqueues one event per finding that has evidence behind it. A finding with no evidence is not referred and no reference is manufactured for it.

Nothing the queue does can reach the product. That is checked by assembling the same question with the queue never opened and comparing bytes.

## Artifact-by-artifact

| file | role |
|---|---|
| `spec/CP-SPEC-015_KYC_Refresh_Beneficial_Ownership.md` | the specification, written and ruled before this code existed; §G.1 is the acceptance authority for every gate, §F.4 the HITL convention and §F.4.1 the construction boundary |
| `ccf_config.yaml` | the Control Plane document: class, four operators, request contract, resolution rules, the λ_c table, the debt profile, the policy bundle, TTL, replay, the door |
| `ccf_environment.yaml` | the NAMES the three sources and four credentials are read from; never a value |
| `artifacts/question.yaml` | the demonstration entity, the intent contrast, the pinned instant |
| `artifacts/perspectives.yaml` | the declared shape per perspective, and the classification vocabulary the gate holds it to |
| `artifacts/source-vocabulary.yaml` | every table, collection and field this deployment reads |
| `artifacts/gates.yaml` | the twenty declared gates with their sabotages and the red each was observed at |
| `acquisition.py` | the estate half: three readers, the envelope computed in one order, dated claims out. Imports no HITL symbol |
| `deployment.py` | claims as envelopes, the debt assessment, the declared gate. Imports no HITL symbol |
| `projection.py` | Π: one plan, three perspectives, the threshold and confidence evaluation, the computed cycle member |
| `produce.py` | the paved producer road — two marker regions, no domain value |
| **`review.py`** | **the HITL half, and the only module that imports `ccf.hitl`.** It takes an already-served product and returns the events it enqueued; it never returns a product |
| `server/serve.py` | the standard door with its three typed overrides, and the HTTP door |
| `run.py` | presentation only; serves first, then refers |
| `FINDINGS.md` | what this rung measured about the SDK |

## What to change first to adapt it

Replace `artifacts/source-vocabulary.yaml` with your own estate's names and `artifacts/perspectives.yaml` with your own audience shapes; rewrite the readers in `acquisition.py`. `produce.py` names no domain value and does not change. The seam that derives the envelope from the verified credential is documented at `public/how-to/condition-acquisition-on-the-verified-credential.md`, and this tree was written against that page.

**If you are adding HITL to your own product, copy `review.py`'s shape rather than its content** — in particular, that it takes a `ServedProduct` rather than anything earlier. That single type choice is what makes the construction boundary structural instead of a convention somebody has to remember.

## Illustrative calibration

This example runs against a point-in-time demonstration estate rather than continuously refreshed production data. Freshness half-lives and related thresholds are calibrated to make the governed behavior observable in that snapshot. They demonstrate how the SDK applies these controls and should not be interpreted as recommended production coverage-policy thresholds.

The Similarity floor is 0 here, and the reason is recorded where it is declared: `kyc_document` carries no text field, so the ranked corpus is composed at the acquisition seam from the document's kind, its entity and owner names and its jurisdiction. The reporting thresholds and the confidence floors are the **estate's own**, not calibrated by this example; what the request may do is raise them, never lower them.
