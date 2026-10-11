# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""Unit tests for the D-02 publish-safety gate (`tools/publish_scan.py`).

A real package, mirroring `tools/lints/tests/`, because `testpaths` is the
shipped suite and does not reach `tools/`; CI runs this directory as its own
step, before the gate it implements.
"""
