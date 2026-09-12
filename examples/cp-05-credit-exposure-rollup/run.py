"""cp-05's client — asks the declared question and prints what came back.

[ADAPT] the rendering. [MECHANISM] `produce.py`, which this program does not
reach around.

**Every request parameter is OPTIONAL.** Omitted, this program asks the
demonstration question declared in ``artifacts/question.yaml`` — a threshold, an
anchor and an intent are request parameters, not deployment configuration, and a
build tool is not a request channel (`example_delivery.md` §3).

Run it::

    make venv
    make example-cp-05
    make example-cp-05 INTENT=internal-appetite
    make example-cp-05 LEI=<lei> DEPTH=2
    make example-cp-05 SCENARIOS=1

**THE DEMONSTRATED RUN IS A GOVERNED REFUSAL.** Against the estate as it stands,
the outstanding balances are days old and this product's half-life is four
hours, so Context Debt is 1.000 and fulfillment is withheld against the class's
own 0.25 tolerance. The $9.325B determination is printed anyway: the fabric may
know what it calculated without being willing to attest that the calculation is
fit to act on. Nothing here is calibrated to make the demonstration serve.
"""

from __future__ import annotations

import argparse
import json
import sys

import deployment as dep
import produce as prod


def _money(value: int) -> str:
    """Whole units with thousands separators. No currency symbol is invented."""
    return f"{value:,}"


def _share(value: object) -> str:
    """A factor as a reader sees it — `0E-18` is a true zero, not a number."""
    from decimal import Decimal

    return f"{round(Decimal(str(value)), 4).normalize():f}"


def render_withheld(governed: object) -> str:
    """What a caller sees when the fabric withholds fulfillment.

    **The determination EXISTS.** It passed every validation gate and its
    record is on the store; what is withheld is the fabric's willingness to
    let this caller act on it at the fitness bar in force. So this renders the
    refusal's own disclosed shell rather than an apology, and names the
    authority that supplied the tolerance — a caller who never sent one is owed
    the reason their answer was withheld.

    The shell is whatever `disclosure` permits and nothing more. Under
    `minimal` that is deliberately thin: the fabric does not narrate a
    determination it has declined to release (`D-IMPL-254`).
    """
    kind = getattr(governed, "kind", "refused")
    reason = getattr(governed, "reason", "") or ""
    fields = dict(getattr(governed, "fields", {}) or {})
    replay = getattr(governed, "replay_reference", None) or getattr(
        governed, "replay_ref", ""
    )
    lines = [
        "",
        "  CP-05 · CREDIT EXPOSURE ROLLUP",
        "",
        f"  FULFILLMENT  WITHHELD  ({kind})",
        "",
        "    The determination was assembled and recorded. What is withheld is",
        "    fulfillment: the observed Context Debt exceeded the tolerance in",
        "    force for this caller. A different consumer, with a different",
        "    fitness requirement, may legitimately be served the same answer.",
        "",
    ]
    if reason:
        lines.append(f"    reason      {reason}")
    for name in ("authority", "tolerance", "observed"):
        if name in fields:
            lines.append(f"    {name:<12}{fields[name]}")
    lines += [
        "",
        f"    replay      {replay}",
        "",
        "    The record is the point. A refusal nobody can replay is an outage;",
        "    a refusal with a decision record is governance.",
        "",
    ]
    return "\n".join(lines)


