"""The typed contract base every CCF boundary type derives from.

Whitepaper §6.3 specifies the Context Product Contract as a typed base whose
validation is total at the boundary — unknown fields are a contract violation,
not an extension point. DESIGN.md §2A.2.1 carries that discipline down to the
ingress envelope as well, per the D-IMPL-33 ruling, and D-IMPL-01 fixes the
realization as Pydantic v2.

Two configuration choices are load-bearing and are therefore fixed here rather
than per-model:

``extra="forbid"``
    Validation happens at the boundary, never deferred (CLAUDE.md §11). An
    unexpected field means the producer and the consumer disagree about the
    contract, which is exactly the condition replay cannot survive silently.

``frozen=True``
    Contracts are values, not mutable state. Freezing is what lets a contract
    instance be canonically serialized (:mod:`ccf.contracts.canonical`) and
    content-addressed (D-IMPL-26) with the guarantee that the bytes still
    describe the object that was validated.

``hide_input_in_errors=True``
    A ``ValidationError`` names the field and the reason, never the value it
    refused (``SEC-024``, ``D-IMPL-368``/``D-IMPL-369`` choice C; CLAUDE.md
    §11 "typed contracts at every boundary"). Its ``str()`` and ``repr()`` are what reaches a log or a
    transport's error text, and a refused value is exactly where a credential,
    a subject or a caller's parameter lands. ``.errors()`` still carries the
    input; nothing may render it to a log.

This module is algorithmic (CINV-03): it performs no semantic work and must
never acquire an LLM dependency.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

__ccf_mode__ = "algorithmic"

__all__ = ["CCFContract"]


class CCFContract(BaseModel):
    """Frozen, closed-world base for every typed CCF boundary contract.

    Whitepaper §6.3 (typed contract base, ``extra=forbid``); DESIGN.md
    §2A.2.1; D-IMPL-01 (Python/Pydantic v2 target).

    Subclasses inherit total boundary validation and immutability. They add
    fields; they do not relax the configuration — a subclass that re-opens
    ``extra`` or unfreezes the model is a contract defect.
    """

    model_config = ConfigDict(
        extra="forbid", frozen=True, hide_input_in_errors=True
    )
