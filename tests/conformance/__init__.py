# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""Shared, backend-parametrized Protocol conformance suites (D-16).

One suite per Protocol, run identically against every reference
implementation. Backend-specific tests exist only for substrate quirks; a
semantic that matters is asserted here, once, for all backends.
"""