def render(payload: dict, governed: object, record: object = None) -> str:
    """The transcript. Every figure comes from the payload; none is recomputed here."""
    out: list[str] = []
    a = payload["anchor"]
    g = payload["measures"]["gross"]
    j = payload["measures"]["adjusted"]
    fam = payload["family"]
    ded = payload["guarantee_dedup"]

    out.append("=" * 78)
    out.append(f"  {payload['schema_name']} v{payload['schema_version']}")
    out.append(f"  {a['legal_name']}  ({a['lei']})")
    out.append("=" * 78)
    out.append("")
    out.append(f"  intent            {payload['intent']}   "
               f"[policy {payload['policy_version']}]")
    p = payload["policy"]
    out.append(f"  limit definition  counts_guarantees={p['counts_guarantees']}  "
               f"counts_undrawn={p['counts_undrawn']}  basis={p['connection_basis']}")
    out.append("  ── BUSINESS ANSWER " + "─" * 58)
    out.append("")
    r = payload["request"]
    out.append(f"  request           depth={r['depth']}  materiality={r['materiality']}  "
               f"basis={r['basis']}  guarantees={r['follow_guarantees']}  "
               f"cross_default={r['follow_cross_default']}")
    eff = payload.get("effective_request", {})
    if eff:
        shown = "  ".join(f"{k}={v['value']}({v['authority']})"
                          for k, v in sorted(eff.items()) if k in ("materiality", "depth"))
        out.append(f"  effective         {shown}")
    out.append("")
    out.append("  FAMILY")
    out.append(f"    {fam['nodes']} nodes reached at depth {r['depth']}; "
               f"{fam['members_with_lei']} carry an LEI; "
               f"{fam['members_holding_facilities']} hold a material facility book")
    out.append("")
    out.append("  EXPOSURE                     committed        outstanding           undrawn")
    out.append(f"    gross            {_money(g['committed']):>16}  {_money(g['outstanding']):>17}"
               f"  {_money(g['undrawn']):>16}")
    out.append(f"    adjusted         {_money(j['committed']):>16}  {_money(j['outstanding']):>17}"
               f"  {_money(j['undrawn']):>16}")
    delta = g["committed"] - j["committed"]
    pct = (delta / g["committed"] * 100) if g["committed"] else 0.0
    out.append(f"    guarantee dedup  {_money(-delta):>16}   "
               f"({ded['cases']} case(s), {pct:.2f}% of gross)")
    out.append("")

    if ded["detail"]:
        out.append("  WHAT THE DEDUP REMOVED — the step that makes the answer correct")
        for case in ded["detail"]:
            out.append(f"    {case['guarantor_lei']} guarantees {case['obligor_lei']} "
                       f"at {case['covered_pct']}")
            out.append(f"      -> {_money(case['committed_removed'])} counted once, not twice")
        out.append("")

    if payload["entities"]:
        out.append("  MATERIAL ENTITIES")
        for e in payload["entities"]:
            name = (e["legal_name"] or e["lei"])[:34]
            out.append(f"    {name:<34} {e['facilities']:>2} fac  "
                       f"{_money(e['gross']['committed']):>16}")
        out.append("")

    cwe = payload["connected_without_exposure"]
    out.append("  CONNECTED WITHOUT EXPOSURE — what a borrower-keyed sum cannot reach")
    out.append(f"    {len(cwe)} family members are bound by ownership, guarantee or")
    out.append("    cross-default and hold no facility of their own.")
    out.append("")

    d = payload.get("context_debt")
    if d:
        e = d["evidence"]
        out.append("  CONTEXT DEBT — confidence in the assembled truth, not in the projection")
        out.append(f"    debt {d['debt'][:6]}   signal {d['signal']}")
        out.append(f"    freshness   {e['freshness'][:6]:<8} from {e['balance_observations']} real balance_as_of dates")
        out.append(f"    completeness {e['completeness'][:6]:<7} {e['checkable_members']}/{e['family_size']} family members carry an LEI and can be checked")
        out.append(f"    consistency  {e['semantic_consistency'][:6]:<7} {e['reconciliations_implausible']} of {e['reconciliations_used']} reconciliations used here disagree")
        out.append("")

    rec = payload.get("reconciliation")
    if rec:
        out.append("  RECONCILIATION — the anchor's own book against XBRL-reported debt")
        out.append(f"    anchor committed {_money(rec['anchor_committed'])}  "
                   f"reported debt {_money(rec['reported_debt'])}  "
                   f"share {rec['share']}  plausible={rec['plausible']}")
        out.append("")

    if payload["findings"]:
        out.append("  FINDINGS")
        for f in payload["findings"]:
            out.append(f"    [{f['kind']}]")
            for line in _wrap(f["detail"], 70):
                out.append(f"      {line}")
        out.append("")

    # ------------------------------------------------------------------
    # GOVERNED CONTEXT — read from the ENVELOPE, never from the payload.
    # ------------------------------------------------------------------
    #
    # Everything above is the business answer: what this family owes, which of
    # it is material to this caller, and what the assembly found. Everything
    # below is the fabric's account of whether, why and under whose authority
    # that answer was fit to serve.
    #
    # `D-IMPL-299`: the payload used to carry lineage, the TTL, the content
    # address and a replay block. Those are envelope facts, and duplicating
    # them into business content made the content address a function of how the
    # answer was governed rather than of the answer. The renderer now reads two
    # sources — and showing the split is the point, because
    #
    #     A Context Product is not just a payload. The payload is the business
    #     answer; the governed envelope explains whether, why, and under whose
    #     authority that answer was fit to serve.
    contract = governed.product
    lineage = contract.lineage
    out.append("  ── GOVERNED CONTEXT " + "─" * 56)
    out.append("")
    out.append("  LINEAGE")
    out.append(f"    operators   {' -> '.join(sorted(lineage.operators_invoked))}")
    out.append(f"    policy      {', '.join(sorted(lineage.policy_bundle_versions))}")
    out.append(f"    graph as of {lineage.graph_snapshot_at.isoformat()}")
    # The store head the reads ran against is NOT here (`D-IMPL-309`). It is
    # execution provenance rather than determination identity, so it moved to
    # replay dimension 1 and is printed under DECISION REPLAY below. Reading it
    # off the lineage is what this renderer used to do, and the field it read
    # has correctly stopped existing.
    out.append("")
    out.append("  CONTEXT DEBT — confidence in the assembled truth")
    debt = contract.debt
    out.append(f"    D_c         {str(debt.debt)[:6]}   signal {debt.signal}")
    out.append(f"    factors     F={_share(debt.factors.freshness)}  "
               f"C={_share(debt.factors.completeness)}  "
               f"S={_share(debt.factors.semantic_consistency)}")
    out.append("")
    out.append("  OBLIGATION IN FORCE")
    out.append(f"    {contract.obligation_in_force}")
    out.append("")
    out.append("  IDENTITY AND WINDOW")
    out.append(f"    address     {prod.content_address(payload)}")
    out.append(f"    asked_at    {contract.temporal_boundary.isoformat()}")
    out.append(f"    expires_at  {contract.expires_at.isoformat()}  "
               f"(anchor: {contract.ttl_anchor})")
    out.append("")
    out.append("  DECISION REPLAY — written BEFORE the response was released")
    reference = getattr(governed, "replay_ref", None)
    out.append(f"    record      {getattr(reference, 'uri', reference)}")
    snapshot = getattr(record, "context_fabric_snapshot", None)
    pin = getattr(snapshot, "store_snapshot_pin", None)
    if pin is not None and getattr(pin, "substrate", "none") != "none":
        out.append(f"    store pin   {pin.substrate}:{pin.pin}")
    out.append("")
    out.append("    The store head those reads ran against is dimension 1 of that")
    out.append("    record and is deliberately NOT on the product: a ledger advancing")
    out.append("    for reasons unrelated to the question would otherwise give the same")
    out.append("    question two content addresses (`D-IMPL-309`).")
    out.append("")
    out.append("    Which authority supplied each effective parameter — caller,")
    out.append("    product default, or policy — is recorded in dimension 2 of that")
    out.append("    record. It is deliberately NOT in the payload above: two callers")
    out.append("    whose parameters resolved differently to the same business answer")
    out.append("    share its content address, and the record is what tells their")
    out.append("    determinations apart.")
    out.append("")
    out.append("  FULFILLMENT  SERVED")
    out.append(f"    D_c {str(debt.debt)[:6]} was within the tolerance in force for this caller.")
    out.append("    A consumer with a stricter fitness bar may be refused the SAME")
    out.append("    determination — fitness is the consumer's; truth is not.")
    out.append("=" * 78)
    return "\n".join(out)


