# 378-36 — prose only: P2 (c) and P4 (a) stated as ruled in public docstrings, and one refusal message no longer says "a candidate"

`D-IMPL-378`, Dave's batch ruling of 2026-10-08 12:29 MST (recorded on `main` at `75229b61`), lane `378e-prose`.
Text written before that ruling still called P2 (c) and P4 (a) "a candidate Dave has not ruled". **SEC-020 stays
OPEN**: Dave did not approve its closure, and nothing here changes how any control behaves.

**Documentation only, no behavior change.** The status sentence in the docstrings of
`ccf.deployment.manifest.BootedFabric` (its `question_store` attribute; also reached as `ccf.deployment.BootedFabric`),
`ccf.products.resolver.CompositeNeedsAWithholdingStance`, `ccf.products.resolver.AcquiredFabricReused` and
`ccf.products.resolver.QuestionStoreReopened` now says the ruling it names was made, with its date. No other sentence
in those docstrings changed. The manifest `make surface` writes is unchanged by these edits, because it records
signatures rather than docstring text.

**What the tests measure.** The refusal below is still raised by name, at construction, for a composite that declares
no withholding stance: `tests/products/test_sec020_p2c_composite_stance.py` passes unchanged, and no test in the tree
matches the message text that changed.

## ccf.products.resolver.CompositeNeedsAWithholdingStance

- Surface: ccf.products.resolver.CompositeNeedsAWithholdingStance
- Public surface: true
- Change type: behavior
- Before: the refusal's message ended "(SEC-020; D-IMPL-378 P2 (c), a candidate)".
- After: it ends "(SEC-020; D-IMPL-378 P2 (c))". The type, when it is raised and every other word of the message are unchanged.
- Why: Dave ruled P2 (c) on 2026-10-08 at 12:29 MST (`D-IMPL-378`), so the message no longer calls it a candidate.
- Migration: none, unless code matched the end of the message text; match the refusal by its type instead.
