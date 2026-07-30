"""``ccf_runtime.workflow`` — the in-SDK Workflow engine (CLAUDE.md §8.1).

SDK-defined (an extension beyond the whitepaper, and it says so). The
package holds ORCH-01's execution half: the async-first state machine that
interprets WorkflowFactory-built handles (:mod:`ccf.workflow.factory`) and
the typed state record it suspends under. The contracts the engine executes
stay in ``/src`` (07-04); execution lives here, in the runtime host package,
per D-14 — the engine is a running thing, and the library a caller imports
must not be able to start one by importing it.

This package is deliberately *not* under ``ccf_runtime.adapters``, so the
CINV-02 lint denies harness imports here exactly as it does in ``/src``: the
engine is harness-neutral at every node (CLAUDE.md §8.1).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

__ccf_mode__ = "algorithmic"
