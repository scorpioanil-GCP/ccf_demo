"""Fluree client for the v2 ledger (4.2.4 since 2026-10-15; written for 4.1.4).

API shape, established by probing the deployed instance (4.1.4) and re-proven
by the full suite against 4.2.4 at the cutover. It differs
from the v3-era form the v1 scripts used, and from Fluree's own older docs:

    GET  /v1/fluree/ledgers    list ledgers
    POST /v1/fluree/create     {"ledger": "<name>"}
    POST /v1/fluree/query      Content-Type: application/sparql-query
                               ledger via `FROM <alias>` or Fluree-Ledger header
    POST /v1/fluree/update     Content-Type: application/sparql-update
                               ledger via Fluree-Ledger header

Two traps worth knowing:

1. A query WITHOUT a `FROM` clause returns HTTP 500
   ("Missing dataset specification"), not a helpful 400.
2. SPARQL UPDATE sent to /v1/fluree/query is refused — the endpoints are
   split by operation, and the error only says so if you read the body.

The v2 ledger is a **separate ledger**, not a branch of v1's. `fibo:main` is a
name:branch alias, so a `fibo:v2` alias would have been a *branch of the v1
ledger*. `fibo-v2` is its own ledger and cannot interact with `fibo` at all.

Fluree is append-only. A DELETE is a retraction that changes current state
while preserving history — which is exactly what covenant-in-force-as-of
relies on, and also why a write to the wrong ledger could not be undone.
"""

from __future__ import annotations

import requests

from ccf.config import (
    FLUREE_LEDGER_V1,
    FLUREE_LEDGER_V2,
    FLUREE_URL,
    ProtectedResourceError,
)

QUERY_ENDPOINT = f"{FLUREE_URL}/v1/fluree/query"
UPDATE_ENDPOINT = f"{FLUREE_URL}/v1/fluree/update"
CREATE_ENDPOINT = f"{FLUREE_URL}/v1/fluree/create"
LEDGERS_ENDPOINT = f"{FLUREE_URL}/v1/fluree/ledgers"


class FlureeError(RuntimeError):
    pass


def list_ledgers() -> list[dict]:
    resp = requests.get(LEDGERS_ENDPOINT, timeout=15)
    resp.raise_for_status()
    return resp.json()


def ledger_t(ledger: str = FLUREE_LEDGER_V2) -> int | None:
    """Current transaction number, the exact replay anchor for graph_snapshot_at."""
    name = ledger.split(":")[0]
    for entry in list_ledgers():
        if entry.get("name") == name:
            return entry.get("t")
    return None


def create_ledger(ledger: str) -> dict:
    _guard(ledger)
    resp = requests.post(
        CREATE_ENDPOINT, json={"ledger": ledger}, timeout=60
    )
    if resp.status_code >= 400:
        raise FlureeError(f"create failed {resp.status_code}: {resp.text[:200]}")
    return resp.json()


def query(sparql: str, ledger: str = FLUREE_LEDGER_V2) -> dict:
    """Run a SPARQL SELECT. Read-only, so any ledger is permitted.

    A FROM clause is injected when absent — Fluree returns an unhelpful 500
    rather than a 400 if the dataset is unspecified.
    """
    if "FROM" not in sparql.upper():
        raise FlureeError(
            f"SPARQL query needs an explicit FROM <{ledger}>; "
            "Fluree returns HTTP 500 without it."
        )
    resp = requests.post(
        QUERY_ENDPOINT,
        headers={"Content-Type": "application/sparql-query"},
        data=sparql.encode("utf-8"),
        timeout=60,
    )
    if resp.status_code >= 400:
        raise FlureeError(f"query failed {resp.status_code}: {resp.text[:300]}")
    return resp.json()


