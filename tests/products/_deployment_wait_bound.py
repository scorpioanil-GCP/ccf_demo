"""A deployment's manifest declaring a store-creation lock wait, for the marker and lock tests (SEC-020, D-IMPL-378 19 (b)).

Used by ``tests/products/test_deployment_store_creation_lock_bounded.py`` and
``tests/products/test_deployment_marker_serialized_and_stale_refused.py``. Not collected by pytest (no ``test_``
prefix). Every bound a test declares through it is a test-side value, never one the SDK supplies (``D-IMPL-38``).
"""

from __future__ import annotations

import pathlib

#: The manifest and config field decision 19 (b) adds: how long a plain boot waits for a held store-creation lock.
WAIT_SETTING = "store_creation_lock_wait_seconds"


def manifest_declaring_a_wait(manifest: pathlib.Path, seconds: int) -> pathlib.Path:
    """The same deployment, its manifest declaring ``store_creation_lock_wait_seconds``, written beside the original.

    Beside it, so every entry's ``path`` resolves exactly as the original's does: the documents, and so their content
    addresses, are unchanged; the manifest gains one top-level line.
    """
    text = manifest.read_text(encoding="utf-8")
    if not text.endswith("\n"):
        text += "\n"
    declaring = manifest.with_name(f"{manifest.stem}-wait-{seconds}{manifest.suffix}")
    declaring.write_text(f"{text}{WAIT_SETTING}: {seconds}\n", encoding="utf-8")
    return declaring
