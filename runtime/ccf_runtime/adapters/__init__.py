"""Harness adapter packages — the one module path where a harness may be imported.

SDK-defined extension (CLAUDE.md §7.3), not whitepaper-derived: the whitepaper
specifies no harness binding.

**What lives here.** Implementations of
:class:`~ccf.harness.protocol.HarnessAdapterProtocol`, one sub-package per
harness (``claude_agent``, and — as later plans land them — ``langgraph`` and
``adk``). CLAUDE.md §7.3 places harness bindings in
``runtime/adapters/<harness>/`` and nowhere else, and the ``cinv02-harness``
lint enforces exactly that scope through the ``HARNESS_ADAPTER_MODULES``
module-path carve-out (D-IMPL-53, D-24). The carve-out is dot-bounded: a
sibling named ``adapters_evil`` is still denied, and every other package under
``ccf_runtime`` — ``a2a``, ``cdc``, ``mcp`` — remains at zero harness imports.

**What does not live here.** No agent loop. CCF layers onto a harness as the
trust-and-control plane; it never absorbs the loop and does not ship one
(CLAUDE.md §7.3). An adapter translates between CCF values and whatever its
harness natively wants; the harness then runs its own loop with them.

**This module imports no harness.** The carve-out exists for the leaf adapter
modules that need it, not for the package root, and widening the surface that
touches a vendor SDK past what the binding actually requires is the drift the
carve-out was narrowed to prevent (D-21).

Adapter modules deliberately do **not** carry ``__ccf_mode__ = "algorithmic"``
(CINV-03): they bind a harness that reaches a model, which makes them the
semantic boundary of the Algorithmic ⇄ Semantic Alternation rather than an
algorithmic module.
"""

from __future__ import annotations

__all__: list[str] = []
