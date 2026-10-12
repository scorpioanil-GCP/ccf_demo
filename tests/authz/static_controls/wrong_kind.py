# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""STATIC NEGATIVE CONTROL — D-IMPL-353 §9. This file is meant to FAIL mypy.

It is excluded from the package mypy run and checked on its own by
``test_capability_static.py``, which asserts the EXACT diagnostics below.
**It carries no suppression comment and no cast** — that is the control's
whole point: a handler holding a read capability cannot hand it to a write
handle without silencing the type checker, and §4's lint refuses the silencing.

If this file ever type-checks clean, the static tooth is gone.
"""

from __future__ import annotations

from ccf_runtime.authz.capability import (
    ArtifactRead,
    ArtifactWrite,
    Authorized,
    Execute,
    HitlSubmit,
    Register,
)


def artifact_put(authorized: Authorized[ArtifactWrite]) -> None: ...
def hitl_submit(authorized: Authorized[HitlSubmit]) -> None: ...
def engine_execute(authorized: Authorized[Execute]) -> None: ...
def registry_register(authorized: Authorized[Register]) -> None: ...


def a_reader_tries_to_write(read: Authorized[ArtifactRead]) -> None:
    artifact_put(read)        # WRONG-KIND-1
    hitl_submit(read)         # WRONG-KIND-2
    engine_execute(read)      # WRONG-KIND-3
    registry_register(read)   # WRONG-KIND-4
