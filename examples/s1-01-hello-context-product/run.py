"""examples/s1-01-hello-context-product — the thin driver, and nothing else.

Wire ``deployment.py`` into ``spine.py`` and exit. Every fabric call is in
``spine.py``; every domain value is in ``artifacts/*.yaml``; this file is the
three lines that put them together, and it is deliberately not a second spine.

**What the example is.** A KYC analyst at a fictional bank asks *"who ultimately
owns this company, and does any natural person's stake cross the reporting
threshold?"* — a question a vector store over chunked documents structurally
cannot answer, because the answer is not in any passage. A real interest is a
sum over ownership paths: 12.0% held directly plus 60.0% of a holding company
that itself owns 30.0% is 30.0% in total, and no document states 30.0%. The
fabric traverses an ownership chain, aggregates across hops, filters on a
jurisdiction-conditioned threshold, and serves the result as a typed, gated,
replay-ready **Context Product**. It is deterministic, offline, keyless,
model-free — and there is no agent anywhere in it (phase 16 CONTEXT `D-12`).

**The question is ASKED, not configured** (plan `15.5-13`). Which company and as
of which instant are arguments on a typed
:class:`~ccf.products.request.ProductRequest`, validated at the door against the
request surface the product class declares (whitepaper §6.3 *Addressability*,
D-IMPL-98). One product class answers about **any company at any time**. Run
with no arguments and it asks the three questions
``artifacts/questions.yaml`` declares — two companies, two instants, a
controlled experiment; run it with ``--subject`` and it asks one that is in no
artifact at all.

**It asserts nothing, and it prints its work.** The assertions live in
``tests/examples/test_s1_01_output.py``, where a test runner will run them and a
failure can fail a build; ``make example-s1-01`` exiting 0 means the spine
executed, and is not a correctness result. The printed output lives in
``report.py`` beside this file, which carries **no ``--8<--`` marker regions**
and is therefore not published-snippet surface. The Phase 14.1 finding at
``16-CONTEXT.md:392-397`` — that assertion and print lines inflate an example's
apparent integration cost — is about *snippets*, and this design keeps them out
of snippets rather than out of the program. ``--quiet`` restores the silent
path for a caller that wants it.

**Every domain value is loaded from ``artifacts/*.yaml``** and enumerated by
``artifacts/manifest.yaml`` — entity classes, source systems, identifiers, the
ownership threshold, the decimal scale, the screening query, the TTLs. Deleting
the artifacts leaves this example with nothing meaningful to run (CLAUDE.md
§6.4, the No-Hardcoding Rule). ``artifacts/questions.yaml`` is deliberately
**not** in the manifest: a question is caller input, not Control Plane state,
and it has no business in Decision Replay dimension 2 — the same read-side /
write-side split ``artifacts/source-estate.yaml`` records (phase 16 CONTEXT
`D-04`).

**The substrate is a value in two configuration documents, not a fact about
this code.** ``artifacts/manifest.yaml`` declares the backend KIND — with no
DSN, host, path or credential anywhere near it — and
``artifacts/backends.yaml`` declares how that kind's connection settings are
composed, from an environment variable's name or from a per-run rule and never
from a value written down. Change the documents, not the code.

Run it: ``make example-s1-01`` (or
``PYTHONPATH=src:runtime python examples/s1-01-hello-context-product/run.py``).
It needs a reachable server for the declared kind; ``artifacts/backends.yaml``
names the environment variable, and a run that cannot resolve it refuses rather
than falling back.

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
from collections.abc import Sequence

from ccf.products.request import ProductRequest

EXAMPLE_DIR = pathlib.Path(__file__).resolve().parent

# The example directory is not a package, so its three modules find each other
# the way every multi-module example in this suite does.
sys.path.insert(0, str(EXAMPLE_DIR))

import deployment  # noqa: E402
import report  # noqa: E402
import source_estate  # noqa: E402
import spine  # noqa: E402


def run(
    *, root: pathlib.Path, request: ProductRequest | None = None
) -> spine.Assembled:
    """Assemble and serve one ultimate-beneficial-ownership Context Product.

    The wiring is five arguments, one per thing the fabric asks a deployment to
    supply. Π is handed over as a CLASS rather than as a constructed object:
    ``spine.py`` builds it one statement before it binds it, because a plan
    handed over ready-made is a plan no binder can be shown to have been given
    (design E2, D-IMPL-86 as corrected 2026-08-05).

    ``request`` is the question. It defaults to the first question
    ``artifacts/questions.yaml`` declares so that a caller with nothing
    particular to ask still gets a product — never to a subject or an instant
    written down in this file.
    """
    asked = deployment.declared_questions()[0] if request is None else request
    return spine.assemble_and_serve(
        manifest=deployment.MANIFEST,
        connection=deployment.connection(root=root),
        read=deployment.read,
        plan_class=deployment.UltimateBeneficialOwnershipPlan,
        request=asked,
        root=root,
    )


def ask_all(
    *, root: pathlib.Path, requests: Sequence[ProductRequest]
) -> tuple[spine.Assembled, ...]:
    """Ask every question in turn, each against its own fabric under ``root``.

    Each question gets its own scratch directory, and therefore its own graph
    substrate and its own file-backed ArtifactStore. That is not tidiness: it
    is what lets two replay records — and the query sequences they pin — be
    compared side by side without either run having observed the other.
    """
    answered = []
    for index, request in enumerate(requests):
        scratch = root / f"q{index}"
        scratch.mkdir(parents=True, exist_ok=True)
        answered.append(run(root=scratch, request=request))
    return tuple(answered)


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
    """Ask the declared questions, or one the caller composes on the spot.

    ``--subject`` is the whole demonstration in one flag: supply it and the
    fabric answers about a company no artifact in this directory names. The
    three axes are supplied together and none of them is defaulted — a defaulted
    subject is the frozen-answer defect this example was rewritten to remove,
    and a defaulted instant is a clock read wearing a disguise.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Assemble and serve ultimate-beneficial-ownership Context Products"
            " for the questions declared in artifacts/questions.yaml, or for"
            " one question supplied on the command line."
        )
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help=(
            "print nothing; assemble and serve the products and exit. The"
            " default is to print what the fabric did"
        ),
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
    parser.add_argument(
        "--subject",
        default=None,
        metavar="ENTITY_REF",
        help=(
            "ask about this entity instead of the declared questions; requires"
            " --as-of and --decision-instant"
        ),
    )
    parser.add_argument(
        "--as-of",
        default=None,
        metavar="INSTANT",
        help="read the graph as of this ISO-8601 instant (zone required)",
    )
    parser.add_argument(
        "--decision-instant",
        default=None,
        metavar="INSTANT",
        help="produce the answer at this ISO-8601 instant; the TTL runs from it",
    )
    arguments = parser.parse_args(argv)

    if arguments.estate is not None:
        materialise_estate(root=arguments.estate)
        return 0

    composed = (arguments.subject, arguments.as_of, arguments.decision_instant)
    if any(axis is not None for axis in composed) and not all(
        axis is not None for axis in composed
    ):
        parser.error(
            "--subject, --as-of and --decision-instant are supplied together:"
            " a question missing one of its axes is a question nobody asked,"
            " answered anyway"
        )

    requests = (
        deployment.declared_questions()
        if arguments.subject is None
        else (
            deployment.ad_hoc_question(
                subject=arguments.subject,
                asked_at=arguments.as_of,
                decision_instant=arguments.decision_instant,
            ),
        )
    )
    with tempfile.TemporaryDirectory(prefix="ccf-s1-01-") as scratch:
        answers = ask_all(root=pathlib.Path(scratch), requests=requests)
        # Rendered INSIDE the `with` block, deliberately: the file-backed
        # ArtifactStore lives under this root, and the report resolves the
        # replay record and the pinned graph queries out of it. Rendering after
        # the directory is removed would report an unresolvable pin as a
        # missing one.
        if not arguments.quiet:
            for index, answered in enumerate(answers, start=1):
                print(report.render(answered, index=index, total=len(answers)))
            print(report.render_contrast(answers))
    return 0


if __name__ == "__main__":
    sys.exit(main())
