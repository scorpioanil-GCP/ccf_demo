"""The adopter-facing wiring package — how a deployment is assembled, not run.

SDK-defined mechanism (CLAUDE.md §6.4 and §10). The whitepaper specifies the
Control Plane artifacts and the invariants that hold over them; it does not
specify the wiring that loads those artifacts and hands the assembled pieces to
a fabric. That wiring is the SDK's own extension, and this package is its home.
Nothing here is whitepaper-derived, and nothing here may quietly become an
implementation of something the whitepaper *does* specify.

The package ships empty on purpose. It exists from the moment the phase's
standing guard exists (``tests/products/test_gate_independence.py``) so that the
guard has a real, non-vacuous target rather than being retrofitted around
helpers already written.

CINV-03: "algorithmic" means no model call, not no I/O
------------------------------------------------------

This package is tagged ``__ccf_mode__ = "algorithmic"`` and it will read files —
artifact documents, manifests, schema bundles. That is not a contradiction, and
the reading is written down here so the next contributor does not have to
re-derive it.

The CINV-03 checker, :mod:`tools.lints.algorithmic`, says exactly one thing: a
tagged module may not import the LLM client Protocol (``ccf.llm``) or a vendor
model SDK, at module scope or deferred inside a function. It says nothing at all
about the filesystem. The invariant is Algorithmic ⇄ Semantic Alternation —
LLMs never see raw signal (whitepaper §7.6.6) — and file I/O is orthogonal to
it. Two precedents in the tree carry the tag while doing I/O:

* ``src/ccf/boot.py:55`` carries the tag while opening SQLite files.
* ``src/ccf/controlplane/artifacts.py:47`` carries the tag while importing
  ``yaml`` to parse artifact documents.

The abstraction line: D-15A and the ``run_gates`` worked example
----------------------------------------------------------------

The defining risk of an ergonomics package is that a convenience helper
silently deletes a whitepaper invariant. The worked example is
:func:`ccf.products.gates.run_gates`.

That function takes the engine's resolved operator set *separately* from the
product's own lineage claim::

    run_gates(candidate, engine_resolved=..., now=..., registry=...,
              product_class=...)

``candidate.lineage.operators_invoked`` is what the producer *declares*;
``engine_resolved`` is what the projection engine *observed itself running*.
Lineage strict equality (whitepaper §7.6, INV-CH7-47) is a real check precisely
because those two values arrive from two independent sources. A helper that
computed both from one input — one plan, one execution record, one convenience
argument — would make the gate compare a value against itself. It would still
pass. It would be tautological, and the invariant would be gone with no failing
test to say so.

So this package draws its line here, operationally and without exception:

* No module in this package may import ``ccf.products.gates``. This is enforced
  by the ``cinv02-deployment-gates`` lint rule in
  ``tools/lints/harness_imports.py``, which takes no allowlist.
* No function in this package may accept a ``ProjectionExecution`` and return a
  ``ProductLineage`` — that signature *is* the collapse, whatever it is called.
* Gate execution stays in adopter code. This package wires a deployment
  together; it does not run the deployment's validation gates on the adopter's
  behalf.

Algorithmic package (CINV-03).
"""

from __future__ import annotations

__ccf_mode__ = "algorithmic"

__all__: list[str] = []
