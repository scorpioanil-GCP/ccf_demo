"""The LangGraph harness adapter (CLAUDE.md §7.3; D-IMPL-24).

One of the v0 reference bindings of
:class:`~ccf.harness.protocol.HarnessAdapterProtocol`, and the one where the
adapter — not the harness — owns the execution topology. See
:mod:`ccf_runtime.adapters.langgraph.adapter` for the four-seam binding, for
what this adapter deliberately cannot do, and for the D-IMPL-17 boundary
between this *harness* seam and the distinct orchestration seam that is Phase
I.4 scope.

Importing this package imports ``langgraph``. That is legal exactly here and
nowhere else outside ``ccf_runtime.adapters.*`` (``cinv02-harness``,
D-IMPL-53), and it is why the conformance leg for this harness is guarded by
the ``langgraph`` extra rather than assumed present.
"""

from __future__ import annotations

from ccf_runtime.adapters.langgraph.adapter import (
    AGENT_HASH_METADATA_KEY,
    HARNESS_ID,
    MODEL_METADATA_KEY,
    USAGE_METADATA_KEY,
    HarnessState,
    LangGraphAdapter,
    LangGraphCarrier,
)

__all__ = [
    "AGENT_HASH_METADATA_KEY",
    "HARNESS_ID",
    "MODEL_METADATA_KEY",
    "USAGE_METADATA_KEY",
    "HarnessState",
    "LangGraphAdapter",
    "LangGraphCarrier",
]
