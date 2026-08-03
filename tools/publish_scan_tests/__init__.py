"""Unit tests for the D-02 publish-safety gate (`tools/publish_scan.py`).

A real package, mirroring `tools/lints/tests/`, because `testpaths` is the
shipped suite and does not reach `tools/`; CI runs this directory as its own
step, before the gate it implements.
"""
