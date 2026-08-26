"""The client. It asks the question, and it prints the SPECIFICATION beside
the RESULTING JSON.

[ADAPT] all of it. [MECHANISM] nothing — this file makes no fabric call the
spine does not.

**Why the specification is printed at all, and printed first.** A Context
Product is a *specified* thing: the document declares what the product is,
which store it binds to, which operators run, how it decays and when it stops
being servable — and the JSON below the separator is the dataset that document
describes. Printing one without the other shows a reader half of what a Context
Product is. Pass ``--spec brief`` once the document is familiar; it prints the
front matter and the operator step table, which are the two parts a reader
returns to.

**The run goes through the assembler seam, deliberately.** It builds the
request, constructs ``examples/cp-00-institutional-holders/assembler.py::HoldersAssembler`` and calls its
``assemble`` — it does not call the spine directly. Routing the client through
``src/ccf/agents/assembler.py::ContextAssemblerProtocol`` is a substantial part
of what makes this example a pressure test rather than a demonstration: the
seam had never been exercised by a shipped example, and an example that reaches
past it would have proved nothing about it.

**The threshold is the caller's, and it is a REQUEST parameter — not
configuration.** The product is assembled against the number at the moment it
is asked; two thresholds are two products with two content addresses.
``--min-position`` is therefore what a *client* sends. Omitted, this file asks
the demonstration question declared in ``artifacts/question.yaml`` — scenario
material — so the example runs with no arguments and a reader sees the fabric
work before they have to invent a number. **That default lives in the artifact,
not here and not in the Makefile.** The parameter stays REQUIRED with no
default in the contract: a request without one is refused as
``missing-required-parameter`` before anything is assembled. A CLI convenience
and a contract obligation are different things and this file does not conflate
them.

This module carries **no marker region**, so not one printed line is
published-snippet surface. The governance transcript is behind ``--explain``.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# This example is a directory of modules rather than a package, so its own
# module tree goes on the path before its modules are imported.
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import assembler  # noqa: E402
import deployment  # noqa: E402

from ccf.agents.errors import AssemblyRefused  # noqa: E402
from ccf.contracts.canonical import content_hash  # noqa: E402
from ccf.products.request import ProductRequestViolation  # noqa: E402

#: The two headings ``--spec brief`` prints, in this order. Named rather than
#: sliced by line number: a document that grows a section stays printable.
BRIEF_SECTIONS = ("### 0.4 Front matter", "### D.2 Operator step table")

SEPARATOR = "=" * 78


class _Recorder:
    """Holds whatever one assembly produced, so the client can print it.

    The assembler's return type is pinned to the governed
    ``src/ccf/agents/assembler.py::AssemblyOutcome``, which carries the payload
    and the assembly's governance and — correctly — not the served vessel. The
    content address, the debt figure and the replay reference belong to the
    product, so the client observes the run to reach them rather than asking
    the seam to widen.
    """

    def __init__(self) -> None:
        self.seen: object = None

    def __call__(self, assembled: object) -> None:
        self.seen = assembled


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Institutional holders of one issuer, over a position you choose."
    )
    parser.add_argument(
        "--min-position",
        type=int,
        default=None,
        help=(
            "return managers whose reported position is at or above this."
            " Omitted, the demonstration question in artifacts/question.yaml"
            " is asked instead"
        ),
    )
    parser.add_argument("--as-of", help="the instant to ask as of, ISO-8601 with a zone")
    parser.add_argument(
        "--spec",
        choices=("full", "brief"),
        default="full",
        help="print the whole specification, or its front matter and step table",
    )
    parser.add_argument(
        "--explain", action="store_true", help="print the governance transcript"
    )
    return parser.parse_args()


def specification(*, brief: bool) -> str:
    """The specification document, whole or in the two parts."""
    text = deployment.SPEC.read_text(encoding="utf-8")
    if not brief:
        return text
    lines = text.splitlines()
    parts = [lines[0]]
    for heading in BRIEF_SECTIONS:
        parts.append(_section(lines, heading))
    return "\n\n".join(parts)


def _section(lines: list[str], heading: str) -> str:
    """One heading's block, up to the next heading at its level or above."""
    depth = len(heading) - len(heading.lstrip("#"))
    start = lines.index(heading)
    for offset, line in enumerate(lines[start + 1 :], start=start + 1):
        if line.startswith("#") and len(line) - len(line.lstrip("#")) <= depth:
            return "\n".join(lines[start:offset]).rstrip()
    return "\n".join(lines[start:]).rstrip()


