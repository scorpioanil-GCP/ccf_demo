# Single-file deployment authoring for CCF

**Date:** 2026-08-14
**Author:** Dave, with Claude
**Status:** Design approved in brainstorming. Not yet a ruling — this becomes a
`D-IMPL` entry before implementation.

---

## 1. Why

Dave read `examples/s1-01-hello-context-product/artifacts/` and asked:

> *"I am becoming extremely concerned about what I'm seeing … Do I really
> require this many yaml files to construct my context product?"*

`D-IMPL-131` and `D-IMPL-132` came out of that reading. HW-1
(`examples/s1-00-companies-over-revenue`) discharged them and landed at **10
config files / 99 non-comment lines**, against `s1-01`'s 20 files / 1060 lines.

Measuring HW-1's remainder showed the residue is not domain values:

| Bucket | Files | Lines |
|---|---:|---:|
| **Structural** — `manifest.yaml` (46), `backends.yaml` (10), `perspective.yaml` (3) | 3 | **59** |
| **Values** — request-contract, product-class, resolution-spec, half-life, policy, debt-profile, operator-parameters | 7 | 40 |

`manifest.yaml` alone is **46% of the config surface and is an index of itself**
— a table telling CCF things derivable from the filenames. Every genuine domain
decision totals 40 lines.

The friction is three-layered, in Dave's ordering: **too many files to open**,
**too many concepts to learn**, **no signal about what must be authored**. The
fix is layered the same way — default what can be defaulted, merge what remains,
organise the result by what an adopter does rather than by CCF's internal
artifact taxonomy.

## 2. Goal

A newcomer defines a complete, runnable Context Product deployment in **one
file**, where **every line is a decision they made**. Structural bookkeeping —
paths, keys, class ids, roles, registrations — is derived by the loader. Replay
addressing and `D-IMPL-26` remain intact. Existing multi-file deployments keep
working unchanged.

## 3. The hard blocker, and why it is not one

The obvious objection is that collapsing artifacts into one file collapses their
version identities, breaking `D-IMPL-26`'s promise that replay resolves *exact*
artifact versions. **Measured against the tree, that objection fails**:

- `src/ccf/deployment/pins.py:66-68` — `ArtifactPin.version` is *"The content
  version `register_typed` returned. **A content hash (D-IMPL-26), so pin
  identity *is* content identity.**"*
- `src/ccf/contracts/canonical.py:194` — `canonical_bytes(obj)` addresses the
  **parsed object**: *"Semantically equal inputs produce identical bytes."*
- `src/ccf/deployment/manifest.py:617` — the loader reads a document per entry
  and calls `load_artifact(document, artifact_class)`; **registration
  content-addresses the parsed contract, not the file bytes.**

So the file boundary is a *loading convention*, not an addressing requirement.
Sections parsed from one file yield **byte-identical content addresses** to the
same content in separate files. The declared `semver` is a human label used for
pinned resolution by declared version (`registry.py:550`), and
`register_typed` carries **no D-05 bump check** (`registry.py:128-135`), so a
single top-level `semver` is coherent: it versions the deployment's config, and
per-artifact identity remains the content hash.

**A single top-level `semver` does not weaken replay determinism.**

## 4. The authoring file

**Name:** `ccf_config.yaml` (recommended) or `deployment.yaml`.
**Location:** deployment root, where `manifest.yaml` lives today.

Only this file is required for the value surface. `backends.yaml` stays separate
(§9). `perspective.yaml` is not required where a door exists (§8).

### 4.1 Top-level shape

```yaml
semver: "1.0.0"          # deployment-level label only
tenant_id: hw1-demo
backend: postgres        # kind only; connection material stays in env

product_class:           # required
operators:               # optional; keyed by operator id
request_contract:        # required for a question-answering product
resolution:              # required when a source -> graph mapping is needed
half_life:               # optional; domain decay
debt_profile:            # optional; D_c thresholds
policy:                  # optional; adopter-owned regime
default_perspective:     # optional; in-process deployments with no door
```

**Unknown top-level keys are an error.** A typo becomes *"I don't recognise the
section `resolutoin`"* rather than a refusal about a missing key three layers
down.

## 5. Section definitions

### 5.1 `product_class` — required

```yaml
product_class:
  schema_name: hw1.companies-over-revenue
  schema_version: "1.0.0"
  ttl_anchor: from_decision
  assembly_mode: algorithmic
  max_ttl_key: hw1/product/companies-over-revenue/max-ttl   # optional
  required_operator_keys: [temporal.as-of-boundary]

  discovery:                       # optional; see §8.2
    domain: corporate-credit
    intents: [revenue-screening]
    capabilities: [threshold-filter]
    audiences: [analyst, investment_banker]
```

Becomes the `ccf.product-class` artifact.

### 5.2 `operators` — optional

