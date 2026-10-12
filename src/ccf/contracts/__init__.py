# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""Typed contract surface for the CCF SDK.

Every CCF boundary type derives from :class:`ccf.contracts.base.CCFContract`
(whitepaper §6.3 — the Context Product Contract's typed base with
``extra=forbid``; DESIGN.md §2A.2.1). :mod:`ccf.contracts.canonical` is the
single canonical serialization and content-identity utility the whole SDK
compares against.

This package holds mechanism only: no domain values, no thresholds, no
tables (CLAUDE.md §11, CINV-01).
"""

from __future__ import annotations

__all__ = ["base", "canonical", "claims"]
