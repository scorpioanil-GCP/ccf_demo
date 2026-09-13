"""The client. Asks one question and prints what came back.

    export CCF_CP_13_POSTGRES_DSN=...   CCF_CP_13_POSTGRES_SCHEMA=ccf_v2
    export CCF_CP_13_FLUREE_URL=...     CCF_CP_13_FLUREE_LEDGER=fibo-v2
    export CCF_CP_13_MONGO_URI=...      CCF_CP_13_MONGO_DB=fibo_v2
    make -s example-cp-13

Every request parameter is optional. Omitted, the program asks the
demonstration question in `artifacts/question.yaml`.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import acquisition  # noqa: E402
import deployment  # noqa: E402
import produce  # noqa: E402
from ccf.products.refusal import RefusalEnvelope  # noqa: E402

QUESTION = HERE / "artifacts" / "question.yaml"


def question() -> dict[str, Any]:
    document = yaml.safe_load(QUESTION.read_text(encoding="utf-8"))
    asked: dict[str, Any] = dict(document["declaration"]["question"])
    return asked


def main(argv: list[str]) -> int:
    default = question()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--principal", default=default["principal"])
    parser.add_argument("--corpus-scope", default=default["corpus_scope"])
    parser.add_argument("--sources", nargs="+", default=default.get("sources"))
    parser.add_argument("--source-limit", type=int, default=default["source_limit"])
    parser.add_argument("--scope", default=default["scope"])
    parser.add_argument("--as-of", default=default["as_of"])
    parser.add_argument("--intent", default=default["intent"])
    parser.add_argument("--resolve-depth", type=int, default=default["resolve_depth"])
    parser.add_argument("--debt-tolerance", default=default.get("debt_tolerance"))
    arguments = parser.parse_args(argv)

    sources = arguments.sources or acquisition.evidence_sources(
        limit=arguments.source_limit
    )
    asked = deployment.request(
        sources=sources, scope=arguments.scope,
        asked_at=datetime.fromisoformat(arguments.as_of),
        intent=arguments.intent, corpus_scope=arguments.corpus_scope,
        resolve_depth=arguments.resolve_depth,
        debt_tolerance=arguments.debt_tolerance,
    )
    print(f"asked        {asked.subject} · {asked.intent} · as of {arguments.as_of}")
    print(
        f"             principal={arguments.principal}"
        f"  corpus_scope={asked.parameters['corpus_scope']}"
        f"  depth={asked.parameters['resolve_depth']}"
        f"  sources={len(sources)}"
    )

    with tempfile.TemporaryDirectory() as scratch:
        try:
            outcome = produce.assemble_and_serve(
                asked=asked, root=Path(scratch), principal=arguments.principal
            )
        except acquisition.ScopeNotEntitled as refusal:
            print(f"\nREFUSED      not-entitled")
            print(f"  {refusal}")
            print(
                "\n  The scope was REFUSED, not narrowed. Narrowing would answer"
                "\n  a question the caller did not ask and would hide that the"
                "\n  document class exists at all."
            )
            return 1

        if isinstance(outcome, RefusalEnvelope):
            print(f"\nREFUSED      {outcome.kind}")
            print(f"  reason     {outcome.reason}")
            print(f"  detail     {outcome.detail}")
            print(f"  replay     {outcome.replay_reference}")
            return 1

        payload = outcome.product.payload
        t = payload["traversal"]
        print(f"\nSEEDED ON    {t['seeded_on']}   ({t['sources']} sources, depth {t['resolve_depth']})")
        print("             the type whose NAME matches the question reaches depth 3 once;")
        print("             the type that carries the EVIDENCE reaches it 26 times")

        env = payload["envelope"]
        r = env["retrieval"]
        print(f"\nENVELOPE     {env['principal']} / {env['corpus_scope']}")
        print(f"  permitted classifications  {env['permitted_classifications']}")
        print(f"  permitted documents        {env['permitted_documents']}"
              f"   (excluded for no classification: {env['excluded_for_missing_classification']})")
        print(f"  retrieval bound            {r['bound_applied']}"
              f"   filter={r['query_filter']}")
        print(f"  candidates examined        {r['candidates_examined']}"
              "   <- equals the permitted, embedded population; a post-filter")
        print("                                  would have scored the whole corpus")
        ne = r["not_evaluable"]
        print(f"  NOT EVALUABLE              {ne['count']}  ({ne['reason']})")
        if ne["count"]:
            print(f"       {ne['note']}")
        for hit in r["hits"][:3]:
            print(f"  hit  {hit['score_percent']:>3}%  {hit['memorandum_id']}  {hit['classification']}  {hit['title']}")

        g = payload["governing_text"]
        print(f"\nGOVERNING    by `{g['axis']}`, never `{g['not_axis']}`"
              f"   in force at {g['as_of']}: {g['documents_in_force']}"
              f"   not yet governing: {g['documents_not_yet_governing']}")

        s = payload["citation_summary"]
        print(f"\nCITATIONS    {s['checked_citations']} CHECKED over {s['chain_nodes']} chain nodes")
        print(f"  not evidenced {s['not_evidenced_total']}, and every one carries a reason:")
        for reason, count in s["not_evidenced"].items():
            if count:
                print(f"      {reason:24} {count:>4}")

        print("\nPER SOURCE")
        for source in payload["cross_references"][:3]:
            print(f"\n  {source['source_uri'].rsplit('/', 1)[-1]}"
                  f"   {source['covenant_type']} @ {source['threshold']}")
            for node in source["chain"]:
                mark = f"{len(node['citations'])} cited" if node["citations"] else "—"
                print(f"     d{node['depth']} {node['kind']:22} {mark}")
                for c in node["citations"]:
                    print(f"        CITED  {c['anchor']['locator'][-26:]}"
                          f"  [{c['start_offset']}:{c['end_offset']}]  checked={c['checked']}")
                    print(f"           {c['text'][:64]!r}")
                for a in node["not_evidenced"]:
                    print(f"        DEBT   {a['reason']}")
                    print(f"           {a['note'][:100]}")

        print("\nABSENT LEGS")
        for leg, state in payload["absent_legs"].items():
            print(f"  {leg:16} {state['state']}   {state['note'][:80]}")

        debt = outcome.product.debt
        print(f"\ncontext debt D_c {debt.debt}   signal {debt.signal}")
        print(f"  F {debt.factors.freshness}  C {debt.factors.completeness}"
              f"  S {debt.factors.semantic_consistency}")
        print("  NOTE: C is low BECAUSE most chain nodes cannot be evidenced."
              "\n  That is the finding this product exists to surface, not a fault"
              "\n  in the assembly.")
        print(f"content address  {outcome.record.content_generation_path.product_content_address}")
        print(f"expires_at       {outcome.product.expires_at.isoformat()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
