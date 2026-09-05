"""The client. It asks the question through `ProductClient` and prints the answer.

[ADAPT] all of it. [MECHANISM] nothing — this file makes no fabric call the
spine does not, and it assembles nothing itself.

**THIS IS THE FIRST OF TWO THIN CALLERS OVER ONE STANDALONE ASSEMBLER**
(`D-21`). The second is the MCP door. Neither owns the question: it is composed
once, in `deployment.demonstration_request`, so two callers that disagreed would
disagree about the TRANSPORT and never about what was asked — which is the whole
of what `CFT-G14`'s equivalence proof can be worth.

**THE CONSUME PATH IS `ProductClient(product_id=…, adapter=…)`** — the documented
direct-adapter constructor at `src/ccf/client/client.py::ProductClient.__init__`,
ruled at Gate 1 (`D-IMPL-225` amendment 2). There is **no
`GET /tenant/class/version` anywhere in this example**, and no HTTP path of any
kind: `D-20` rules the consume path a client call or an MCP tool ask and never a
resource URL. Why the shipped in-process adapter could not be used, measured, is
in `transport.py`'s docstring.

**AND THIS IS NOT hw1's CLAIM.** cp-04 is the first `cp-*` rung to consume
through the client seam at all, but the property it demonstrates is `D-21`'s —
one assembler, two callers. The `hw1-*` trees prove a different one, *"same
`consume.py`, different `CCF_BINDING`, identical `Result`"*, and this file
supplies its adapter in code rather than resolving one from a binding, so it does
not re-prove it (`D-IMPL-225`).

**`--max-depth` IS THE FLAG THIS RUNG EXISTS FOR.** Four properties ride on it
and each is gated separately: absent takes the **declared** default; a depth
this estate cannot exhibit is **served**, with the depth reached carried beside
the depth asked; a depth above the **backend's technical capability** is refused
by name with authority `technical` and answered at no narrower depth; and two
depths are **two content addresses**, because they are two answers to two
different questions.

SUPERSEDED 2026-09-04 (`24.6-L-01`, `D-IMPL-251` C5): the first property read *"above the ceiling is refused by name and never clamped"*.
The ceiling it named was a measurement of how deep this estate goes, so a
request at 8 was refused for exhibiting nothing rather than for exceeding
anything; it is served now. What survives whole is the refusal to answer a
narrower question than the one asked — it applies where there is a genuine
limit.

**NEITHER FIGURE IS TYPED INTO THIS FILE.** The default is Control Plane state
in `ccf_config.yaml`; the technical limit is the graph leg's own capability,
read off the substrate through `ccf.graph.protocols::TraversalDepthCapability`.
Both are interpolated into the help text and neither is written here. A copy of
either in an argparse default or in a help string is the No-Hardcoding Rule
firing (CLAUDE.md §6.4), and it is the same defect twice over: an edit would
move the walk and leave the help text lying about it.

**THE WALK IS A NEIGHBORHOOD, NOT A DIRECTED DESCENDANT TREE**, and nothing this
file prints says otherwise (`D-36`). `TraversalNeighborhood` adds both
`subject→object` and `object→subject` for every traversable edge, so *depth* here
is hops through undirected adjacency. Measured over the demonstration anchor the
operator serves 20 / 22 / 22 nodes at depths 1 / 2 / 3 where a directed
parent→child tree gives 20 / 21 / 22 — the one divergent node arrives at depth 2
through cycle 1's closing edge. Everything demonstrated sits at the declared
default, where the two agree.

**`--role` SHIPS BECAUSE IT WAS MEASURED TO CHANGE WHAT IS SEALED, AND THAT IS
THE ONLY REASON IT SHIPS** (`D-IMPL-231` part 3). Dave: *"A flag that changes
nothing is `D-IMPL-228` again"* — the nine-row fiction in argv form — and *"don't
leave a switch that cannot fail."* So the test was the **content address**, not
a field or an ordering: two roles that sealed identically would have changed
nothing that survives. Measured against the estate at the demonstration anchor
and the declared default depth, `credit-officer` seals to
`205ae0658ea626982b9d2923d81a226a00899b0c43ba74bbae4dfea8a140d498` with 22
members detailed and `kyc-analyst` to
`838afbb037a8ca820a2854b1ac7eedd296262508ce00d747369bf48ee6077ea8` with 0. The
measurement is a standing check —
`tests/examples/test_cp_04_two_callers.py::test_the_two_declared_roles_seal_to_different_content_addresses`
— rather than a figure in this docstring, so a build in which the two roles
converge goes red rather than leaving this paragraph lying. **`--principal` is
still NOT shipped**, on exactly the same rule and for want of exactly the same
measurement (§B.2's `[TBC — identity and access]`).

**`--asked-at` PINS THE TRANSCRIPT.** The demonstrated run assembles over the
instant `artifacts/question.yaml` names, so the printed output reproduces against
a quiescent ledger for that run. A reader whose numbers differ has RE-DERIVED,
not replayed, and the most likely reason is that the ledger moved.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

from ccf.agents.errors import AssemblyRefused  # noqa: E402
from ccf.client.client import ProductClient  # noqa: E402
from ccf.client.result import Result  # noqa: E402
from ccf.client.wire import TransportAdapter  # noqa: E402

import deployment  # noqa: E402
import projection  # noqa: E402  (its finding-type token, never a literal here)
import transport  # noqa: E402
import assembler  # noqa: E402  (loaded by transport; its constants name the implementation that ran HERE)


def _parser() -> argparse.ArgumentParser:
    """The command surface. **Every parameter is optional.**

    Omitted, each falls back to the demonstration question declared in
    `artifacts/question.yaml`, so the example runs from a cold shell with no
    arguments. A request parameter is the CALLER's; a build tool and a command
    line are request channels, not deployment configuration.
    """
    # READ FROM THE DOCUMENT AND OFF THE SUBSTRATE, INTERPOLATED INTO THE
    # HELP. Not restated. The default is Control Plane state; the technical
    # limit is the graph leg's own capability, read through
    # `ccf.graph.protocols::TraversalDepthCapability` — so neither number is
    # typed into this file and a change to either moves the help text with it.
    default_depth = deployment.declared_depth_default()
    capability = deployment.traversal_depth_capability()
    roles = deployment.declared_roles()

    parser = argparse.ArgumentParser(
        description=(
            "Walk one corporate family from an anchor LEI and serve the tree,"
            " every node's FIBO class chain, and the cycles it contains as"
            " findings."
        )
    )
    parser.add_argument(
        "--lei",
        help=(
            "the anchor. Defaults to the demonstration anchor in"
            " artifacts/question.yaml. An anchor that resolves to no entity is"
            " a 404 and never an empty payload."
        ),
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        help=(
            f"how many hops of the family NEIGHBORHOOD to walk from the anchor."
            f" Omitted, the DECLARED default of {default_depth} applies, read"
            f" from ccf_config.yaml and never invented at serve time. A depth"
            f" this estate cannot exhibit is SERVED — the findings carry the"
            f" depth reached beside the depth asked. Above"
            f" {capability.max_traversal_depth}, the technical capability of"
            f" {capability.capability_identity}, the request is refused BY NAME"
            f" with authority `technical` and is never answered at a narrower"
            f" depth. Two depths are two content addresses."
        ),
    )
    parser.add_argument(
        "--role",
        choices=roles,
        help=(
            "the perspective to serve under — the two declared roles sit on"
            " opposite sides of one FIBO class axis and see the same family"
            " differently, and an undeclared role is refused by name rather"
            " than served a default view"
        ),
    )
    parser.add_argument(
        "--asked-at",
        help=(
            "the instant to ask as of, ISO-8601 and timezone-aware. Defaults to"
            " the pin in artifacts/question.yaml so the transcript reproduces."
        ),
    )
    # THE INERT PARAMETERS ARE GENERATED FROM THE DECLARATION, not typed here.
    # `ccf_config.yaml::unsupported_arguments` is the only place this tier's
    # declared-but-inert surface lives; a flag spelled here would be a second
    # copy, and a parameter this tier stopped refusing — or started — would
    # leave the CLI disagreeing with the contract while still looking right.
    # Each is exposed so its refusal is one command away rather than a
    # paragraph, and each carries the DECLARED reason as its help text.
    for name, reason in deployment.unsupported_arguments().items():
        parser.add_argument(
            f"--{name.replace('_', '-')}",
            dest=name,
            help=f"DECLARED BUT INERT at this tier (§B.4.3) — {reason}",
        )
    return parser


def _wire_parameters(args: argparse.Namespace) -> dict[str, Any]:
    """The question, as WIRE-STABLE values.

    Composed from `deployment.demonstration_request`, so this caller and the MCP
    caller ask the same question and can only differ in how it travels. The
    typed request is then flattened back to wire-stable values: `WireRequest`
    refuses a `Decimal`, because canonical JSON renders one as text and the
    decoded echo would differ from what was sent — reporting a transport failure
    on a healthy wire. `transport.py` converts it back at the door, which is
    where a client sending JSON would convert it too.
    """
    asked_at = datetime.fromisoformat(args.asked_at) if args.asked_at else None
    typed = deployment.demonstration_request(
        max_depth=args.max_depth, asked_at=asked_at
    )
    parameters: dict[str, Any] = {
        name: (value if isinstance(value, (str, int, bool)) else format(value, "f"))
        for name, value in typed.parameters.items()
    }
    if args.max_depth is None:
        # ABSENT MEANS ABSENT, AND THAT IS WHAT MAKES THE DECLARED DEFAULT
        # REACHABLE FROM THIS CALLER. `question.yaml` names the demonstration's
        # depth under `parameters:` and `ccf_config.yaml` declares what a
        # MISSING one resolves to. Both say the same number, which is exactly
        # the situation where a reader cannot tell which is operative — and
        # measured, the artifact's copy won: naming it on the wire made the
        # contract's declared default unreachable from here, so moving the
        # declared default moved this file's help text and NOT its walk.
        # A caller who did not name a depth asks without one.
        _refuse_disagreeing_depth(parameters.pop(deployment.PARAM_MAX_DEPTH, None))
    if args.lei is not None:
        parameters[deployment.PARAM_LEI] = args.lei
    for name in deployment.unsupported_arguments():
        supplied = getattr(args, name, None)
        if supplied is not None:
            parameters[name] = supplied
    return parameters


def _refuse_disagreeing_depth(declared_by_question: Any) -> None:
    """Refuse two documents that name one depth differently, rather than drop one.

    Dropping the artifact's copy silently is the defect this function exists to
    prevent: the value would still be sitting in `question.yaml` looking
    operative, and a reader who edited it would watch the walk ignore them. So
    the value is READ on the way past and a disagreement is a refusal that names
    both documents.
    """
    default = deployment.declared_depth_default()
    if declared_by_question is None or int(declared_by_question) == default:
        return
    raise SystemExit(
        f"artifacts/question.yaml declares the demonstration depth"
        f" {int(declared_by_question)} and ccf_config.yaml declares a default of"
        f" {default}. With no --max-depth this caller asks WITHOUT naming a"
        " depth, so the declared default is what applies and the artifact's"
        " value would be silently ignored. Pass --max-depth"
        f" {int(declared_by_question)}, or make the two documents agree"
    )


def _asked_instant(args: argparse.Namespace) -> datetime:
    """The instant the door answers at — the artifact's pin unless overridden."""
    if args.asked_at:
        return datetime.fromisoformat(args.asked_at)
    return deployment.demonstration_request().asked_at


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    parameters = _wire_parameters(args)
    asked_at = _asked_instant(args)

    with tempfile.TemporaryDirectory(prefix="cp04-") as tmp:
        adapter = transport.FamilyTreeInProcessAdapter(
            root=Path(tmp), role=args.role
        )
        # ASSERTED, NOT INSPECTED. `TransportAdapter` is `runtime_checkable`,
        # so conformance is a fact this program establishes about itself rather
        # than a claim a reader has to take from a docstring.
        if not isinstance(adapter, TransportAdapter):
            print(
                "transport.FamilyTreeInProcessAdapter does not conform to"
                " ccf.client.wire.TransportAdapter",
                file=sys.stderr,
            )
            return 2
        client = ProductClient(
            product_id=transport.declared_product_id(), adapter=adapter
        )
        try:
            result = client.ask(parameters, as_of=asked_at)
        except AssemblyRefused as failure:
            # NOTHING ABOUT THE CALLER REACHES THIS BRANCH. `24.6-L-02`
            # narrowed `ccf.agents.errors::AssemblyRefused` to what
            # `D-IMPL-255` (5) leaves it — *"the authoritative inputs required
            # to know whether the answer is valid contradict one another or
            # violate a required invariant"* — so an exception here is an
            # INVARIANT FAILURE inside this deployment and never a verdict
            # about the question. Three sites in `deployment.py` can reach it:
            # a node the walk admitted that the minting step did not cover, a
            # served member set carrying no jurisdiction against a declared
            # requirement, and a served jurisdiction outside the declared
            # closed world.
            #
            # EXIT 2, NOT 1, and the difference is the point. Exit 1 above is
            # *the fabric answered and the answer was no*; this is *the fabric
            # could not reach an answer*, and a runner that reported the two
            # identically would make a broken deployment look like a governed
            # refusal.
            #
            # SUPERSEDED 2026-09-04 (`24.6-L-01`, `24.6-L-02`): this comment
            # said two depth conditions signaled by exception because they were
            # this example's own types with no envelope in the SDK's closed
            # vocabulary. Both are governed determinations now — a non-integer
            # depth is a `product-request-violation` and an over-capability
            # depth is a `constraint-refusal` — and both arrive as values on
            # the branch below.
            print(f"CCF runtime failure: {failure}", file=sys.stderr)
            return 2

        # BRANCHED ON AS DATA. A governed refusal is the fabric working, so it
        # is a value on the result and never an exception.
        if result.refused:
            refusal = result.refusal
            assert refusal is not None
            # THE KEY SUFFIX ONLY WHEN THE ENVELOPE NAMES ONE. A pre-assembly refusal
            # such as `anchor-ambiguity-refusal` carries no `key`, and `— None` is
            # a printed lie about the envelope (`deferred-items.md` item 3, 24.5).
            suffix = "" if refusal.key is None else f" — {refusal.key}"
            print(f"refused: {refusal.reason}{suffix}", file=sys.stderr)
            return 1

        print(json.dumps(dict(result.payload), indent=2, sort_keys=True))
        _report(result, args=args, asked_at=asked_at)
    return 0