```yaml
operators:
  temporal.as-of-boundary:
    require_valid_at_boundary: true
```

Keyed by the operator id appearing in `required_operator_keys`. Replaces the
separate `operator-parameters-*.yaml` files; the loader materialises the
matching `ccf.operator-parameters.*` artifacts.

**Behaviour lives with the operator it configures**, not inside `product_class`.
This scales when a second operator appears.

### 5.3 `request_contract` — required for question-answering products

```yaml
request_contract:
  arguments:
    properties:
      revenue_threshold:
        type: number
        description: Return companies whose revenue exceeds this amount.
    required: [revenue_threshold]
```

A **reserved section name** whose contents are **adopter-owned**. The loader
supplies the class id and registration metadata; the SDK does not own the
argument vocabulary.

### 5.4 `resolution` — required when mapping source data

```yaml
resolution:
  entity_rules:
    - match_key: company_ref
      entity_class: company
      identity_keys: [company_ref]
      attribute_keys: [company_name, company_revenue]
```

Becomes `ccf.resolution-spec`. Observed-time handling is unchanged: a source
column such as `last_updated` arrives as the envelope's `observed_time` and
becomes the claim's `observed_at`, which the half-life curve reads. It is not a
projected attribute.

### 5.5 `half_life` — optional

```yaml
half_life:
  company:
    half_life_seconds: 31536000
    decay_driver: the annual revenue reporting cycle
    supersession_event: a newer filing restating the same company's revenue
```

Becomes `ccf.half-life-table`.

### 5.6 `debt_profile` — optional

```yaml
debt_profile:
  risk_sensitivity: "1.0"
  forced_llm_threshold: "0.20"
  fail_closed_threshold: "0.60"
```

Becomes `ccf.debt-profile`.

### 5.7 `policy` — optional

```yaml
policy:
  regime: published-annual-revenue-disclosure
```

A **reserved section name** whose contents remain **adopter-owned and opaque**.
The loader materialises it as the policy-bundle artifact; the SDK does not
interpret regime names and claims only the `ccf.` prefix (`D-IMPL-84`).

## 6. What the loader derives

For each section the loader produces a typed artifact and a manifest entry.
These fields are **derived-with-override** — an explicit value always wins.

| Field | Derivation |
|---|---|
| `path` | Literally `ccf_config.yaml`. **Not a synthetic placeholder** — see §11.1. |
| `key` | The section name |
| `class_id` | `ccf.<stem>` when it resolves to an SDK class; otherwise the adopter-owned class the section maps to |
| `role` | `ccf.*` classes → `register`. **Adopter-owned classes: must be stated. There is no default.** |
| `registration` | `ccf.*` classes → `typed`. **Adopter-owned classes: must be stated. There is no default.** |

An earlier draft of this table said adopter-owned classes could be *"stated, or
defaulted by documented convention"*. That is ambiguous enough to produce two
incompatible implementations, and it weakens the very rulings §6.1 claims to
preserve. Corrected: for any class the SDK does not own, both fields remain
required exactly as `D-IMPL-80` and `D-IMPL-85` specify. HW-1's two adopter
sections (`policy`, `request_contract`) therefore each carry two lines, which is
the whole cost of keeping both rulings intact.

### 6.2 The two top-level key pointers

Today's manifest carries `resolution_spec_key: resolution-spec` and
`policy_bundle_key: policy-bundle` as top-level fields, naming which registered
key holds each. In the single-file form both are **derived from the section
names** — `resolution:` and `policy:` — and are not authored. They remain
overridable for a deployment that registers several and must name which is in
force.

### 6.1 The `D-IMPL-80` / `D-IMPL-85` narrowing

`role` and `registration` are today **required with no default**, by explicit
ruling: `D-IMPL-80` (2026-08-04) because registering content-hashes an artifact
into replay dimension 2, and `D-IMPL-85` (2026-08-05) because it selects between
`register_typed` and `register_versioned` with its D-05 bump check.

This design **narrows** both rather than revoking either. They stay mandatory
for every class the SDK does not own — which is exactly where the hazard lives,
since the risk is an adopter accidentally content-hashing event data into the
audit plane. They become silent only for `ccf.*` classes, where there is exactly
one correct answer and requiring the field is transcription rather than
deliberation.

**Consequence worth keeping:** after the narrowing, `role` appears only where it
was actually chosen. In HW-1 exactly one entry is `role: load`
(`request-contract`), and today it is camouflaged by seven lines of
`role: register` transcription.

## 7. The manifest

`manifest.yaml` becomes **optional**. When absent, the loader builds the full
manifest from the sections. When present, it carries only entries that deviate
from derivation.

## 8. Perspective, and the discovery distinction

These are two different things and the design keeps them apart.

### 8.1 Runtime perspective

