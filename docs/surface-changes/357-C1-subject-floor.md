# 357-C1 — the mechanism floor: `SUBJECT_FLOOR_V1` and `refuse_floor`

`D-IMPL-357` C1/C1a (ruling locked). Lane C, task C1: `ProductRequestViolationReason`
gains a tenth member, `"malformed-value"`, appended LAST; the SDK-owned
mechanism floor `SUBJECT_FLOOR_V1` (512-character ASCII allowlist, both quote
characters excluded) and its version marker `SUBJECT_FLOOR_VERSION`; and the
pure judge `refuse_floor`, which walks the request's subject and every
declared `string` — at every declared depth (root, an object member, an
array element, and an object member inside an array) — against the floor.
Not wired into `GovernedResolver.__call__` in this task; that is C2.

## ccf.products.request.SUBJECT_FLOOR_V1

- Surface: ccf.products.request.SUBJECT_FLOOR_V1
- Public surface: true
- Change type: added
- Before: absent
- After: `Final[re.Pattern[str]]` — `re.compile(r"^[A-Za-z0-9][A-Za-z0-9:/._~@+=-]{0,511}\Z")`, the SDK-owned mechanism floor (`D-IMPL-357` C1a)
- Why: the fabric's own grammar for what can be placed safely in a SPARQL IRI `<…>` position and a single- or double-quoted literal — an allowlist rather than a denylist, so `'` (which a denylist could admit by omission) never reaches an acquisition splice. NOT a URL-path-segment guarantee: the grammar admits `/` and `..` because a measured subject is itself a URI; a value that passes must still be percent-encoded before use in a URL path or query.
- Migration: none; new name

## ccf.products.request.SUBJECT_FLOOR_VERSION

- Surface: ccf.products.request.SUBJECT_FLOOR_VERSION
- Public surface: true
- Change type: added
- Before: absent
- After: `Final[str] = "SUBJECT_FLOOR_V1"`
- Why: the grammar is versioned by name; a future tightening of the pattern is a new name, and the name rides on every refusal it decides (`detail`)
- Migration: none; new name

## ccf.products.request.refuse_floor

- Surface: ccf.products.request.refuse_floor
- Public surface: true
- Change type: added
- Before: absent
- After: `refuse_floor(*, request: ProductRequest, declared: ProductRequestContract) -> ProductRequestViolation | None` — pure (no clock, no registry, no I/O); judges `request.subject` first, then every declared `string` at every declared depth (`parent`, `parent.member`, `parent[]`, `parent[].member` — the same keying `refuse_payload` uses) in sorted-name order at each level, returning the first `malformed-value` violation or `None`
- Why: `D-IMPL-357` C1 — the mechanism floor judge. `GovernedResolver.__call__` will run this after the addressing verdicts and before the overridable constraint-resolver seam (C2 adds that call site, not this task); a direct validator holding no declaration (`AssemblerAgent`) calls `refuse_request` on its own path and does not judge this separately.
- Migration: none; new name, not yet called from any production path in this commit

## ccf.products.request.ProductRequestViolationReason

- Surface: ccf.products.request.ProductRequestViolationReason
- Public surface: true
- Change type: reshaped
- Before: `Literal["undeclared-parameter", "missing-required-parameter", "type-mismatch", "class-mismatch", "not-supported-at-tier", "not-a-proportion", "below-minimum", "above-maximum", "not-in-domain"]` (nine members)
- After: the same nine, plus `"malformed-value"` appended LAST (never inserted) — ten members
- Why: `D-IMPL-357` C1 — the tenth reason `refuse_floor` returns; appending rather than inserting keeps every older record's reason meeting the same roster prefix
- Migration: none for an exhaustive `match`/`if` chain that already has a catch-all; a chain that enumerates every member explicitly needs a `"malformed-value"` arm added

## ccf.products.request.ProductRequestViolation

- Surface: ccf.products.request.ProductRequestViolation
- Public surface: true
- Change type: reshaped
- Before: `reason` typed over the nine-member `ProductRequestViolationReason`
- After: `reason` typed over the ten-member `ProductRequestViolationReason` (the reshape is entirely inherited from that Literal widening; no field added or removed)
- Why: as `ProductRequestViolationReason`
- Migration: none
