# 378-66 — four public docstrings cite the worked examples' nested functions by their qualified names

`D-IMPL-378`, lane `378j-cites`, repair 1.7. Dave ruled on 2026-10-09 at 10:54 MST (recorded on `main` at `f07e558e`),
verbatim: *"Implement the specified documentation, citation-checker and shared-owner fixes."* The citation-checker fix,
as the panel's findings brief specifies it: *"Take bindings only from the cited file's module and class bodies; let
tuple, `for` and `with` targets bind; cap the 'unfollowable member' count at 0 with a test."* No SEC row changes here.

**What changed, and why these docstrings.** The citation checker's `cite03` rule now resolves a `path.py::name`
citation only through a binding in the cited file's module body or in a class body
(`tools/lints/citations.py::_definitions`), so a name bound only inside a function is no longer found. Four public
docstrings cited a function of a worked example by its bare name, and each of those functions is defined inside the
example's `main`: the archived cross-process example's `resolve`, the shipped call site of `refuse_bound_payload`, and
the archived hello-context example's `context_provider`. Each citation now names the enclosing function first,
`main.resolve` and `main.context_provider`: the name Python's `__qualname__` gives each with `<locals>` dropped, and the
form the checker resolves. The example paths are unchanged, so `tools/docs_tests/test_resolver_seam_obligations.py`,
which pins them, reads the same paths.

Documentation only, no behavior change. The manifest `make surface` writes is unchanged, because it records signatures
rather than docstring text, and no signature changed.

## ccf.products.bind

- Surface: ccf.products.bind
- Public surface: true
- Change type: behavior
- Before: the module docstring cited the shipped call site of `refuse_bound_payload` as the archived cross-process example's `resolve`, by its bare name, though `resolve` is defined inside that example's `main`.
- After: documentation only; the behavior is unchanged. The citation is `archive/examples/04-cross-process/producer_child.py::main.resolve`; the example path is the same.
- Why: `D-IMPL-378` repair 1.7 (Dave, 2026-10-09): the citation checker takes bindings only from the cited file's module and class bodies, so a bare name bound inside a function no longer resolves.
- Migration: none.

## ccf_runtime.mcp.egress.ProductResolverProtocol

- Surface: ccf_runtime.mcp.egress.ProductResolverProtocol
- Public surface: true
- Change type: behavior
- Before: the docstring's "Where a working example is" paragraph cited the payload bind's shipped call site as the archived cross-process example's `resolve`, by its bare name, though `resolve` is defined inside that example's `main`.
- After: documentation only; the behavior is unchanged. The citation is `archive/examples/04-cross-process/producer_child.py::main.resolve`; the example path is the same, and the request refusal's citation is untouched.
- Why: `D-IMPL-378` repair 1.7 (Dave, 2026-10-09): the citation checker takes bindings only from the cited file's module and class bodies, so a bare name bound inside a function no longer resolves.
- Migration: none.

## ccf_runtime.mcp.experience.ExperienceProductResolverProtocol

- Surface: ccf_runtime.mcp.experience.ExperienceProductResolverProtocol
- Public surface: true
- Change type: behavior
- Before: the docstring's "Where a working example is" paragraph cited the payload bind's shipped call site as the archived cross-process example's `resolve`, by its bare name, though `resolve` is defined inside that example's `main`.
- After: documentation only; the behavior is unchanged. The citation is `archive/examples/04-cross-process/producer_child.py::main.resolve`; the example path is the same, and the request refusal's citation is untouched.
- Why: `D-IMPL-378` repair 1.7 (Dave, 2026-10-09): the citation checker takes bindings only from the cited file's module and class bodies, so a bare name bound inside a function no longer resolves.
- Migration: none.

## ccf_runtime.mcp.experience.ContextProviderProtocol

- Surface: ccf_runtime.mcp.experience.ContextProviderProtocol
- Public surface: true
- Change type: behavior
- Before: the docstring cited the shipped example that compares the product it is handed with the one it assembled as the archived hello-context example's `context_provider`, by its bare name, though `context_provider` is defined inside that example's `main`.
- After: documentation only; the behavior is unchanged. The citation is `archive/examples/external/00-hello-context/serve.py::main.context_provider`; the example path is the same.
- Why: `D-IMPL-378` repair 1.7 (Dave, 2026-10-09): the citation checker takes bindings only from the cited file's module and class bodies, so a bare name bound inside a function no longer resolves.
- Migration: none.
