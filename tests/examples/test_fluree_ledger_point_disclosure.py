"""`LEX-F-04` — which route a rung asks for the ledger point, and what it gets.

**The finding this pins, and the correction it carries.** `LEX-F-04` (cp-21)
concluded that *"the point at which the group was derived is not recoverable
from this estate"*, on two measurements that are both still true:

* the SPARQL endpoint emits **no `x-fdb-t` response header**; and
* **`GET /fluree/ledgers` answers 404.**

**The conclusion does not follow.** Measured 2026-09-22 on the
release-hardening sweep: **`GET /v1/fluree/ledgers` answers 200 and reports
`fibo-v2` at a ledger point.** The estate publishes its watermark; the route
`LEX-F-04` tried was missing the server's `/v1` API-base prefix, which
`/.well-known/fluree.json` names. A correct measurement did not validate its
explanation.

**Consequence, and why it is evidence rather than a repair here.** Five
shipped rungs — cp-16, cp-18, cp-21, cp-23, cp-24 — read the header route and
therefore record `ledger_t: "unreported"` for a watermark that is available.
Two — cp-17 and cp-20 — read the listing route and get the real point.

Correcting the five would change what five shipped products SERVE: the
payload's `ledger_t` value, its content address, and cp-21's `LEX-G21`, which
gates on the disclosure `ledger_point_resolvable: "false"`. That is a product
semantics change, so under the release-hardening scope it is **returned as a
measured defect with a proposed scope, not implemented**. This module makes
the measurement executable so it cannot decay back into prose.

**What is NOT wrong, and is asserted here so it stays that way.** No rung
manufactures a ledger point — every one of them falls back to the literal
`"unreported"` — and no rung confuses the source's watermark with the CCF
snapshot instant the replay record retains. Those two are the durable
invariants; the route is the defect.
"""

from __future__ import annotations

import ast
import os
import pathlib

import httpx
import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLES = REPO_ROOT / "examples"

#: The literal every rung falls back to. Never a number, never an empty string,
#: never the CCF snapshot instant standing in for a source watermark.
UNREPORTED = "unreported"

#: The route the server actually implements, and the one it does not. The
#: `/v1` prefix is the API base `/.well-known/fluree.json` advertises.
WORKING_ROUTE = "/v1/fluree/ledgers"
DEAD_ROUTE = "/fluree/ledgers"

#: Rungs that read the ledger point from the `x-fdb-t` RESPONSE HEADER, which
#: this deployment never emits. They record `unreported` for a watermark that
#: is available (`LEX-F-04`, corrected). Frozen or shipped; not repaired here.
HEADER_ROUTE_RUNGS = (
    "cp-16-abs-securitization-surveillance",
    "cp-18-ib-opportunity-synthesis",
    "cp-21-large-exposure",
    "cp-23-portfolio-early-warning",
    "cp-24-portfolio-what-if",
)

#: Rungs that read the LEDGER LISTING, and get the real point.
LISTING_ROUTE_RUNGS = (
    "cp-17-mnpi-wall-enforcement",
    "cp-20-syndicated-lending-co-lender",
    "peer-cp-20-co-lender",
)

ESTATE_URL = "CCF_CP_20_FLUREE_URL"


def _acquisition(rung: str) -> str:
    return (EXAMPLES / rung / "acquisition.py").read_text(encoding="utf-8")


def test_no_rung_manufactures_a_ledger_point() -> None:
    """`LEX-F-04`'s durable half — the one that is NOT a defect.

    Every rung that reports a ledger point falls back to the literal
    ``unreported`` when the source does not give one. None substitutes a
    plausible number, an empty string, or its own snapshot instant.

    A fabricated watermark would be worse than an absent one: a specific,
    checkable, false claim about the source's state.
    """
    checked = 0
    for rung in HEADER_ROUTE_RUNGS + LISTING_ROUTE_RUNGS:
        source = _acquisition(rung)
        assert UNREPORTED in source, (
            f"{rung} resolves a ledger point and declares no explicit"
            " unavailable value; an absent watermark must be SAID"
        )
        # nothing derives the fallback from the fabric's own clock
        for forbidden in ("asked_at", "datetime.now", "graph_snapshot_at"):
            window = source[max(0, source.find(UNREPORTED) - 400):]
            assert f"{forbidden}" not in window.split("\n\n")[0], (
                f"{rung} appears to derive its ledger-point fallback from"
                f" {forbidden!r}; the source's watermark and the CCF snapshot"
                " instant are two different clocks"
            )
        checked += 1
    assert checked == len(HEADER_ROUTE_RUNGS) + len(LISTING_ROUTE_RUNGS)


