# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""Scaffold smoke test: both distributed packages import (D-05 Wave 1)."""


def test_ccf_imports() -> None:
    import ccf

    assert ccf.__all__ == []


def test_ccf_runtime_imports() -> None:
    import ccf_runtime

    assert ccf_runtime.__all__ == []
