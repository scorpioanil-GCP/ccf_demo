"""Populate this example's deployment from its declared signal-batch input.

The pre-boot seed program `D-IMPL-245` amendment 2 (Dave, 2026-09-03) names,
step for step: (1) read a committed, declarative signal-batch artifact —
``signal-batch.yaml`` beside this file; (2) open the deployment's graph through
the existing approved write path — ``load_config_and_boot`` with the connection
the deployment's own ``binding.yaml`` states; (3) ingest through the **single
writer** — ``booted.handle.worker.ingest``, the only handle that writes to L3
(CLAUDE.md §10); (4) close the writer cleanly — in a ``finally``, so the door
that boots next can take the writer; (5) then run the existing ``inprocess:``
and ``mcp+stdio:`` legs. Steps 1–4 are this program; step 5 is the README's two
documented commands, which ``make example-hw1`` and ``make example-hw1-mcp``
run after this program by prerequisite.

**Declared input, not a hidden bootstrap.** Nothing in ``src/``, ``runtime/``,
``deployment/binding.yaml`` or the in-process adapter knows this program exists.
The in-process adapter's contract is that it *boots* a deployment somebody has
already populated, and this is the somebody: an example-local program a reader
runs once, whose whole input is the document next to it. The populated store it
leaves behind is generated state and stays uncommitted (``deployment/.gitignore``).

**Why it lives in ``runner/`` and is not ``run.py``.**
``tests/examples/test_client_example_purity.py::reader_visible_modules`` walks
the example root with a non-recursive ``glob("*.py")`` whose permitted import
set is ``{ccf.client}``; this program imports ``ccf.deployment``, so it lives one
directory down where the reader-visible surface stays ``consume.py`` alone.
``tests/examples/test_artifact_schema_headers.py`` treats any directory holding
a ``run.py`` as an example root demanding an ``artifacts/`` directory, so this
file is not named that. ``deployment/`` may hold one Python module (the
projection, ``D-IMPL-141`` A.3) and ``server/`` exactly two, so neither is a
legal home either. The same two gates put ``examples/hw1-harness-clients/runner/drive.py``
where it is.

**No arguments.** The program seeds the deployment beside it, so a copied
example seeds its own copy — ``tests/examples/test_hw1_two_transports.py`` runs
this file out of a temporary copy and reaches that copy's deployment.
"""

from __future__ import annotations

import pathlib
import shutil
import sys

from ccf.client.adapters.binding_document import load_binding_document
from ccf.controlplane.artifacts import SIGNAL_BATCH, load_artifact
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment import load_config_and_boot

#: The deployment this program populates: the one beside it, never an argument.
DEPLOYMENT = pathlib.Path(__file__).resolve().parents[1] / "deployment"

#: The declared input. Every id and instant the fabric will record is in it.
DOCUMENT = pathlib.Path(__file__).with_name("signal-batch.yaml")

#: What a populated deployment leaves on disk — the three names
#: ``deployment/.gitignore`` lists, and nothing else. Removed before every run
#: so the store is rebuilt from the document alone, which is what makes two
#: consecutive runs print the same content address.
GENERATED_STATE = ("graph.sqlite3", "graph.sqlite3-*", "artifact-store")


def clear_generated_state(deployment: pathlib.Path) -> None:
    """Remove the ignored store files so the seed starts from an empty fabric."""
    for pattern in GENERATED_STATE:
        for path in deployment.glob(pattern):
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()


def main() -> int:
    """Seed ``DEPLOYMENT`` from ``DOCUMENT`` through the single writer."""
    clear_generated_state(DEPLOYMENT)
    batch = load_artifact(DOCUMENT.read_text(encoding="utf-8"), SIGNAL_BATCH)

    booted = load_config_and_boot(
        DEPLOYMENT / "ccf_config.yaml",
        registry=ControlPlaneRegistry(),
        # The binding's own connection, never a recomposed one: `binding.yaml`
        # is the one place the graph's location is decided.
        connection=load_binding_document(DEPLOYMENT).connection,
    )
    try:
        if batch.tenant_id != booted.tenant_id:
            print(
                f"refused: {DOCUMENT.name} declares tenant {batch.tenant_id!r}"
                f" but the deployment booted as {booted.tenant_id!r}",
                file=sys.stderr,
            )
            return 2
        for envelope in batch.envelopes:
            booted.handle.worker.ingest(envelope)
    finally:
        # The load-bearing line: releases the single writer so the transport
        # that boots next does not raise `SingleWriterViolation`.
        booted.handle.close()

    # Reported relative to the working directory (the repository root, when run
    # as documented); a copy seeded from elsewhere reports its absolute path.
    try:
        where = DEPLOYMENT.relative_to(pathlib.Path.cwd()).as_posix()
    except ValueError:
        where = DEPLOYMENT.as_posix()
    print(f"seeded {len(batch.envelopes)} envelope(s) into {where}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
