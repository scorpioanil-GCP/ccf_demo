"""Reconstruct a governed determination from its record — calling no producer.

The adopter-facing form of what every paved producer's replay proof does in its
own test suite. It opens a paved product tree, asks one question, and then
reproduces the recorded determination through the SDK's own engine
(`ccf.replay.engine.replay` for a served product, `replay_refusal` for a
refused one) with an environment built from the RECORD and the deployment's two
documents. Nothing here re-reads a source, invokes the deployment's question
mapping, or calls a producer: what the engine re-executes is the recorded
operator path over the recorded snapshot, held to the recorded addresses.

Usage (the producer's own environment names must be exported — for the default
tree those are the ``CCF_CP_06C_*`` variables its ``ccf_environment.yaml``
declares)::

    .venv/bin/python examples/dr-01-replay-a-governed-determination/replay.py \\
        --tree examples/cp-06-canonical-collateral-and-setoff-coverage \\
        --subject FAC-5B8418 --intent lgd-assessment --freshness as-filed \\
        --asked-at 2026-09-07T12:00:00+00:00 \\
        --parameters '{"facility_id": "FAC-5B8418", "borrower_scope": ["2549001IGRCG4F0RLD36"]}'

Pass ``--refuse`` to ask a question the product refuses (a scope nobody holds)
and reconstruct THAT determination instead, through the refusal path.

**One private dependency, named rather than hidden.** Re-executing the
recorded operator path needs each operator's parameter artifact bound from the
EFFECTIVE request the record carries. The SDK exposes that binding only as
``GovernedResolver.operator_parameters``, reached here by building a resolver
from the opened product's own arguments. It is the one call in this file that
is not public contract, and the reason this example lives beside the product
trees rather than inside one: a paved tree's structural classifier forbids the
builder call in the tree.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from ccf.artifacts.file_store import FileArtifactStore
from ccf.contracts.canonical import content_hash
from ccf.products.refusal import RefusalEnvelope
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.environment import RecordedEnvironment

REPO_ROOT = Path(__file__).resolve().parents[2]


# --8<-- [start:environment]
# THE ENVIRONMENT IS THE SDK'S (`D-IMPL-346`). Before it existed, this script
# and five example test suites each wrote the same 40-95 lines and each reached
# the same private member to bind operator parameters — `CP06C-F-01`,
# `CP13C-F-02`, `CP17-F-06`, `ATM-F-12`, `IBO-F-11`, `UBO-F-12`. Three
# arguments replace all of it, and the engine still checks everything the
# environment returns: a wrong plan fails the step sequence, a wrong parameter
# set fails the parameter hash, a wrong envelope fails the content address.
def recorded_environment(*, opened: Any, fabric: Any, record: DecisionReplayRecord) -> RecordedEnvironment:
    """The supported environment for `record`, built from the deployment it names."""
    return RecordedEnvironment(record=record, opened=opened, fabric=fabric)
# --8<-- [end:environment]


@contextmanager
def _reopened_fabric(opened: Any, tree: Path) -> Iterator[Any]:
    """The question's own minted substrate, reopened as the replay reader.

    The record pins a snapshot boundary; the reader is scoped to it by the
    engine before anything reads through it. What is reopened is the substrate
    the question was answered on — never a fresh acquisition.
    """
    from ccf.deployment import load_config_and_boot

    substrate = yaml.safe_load((tree / "ccf_environment.yaml").read_text(encoding="utf-8"))["substrate"]
    minted = sorted(opened.scratch.glob(f"{substrate['prefix']}*{substrate['suffix']}"))[-1]
    fabric = load_config_and_boot(opened.config_path, registry=opened.control_plane, connection={"database_path": str(minted)})
    try:
        yield fabric
    finally:
        fabric.handle.close()


def _record_address(opened: Any, outcome: Any) -> str:
    """The RECORD's address — where the determination landed, served or refused."""
    if isinstance(outcome, RefusalEnvelope):
        store = FileArtifactStore(root=opened.scratch / opened.replay.store_dirname)
        return store.resolve_uri(uri=outcome.replay_reference)
    return outcome.replay_ref.content_address


# --8<-- [start:reconstruct]
def reconstruct(*, tree: Path, opened: Any, produce: Any, outcome: Any) -> None:
    """Reproduce the determination `outcome` records, through the SDK's engine."""
    from ccf.replay.engine import replay, replay_refusal
    store = FileArtifactStore(root=opened.scratch / opened.replay.store_dirname)
    record_address = _record_address(opened, outcome)
    record = DecisionReplayRecord.model_validate_json(store.get(content_address=record_address))
    with _reopened_fabric(opened, tree) as fabric:
        environment = recorded_environment(opened=opened, fabric=fabric, record=record)
        shared = {"record_address": record_address, "store": store, "reader": fabric.handle.reader, "control_plane": opened.control_plane, "environment": environment}
        if isinstance(outcome, RefusalEnvelope):
            # A REFUSAL is reconstructed positively — the recorded refusal held
            # to the recorded evidence — and never rehydrated into a product.
            reconstructed = replay_refusal(**shared)
            print(f"record address     : {record_address}")
            print(f"refused            : {outcome.kind} / {outcome.reason}")
            print(f"reconstructed      : {type(reconstructed).__name__} — the recorded refusal, held to its evidence")
            return
        # A SERVED product is re-executed and rehydrated, and the engine holds
        # the rebuilt product to the PRODUCT address the record names.
        replayed = replay(**shared)
    product_address = content_hash(outcome.product)
    print(f"record address     : {record_address}")
    print(f"product address    : {product_address}")
    print(f"replayed to        : {replayed.product_content_address}")
    print(f"identical bytes    : {replayed.product_content_address == product_address}")
    print(f"anchor held        : ttl_anchor_at={replayed.product.ttl_anchor_at} expires_at={replayed.product.expires_at.isoformat()}")
# --8<-- [end:reconstruct]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tree", default="examples/cp-06-canonical-collateral-and-setoff-coverage")
    parser.add_argument("--subject", default="FAC-5B8418")
    parser.add_argument("--intent", default="lgd-assessment")
    parser.add_argument("--freshness", default="as-filed")
    parser.add_argument("--asked-at", default="2026-09-07T12:00:00+00:00")
    parser.add_argument("--parameters", default='{"facility_id": "FAC-5B8418", "borrower_scope": ["2549001IGRCG4F0RLD36"]}')
    parser.add_argument("--refuse", action="store_true", help="ask with a scope nobody holds, and reconstruct the refusal")
    parsed = parser.parse_args(argv[1:])

    tree = (REPO_ROOT / parsed.tree).resolve()
    sys.path.insert(0, str(tree))
    produce = importlib.import_module("produce")
    parameters = json.loads(parsed.parameters)
    if parsed.refuse:
        parameters = {**parameters, "borrower_scope": ["A-SCOPE-NOBODY-HOLDS"]}

    with tempfile.TemporaryDirectory(prefix="replay-") as scratch, produce.product(Path(scratch)) as opened:
        asked = opened.question(
            subject=parsed.subject, asked_at=datetime.fromisoformat(parsed.asked_at),
            intent=parsed.intent, freshness=parsed.freshness, parameters=parameters,
        )
        outcome = opened.answer(asked)
        kind = "REFUSED" if isinstance(outcome, RefusalEnvelope) else "SERVED"
        print(f"question           : {parsed.subject} at {parsed.asked_at} -> {kind}")
        reconstruct(tree=tree, opened=opened, produce=produce, outcome=outcome)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