def _wrap(text: str, width: int) -> list[str]:
    words, line, lines = text.split(), "", []
    for word in words:
        if len(line) + len(word) + 1 > width:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        lines.append(line)
    return lines


def scenario_line(name: str, requested: dict, payload: dict,
                  governed: object) -> list[str]:
    """One consumer's row in the sweep — the six columns Dave's ruling names.

    requested -> effective + authority -> assembled truth -> projection -> Debt
    -> fulfillment outcome. All six on one screen, because the teaching is the
    CONTRAST between rows and a reader who has to scroll cannot see it.
    """
    # TWO SOURCES, and the row is more honest for it (`D-IMPL-299`). The scope
    # a caller asked in comes off the payload; whether the fabric was willing to
    # serve it, and under whose authority, comes off the governed envelope. The
    # payload no longer restates the effective request, so a withheld row has no
    # payload at all — which is itself the lesson.
    from ccf.products.refusal import RefusalEnvelope

    withheld = isinstance(governed, RefusalEnvelope)
    if withheld:
        fields = dict(getattr(governed, "fields", {}) or {})
        shown = "  ".join(
            f"{k}={fields[k].strip(chr(34))}"
            for k in ("tolerance", "authority") if k in fields
        )
        return [
            f"  {name}",
            f"    requested    {requested or 'nothing — every value falls to the class default'}",
            f"    effective    {shown}",
            "    assembled    (the determination exists and is recorded)",
            f"    fulfillment  WITHHELD  {getattr(governed, 'reason', '')}",
            "",
        ]
    g = payload["measures"]["gross"]
    j = payload["measures"]["adjusted"]
    scope = payload["request"]
    shown = f"materiality={scope['materiality']}  depth={scope['depth']}  basis={scope['basis']}"
    verdict = "SERVED  "
    return [
        f"  {name}",
        f"    requested    {requested or 'nothing — every value falls to the class default'}",
        f"    effective    {shown}",
        f"    assembled    family {payload['family']['nodes']}   "
        f"gross {_money(g['committed'])}   adjusted {_money(j['committed'])}",
        f"    projected    {len(payload['entities'])} material  "
        f"residual {_money(payload['residual']['committed'])}  "
        f"({len(payload['connected_without_exposure'])} connected without exposure)",
        # Debt, the outcome and the address are ENVELOPE facts (`D-IMPL-299`).
        f"    debt         {_share(governed.product.debt.debt)}  "
        f"({governed.product.debt.signal})",
        f"    fulfillment  {verdict}  within this caller's tolerance",
        f"    address      {prod.content_address(payload)}",
        # The LAST governed member this row read out of the payload. The record's
        # identity is the envelope's — `D-IMPL-299`, and the sweep is the place
        # a reader is most likely to mistake one for the other, because the six
        # columns sit side by side.
        f"    replay       served · "
        f"{getattr(getattr(governed, 'replay_ref', None), 'content_address', '')[:16]}",
    ]


