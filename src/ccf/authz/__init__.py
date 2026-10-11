# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""Authorization primitives that ``src/`` handles require (D-IMPL-353).

The capability, the action vocabulary and the decision contract live here so
that library handles can demand proof of authorization without importing the
runtime (D-29). The gate and the MCP wrapper that MINT capabilities stay in
``runtime/``; minting needs a door, requiring does not.
"""