def _guard(ledger: str) -> str:
    if ledger.split(":")[0] == FLUREE_LEDGER_V1.split(":")[0]:
        raise ProtectedResourceError(
            f"Refusing to write to '{ledger}'. It resolves to the v1 ledger "
            f"'{FLUREE_LEDGER_V1}', which is preserved as a comparison "
            "baseline. Fluree is append-only, so this could not be undone."
        )
    if ledger != FLUREE_LEDGER_V2:
        raise ProtectedResourceError(
            f"Refusing to write to '{ledger}'. v2 writes only to "
            f"'{FLUREE_LEDGER_V2}'."
        )
    return ledger


def update(sparql: str, ledger: str = FLUREE_LEDGER_V2) -> dict:
    """Run a SPARQL UPDATE (INSERT DATA / DELETE DATA). Guarded to v2."""
    _guard(ledger)
    resp = requests.post(
        UPDATE_ENDPOINT,
        headers={
            "Content-Type": "application/sparql-update",
            "Fluree-Ledger": ledger,
        },
        data=sparql.encode("utf-8"),
        timeout=120,
    )
    if resp.status_code >= 400:
        raise FlureeError(f"update failed {resp.status_code}: {resp.text[:300]}")
    return resp.json()


def stable_scalar(sparql: str, *, attempts: int = 6, delay: float = 0.75,
                  ledger: str = FLUREE_LEDGER_V2) -> int:
    """Read one aggregate, retrying until CONSECUTIVE READS AGREE.

    A verification query issued immediately after `INSERT DATA` can be served
    before the index catches up. Observed 2026-08-22 (Wave 13b Task 4): three
    aggregates over the same freshly-written predicate, run back to back,
    returned 40 distinct subjects, **0** rows, and 40 typed nodes. The 0 was
    the index, not the data — a re-run reported 150, and the ledger had held
    150 the whole time.

    The retry condition is **stability, not correctness**. Retrying until the
    number matches what the caller expects would be a check that cannot fail,
    which is this estate's most-repeated defect (`known-issues.md` §12). This
    function has no idea what the caller expects; it returns as soon as the
    store says the same thing twice, and the comparison happens once,
    afterwards, in the caller.
    """
    import time

    previous: int | None = None
    for attempt in range(attempts):
        rows = query(sparql, ledger)["results"]["bindings"]
        current = int(rows[0][next(iter(rows[0]))]["value"]) if rows else 0
        if previous is not None and current == previous:
            return current
        previous = current
        if attempt < attempts - 1:
            time.sleep(delay)
    return previous if previous is not None else 0


def count_triples(ledger: str = FLUREE_LEDGER_V2) -> int:
    result = query(
        f"SELECT (COUNT(*) AS ?n) FROM <{ledger}> WHERE {{ ?s ?p ?o }}", ledger
    )
    rows = result.get("results", {}).get("bindings", [])
    return int(rows[0]["n"]["value"]) if rows else 0


def types_present(ledger: str = FLUREE_LEDGER_V2) -> list[tuple[str, int]]:
    """rdf:type census. Useful for the no-OWL-inference check: a query for
    Party returns only entities *explicitly* typed Party."""
    result = query(
        f"SELECT ?t (COUNT(?s) AS ?n) FROM <{ledger}> "
        "WHERE { ?s a ?t } GROUP BY ?t ORDER BY DESC(?n)",
        ledger,
    )
    return [
        (b["t"]["value"], int(b["n"]["value"]))
        for b in result.get("results", {}).get("bindings", [])
    ]


def ensure_ledger(ledger: str = FLUREE_LEDGER_V2) -> bool:
    """Create the ledger if absent. Returns True if it was created."""
    _guard(ledger)
    name = ledger.split(":")[0]
    if any(e.get("name") == name for e in list_ledgers()):
        return False
    create_ledger(ledger)
    return True


# ===========================================================================
# The co-lender fabric
# ===========================================================================
#
# A separate Fluree instance, reached by its own URL and writing its own
# ledger. Kept as distinct functions rather than a `fabric=` parameter on the
# existing ones, deliberately: every one of the twenty-odd loaders in this
# repository calls `query()` and `update()` with no fabric argument, and a
# defaulted parameter is exactly how a local loader ends up writing to the
# peer when someone changes a default. Crossing the boundary should require
# typing a different function name.


