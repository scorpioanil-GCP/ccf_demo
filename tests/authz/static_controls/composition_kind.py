"""mypy --strict control: a door kind cannot be minted at composition (D-IMPL-354).

The overloads of ``mint_at_composition`` accept ``ReplayMint`` and ``Register``
and nothing else, so each marked line below is a type error; the two unmarked
calls are the composition kinds and are clean. No suppression in this file.
"""

from __future__ import annotations

from ccf.authz.capability import (
    ArtifactWrite,
    HitlSubmit,
    Register,
    ReplayMint,
    mint_at_composition,
)


def composition_roots() -> None:
    mint_at_composition(ReplayMint, tenant="t", principal="p", resource="ccf.decision-replay", decision_id="d")
    mint_at_composition(Register, tenant="t", principal="p", resource="t/policy/bundle", decision_id="d")
    mint_at_composition(ArtifactWrite, tenant="t", principal="p", resource="c/n", decision_id="d")  # COMPOSITION-KIND-1
    mint_at_composition(HitlSubmit, tenant="t", principal="p", resource="e", decision_id="d")  # COMPOSITION-KIND-2
