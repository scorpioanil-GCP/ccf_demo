---
phase: 15-sdk-ergonomics-the-integration-surface
plan: 09
subsystem: controlplane-artifacts
tags: [artifacts, signal, projection, products, d-impl-80]
requires: ["15-07", "15-08"]
provides:
  - ccf.controlplane.artifacts.SignalBatch
  - ccf.controlplane.artifacts.SIGNAL_BATCH
  - ccf.controlplane.artifacts.PerspectiveArtifact
  - ccf.controlplane.artifacts.PERSPECTIVE
  - ccf.controlplane.artifacts.ProductClassDeclaration
  - ccf.controlplane.artifacts.PRODUCT_CLASS
affects: ["15-10", "15-13", "15-14", "15-19", "15-21"]
tech-stack:
  added: []
  patterns:
    - "subclass the existing SDK contract rather than declare a parallel one"
    - "role: load artifacts parse but never register (D-IMPL-80)"
key-files:
  created:
    - docs/surface-changes/15-09-signal-perspective-productclass.md
  modified:
    - src/ccf/controlplane/artifacts.py
    - src/ccf/deployment/classes.py
    - tests/controlplane/test_artifact_roundtrip.py
decisions:
  - "required_operator_keys keeps min_length=1 on whitepaper §7.6 authority (empty-operator guard) — a reading, not a design choice; no D-IMPL entry"
metrics:
  tasks: 3
  duration: ~35m
  completed: 2026-08-04
---

# Phase 15 Plan 09: Signal Batch, Perspective, and Product Class Summary

Three artifact classes close the last hand-marshalled shapes ROADMAP Criterion 2
names — the signal batch, the perspective, and the product-class declaration —
so every one now reaches adopters through the same `parse_artifact` seam that
already served half-life tables and debt profiles.

## The open question I owned: `required_operator_keys` cardinality

**Ruling: `min_length=1` stands. The whitepaper settles it, so this is a reading
and needs no decision-log entry** (CLAUDE.md §15).

`docs/CCF_Whitepaper_1-2.md` §7.6 specifies the empty-operator guard as the
first of the three validation gates and gives its rationale in terms that decide
the question directly:

> The empty-operator guard rejects a Contract whose `operators_invoked` is empty
> — a projection must have resolved at least one operator to have meaningfully
> read the graph, and an empty set indicates a misconfigured projection rather
> than a trivially-successful one.

The reviewer's framing — "a product/projection requiring zero operators should
still be representable if the gate compares declared vs resolved empty sets" — is
the case the whitepaper explicitly forecloses. Gate 2 comparing `∅` to `∅` would
succeed, but Gate 1 runs first and refuses the product regardless, because the
whitepaper treats an empty resolved set as *evidence of misconfiguration*, not as
a legitimate degenerate case. A declaration of zero operators can therefore only
ever produce a product Gate 1 rejects at assembly time. Refusing it at parse is
the same rule applied where the author can still fix it — earlier, not stricter.

The distinction that makes this non-overconstraining: **a deployment that serves
no product simply authors no document of this class.** That is a different thing
from a product class declaring that it requires nothing.

### The reviewer's supporting claim, checked against the tree

I was asked to verify rather than accept the claim that 15-14 and 15-19 rely on
examples with partial or no operator sets. Both halves are falsified:

- **15-14** turns on example 02 registering **three of four operator
  *categories*** (no similarity). Three is not zero, and the plan's own text says
  the point is that "the artifact set decides" which categories exist. `min_length=1`
  is not in tension with a partial category set. This is the same distinction
  15-08's executor drew, and it is correct.
- **15-19** (example 05, workflow-HITL) registers no operators — and **registers
  no product class either**. `grep` for `register_product_class` in
  `examples/05-workflow-hitl/run.py` returns only a `_no_product` failure helper.
  It never authors a `ProductClassDeclaration`, so the field's cardinality cannot
  constrain it.

So no plan in the phase is blocked by the constraint, and nothing in the tree
needs a zero-operator product class.

### What the field is actually for

`required_operator_keys` exists to keep the projection's **declaration** and the
engine's **resolution** two independent mechanisms. Gate 2 compares them for
strict equality (INV-CH7-47), so a projection returning the operator registry's
own keys makes that comparison a value against itself and the gate silently stops
being a gate. **Every example in the tree today does exactly that** —
`required=operators.keys()` at four sites and `required=self._registry().keys()`
at one. Plan 15-21's AST guard turns that shortcut into a red build tree-wide;
this field is what gives 15-13 an authored source to replace it with.

## Task-by-task

| Task | What | Commit |
| --- | --- | --- |
| 1 | `SignalBatch` + `SIGNAL_BATCH` over `SignalEnvelope` | `d2d1ef7` |
| 2 | `PerspectiveArtifact`, `ProductClassDeclaration` + constants | `822cac9` |
| 3 | Round-trip cases and the surface-change fragment | `3b862cd` |