def _co_lender_endpoints() -> dict[str, str]:
    from ccf.config import CO_LENDER_FLUREE_URL, _require_co_lender

    _require_co_lender()
    base = CO_LENDER_FLUREE_URL.rstrip("/")
    return {
        "query": f"{base}/v1/fluree/query",
        "update": f"{base}/v1/fluree/update",
        "create": f"{base}/v1/fluree/create",
        "ledgers": f"{base}/v1/fluree/ledgers",
    }


def _co_lender_guard(ledger: str) -> str:
    """Refuse a peer write aimed at one of OUR ledgers.

    The mirror of `_guard`. Both are allowlists, so neither fabric can write
    the other's ledger even if the URLs were swapped in `.env`.
    """
    from ccf.config import (
        CO_LENDER_FLUREE_LEDGER,
        FabricBoundaryError,
        assert_distinct_fabrics,
    )

    assert_distinct_fabrics()
    if ledger.split(":")[0] in (FLUREE_LEDGER_V2.split(":")[0],
                                FLUREE_LEDGER_V1.split(":")[0]):
        raise FabricBoundaryError(
            f"Refusing to write {ledger!r} on the co-lender fabric. That is "
            f"one of OUR ledgers, and Fluree is append-only."
        )
    if ledger != CO_LENDER_FLUREE_LEDGER:
        raise FabricBoundaryError(
            f"Refusing to write {ledger!r}. The co-lender fabric writes only "
            f"to {CO_LENDER_FLUREE_LEDGER!r}."
        )
    return ledger


def co_lender_query(sparql: str, ledger: str | None = None) -> dict:
    """Run a SPARQL SELECT against the PEER fabric. Read-only, never local."""
    from ccf.config import CO_LENDER_FLUREE_LEDGER, assert_distinct_fabrics

    assert_distinct_fabrics()
    ledger = ledger or CO_LENDER_FLUREE_LEDGER
    if "FROM" not in sparql.upper():
        raise FlureeError(
            f"SPARQL query needs an explicit FROM <{ledger}>; "
            "Fluree returns HTTP 500 without it."
        )
    resp = requests.post(
        _co_lender_endpoints()["query"],
        headers={"Content-Type": "application/sparql-query"},
        data=sparql.encode("utf-8"),
        timeout=60,
    )
    if resp.status_code >= 400:
        raise FlureeError(
            f"co-lender query failed {resp.status_code}: {resp.text[:300]}")
    return resp.json()


def co_lender_update(sparql: str, ledger: str | None = None) -> dict:
    """Run a SPARQL UPDATE against the PEER fabric. Guarded to its ledger."""
    from ccf.config import CO_LENDER_FLUREE_LEDGER

    ledger = _co_lender_guard(ledger or CO_LENDER_FLUREE_LEDGER)
    resp = requests.post(
        _co_lender_endpoints()["update"],
        headers={
            "Content-Type": "application/sparql-update",
            "Fluree-Ledger": ledger,
        },
        data=sparql.encode("utf-8"),
        timeout=120,
    )
    if resp.status_code >= 400:
        raise FlureeError(
            f"co-lender update failed {resp.status_code}: {resp.text[:300]}")
    return resp.json()


def co_lender_ledger_t() -> int | None:
    """The peer's own ledger `t` — the replay anchor in federated lineage.

    §B of `syndicated-lending-co-lender` makes this the point of the boundary:
    a federated product carries a REFERENCE to the peer's lineage, never the
    peer's operator plan. The peer's `t` is what makes that reference
    verifiable rather than a claim.
    """
    from ccf.config import CO_LENDER_FLUREE_LEDGER

    for entry in requests.get(_co_lender_endpoints()["ledgers"],
                              timeout=15).json():
        if entry.get("name") == CO_LENDER_FLUREE_LEDGER.split(":")[0]:
            return entry.get("t")
    return None
