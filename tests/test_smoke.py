"""Scaffold smoke test: both distributed packages import (D-05 Wave 1)."""


def test_ccf_imports() -> None:
    import ccf

    assert ccf.__all__ == []


def test_ccf_runtime_imports() -> None:
    import ccf_runtime

    assert ccf_runtime.__all__ == []
