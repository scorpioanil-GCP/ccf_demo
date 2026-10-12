# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""Unit tests for the CCF invariant lints (D-06: each checker gets its own).

A package (not a bare test directory) so that pytest resolves the repo root as
the import root and `from tools.lints...` works regardless of how pytest is
invoked.
"""