def sweep() -> str:
    """Every declared consumer, in order, against one estate and one instant.

    **The scenarios are READ from `artifacts/scenarios.yaml`.** A table of
    thresholds and tolerances written into this client would be the same
    No-Hardcoding violation as a threshold written into `produce.py`.
    """
    declared = dep.load(dep.SCENARIOS)[dep.DECLARATION]["consumers"]
    out = ["=" * 78,
           "  cp-05 · ONE QUESTION, ONE ESTATE, ONE INSTANT — EIGHT CONSUMERS",
           "=" * 78, ""]
    for entry in declared:
        params = dict(entry["parameters"])
        try:
            payload, governed, _record = prod.produce_governed(**params)
        except prod.RequestRefused as exc:
            out.append(f"  {entry['name']}")
            out.append(f"    requested    {params or 'nothing'}")
            out.append("    REFUSED AT THE REQUEST BOUNDARY — before any assembly ran")
            for line in _wrap(str(exc), 70):
                out.append(f"      {line}")
        else:
            out.extend(scenario_line(entry["name"], params, payload, governed))
        for line in _wrap(entry["teaches"], 72):
            out.append(f"      {line}")
        out.append("")
    out.append("=" * 78)
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, add_help=True)
    parser.add_argument("--lei", default=None, help="anchor obligor; omitted asks the declared question")
    parser.add_argument("--intent", default=None, help="selects the limit definition")
    parser.add_argument("--depth", type=int, default=None)
    # TAKEN AS TEXT, NEVER AS A FLOAT. `argparse`'s `type=float` would hand the
    # fabric the one value shape the Control Plane refuses -- floats are not
    # bit-stable across platforms, so a float threshold would make the content
    # address reproduce on this machine and nowhere else. The string is
    # converted to `Decimal` where the request is built.
    parser.add_argument("--materiality", default=None,
                        help="e.g. 0.02 or 0.10; the product default is 0.05")
    parser.add_argument("--basis", default=None, choices=["committed", "outstanding", "both"])
    # TAKEN AS TEXT for the same reason `--materiality` is: the Control Plane
    # refuses a bare float, and a float fitness bar would compare against D_c
    # differently on different machines.
    parser.add_argument("--debt-tolerance", default=None,
                        help="the most Context Debt this consumer will act on; default 0.25")
    parser.add_argument("--as-of", default=None,
                        help="declared and REFUSED at this rung; see artifacts/question.yaml")
    parser.add_argument("--scenarios", action="store_true",
                        help="run every consumer declared in artifacts/scenarios.yaml")
    parser.add_argument("--no-guarantees", action="store_true")
    parser.add_argument("--no-cross-default", action="store_true")
    parser.add_argument("--json", action="store_true", help="emit the payload rather than the transcript")
    args = parser.parse_args(argv)

    if args.scenarios:
        print(sweep())
        return 0

    try:
        # THE GOVERNED RESULT, NOT THE PAYLOAD ALONE.
        #
        # A withheld determination HAS no payload — it has a refusal envelope
        # carrying what disclosure permits. This asked `produce()` until the
        # canonical adoption (`D-IMPL-298`), and the hand-composed spine could
        # hand back figures beside a `withheld` flag because it computed them
        # locally and decided fulfillment afterwards. On the canonical path the
        # FABRIC decides, and a refused caller sees what the deployment's
        # disclosure policy allows and no more. Rendering the two outcomes
        # differently is the honest consequence, not a regression.
        payload, governed, record = prod.produce_governed(
            anchor=args.lei, intent=args.intent, depth=args.depth,
            materiality=args.materiality, basis=args.basis,
            follow_guarantees=False if args.no_guarantees else None,
            follow_cross_default=False if args.no_cross_default else None,
            debt_tolerance=args.debt_tolerance, as_of=args.as_of,
        )
        if not payload:
            print(render_withheld(governed))
            return 0
    except dep.DeclarationMissing as exc:
        print(f"\n  This deployment is not configured.\n\n  {exc}\n", file=sys.stderr)
        return 2
    except dep.GraphUnavailable as exc:
        print(f"\n  The graph leg could not be read: {exc}\n\n"
              "  Not degraded to an empty family — an unreachable graph and a graph with\n"
              "  no matching edges are different facts.\n", file=sys.stderr)
        return 3
    except LookupError as exc:
        # An unresolvable anchor or an unknown intent. A REFUSAL, not a crash:
        # the caller asked a well-formed question the estate cannot answer.
        print(f"\n  Refused: {exc}\n", file=sys.stderr)
        return 4
    except ValueError as exc:
        # A request argument outside its DECLARED bound — refused BY NAME
        # rather than silently narrowed, in the SDK's own words. Caught here so
        # the refusal exits with a documented code
        # rather than a traceback: `example_delivery.md` §9 requires every
        # refusal's exit code to match what the README claims, and a traceback
        # has no exit code a reader can rely on.
        print(f"\n  Refused: {exc}\n", file=sys.stderr)
        return 5

    print(json.dumps(payload, indent=2) if args.json
          else render(payload, governed, record))
    # EXIT 0 EVEN WHEN FULFILLMENT IS WITHHELD, and it is a ruling rather than
    # an oversight. `D-IMPL-251`: a tolerance breach is a refusal OF
    # FULFILLMENT, not of response. The program was asked a question and
    # answered it completely — here is the determination, here is the measured
    # Debt, here is the tolerance that was not met, and here is who set it.
    # A non-zero exit would say the request failed; it did not. The exit codes
    # above are for requests that could not be ANSWERED (unconfigured
    # deployment, unreachable graph, unresolvable anchor, out-of-bound
    # argument), which is a different kind of event.
    return 0


if __name__ == "__main__":  # pragma: no cover - program entry point
    raise SystemExit(main())