Derived from the caller's grant at the door — `entitled_perspective(grant=...)`
at `runtime/ccf_runtime/mcp/egress.py:451-454`. A principal's grant carries a
**set** of `permitted_roles` (`src/ccf/products/entitlement.py:136`) and asserts
one per call. No file is required.

For in-process deployments with no door, one optional top-level key:

```yaml
default_perspective:
  principal_id: revenue-screening-desk-1
  role: analyst
```

This is why `perspective.yaml` exists in HW-1 at all: its client is in-process,
so there is no grant to derive from.

### 8.2 Discovery advertisement

Who a product is *aimed at* is discovery metadata, not runtime conditioning. It
lives on `product_class.discovery` and maps to the shipped §6.3 element
`ProductDiscovery` (`src/ccf/products/contract.py:373-395`), which today carries
three axes: `domain: str`, `intents: frozenset[str]`,
`capabilities: frozenset[str]`.

**`ProductDiscovery` gains a fourth axis, `audiences: frozenset[str]`** (Dave,
2026-08-14). Roles and audiences map onto none of the existing three; calling
`analyst` an intent or a capability would corrupt both meanings. Like the other
three, `audiences` values are opaque deployment-declared identifiers the SDK
matches structurally and interprets none of.

This is a surface change to a shipped element and requires a
`docs/surface-changes/` fragment, a `_SHAPE_MOVED_BY_FRAGMENT` claim
(`D-IMPL-130`) if the class shape moves, and its own `D-IMPL`.

**Out of scope:** the product-catalog *door*. `ProductDiscovery` is the schema and
`RegisteredProductClass` the registry entry, but nothing in `runtime/` serves a
catalog — `discovery` defaults to `NOT_DISCOVERABLE`
(`contract.py:569`). Deferred deliberately.

## 9. Backends stay out

`backends.yaml` remains **outside** this file. Connection material is deployment
environment, not Control Plane state, and a DSN inside a content-hashed artifact
is a DSN persisted into the audit plane forever. HW-1's `backends.yaml` already
holds **no connection values** — only env-var names and a per-run schema rule.

## 10. Compatibility

- Existing multi-file deployments work unchanged.
- The single-file form is an **additional authoring surface**, not a replacement
  for the typed artifact model.
- Gates, replay and registration see the same typed objects they see today.

## 11. Findings from design review

Three issues surfaced while reviewing the draft against the tree. All three are
resolved here rather than left for implementation to discover.

### 11.1 `path` is validated even when derived

`ManifestEntry.path` carries two validators
(`src/ccf/controlplane/artifacts.py:983`, `:995`): it rejects glob characters —
*"a manifest enumerates … Name the file"* — and rejects paths leaving the
manifest's own directory.

**Resolution:** every derived entry's `path` is literally `ccf_config.yaml`.
Truthful, since that is where the section came from; passes both validators;
uniqueness comes from `key`, not `path`. An implementer must not invent
`<memory>`, an empty string, or a `section#name` form.

### 11.2 The operator set is enumerated twice

`product_class.required_operator_keys` and the `operators:` keys state the same
set. That is precisely the condition
`refuse_operator_set_divergence` guards — and it is why HW-1 ships **no**
`projection-requirements.yaml` and makes no binder call, on the stated ground
that *"this deployment authors one operator set, so the binder would compare a
value with itself."*

The single-file form reintroduces two enumerations. Not across independently
authored documents, but two nonetheless.

**Resolution:** the loader **refuses at parse time** when the two disagree,
naming both sites. Neither is authoritative — refusing beats picking. This turns
a wave-11 gate failure into an immediate typo message.

**The general lesson, recorded because it will recur:** consolidating *files*
does not consolidate *claims*. A guard justified by "there is only one statement
here" needs re-checking whenever the authoring surface changes shape.

### 11.3 `intended_for` had no home in the shipped discovery element

Resolved in §8.2 by adding `audiences` to `ProductDiscovery`.

## 12. Implementation notes

1. Parse `ccf_config.yaml`.
2. For each recognised section, materialise the corresponding typed artifact.
3. Apply the derivation rules in §6.
4. Cross-check `required_operator_keys` against `operators` keys; refuse on
   disagreement (§11.2).
5. Register each artifact exactly as the multi-file path does today.
6. Reject unknown top-level keys.
7. Preserve override of any derived field by writing it explicitly.

## 13. Target

A complete minimal product in roughly **30 lines**, against HW-1's current 99 —
with no hand-written index, no required `perspective.yaml`, and no
seven-line transcription blocks.

## 14. Rulings this design needs

None of these are settled by this document.

1. The `D-IMPL-80` / `D-IMPL-85` narrowing (§6.1).
2. `audiences` as a fourth `ProductDiscovery` axis (§8.2).
3. Reserved-section semantics for `policy` and `request_contract` — the SDK owns
   the *slot*, the adopter owns the *schema* (§5.3, §5.7), which must be stated
   as compatible with `D-IMPL-84` rather than assumed.