def _report(result: Result, *, args: argparse.Namespace, asked_at: datetime) -> None:
    """What a plain SELECT would not have told you.

    Every figure here is read off the SERVED VESSEL or off the result the client
    decoded — never recomputed from a store, and never carried out of the
    assembly by a side channel. A report that re-queried would be a second
    program agreeing with the first.
    """
    payload: Mapping[str, Any] = result.payload
    nodes: list[Mapping[str, Any]] = list(payload["nodes"])
    anchor: Mapping[str, Any] = payload["anchor"]
    findings: list[Mapping[str, Any]] = list(payload["findings"])
    resolved = [node for node in nodes if node["attributes"]]
    unresolved = [node for node in nodes if not node["attributes"]]
    # `projection.py::_node` serves `NOT_EVALUABLE` — a declared member of the
    # depth field's vocabulary (§C.4 trap 5: never `0`, never `null`) — for a
    # node the undirected L4 walk admits outside the directed reach at the
    # ceiling (the `D-36` gap the sentinel exists for). A finding the product is
    # ALLOWED to emit must not take the reporter down: the sentinel is skipped
    # for `deepest` and its count is surfaced instead, so the gap is made
    # visible rather than crashing `int()` after the JSON already printed (WR-05).
    integer_depths = [node["depth"] for node in nodes if isinstance(node["depth"], int)]
    deepest = max(integer_depths, default=0)
    not_evaluable = sum(1 for node in nodes if not isinstance(node["depth"], int))
    asked_depth = (
        f"{args.max_depth}   (named by the caller)"
        if args.max_depth is not None
        else (
            f"absent -> the DECLARED default"
            f" {deployment.declared_depth_default()}, read from"
            f" ccf_config.yaml's request_contract defaults by the SDK's own"
            f" resolution"
        )
    )
    # THE WALK'S OWN ROW OF THE ROSTER (`D-23`). Read off the served payload
    # like every other figure here — never recomputed, and never timed.
    traversal = next(
        (row for row in findings if row["type"] == projection.FINDING_TRAVERSAL),
        None,
    )
    capability = deployment.traversal_depth_capability()
    debt = result.debt

    print("\nWhat a plain SELECT would not have told you:")
    print(f"   asked as of        {asked_at.isoformat()}")
    print(f"   anchor             {anchor['lei']}  {anchor['label']}")
    print(f"   ...its class chain {len(anchor['type_chain'])} FIBO classes,"
          f" from {_local(anchor['type_chain'][0])}")
    print(f"   depth asked        {asked_depth}")
    if traversal is not None:
        cost = traversal["cost"]
        print(f"   depth applied      {traversal['requested_depth']}"
              f"   requested, {traversal['depth_reached']} reached"
              f" — a depth this estate cannot exhibit is SERVED")
        print(f"   ...what it cost    {cost['nodes_visited']} node(s) visited,"
              f" {cost['edges_walked']} edge(s) walked — STRUCTURAL counts, so"
              f" two runs of one question seal identically")
        print(f"   ...the hard limit  {capability.max_traversal_depth}, the"
              f" backend's capability (authority technical, source"
              f" {capability.capability_identity}); over it the request is"
              f" refused by name and answered at no narrower depth")
    print(f"   deepest node       {deepest} hop(s) out — an undirected"
          f" NEIGHBORHOOD, not a directed descendant tree (D-36)")
    if not_evaluable:
        print(f"   ...NOT_EVALUABLE   {not_evaluable} node(s) the undirected walk"
              f" admits outside the directed reach at the ceiling (D-36) — the"
              f" gap made visible, never a depth of 0")
    print(f"   nodes returned     {len(nodes)}")
    # THE HEADLINE OF THIS RUNG. The two numbers are the multi-store split made
    # visible on one small subtree, and the second one is the point: a build
    # that quietly served only the members it could resolve would return a
    # smaller, tidier, WRONG family.
    print(f"   ...resolved in the attribute store    {len(resolved)}")
    print(f"   ...resolved to NO row                 {len(unresolved)}"
          f"   — STILL IN THE TREE. A member with no LEI is a member")
    print(f"   jurisdictions      {payload['jurisdictions']}"
          f"   — SERVED and asserted, never a permission key")
    print(f"   perspective role   {payload['perspective_role']}"
          f"   (class axis {payload['class_axis']},"
          f" {len(payload['detailed_members'])} member(s) detailed)")
    print(f"   findings           {len(findings)}")
    for finding in findings:
        # THE ROSTER, NEVER THE COUNT (`D-13`). A finding asserted as
        # `len(findings) > 0` is a check that cannot tell which cycle it found.
        #
        # THE TRAVERSAL ROW IS PRINTED ABOVE, IN FULL, and is skipped here
        # rather than rendered twice: it carries no members — it is a fact
        # about the walk rather than about a set of them — so this loop's
        # member-roster form would print `0 member(s)` and say nothing. It is
        # still COUNTED in `findings`, so the count above does not move.
        if finding["type"] == projection.FINDING_TRAVERSAL:
            continue
        print(f"     - {finding['type']}: {len(finding['members'])} member(s)")
        for member in finding["members"]:
            print(f"         {_local(member)}")
        if finding["closing_edge"]:
            closing = finding["closing_edge"]
            print(f"         closing edge {_local(closing[0])}"
                  f" -> {_local(closing[1])} ({finding['predicate']})")
    print(f"   operators invoked  {sorted(result.lineage.operators_invoked)}")
    print("   ...TWO on this rung, and one on every rung before it — the"
          " traversal is where the count moves off one")
    # THE IMPLEMENTATION THAT PRODUCED `result`, BY NAME. The in-process
    # adapter runs `assembler.py` in THIS process, so the module constants ARE
    # the identity of the code that assembled the vessel above — TRANSCRIPT
    # evidence (`D-IMPL-245` am.1), never a replay claim: Decision Replay
    # carries no assembler identity today, and that carriage is a 24.6 row.
    print(f"   assembled by       {assembler.ASSEMBLER_ID}@{assembler.ASSEMBLER_VERSION}")
    if debt is not None:
        print(f"   context debt D_c   {debt.debt:.4f}  ->  {debt.signal}")
        print(f"   ...decomposed      F={debt.factors.freshness}"
              f"  C={debt.factors.completeness}"
              f"  S={debt.factors.semantic_consistency}")
    print(f"   policy version     {sorted(result.lineage.policy_bundle_versions)}")
    print(f"   expires at         {result.expires_at.isoformat()}")
    print(f"   content address    {result.content_address}")
    print(f"   replay record      {result.replay_ref}")


def _local(iri: str) -> str:
    """The last path segment of an IRI, for a report a human reads."""
    return iri.rstrip("/").rsplit("/", 1)[-1]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