def main() -> int:
    args = parse_args()

    # The caller's number, or the demonstration's if this run supplied none.
    minimum = args.min_position
    if minimum is None:
        minimum = deployment.demonstration_threshold()

    print(specification(brief=args.spec == "brief"))
    print(f"\n{SEPARATOR}\nTHE DATASET THE SPECIFICATION ABOVE DESCRIBES\n{SEPARATOR}\n")

    recorder = _Recorder()
    with tempfile.TemporaryDirectory() as scratch:
        root = Path(scratch)
        product = assembler.HoldersAssembler(
            config=deployment.CONFIG,
            root=root,
            connection=deployment.connection(root=root),
            read=deployment.read,
            plan_class=deployment.plan_class(),
            observer=recorder,
        )
        try:
            outcome = product.assemble(
                request=deployment.request(
                    parameters={deployment.THRESHOLD_PARAMETER: minimum},
                    asked_at=(
                        datetime.fromisoformat(args.as_of) if args.as_of else None
                    ),
                ),
                perspective=deployment.perspective(),
                tenant_id=deployment.tenant_id(),
            )
        except AssemblyRefused as refused:
            # BRANCHED ON AS DATA. The seam can only report a governed refusal
            # by raising, but the violation itself is a typed value the
            # observer already holds, so what is printed comes from the value
            # rather than from the exception's message.
            seen = recorder.seen
            if isinstance(seen, ProductRequestViolation):
                print(f"refused: {seen.reason} — {seen.key}")
                return 1
            raise refused

        print(json.dumps(dict(outcome.payload), indent=2, sort_keys=True))
        report(recorder.seen, outcome, explain=args.explain)
    return 0


def report(assembled: object, outcome: object, *, explain: bool) -> None:
    """Print what a plain SELECT would not have told you."""
    served = assembled.served  # type: ignore[attr-defined]
    product = served.product
    debt = product.debt

    print("\nWhat a plain SELECT would not have told you:")
    print(f"   context debt D_c   {debt.debt:.4f}  ->  {debt.signal.value}")
    print(
        f"                      (F={debt.factors.freshness:.4f} from the reported"
        f" quarter end against the declared half-life)"
    )
    print(
        "   policy version     "
        + ", ".join(sorted(product.lineage.policy_bundle_versions))
    )
    print(f"   content address    {content_hash(product)}")
    print(f"   replay record      {served.replay_ref.content_address}")
    print(f"   assembled by       {outcome.assembler_id}@{outcome.assembler_version}")  # type: ignore[attr-defined]
    print(f"   debt profile       {outcome.halflife_debt_profile}")  # type: ignore[attr-defined]

    if explain:
        record = assembled.record  # type: ignore[attr-defined]
        print("\n--- governance transcript")
        print(f"   operators invoked  {sorted(product.lineage.operators_invoked)}")
        # The anchor and the mode are two different facts and the smaller
        # example's transcript prints the first under the second's label.
        # `ContextProductContract` carries no `assembly_mode`; the replay
        # record's dimension 3 does, and that is where it is read from.
        print(f"   ttl anchor         {product.ttl_anchor}")
        print(f"   assembly mode      {record.model_version.assembly_mode}")
        print(f"   graph snapshot at  {product.lineage.graph_snapshot_at.isoformat()}")
        print(f"   expires at         {product.expires_at.isoformat()}")
        print(f"   completeness C     {debt.factors.completeness}")
        print(f"   semantic consist.  {debt.factors.semantic_consistency}")
        print(f"   consulted          {outcome.consultations}")  # type: ignore[attr-defined]
        print(f"   skills in force    {outcome.skill_set_in_force}")  # type: ignore[attr-defined]


if __name__ == "__main__":
    raise SystemExit(main())
