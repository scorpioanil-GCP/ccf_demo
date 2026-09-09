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


def render(payload: dict) -> str:
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

    lin = payload["lineage"]
    out.append("  LINEAGE")
    out.append(f"    operators   {' -> '.join(lin['operators_invoked'])}")
    out.append(f"    ledger      {lin['graph_snapshot_ledger']}")
    out.append(f"    policy      {lin['policy_version']}")
    out.append(f"    asked_at    {lin['asked_at']}")
    out.append(f"    expires_at  {payload['expires_at']}")
    out.append("")
    out.append(f"  content address  {payload['content_address']}")

    rep = payload.get("replay")
    if rep:
        d = rep["dimensions"]
        out.append("")
        out.append("  DECISION REPLAY — written BEFORE the response was released")
        out.append(f"    outcome     {rep['outcome']}   "
                   f"({rep['record_bytes_persisted']} bytes persisted)")
        out.append(f"    record      {rep['record_content_address']}")
        out.append(f"    1 fabric    boundary {d['1_context_fabric']['temporal_boundary']}  "
                   f"touched {d['1_context_fabric']['touched_entities']} entities")
        for binding in d["2_policy_bindings"]["bindings"]:
            out.append(f"    2 policy    {binding}")
        out.append(f"    2 policy    effective request recorded: "
                   f"{d['2_policy_bindings']['request_resolution_present']}")
        out.append(f"    3 model     assembly_mode={d['3_model_version']['assembly_mode']}  "
                   f"model={d['3_model_version']['model_version']}")
        out.append(f"    4 role      {d['4_perspective']['principal_id']} / "
                   f"{d['4_perspective']['role']}")
        out.append(f"    5 content   plan {d['5_content_path']['plan_id']}")
        out.append(f"    5 content   product address "
                   f"{d['5_content_path']['product_content_address'][:32]}")
        out.append(f"    5 content   debt {str(d['5_content_path']['debt'])[:5]}  "
                   f"refusal recorded: {d['5_content_path']['refusal_recorded']}")
        out.append("")
        out.append("    WHAT REPLAY RE-ASKS — the EFFECTIVE question, not the caller's")
        for name, value in sorted(rep["effective_question"].items()):
            out.append(f"      {name:<22} {value}")

    f = payload.get("fulfillment")
    if f:
        out.append("")
        out.append("-" * 78)
        if f["served"]:
            out.append(f"  FULFILLMENT  SERVED   "
                       f"D_c {f['observed_debt'][:5]} <= tolerance {f['tolerance']} "
                       f"({f['tolerance_authority']})")
        else:
            out.append(f"  FULFILLMENT  WITHHELD  "
                       f"D_c {f['observed_debt'][:5]} > tolerance {f['tolerance']} "
                       f"({f['tolerance_authority']})")
            for line in _wrap(f["detail"], 74):
                out.append(f"    {line}")
            out.append("")
            out.append("    The determination above is NOT withdrawn. The product passed every")
            out.append("    validation gate and exists; what is withheld is the fabric's")
            out.append("    attestation that it is fit for this consumer to act on.")
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


def scenario_line(name: str, requested: dict, payload: dict) -> list[str]:
    """One consumer's row in the sweep — the six columns Dave's ruling names.

    requested -> effective + authority -> assembled truth -> projection -> Debt
    -> fulfillment outcome. All six on one screen, because the teaching is the
    CONTRAST between rows and a reader who has to scroll cannot see it.
    """
    eff = payload["effective_request"]
    g = payload["measures"]["gross"]
    j = payload["measures"]["adjusted"]
    f = payload["fulfillment"]
    shown = "  ".join(
        f"{k}={eff[k]['value']}({eff[k]['authority']})"
        for k in ("materiality", "debt_tolerance") if k in eff
    )
    verdict = "SERVED  " if f["served"] else "WITHHELD"
    return [
        f"  {name}",
        f"    requested    {requested or 'nothing — every value falls to the class default'}",
        f"    effective    {shown}",
        f"    assembled    family {payload['family']['nodes']}   "
        f"gross {_money(g['committed'])}   adjusted {_money(j['committed'])}",
        f"    projected    {len(payload['entities'])} material  "
        f"residual {_money(payload['projection']['residual']['committed'])}  "
        f"({len(payload['connected_without_exposure'])} connected without exposure)",
        f"    debt         {payload['context_debt']['debt'][:5]}  "
        f"({payload['context_debt']['signal']})",
        f"    fulfillment  {verdict}  against tolerance "
        f"{f['tolerance']} ({f['tolerance_authority']})",
        f"    address      {payload['content_address']}",
        f"    replay       {payload['replay']['outcome']} · "
        f"{payload['replay']['record_content_address'][:16]} · "
        f"{payload['replay']['record_bytes_persisted']} bytes",
    ]


def sweep() -> str:
    """Every declared consumer, in order, against one estate and one instant.

    **The scenarios are READ from `artifacts/scenarios.yaml`.** A table of
    thresholds and tolerances written into this client would be the same
    No-Hardcoding violation as a threshold written into `produce.py`.
    """
    declared = dep.load(dep.SCENARIOS)[dep.DECLARATION]
    out = ["=" * 78,
           "  cp-05 · ONE QUESTION, ONE ESTATE, ONE INSTANT — EIGHT CONSUMERS",
           "=" * 78, ""]
    for entry in declared:
        params = dict(entry["parameters"])
        try:
            payload = prod.produce(**params)
        except prod.RequestRefused as exc:
            out.append(f"  {entry['name']}")
            out.append(f"    requested    {params or 'nothing'}")
            out.append("    REFUSED AT THE REQUEST BOUNDARY — before any assembly ran")
            for line in _wrap(str(exc), 70):
                out.append(f"      {line}")
        else:
            out.extend(scenario_line(entry["name"], params, payload))
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
        payload = prod.produce(
            anchor=args.lei, intent=args.intent, depth=args.depth,
            materiality=args.materiality, basis=args.basis,
            follow_guarantees=False if args.no_guarantees else None,
            follow_cross_default=False if args.no_cross_default else None,
            debt_tolerance=args.debt_tolerance, as_of=args.as_of,
        )
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

    print(json.dumps(payload, indent=2) if args.json else render(payload))
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
