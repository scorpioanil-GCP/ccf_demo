# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""Cross-process proofs: real subprocesses, real loopback HTTP (D-15/D-16).

A package rather than a bare directory because the child server entry points
under :mod:`crossproc.servers` are imported by the parent tests — the same
builder that the child serves is the one the parent recomputes its expected
value from, so there is no second copy to drift.
"""
