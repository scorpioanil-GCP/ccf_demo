# 357-C4 — the declared grammar: `ArgumentDomain.pattern` and `ProductRequestContract.subject_domain`

`D-IMPL-357` C4 (ruling locked). Lane C, task C4: `ArgumentDomain` gains a
THIRD exclusive shape — a grammar (`pattern`) beside numeric bounds and an
enumerated member set, amending `D-IMPL-264` D-03 — and
`ProductRequestContract` gains `subject_domain`, the further constraint a class
holds its SUBJECT to. The subject is an address axis (§6.3) rather than a
parameter, so it has no entry in `argument_domains` and needs a declaration of
its own; `refuse_request` judges it in a new step immediately after the address
check.

**The property that governs the whole entry: a declared pattern can only
NARROW, never widen past the mechanism floor.** `SUBJECT_FLOOR_V1` (`357-C1`)
is judged by `refuse_floor` inside `GovernedResolver.__call__` **before** the
overridable constraint-resolver seam, and `refuse_request` — and therefore the
new subject step — is reached only from inside that seam's resolution. So an
adopter declaring `pattern=".*"` (a grammar admitting an apostrophe, and so a
single-quoted-literal splice) does not thereby make an apostrophe-bearing
subject servable: the floor has already refused the request. The ordering is
pinned at both levels, on the pure functions
(`tests/products/test_request_contract.py::test_a_permissive_declared_pattern_cannot_widen_past_the_mechanism_floor`)
and at the resolver
(`tests/products/test_resolver_seam.py::test_a_permissive_subject_domain_cannot_widen_past_the_mechanism_floor`).

**The floor's own covered surface is untouched by this task.** Its grammar, the
positions it judges (the subject and every declared `string` parameter, and
nothing else) and its call site are exactly what `357-C2` left; whether that
coverage should widen remains `D-IMPL-357`'s open question, held for the
project owner.

## ccf.products.request.ArgumentDomain

- Surface: ccf.products.request.ArgumentDomain
- Public surface: true
- Change type: reshaped
- Before: three fields — `minimum: Decimal | None`, `maximum: Decimal | None`, `members: tuple[str | int | bool | Decimal, ...] | None`; exactly one of two shapes (numeric bounds OR an enumerated set), enforced by pairwise comparison
- After: a fourth field, `pattern: str | None = None` (hash-transparent `True`), and exactly one of THREE shapes, enforced by a shape COUNT rather than a pairwise chain. A pattern is judged by `re.fullmatch` (never `re.search` — a value that merely contains the grammar satisfies a wider domain than the one declared) and is compiled once at construction so a non-compiling grammar is refused by name where the author can still fix it. `refuses(value)` returns `"not-in-domain"` for a non-string, or for a string the grammar does not match in full.
- Why: `D-IMPL-357` C4 — an identifier whose legal form is a RULE (an LEI, an internal account format, a jurisdiction code) cannot be declared as a roster, and the alternative an adopter reaches for is validation in deployment code, which is a second authority over one bound (`D-IMPL-315`). Sentinel-silent at `None` (`D-IMPL-243`), so every domain written before the grammar existed canonicalizes byte-for-byte as it did and no committed request contract's content address moves.
- Migration: none for any existing declaration. An author who reads the refusal message should note it now names a shape COUNT ("declares 2") rather than "both"; the word "neither" is retained for the no-shape case.

## ccf.products.request.ProductRequestContract

- Surface: ccf.products.request.ProductRequestContract
- Public surface: true
- Change type: reshaped
- Before: no declaration surface for the subject; a class could constrain any declared parameter and nothing about the address axis the question is actually about
- After: `subject_domain: ArgumentDomain | None = None` (hash-transparent `True`), plus a validator refusing a NUMERIC subject domain by name — a subject is an identifier, not a magnitude, so bounds over one bound nothing (the sibling of the existing `unmeasurable` refusal over a declared `string`). `from_declared` reads it as the optional NINTH declaration key, so the field is reachable from an artifact and not only from Python. The declaration-time domain validator additionally refuses a `pattern` declared over a parameter whose type is not `string` (a grammar judges text; over any other type no value could satisfy it), named in the same exhaustive message as the five defects it already reports.
- Why: `D-IMPL-357` C4. An adopter who knows their subjects are LEIs should be able to say so in the governed declaration rather than nowhere. Sentinel-silent at `None`, so every request contract written before the field keeps its content address; a declared domain renders and therefore MOVES the hash, deliberately — two classes holding their subjects to different grammars must not share one contract identity.
- Migration: none. A contract declaring no `subject_domain` holds its subject to exactly what it did: the mechanism floor, judged by `refuse_floor`, which no declaration can reach under.

## ccf.products.request.refuse_request

- Surface: ccf.products.request.refuse_request
- Public surface: true
- Change type: behavior
- Before: five ordered steps — address, tier, the payload comparison, the tolerance interval, the declared parameter domains
- After: SIX ordered steps, with the subject's declared domain inserted SECOND, immediately after the address check and before the tier step: the subject is an address axis, so its verdict belongs beside the other address verdicts and none of the parameter steps has anything to say about it. The returned violation carries `reason` (`"not-in-domain"`), `key="subject"`, `declared_type="string"`, and the declared grammar or member set in `detail` — never the presented subject, on `refuse_floor`'s own discipline that `detail` states the RULE and never echoes untrusted caller text.
- Why: `D-IMPL-357` C4. One comparison, so a registration-time capability check and a live request are judged by one reading of "well-formed". The step is a NARROWING and is explicitly NOT the mechanism floor: the paragraph `357-C2` added — that this function deliberately does not carry the floor, and that a caller validating a request outside `GovernedResolver` must call `refuse_floor` itself — remains true and is now stated alongside the narrowing step so the two cannot be confused.
- Migration: none for a contract declaring no `subject_domain` (the step returns `None` immediately). A caller that declares one gets a `not-in-domain` violation keyed `"subject"`, which is an existing reason and an existing violation class — the door still maps by CLASS (`ProductRequestViolation` -> 400), never by reason token.

## docs/schemas/ccf.product-request-contract.json

- Surface: docs/schemas/ccf.product-request-contract.json
- Public surface: false
- Change type: reshaped
- Before: `ArgumentDomain` advertised three properties; the contract advertised nine
- After: `ArgumentDomain` advertises `pattern` and the contract advertises `subject_domain`, both carrying `"ccf_hash_transparent": true` and `"default": null`
- Why: the committed schema tree is the authoring baseline an adopter reads in their editor (ERGO-12); a declaration key that exists in the type and not in the schema is a key nobody can discover
- Migration: none — both keys are optional and default to absent

## ccf.products.request_schema.render_request_input_schema

- Surface: ccf.products.request_schema.render_request_input_schema
- Public surface: true
- Change type: behavior
- Before: derived exactly one of two things onto a domained property — `enum`, or `minimum` / `maximum` — and refused a base render that already carried any of those three keys
- After: derives one of THREE — `pattern` verbatim for the grammar shape (a regular expression is text, so there is no value translation for it to need) — and refuses a planted `pattern` on the same D-00 / P-1 terms: the base render is not a declaration surface for legal values at all
- Why: `D-IMPL-357` C4 on P-1's terms — the request contract is the authority for legal values and this module ADVERTISES that authority; a declared grammar reaching a caller as JSON Schema's own `pattern` keyword is the derivation, and a `pattern` written on the base render would be a second declaration that could disagree
- Migration: none. This module still publishes nothing — no MCP tool, no HTTP route, no CLI verb serves the render (carry row `24.7-C-01`).
