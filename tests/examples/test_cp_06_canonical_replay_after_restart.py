# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""A cp-06C decision answered from the live estate is reconstituted after a restart (`D-IMPL-383`).

Dave, 2026-10-15 22:36: *"Let's make sure we can reconsitute a decision replay
record as a test."* — after the estate's Fluree moved to `4.2.4` (`D-IMPL-384`).

The paved-fixture proof (`tests/replay/test_replay_evidence_383.py`) replaces
acquisition with a stub. This one does not: the first opening reads the CURATED
estate (Fluree `fibo-v2`, PostgreSQL `ccf_v2`, read-only, seeding nothing), so the
graph each question closes was built from real Fluree `4.2.4` answers. The
second opening of the SAME ``evidence_root`` — over a new, empty scratch, as a
restarted process's temporary directory would be (Dave, 2026-10-16) — is the
restarted service, and its sources point at an address nothing listens on — a
replay that reached a source would fail to connect, so a passing replay read
only the retained evidence.

Three decisions, one of each kind the reviewer named: served; refused after the
graph was built (the facility whose freshest valuation is outside the appraisal
window); refused before any graph (an address this product does not serve).
"""

from __future__ import annotations

import contextlib
import os
import pathlib
import sys
from collections.abc import Iterator, Mapping
from datetime import UTC, datetime
from typing import Any

import httpx
import psycopg
import pytest

from ccf.contracts.canonical import content_hash
from ccf.products.product import OpenedProduct
from ccf.products.refusal import RefusalEnvelope
from ccf.replay.engine import RefusalReplayOutcome, ReplayOutcome
from ccf.replay.evidence import ReplayEvidenceUnavailable
from ccf.replay.serve import ServedProduct

pytestmark = [pytest.mark.fluree, pytest.mark.postgres]

EXAMPLE = pathlib.Path(__file__).resolve().parents[2] / "examples" / "cp-06-canonical-collateral-and-setoff-coverage"
COLLIDING = ("acquisition", "deployment", "produce", "projection", "serve", "server")
ESTATE_VARIABLES = (
    "CCF_CP_06C_FLUREE_URL", "CCF_CP_06C_FLUREE_LEDGER",
    "CCF_CP_06C_POSTGRES_DSN", "CCF_CP_06C_POSTGRES_SCHEMA",
)
ESTATE_REQUIRED = "CCF_REQUIRE_ESTATE"
#: Nothing listens here: the restarted service's sources are unreachable.
UNREACHABLE_FLUREE = "http://127.0.0.1:9"
UNREACHABLE_POSTGRES = "postgresql://nobody@127.0.0.1:9/none?connect_timeout=1"

CP14_INSTANT = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)
INTENT, FRESHNESS = "lgd-assessment", "as-filed"
SERVED_FACILITY, SERVED_SCOPE = "FAC-5B8418", "2549001IGRCG4F0RLD36"
EXPIRED_FACILITY, EXPIRED_SCOPE = "FAC-D3D1A4", "B3BS7ACMDUWISF18KY76"


@pytest.fixture(scope="module")
def estate() -> dict[str, str]:
    """The CURATED estate, read-only, seeding nothing."""
    missing = [n for n in ESTATE_VARIABLES if not os.environ.get(n)]
    if missing:
        message = f"the curated estate is not configured: {', '.join(missing)} unset"
        if os.environ.get(ESTATE_REQUIRED):
            pytest.fail(message)
        pytest.skip(message)
    return {name: os.environ[name] for name in ESTATE_VARIABLES}


@pytest.fixture(scope="module")
def modules() -> Iterator[dict[str, Any]]:
    saved = {n: sys.modules.pop(n, None) for n in COLLIDING}
    sys.path.insert(0, str(EXAMPLE))
    try:
        import deployment  # noqa: PLC0415
        import produce  # noqa: PLC0415
        from server import serve as door  # noqa: PLC0415

        assert pathlib.Path(deployment.__file__).parent == EXAMPLE, "the eviction did not hold"
        yield {"deployment": deployment, "produce": produce, "door": door}
    finally:
        sys.path.remove(str(EXAMPLE))
        for name in COLLIDING:
            sys.modules.pop(name, None)
            if saved[name] is not None:
                sys.modules[name] = saved[name]


def _question(opened: OpenedProduct, deployment: Any, facility: str, scope: str) -> Any:
    return opened.question(
        subject=facility, asked_at=CP14_INSTANT, intent=INTENT, freshness=FRESHNESS,
        parameters={deployment.FACILITY: facility, deployment.BORROWER_SCOPE: [scope]},
    )


@contextlib.contextmanager
def _service(modules: dict[str, Any], evidence: pathlib.Path, environ: Mapping[str, str]) -> Iterator[tuple[OpenedProduct, pathlib.Path]]:
    """One run of the bank service: the launcher reads ``CCF_REPLAY_EVIDENCE_ROOT``, validates it and
    passes it as ``evidence_root=``, over a NEW temporary scratch each run (Dave, 2026-10-16)."""
    door, produce = modules["door"], modules["produce"]
    with door.door_roots({door.EVIDENCE_ROOT_VARIABLE: str(evidence)}) as (scratch, evidence_root):
        assert evidence_root == evidence and scratch != evidence
        with produce.product(scratch, evidence_root=evidence_root, environ=environ) as opened:
            yield opened, scratch


def _address(opened: OpenedProduct, outcome: ServedProduct | RefusalEnvelope) -> str:
    if isinstance(outcome, ServedProduct):
        return outcome.replay_ref.content_address
    return opened.artifact_store.resolve_uri(uri=outcome.replay_reference)


def test_a_live_decision_is_reconstituted_after_a_restart_with_the_sources_unreachable(
    estate: dict[str, str], modules: dict[str, Any], tmp_path: pathlib.Path
) -> None:
    deployment = modules["deployment"]
    evidence = tmp_path / "evidence"
    evidence.mkdir(mode=0o700)

    # --- the first run of the service: real answers from the live estate ---------------
    with _service(modules, evidence, estate) as (opened, first_scratch):
        served = opened.answer(_question(opened, deployment, SERVED_FACILITY, SERVED_SCOPE))
        assert isinstance(served, ServedProduct), getattr(served, "detail", served)
        refused_after = opened.answer(_question(opened, deployment, EXPIRED_FACILITY, EXPIRED_SCOPE))
        assert isinstance(refused_after, RefusalEnvelope), refused_after
        refused_before = opened.resolve(
            tenant=opened.tenant_id, product_class="no.such-class", version="1.0.0",
            perspective=opened.default_perspective,
            request=_question(opened, deployment, SERVED_FACILITY, SERVED_SCOPE),
        )
        assert isinstance(refused_before, RefusalEnvelope), refused_before

        originals = {
            "served": (_address(opened, served), opened.record_of(served)),
            "after": (_address(opened, refused_after), opened.record_of(refused_after)),
            "before": (_address(opened, refused_before), opened.record_of(refused_before)),
        }
        assert opened.evidence.incomplete() == [], "every decision finished publishing its evidence"
        assert not list(first_scratch.rglob("*.sqlite3")), "no graph was left in the run's scratch"

    graphs = sorted(p.name for p in evidence.rglob("*.sqlite3"))
    assert len(graphs) == 2, f"two questions reached a graph, one did not: {graphs}"
    assert not first_scratch.exists(), "the run's scratch was temporary"

    # --- the restarted service: same evidence root, new scratch, sources unreachable ---
    offline = {
        **estate,
        "CCF_CP_06C_FLUREE_URL": UNREACHABLE_FLUREE,
        "CCF_CP_06C_POSTGRES_DSN": UNREACHABLE_POSTGRES,
    }
    with _service(modules, evidence, offline) as (restarted, _):
        for name, (address, original) in originals.items():
            # The record itself, reconstituted from the store by its address alone.
            assert restarted.artifact_store.exists(content_address=address), name
            entry = restarted.evidence.entry(address)
            assert entry is not None, f"{name}: no evidence mapping after restart"
            assert entry.graph_required is (name != "before"), name

        # FIRST, the pre-graph refusal: nothing has booted in this opening yet, the
        # ordering that hid a `ReplayUnresolvable` until the close-panel fixes.
        first = restarted.replay_decision(originals["before"][0])
        assert isinstance(first, RefusalReplayOutcome), first

        reproduced = restarted.replay_decision(originals["served"][0])
        assert isinstance(reproduced, ReplayOutcome), reproduced
        assert reproduced.record == originals["served"][1], "the reconstituted record is the original"
        assert reproduced.product_content_address == content_hash(served.product)
        assert reproduced.product == served.product, "the reproduced product equals the served one"

        for name in ("after",):
            outcome = restarted.replay_decision(originals[name][0])
            assert isinstance(outcome, RefusalReplayOutcome), (name, outcome)

        listed = {e.subject for e in restarted.evidence.decisions(involving=SERVED_FACILITY)}
        assert listed == {SERVED_FACILITY}, listed

        # Positive control on the offline claim: a NEW question cannot be answered,
        # so the replays above did not quietly reach a source.
        # Measured 2026-10-15: today the unreachable source surfaces as the driver's
        # own connection error rather than a governed refusal; either proves it.
        try:
            fresh: object = restarted.answer(_question(restarted, deployment, SERVED_FACILITY, SERVED_SCOPE))
        except (psycopg.OperationalError, httpx.ConnectError) as unreachable:
            fresh = unreachable
        assert not isinstance(fresh, ServedProduct), "the restarted service's sources were reachable"
        served_entry = restarted.evidence.entry(originals["served"][0])
        assert served_entry is not None
        served_graph = restarted.evidence.graph_path(served_entry)

    # Deleting the served decision's graph affects only that decision.
    served_graph.unlink()
    with _service(modules, evidence, offline) as (again, _):
        with pytest.raises(ReplayEvidenceUnavailable):
            again.replay_decision(originals["served"][0])
        assert isinstance(again.replay_decision(originals["after"][0]), RefusalReplayOutcome)

