"""LLM client seam for the SDK's semantic stages.

SDK-defined extension (CLAUDE.md §11, D-IMPL-09): the whitepaper commits to the
Algorithmic - Semantic Alternation (§7.6.6) but not to a model-access API. The
SDK routes every model call through a Protocol so that (a) vendor SDKs stay
behind one seam and (b) CINV-03 has a single crisp import target — a module
tagged ``__ccf_mode__ = "algorithmic"`` may not import this package.

This is the Protocol's home only; the concrete vendor adapters land with the
semantic stages that need them, and are the one place ``anthropic`` and peers
may be imported (see ``tools/lints/harness_imports.py``).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

__all__ = ["LLMClientProtocol"]


@runtime_checkable
class LLMClientProtocol(Protocol):
    """Structural contract every semantic-stage model client satisfies.

    Kept deliberately minimal at I.1: it exists so the alternation invariant has
    something to name. The generation surface (messages, citations per
    whitepaper §7.10.3, model-version capture for Decision Replay dimension 3)
    is filled in by the plan that ships the first semantic stage.
    """

    @property
    def model_version(self) -> str:
        """Exact model identifier recorded in the Decision Replay record."""
        ...