**Task 1.** `SignalBatch` declares `tenant_id: str` and
`envelopes: tuple[SignalEnvelope, ...]` with `min_length=1`. Pydantic parses each
mapping into a real envelope, which is the point: the *document* adopts the SDK's
vocabulary (`source: {system_id: ...}`, `raw_payload:`) rather than the SDK
growing a second vocabulary to accommodate the document's flat keys. The
translation is removed, not relocated. `src/ccf/signal/envelope.py` is untouched
(`git diff` empty) — `raw_payload` stays opaque to L1 and its keys stay the
source's vocabulary. A `model_validator` refuses a batch whose envelopes name
another tenant, naming the offending envelope ids; it never stamps the batch
value onto an envelope that omitted or contradicted it.

**Task 2.** `PerspectiveArtifact` subclasses `ccf.projection.plan.Perspective`
verbatim (15-08's shape), so a parsed artifact *is* a `Perspective`.
`ProductClassDeclaration` declares six fields and deliberately **not**
`max_ttl_version` — that pin is minted by registering the `MaxTTL`, D-IMPL-76's
shape. Keeping it out is what preserves Gate 3: the ceiling is an authored
artifact value, the pin is derived from registering it, and `expires_at` is a
separately authored number, so the gate checks two independent things.

No helper calling `register_product_class` was added. 15-10 owns registration; a
second path would make "what was in force" answerable from two places.

**Task 3.** Three round-trip cases (the vacuity guard now passes), plus:
a batch with a `...Z` timestamp parsing through `load_artifact` to an aware UTC
value with `utcoffset() == timedelta(0)` — the test that makes 15-05's eleven
`_instant` helpers *redundant* rather than merely unfashionable; the cross-tenant
refusal; the empty-batch refusal; the `max_ttl_version` refusal; and the
zero-operator refusal carrying the §7.6 rationale in its docstring.

## Message to 15-10 — how I hardened the `role` mistake from my side

You own the manifest and its enforcement. Three things exist on my side to make
marking a signal batch `role: register` harder to do by accident:

1. **The `SignalBatch` class docstring** states the `role: load` status in bold,
   with the reason: registering a batch content-hashes raw event data into
   Control Plane state, and by D-06's rationale the registered artifact set is
   replay dimension 2 — re-authoring an events file would then change "what was
   in force" exactly as a policy-bundle bump does. mkdocstrings publishes this,
   so it lands in Phase 16's rendered reference.
2. **The `SIGNAL_BATCH` constant's `#:` comment** repeats it in one sentence, so
   the reader who jumps to the constant rather than the class still sees it.
3. **A `# role: load` comment on the `SDK_ARTIFACT_CLASSES` entry** in
   `classes.py`, stating that the mapping only says the class *exists* and that
   the manifest's `role` field carries the distinction you enforce.

What I did **not** do: encode the role as a field on `ArtifactClass` or as a
type-level distinction. That would be inventing manifest mechanism inside the
artifact surface, and it is yours. If you want a machine-checkable signal rather
than three docstrings, the cheapest one is a lint or a manifest-parse rule
keyed on `class_id == "ccf.signal-batch"` implying `role: load` — but that is a
15-10 decision and I deliberately did not pre-empt it.

## Message to 15-13 and 15-19

- **15-13**: `required_operator_keys` is the authored source your instruction
  ("declare `required` from the artifact") needs. It is on the **product-class**
  declaration, not a projection artifact. Do not fall back to
  `operators.keys()` — that is the tautology 15-21's AST guard will catch.
- **15-19**: nothing here constrains example 05. It authors no product class, so
  `min_length=1` never fires for it. It also registers no operators, and the
  manifest simply names no operator-parameters documents — unchanged by this plan.

## Deviations from Plan

None. The plan executed as written. Two notes that are clarifications rather
than deviations:

- The plan's Task 1 verify command named `tests/signal/`, which does not exist;
  the directory is `tests/signal_layer/`. Ran that plus `tests/controlplane/`.
- `ProductClassDeclaration` carries both `semver` (the artifact document's lane,
  from `VersionedArtifact`) and `schema_version` (the product class's own lane,
  INV-CH7-49). Two lanes because they version different things; the docstring
  says so, since the pairing reads like a duplication otherwise.

## Known Stubs

None.

## Threat Flags

None. No new network endpoint, auth path, file access pattern, or trust-boundary
schema change beyond what the plan's threat model already registers. The two
Spoofing dispositions (T-15-09-01 cross-tenant batch, T-15-09-06 tautological
lineage gate) are mitigated in code and pinned by tests; T-15-09-05
(raw event data into replay dimension 2) is mitigated by docstring and constant
comment on my side, with enforcement delegated to 15-10 as the plan specifies.

## Surface manifest

`docs/surface/v0.2-surface.json` and `docs/surface/v0.2-surface-baseline.json`
are **untouched** (`git status --short docs/surface/` empty). `make surface` was
never run. `--report` shows 26 accumulated added names across 15-06 through
15-09; my fragment claims the six that are mine and no others, per the 15-07
accumulation ruling.

## Self-Check: PASSED

- `src/ccf/controlplane/artifacts.py` — FOUND
- `src/ccf/deployment/classes.py` — FOUND
- `tests/controlplane/test_artifact_roundtrip.py` — FOUND
- `docs/surface-changes/15-09-signal-perspective-productclass.md` — FOUND
- Commits `d2d1ef7`, `822cac9`, `3b862cd` — FOUND
- `make typecheck` 0, `tools.lints --all` 0, `make ci-core` 0 (1681 passed, 2 skipped)
