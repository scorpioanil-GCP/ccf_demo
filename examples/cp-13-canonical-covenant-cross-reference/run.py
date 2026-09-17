"""Run the example and show a reader what came back.

[ADAPT] freely — this file is presentation and nothing else.

**It carries no marker region**, so nothing printed here is published-snippet
surface: an adopter copies ``produce.py``'s two regions, not this. It is also
the ONLY module in this example that writes to a terminal.

Usage::

    export CCF_CP_13C_POSTGRES_DSN=...   CCF_CP_13C_POSTGRES_SCHEMA=ccf_v2
    export CCF_CP_13C_FLUREE_URL=...     CCF_CP_13C_FLUREE_LEDGER=fibo-v2
    export CCF_CP_13C_MONGO_URI=...      CCF_CP_13C_MONGO_DB=fibo_v2
    make -s example-cp-13-canonical
    .venv/bin/python examples/cp-13-canonical-covenant-cross-reference/run.py --door

Every request parameter is optional. Omitted, the program asks the
demonstration question in ``artifacts/question.yaml``. The entitlement
principal is the PERSPECTIVE's role (`CP-SPEC-013C` §0.2): ``--role`` states
the perspective a local caller asks under; the door serves under the
deployment's declared default and takes no such flag.
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
from ccf.projection.plan import Perspective  # noqa: E402

QUESTION = HERE / "artifacts" / "question.yaml"


def question() -> dict[str, Any]:
    document = yaml.safe_load(QUESTION.read_text(encoding="utf-8"))
    asked: dict[str, Any] = dict(document["declaration"]["question"])
    return asked


def main(argv: list[str]) -> int:
    default = question()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--role", default=None, help="the perspective role to ask under; omit for the declared default")
    parser.add_argument("--corpus-scope", default=None, help="omit to let the class default resolve")
    parser.add_argument("--sources", nargs="+", default=default.get("sources"))
    parser.add_argument("--source-limit", type=int, default=default["source_limit"])
    parser.add_argument("--scope", default=default["scope"])
    parser.add_argument("--as-of", default=default["as_of"])
    parser.add_argument("--intent", default=default["intent"])
    parser.add_argument("--resolve-depth", type=int, default=None, help="omit to let the class default resolve")
    parser.add_argument("--debt-tolerance", default=default.get("debt_tolerance"))
    parser.add_argument(
        "--door", action="store_true",
        help="instead of asking once: boot the MCP egress door on an ephemeral 127.0.0.1"
             " port, print `READY {port}`, and serve questions from other processes until terminated",
    )
    arguments = parser.parse_args(argv)

    if arguments.door:
        from server import serve as door  # noqa: PLC0415

        door.loopback(announce=lambda port: print(f"READY {port}", flush=True))
        return 0

    with tempfile.TemporaryDirectory() as scratch, produce.product(Path(scratch)) as opened:
        sources = arguments.sources or acquisition.evidence_sources(
            limit=arguments.source_limit, graph_settings=opened.sources[deployment.SOURCE_GRAPH],
        )
        sources = sorted(dict.fromkeys(sources))
        parameters: dict[str, Any] = {deployment.COVENANT_SOURCES: sources}
        if arguments.corpus_scope is not None:
            parameters[deployment.CORPUS_SCOPE] = arguments.corpus_scope
        if arguments.resolve_depth is not None:
            parameters[deployment.RESOLVE_DEPTH] = arguments.resolve_depth
        if arguments.debt_tolerance is not None:
            parameters["debt_tolerance"] = arguments.debt_tolerance
        subject = sources[0] if len(sources) == 1 else arguments.scope
        asked = opened.question(
            subject=subject, asked_at=datetime.fromisoformat(arguments.as_of),
            intent=arguments.intent, freshness="amendment-driven", parameters=parameters,
        )
        perspective = None
        if arguments.role is not None:
            perspective = Perspective(principal_id=opened.default_perspective.principal_id, role=arguments.role)
        role = arguments.role or opened.default_perspective.role
        print(f"asked        {asked.subject} · {asked.intent} · as of {arguments.as_of}")
        print(
            f"             role={role}"
            f"  corpus_scope={arguments.corpus_scope or 'absent — the class default resolves'}"
            f"  depth={arguments.resolve_depth if arguments.resolve_depth is not None else 'absent — the class default resolves'}"
            f"  sources={len(sources)}"
        )
        try:
            outcome = opened.answer(asked, perspective=perspective)
        except acquisition.ScopeNotEntitled as refusal:
            print("\nREFUSED      not-entitled")
            print(f"  {refusal}")
            return 2
        except acquisition.UnknownCovenantSource as refusal:
            print("\nREFUSED      unknown-source")
            print(f"  {refusal}")
            return 2
        if isinstance(outcome, RefusalEnvelope):
            print(f"\nREFUSED      {outcome.kind} · {outcome.reason}")
            print(f"  {outcome.detail}")
            print(f"  replay     {outcome.replay_reference}")
            return 1
        product = outcome.product
        payload = product.payload
        print(f"\nSERVED       {product.schema_name}@{product.schema_version}")
        print(f"  address    {outcome.replay_ref.content_address}")
        print(f"  expires    {product.expires_at.isoformat()}")
        print(f"  debt       D_c={product.debt.debt}  signal={product.debt.signal}")
        summary = payload["citation_summary"]
        print(
            f"  chain      {summary['chain_nodes']} nodes · {summary['checked_citations']} checked citations"
            f" · {summary['not_evidenced_total']} explained absences"
        )
        envelope = payload["envelope"]
        print(
            f"  envelope   principal={envelope['principal']} scope={envelope['corpus_scope']}"
            f" bound={envelope['retrieval']['bound_applied']} candidates={envelope['retrieval']['candidates_examined']}"
        )
        governing = payload["governing_text"]
        print(f"  governing  {len(governing['documents_in_force'])} in force · {len(governing['documents_not_yet_governing'])} not yet")
        print(f"  in view    {payload['graph']['entities_in_view']} entities")
        for source in payload["cross_references"]:
            checked = sum(len(node["citations"]) for node in source["chain"])
            print(f"    {source['source_uri']}  {source['covenant_type']}  chain={len(source['chain'])} checked={checked}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
