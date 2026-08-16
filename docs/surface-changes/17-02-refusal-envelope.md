# 17-02 — the canonical refusal envelope

## What did **not** change, stated first

A reader's first question about a change touching the refusal types is whether
any of them moved.

- **No shipped refusal type was edited.** All sixteen — the `GateRefusal`
  hierarchy, the six peering-admission refusals, `ProductMountRefusal`,
  `ProductRequestViolation`, `PayloadSchemaViolation` and `MixingRefusal` —
  keep the exact fields, bases and semantics they had. This plan adds one new
  module and modifies none.
- **`Result` and `Refusal` are unchanged**, because they do not exist yet;
  spec §4 approves them and this envelope concerns only how their information
  crosses a seam.
- **No door emits anything new.** No door emitted a refusal in any body
  before this change and none does after it. The envelope is defined ahead of
  the doors deliberately: there was nothing for a door to emit until the shape
  existed, which is the whole of Amendment 1 §A's ruling.
- **No behavior changed anywhere.** The module is additive and nothing in
  `src/`, `runtime/` or `examples/` imports it yet.

## ccf.products.refusal.RefusalEnvelope

- Surface: ccf.products.refusal.RefusalEnvelope
- Public surface: true
- Change type: added
- Before: absent — every fabric refusal type reached no wire at all; the
  product resolver seam is typed to return a servable product and admits no
  refusal in its union, so a refusal could not cross a door even in principle
- After: a frozen `CCFContract` carrying `kind`, `reason`, `key`, `detail`,
  `fields` (the refusal type's own declared fields, canonically rendered),
  `request`, and `pre_assembly_lineage`
- Why: `D-28` / spec Amendment 1 §A ruled one canonical envelope defined in
  `src/` before any door changes, carrying every refusal kind **without
  flattening** — losing *which kind* a refusal was makes a client's
  `refusal.reason` mush and kills the auditable-refusal guarantee at the seam
- Migration: none. Nothing consumed a refusal across a seam before, so there
  is no prior shape to migrate from. Producers of refusals are unaffected —
  the envelope reads refusal types, it does not change them

## ccf.products.refusal.RequestIdentity

- Surface: ccf.products.refusal.RequestIdentity
- Public surface: true
- Change type: added
- Before: absent — no door echoed the question back, and no refusal type
  carries the question it refused
- After: a frozen `CCFContract` carrying `product_id`, `product_version`,
  `parameters` and `temporal_boundary`
- Why: `D-28`(b) — a refused result must still say *what was asked*, which is
  the pre-assembly half of `D-09`'s field split; the refusal types are values
  about what was wrong and hold none of it
- Migration: none. Constructed by the caller that holds the request

## ccf.products.refusal.envelope_for

- Surface: ccf.products.refusal.envelope_for
- Public surface: true
- Change type: added
- Before: absent
- After: `envelope_for(refusal, *, request, pre_assembly_lineage=None)`, total
  over every type in `REFUSAL_KINDS`, raising `TypeError` on anything else and
  `ValueError` when a lineage is offered alongside a refusal the fabric reaches
  before touching the graph
- Why: the translation has to exist in exactly one place for the kind to be
  preserved consistently; dispatch is on the **exact** type rather than
  `isinstance` because an `isinstance` chain reports an unknown subclass as its
  nearest known ancestor, producing a well-formed envelope carrying the wrong
  kind
- Migration: none — new callable

## ccf.products.refusal.REFUSAL_KINDS

- Surface: ccf.products.refusal.REFUSAL_KINDS
- Public surface: true
- Change type: added
- Before: absent — no enumeration of the fabric's refusal vocabulary existed
  anywhere
- After: a closed `Mapping[type[CCFContract], str]` of the sixteen shipped
  refusal types to their wire tokens
- Why: `kind` must come from one mapping rather than from literals at call
  sites, so the vocabulary is closable; `tests/products/test_refusal_envelope.py`
  asserts its key set equals a structural AST walk of `src/` by **set
  equality**, so a refusal type added and translated nowhere fails the build
- Migration: none. Adopters read it; a new SDK refusal type will appear in it

## ccf.products.refusal.NON_PRODUCT_REFUSALS

- Surface: ccf.products.refusal.NON_PRODUCT_REFUSALS
- Public surface: true
- Change type: added
- Before: absent
- After: a `frozenset[str]` naming the three `…Refusal` contracts under `src/`
  that are not product refusals — `RegistrationRefusal` (a Control Plane
  registration verdict), `EffectRefusal` (a harness effect-capture verdict) and
  `GrantRefusal` (a skilling-governance verdict)
- Why: an omission and an exclusion look identical from the outside. Declaring
  the exclusions lets the exhaustiveness gate close this half by set equality,
  so a fourth such class is a **failure demanding a ruling** rather than a
  silent pass
- Migration: none

## ccf.products.refusal.NON_VALUE_VIOLATIONS

- Surface: ccf.products.refusal.NON_VALUE_VIOLATIONS
- Public surface: true
- Change type: added
- Before: absent
- After: a `frozenset[str]` naming the four `…Violation` classes under `src/`
  that are exceptions rather than values — `TrustPolicyViolation`,
  `SnapshotScopeViolation`, `ProductEntitlementViolation` and
  `SingleWriterViolation`
- Why: two of the sixteen kinds are named `…Violation` rather than `…Refusal`,
  so the gate must walk both name families and partition them by resolved base.
  Without this second allowlist the `…Violation` half would stay enumerated by
  hand, and a new `CCFContract`-based `…Violation` would be neither discovered
  nor excluded — shipping untranslated with the gate green, which is precisely
  the defect `D-28`(a) exists to prevent
- Migration: none. Contract-level principal and entitlement handling at the
  client seam is deferred by the v0 not-list, which is why
  `ProductEntitlementViolation` is recorded here rather than translated
