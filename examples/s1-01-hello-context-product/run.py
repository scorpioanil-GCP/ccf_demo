"""examples/s1-01-hello-context-product — wave-2 placeholder driver.

**Plan 16-05 REPLACES this file at wave 3** with the full seven-step Section 1
driver. It replaces it in place; it does not delete it and recreate it, and
the wave-3 executor should expect to find this file already here.

Why it exists at wave 2 rather than at wave 3. The tree-wide artifact-header
gate (``tests/examples/test_artifact_schema_headers.py``) defines an *example
root* as a directory that directly contains ``run.py``, and closes a two-sided
bijection between example roots and covered ``artifacts/`` directories. Plan
16-02 ships this directory's ``artifacts/`` tree. Without this file in the same
commit the bijection would have a right-side violation — a covered artifact
directory under no example root — from wave 2 until wave 3.

What it does: materialise the declared KYC/UBO source estate under a
caller-supplied output directory, and exit 0. Nothing here reaches CCF's
Context Graph; ``source_estate`` writes an *enterprise source system* and
L1 ingress is what reads it (phase 16 CONTEXT D-04).

It carries no checks and no output of its own (ERGO-16 / phase 16 CONTEXT
D-09). ``tests/examples/test_source_estate.py`` is where the estate's
properties are stated, because that is where a failure can fail a build.
"""

from __future__ import annotations

import argparse
import pathlib
import sys
import tempfile
from typing import Any

import source_estate


def run(*, root: pathlib.Path) -> dict[str, Any]:
    """Materialise the declared estate under ``root`` and return its manifest."""
    return source_estate.generate(source_estate.load_declaration(), root)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Materialise the declared KYC/UBO enterprise source estate as"
            " standalone source-system files (JSONL + SQLite). Nothing this"
            " writes enters CCF's Context Graph."
        )
    )
    parser.add_argument(
        "--out",
        type=pathlib.Path,
        default=None,
        help=(
            "directory to write the estate into; omitted, a scratch directory"
            " is used and discarded"
        ),
    )
    destination = parser.parse_args(argv).out
    if destination is not None:
        run(root=destination)
        return 0
    with tempfile.TemporaryDirectory(prefix="ccf-s1-01-estate-") as scratch:
        run(root=pathlib.Path(scratch))
    return 0


if __name__ == "__main__":
    sys.exit(main())