def test_the_two_routes_are_used_as_this_module_records() -> None:
    """The roster, enumerated from the tree rather than counted.

    A right count with a wrong member audits clean forever. This reads each
    rung's own acquisition and asserts which route it takes, so the day a
    rung is moved onto the working route this module goes red and the
    correction is made here rather than discovered again.
    """
    for rung in HEADER_ROUTE_RUNGS:
        source = _acquisition(rung)
        assert "x-fdb-t" in source, (
            f"{rung} no longer reads the `x-fdb-t` header; if it moved to"
            f" {WORKING_ROUTE!r}, move it to LISTING_ROUTE_RUNGS and re-measure"
            " what it now serves (`LEX-F-04`)"
        )
    for rung in LISTING_ROUTE_RUNGS:
        source = _acquisition(rung)
        assert WORKING_ROUTE in source, (
            f"{rung} no longer reads {WORKING_ROUTE!r}; it would silently"
            " record `unreported` for an available watermark"
        )
        assert "x-fdb-t" not in source, f"{rung} reads both routes"


@pytest.mark.fluree
def test_the_estate_publishes_a_ledger_point_on_exactly_one_route() -> None:
    """The measurement `LEX-F-04` did not complete, made executable.

    Three facts, and the third is the correction:

    1. the SPARQL response carries **no** `x-fdb-t` header — as recorded;
    2. `GET /fluree/ledgers` answers **404** — as recorded;
    3. `GET /v1/fluree/ledgers` answers **200 with a ledger point** — which
       `LEX-F-04` did not try, and which makes its conclusion that the point
       *"is not recoverable from this estate"* wrong.

    Asserted as a RELATIONSHIP — a point exists and is not the literal
    fallback — never as a pinned value, so ledger growth exercises this
    instead of breaking it.
    """
    url = os.environ.get(ESTATE_URL)
    ledger = os.environ.get("CCF_CP_20_FLUREE_LEDGER")
    if not url or not ledger:
        message = (
            f"the live estate is not configured: {ESTATE_URL} /"
            " CCF_CP_20_FLUREE_LEDGER unset (CLAUDE.md §9)"
        )
        if os.environ.get("CCF_REQUIRE_ESTATE"):
            pytest.fail(message)
        pytest.skip(message)
    base = url.rstrip("/")

    with httpx.Client(timeout=30.0) as client:
        probe = client.post(
            f"{base}/v1/fluree/query",
            headers={"Content-Type": "application/sparql-query"},
            content=f"SELECT ?s FROM <{ledger}> WHERE {{ ?s ?p ?o }} LIMIT 1".encode(),
        )
        assert probe.status_code == 200, probe.text[:200]
        assert "x-fdb-t" not in {name.lower() for name in probe.headers}, (
            "the SPARQL endpoint now emits `x-fdb-t`; the five header-route"
            " rungs would begin reporting a real point, which is a change to"
            " what they SERVE — re-measure before assuming it is an improvement"
        )

        assert client.get(f"{base}{DEAD_ROUTE}").status_code == 404, (
            f"{DEAD_ROUTE!r} now answers; `LEX-F-04`'s second measurement has"
            " moved and this module's roster needs re-deriving"
        )

        listing = client.get(f"{base}{WORKING_ROUTE}")
        assert listing.status_code == 200, listing.text[:200]
        name, _, branch = ledger.partition(":")
        branch = branch or "main"
        points = [
            entry.get("t")
            for entry in listing.json()
            if entry.get("name") == name and entry.get("branch", "main") == branch
        ]
        assert points, (
            f"{WORKING_ROUTE!r} answered but carries no entry for {ledger!r}"
        )
        assert points[0] not in (None, "", UNREPORTED), (
            "the listing carries no usable ledger point, which would restore"
            f" `LEX-F-04`'s conclusion: {points!r}"
        )


def test_the_source_watermark_is_not_the_ccf_snapshot() -> None:
    """The second durable invariant: two clocks, never fused.

    A source store's transaction index and the instant the fabric took its
    own snapshot answer different questions. A payload that served one as the
    other would let a reader reconstruct against the wrong point entirely.

    Asserted structurally: no rung assigns its ledger point from the fabric's
    snapshot field, or the reverse.
    """
    for rung in HEADER_ROUTE_RUNGS + LISTING_ROUTE_RUNGS:
        path = EXAMPLES / rung / "acquisition.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            targets = {
                target.id for target in node.targets if isinstance(target, ast.Name)
            } | {
                target.attr for target in node.targets if isinstance(target, ast.Attribute)
            }
            source_text = ast.unparse(node.value)
            if targets & {"ledger_t", "_watermark", "watermark"}:
                assert "graph_snapshot_at" not in source_text, (
                    f"{rung} assigns its source watermark from the CCF snapshot"
                    f" instant: {source_text[:80]!r}"
                )
