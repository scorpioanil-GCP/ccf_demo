"""``EmbedderProtocol`` — the text-to-vector seam (D-IMPL-07).

CLAUDE.md §12 (D-IMPL-07: an ``EmbedderProtocol`` with reference adapters,
never one model baked into the fabric) and §11 ("Prefer Protocols over
inheritance"; "Mechanism, not values"). Whitepaper §7.4 makes the reason
structural rather than stylistic: the Similarity determinism contract is
``(corpus_version, embedding_model_version, query, threshold, policy_regime) ->
same result`` (INV-CH7-27), which only means anything if the embedding model
*has* a nameable version that travels into provenance. Hence
:attr:`EmbedderProtocol.model_version` is part of the contract, not metadata a
deployment is trusted to remember.

**This module ships no implementation, deliberately.** Every other pluggable
substrate in the SDK ships a reference impl beside its Protocol (CLAUDE.md
§11), and this one is the exception because the only honest reference embedder
is a model call — which would put a semantic stage inside modules the
Algorithmic ⇄ Semantic Alternation keeps algorithmic (CINV-03), and would make
``pip install ccf`` drag a model runtime behind it. I.1's vector indexes are
conformance-tested against a deterministic hashing fake defined in the test
suite; a deployment supplies its own embedder, and the vendor adapters land
with the semantic surface in a later phase.

Nothing here imports an LLM or embedding SDK, so the module is safe to hold the
algorithmic tag: it declares a shape, it does not call a model. An
*implementation* of this Protocol is a semantic component and belongs in an
untagged module.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

__ccf_mode__ = "algorithmic"

__all__ = ["EmbedderProtocol"]


@runtime_checkable
class EmbedderProtocol(Protocol):
    """Turns text into a fixed-width vector, and names the model that did it."""

    @property
    def model_version(self) -> str:
        """Version identity of the embedding model.

        Composed into the index version an operator pins into provenance
        (INV-CH7-27): re-embedding the same corpus with a different model is a
        different index, and a replay that could not tell them apart would
        reproduce a decision from state that no longer exists.
        """
        ...

    @property
    def dimensions(self) -> int:
        """Width of every vector this embedder produces.

        Fixed and declared rather than inferred from the first call, because a
        vector store's schema has to exist before there is anything to embed.
        """
        ...

    def embed(self, *, text: str) -> tuple[float, ...]:
        """Return the embedding of ``text``, of length :attr:`dimensions`.

        Keyword-only, like every other boundary in the SDK: a positional string
        argument is the one call site where a query and a document can be
        swapped without a type error.
        """
        ...
