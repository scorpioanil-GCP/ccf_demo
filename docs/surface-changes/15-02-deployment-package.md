# 15-02 — the `ccf.deployment` package shell and its gate-independence ban

Plan 15-02 creates the SDK's adopter-facing wiring package as an empty,
documented, algorithmic-tagged shell, and lands the D-15A standing guard around
it *before* any helper exists.

## src/ccf/deployment/\_\_init\_\_.py

- Surface: src/ccf/deployment/__init__.py
- Public surface: false
- Change type: added
- Before: absent — there was no home for adopter-facing wiring, so an
  ergonomics helper would have landed wherever it was first needed
- After: an empty, algorithmic-tagged package root whose docstring records the
  SDK-extension citation (CLAUDE.md §6.4/§10), the CINV-03 reading
  ("algorithmic" is no model call, not no I/O), and the D-15A abstraction line
- Why: the phase's defining risk is an ergonomic helper silently deleting a
  whitepaper invariant. The package that will hold every helper states the line
  in its own docstring, and the standing guard has a real, non-vacuous target
  from the moment it is written rather than being retrofitted later
- Migration: none — the package exports nothing yet

**Why this entry is `Public surface: false`, despite being a new module.**
`tools/dump_surface.py` skips any module whose `__all__` is falsy
(`build_surface`: `if not exported: continue`), and this package's `__all__` is
deliberately `[]` — it is a shell. `tools/dump_surface.py --report` confirms it:
zero added, zero removed, zero reshaped. There is therefore no fully-qualified
name to claim and no diff line for 15-21's completeness cross-check to match, so
a `true` classification would fail that check as an unmet claim. The `Surface`
token is the repo-relative path, which can never appear in a manifest diff (diff
entries are dotted names), so the `false`-direction assertion holds too. The
first *export* this package gains is a genuine public-surface addition and is
claimed as `Public surface: true` by whichever plan adds it, under its own
fully-qualified name.

## cinv02-deployment-gates

- Surface: tools/lints/harness_imports.py
- Public surface: false
- Change type: added
- Before: two rules under one AST walk — `cinv02-harness` and
  `cinv02-graph-writer`
- After: a third rule, `cinv02-deployment-gates`, refusing any import of
  `ccf.products.gates` from `ccf.deployment` or any of its submodules, in both
  the `import ccf.products.gates` and `from ccf.products import gates`
  spellings, with no allowlist
- Why: `run_gates` compares the product's declared
  `lineage.operators_invoked` against the engine's `engine_resolved`, and that
  comparison is a real check only because the two values arrive from two
  independent sources. A wiring helper that ran the gate is one step from
  deriving both from one input, at which point the gate compares a value against
  itself — green, tautological, and lineage strict equality (whitepaper §7.6,
  INV-CH7-47) deleted with nothing failing to say so. Gate execution stays in
  adopter code
- Migration: none for existing code — the rule denies one importer and the
  package it denies is new. Anything else may still name `ccf.products.gates`;
  the opposite-direction regression guard in
  `tests/lints/test_deployment_gates_ban.py` proves the ban did not widen

A lint rule can never appear in the manifest diff — `dump_surface.py` walks only
`/src` and `/runtime` — which is why this entry is `Public surface: false` with
a repo-relative path as its `Surface` token. It is recorded here regardless
because D-15 requires the curated log to carry every constraint an adopter or
contributor must act on, and a CI rule that refuses an import is exactly that.
