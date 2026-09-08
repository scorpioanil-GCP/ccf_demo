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
    parser.add_argument("--no-guarantees", action="store_true")
    parser.add_argument("--no-cross-default", action="store_true")
    parser.add_argument("--json", action="store_true", help="emit the payload rather than the transcript")
    args = parser.parse_args(argv)

    try:
        payload = prod.produce(
            anchor=args.lei, intent=args.intent, depth=args.depth,
            materiality=args.materiality, basis=args.basis,
            follow_guarantees=False if args.no_guarantees else None,
            follow_cross_default=False if args.no_cross_default else None,
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
        # A request argument outside its DECLARED bound — refused BY NAME and
        # never clamped. Caught here so the refusal exits with a documented code
        # rather than a traceback: `example_delivery.md` §9 requires every
        # refusal's exit code to match what the README claims, and a traceback
        # has no exit code a reader can rely on.
        print(f"\n  Refused: {exc}\n", file=sys.stderr)
        return 5

    print(json.dumps(payload, indent=2) if args.json else render(payload))
    return 0


if __name__ == "__main__":  # pragma: no cover - program entry point
    raise SystemExit(main())
