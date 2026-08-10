"""examples/s1-01-hello-context-product — the thin driver, and nothing else.

Wire ``deployment.py`` into ``spine.py`` and exit. Every fabric call is in
``spine.py``; every domain value is in ``artifacts/*.yaml``; this file is the
three lines that put them together, and it is deliberately not a second spine.

**What the example is.** A KYC analyst at a fictional bank asks *"who ultimately
owns Acme Corporation?"* — a question a vector store over chunked documents
structurally cannot answer, because the answer is not in any passage. Jane Doe's
real interest is 12.0% directly plus 60.0% of a holding company that itself owns
30.0%, which is 30.0% in total and crosses the regime's 25.0% threshold. No
document states 30.0%. The fabric traverses an ownership chain, aggregates
across hops, filters on a jurisdiction-conditioned threshold, and serves the
result as a typed, gated, replay-ready **Context Product**. It is deterministic,
offline, keyless, model-free — and there is no agent anywhere in it (phase 16
CONTEXT `D-12`).

**It asserts nothing and prints nothing** (`D-09`). Its assertions live in
``tests/examples/test_s1_01_output.py``, where a test runner will run them and a
failure can fail a build. ``make example-s1-01`` exiting 0 means the spine
executed; it is not a correctness result.

**Every domain value is loaded from ``artifacts/*.yaml``** and enumerated by
``artifacts/manifest.yaml`` — entity classes, source systems, identifiers, the
ownership threshold, the decimal scale, the screening query, the TTLs, the
temporal boundary, the subject of the question itself. Deleting the artifacts
leaves this example with nothing meaningful to run (CLAUDE.md §6.4, the
No-Hardcoding Rule).

**The substrate is a value in a configuration document, not a fact about this
code.** ``artifacts/manifest.yaml`` says ``backend: sqlite`` — a kind, with no
DSN, host, path or credential anywhere near it. Change the document, not the
code.

Run it: ``make example-s1-01`` (or
``PYTHONPATH=src:runtime python examples/s1-01-hello-context-product/run.py``).

``--estate`` materialises the declared enterprise source estate instead — the
world that exists before any fabric does, which ``artifacts/events.yaml``
selects from. Nothing it writes enters CCF's Context Graph (phase 16 CONTEXT
`D-04`).
"""

from __future__ import annotations

import argparse
import pathlib
import sys
import tempfile

EXAMPLE_DIR = pathlib.Path(__file__).resolve().parent

# The example directory is not a package, so its three modules find each other
# the way every multi-module example in this suite does.
sys.path.insert(0, str(EXAMPLE_DIR))

import deployment  # noqa: E402
import source_estate  # noqa: E402
import spine  # noqa: E402


def run(*, root: pathlib.Path) -> spine.Assembled:
    """Assemble and serve one ultimate-beneficial-ownership Context Product."""
    return spine.assemble_and_serve(deployment.KycDeployment(), root=root)


def materialise_estate(*, root: pathlib.Path) -> dict[str, object]:
    """Write the declared enterprise source estate under ``root``.

    Separate from :func:`run` because it is a separate thing: the estate is an
    enterprise source system, not CCF state. ``artifacts/events.yaml`` is the
    SELECTION of it this Context Product needs, expressed as L1 envelopes —
    CCF reads an estate and assembles selectively, and never mirrors one
    wholesale into its own graph (`D-04`).
    """
    return source_estate.generate(source_estate.load_declaration(), root)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Assemble and serve one ultimate-beneficial-ownership Context"
            " Product from the declared KYC/UBO artifacts."
        )
    )
    parser.add_argument(
        "--estate",
        type=pathlib.Path,
        default=None,
        metavar="DIR",
        help=(
            "materialise the declared enterprise source estate into DIR and"
            " exit, instead of running the fabric"
        ),
    )
    destination = parser.parse_args(argv).estate
    if destination is not None:
        materialise_estate(root=destination)
        return 0
    with tempfile.TemporaryDirectory(prefix="ccf-s1-01-") as scratch:
        run(root=pathlib.Path(scratch))
    return 0


if __name__ == "__main__":
    sys.exit(main())
