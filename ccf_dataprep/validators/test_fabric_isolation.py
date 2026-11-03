#!/usr/bin/env python3
"""Prove the two fabrics cannot reach each other.

    uv run validators/test_fabric_isolation.py

`syndicated-lending-co-lender` §C requires a second CCF instance, and its own
prose is blunt: *"A2A cannot be demonstrated against one fabric."* The whole
product rests on a property that is trivial to break by accident — **our
queries must not be able to reach the peer's data except through the
negotiated interface.**

What is protected is not the data. A stray write to the peer is recoverable.
What is not recoverable is the **claim**: if a loader on our side can read or
write the peer's tables, then the co-lender's policy envelope was never
enforced by anything, and every federation result is an artifact of a shared
connection rather than a negotiated one. Nothing about that failure announces
itself — every connection succeeds and every query returns rows.

**This file runs BEFORE the peer instance exists, and that is the point.** Every
arm here tests a guard's refusal, and a refusal needs no server. When the
instance is provisioned, these same arms keep holding.

Arm 7 is the falsification: a correctly-distinct configuration must PASS. A
guard that refuses every configuration is as useless as one that refuses none,
and only that arm tells them apart.
"""

from __future__ import annotations

import sys
from contextlib import contextmanager

from ccf import config, fluree
from ccf.config import (
    CoLenderNotConfigured,
    FabricBoundaryError,
    ProtectedResourceError,
)

#: A configuration that is genuinely two fabrics. Arm 7 requires it to pass;
#: arms 2–4 mutate one field of it at a time and require a refusal.
DISTINCT = {
    "CO_LENDER_FLUREE_URL": "http://192.168.4.77:8090",
    "CO_LENDER_FLUREE_LEDGER": "colender-main",
    "CO_LENDER_PG": {"host": "192.168.4.77", "port": "5432",
                     "dbname": "colenderdb", "user": "colender",
                     "password": "x"},
    "CO_LENDER_PG_SCHEMA": "colender",
    "CO_LENDER_MONGO_URI": None,
    "CO_LENDER_MONGO_DB": "colender",
}


@contextmanager
def configured(**overrides):
    """Temporarily present a peer configuration, then put it back."""
    settings = {**DISTINCT, **overrides}
    saved = {k: getattr(config, k) for k in settings}
    try:
        for k, v in settings.items():
            setattr(config, k, v)
        yield
    finally:
        for k, v in saved.items():
            setattr(config, k, v)


def expect_raise(label: str, exc, fn) -> bool:
    try:
        fn()
    except exc as e:
        print(f"    ok    {label}: {type(e).__name__} — {str(e)[:74]}")
        return True
    except Exception as e:  # noqa: BLE001
        print(f"    FAIL  {label}: raised {type(e).__name__}, expected "
              f"{exc.__name__} — {str(e)[:60]}")
        return False
    print(f"    FAIL  {label}: did NOT raise")
    return False


#: An explicitly EMPTY peer configuration. Arm 1 must impose this rather than
#: assume it -- see the comment in `check_unconfigured`.
UNCONFIGURED = {
    "CO_LENDER_FLUREE_URL": None,
    "CO_LENDER_FLUREE_LEDGER": "colender-main",
    "CO_LENDER_PG": {"host": None, "port": "5432", "dbname": "colenderdb",
                     "user": None, "password": None},
    "CO_LENDER_MONGO_URI": None,
    "CO_LENDER_MONGO_DB": "colender",
}


def check_unconfigured() -> bool:
    """An unconfigured peer must refuse, and never fall back to us.

    This arm CLEARS the configuration explicitly. It did not always: until
    2026-08-23 it called the guards directly and relied on the ambient
    environment happening to be empty, which it was for as long as no peer
    fabric existed. So it reported green for eleven waves while testing
    nothing -- and it failed the moment a real peer was provisioned, which is
    precisely the moment it needed to work.

    That is this project's dominant defect shape (`known-issues.md` §12) in
    the worst possible place: a validator whose entire job is proving the
    fabric boundary is a control rather than a convention. A check that
    depends on ambient state is measuring the environment, not the code.
    """
    print("\n1 · an unconfigured peer refuses, and never falls back to us")
    with configured(**UNCONFIGURED):
        ok = expect_raise("co_lender_pg_connect", CoLenderNotConfigured,
                          lambda: config.co_lender_pg_connect())
        ok &= expect_raise("co_lender_query", CoLenderNotConfigured,
                           lambda: fluree.co_lender_query(
                               "SELECT ?s FROM <x> WHERE { ?s ?p ?o }"))
        # The dangerous version of this failure is a SILENT fallback: a
        # federation demonstration run entirely against one store, reporting
        # success.
        if config.co_lender_configured():
            print("    FAIL  co_lender_configured() is True with nothing set")
            ok = False
    return bool(ok)


def check_same_database() -> bool:
    print("\n2 · a peer pointed at OUR database is refused")
    with configured(CO_LENDER_PG={**DISTINCT["CO_LENDER_PG"],
                                  "host": config.PG["host"],
                                  "port": str(config.PG["port"]),
                                  "dbname": config.PG["dbname"]}):
        return expect_raise("assert_distinct_fabrics", FabricBoundaryError,
                            config.assert_distinct_fabrics)


def check_same_role() -> bool:
    print("\n3 · a peer connecting as OUR role is refused")
    # A separate database is not enough. That role can reach ours whether or
    # not it is pointed at it today, so the boundary would be a convention.
    with configured(CO_LENDER_PG={**DISTINCT["CO_LENDER_PG"],
                                  "user": config.PG["user"]}):
        return expect_raise("assert_distinct_fabrics", FabricBoundaryError,
                            config.assert_distinct_fabrics)


def check_same_ledger() -> bool:
    print("\n4 · a peer writing OUR ledger is refused")
    ok = True
    with configured(CO_LENDER_FLUREE_LEDGER=config.FLUREE_LEDGER_V2):
        ok &= expect_raise("assert_distinct_fabrics", FabricBoundaryError,
                           config.assert_distinct_fabrics)
    with configured():
        ok &= expect_raise("_co_lender_guard('fibo-v2')", FabricBoundaryError,
                           lambda: fluree._co_lender_guard("fibo-v2"))
        ok &= expect_raise("_co_lender_guard('fibo:main')", FabricBoundaryError,
                           lambda: fluree._co_lender_guard("fibo:main"))
    return bool(ok)


def check_local_refuses_peer() -> bool:
    print("\n5 · OUR guards refuse the peer's namespaces")
    # These are allowlists, so they refused the peer before it existed. Tested
    # anyway: "it happens to work" and "it is guaranteed" look identical until
    # someone widens an allowlist.
    ok = expect_raise("assert_v2_schema('colender')", ProtectedResourceError,
                      lambda: config.assert_v2_schema("colender"))
    ok &= expect_raise("fluree._guard('colender-main')", ProtectedResourceError,
                       lambda: fluree._guard("colender-main"))
    ok &= expect_raise("mongo_db('colender')", ProtectedResourceError,
                       lambda: config.mongo_db("colender"))
    return bool(ok)


def check_peer_refuses_local() -> bool:
    print("\n6 · the PEER's guards refuse our namespaces")
    with configured():
        ok = expect_raise("assert_co_lender_schema('ccf_v2')",
                          FabricBoundaryError,
                          lambda: config.assert_co_lender_schema("ccf_v2"))
        ok &= expect_raise("assert_co_lender_schema('public')",
                           FabricBoundaryError,
                           lambda: config.assert_co_lender_schema("public"))
    return bool(ok)


def check_distinct_config_passes() -> bool:
    print("\n7 · falsification — a genuinely distinct configuration PASSES")
    with configured():
        try:
            config.assert_distinct_fabrics()
        except Exception as e:  # noqa: BLE001
            print(f"    FAIL  a correct configuration was refused: "
                  f"{type(e).__name__} — {str(e)[:70]}")
            print("          the guard refuses everything and proves nothing")
            return False
        if config.assert_co_lender_schema("colender") != "colender":
            print("    FAIL  the peer's own schema was not accepted")
            return False
        if fluree._co_lender_guard("colender-main") != "colender-main":
            print("    FAIL  the peer's own ledger was not accepted")
            return False
    print("    ok    distinct host, database, role and ledger all accepted — "
          "arms 2-6 discriminate")
    return True


def main() -> int:
    print("Fabric isolation — the co-lender cannot be reached by accident")
    print(f"  ours: {config.PG['dbname']}/{config.PG_SCHEMA_V2} · "
          f"{config.FLUREE_LEDGER_V2} · {config.MONGO_DB_V2}")
    print(f"  peer configured: {config.co_lender_configured()}")

    results = [
        check_unconfigured(),
        check_same_database(),
        check_same_role(),
        check_same_ledger(),
        check_local_refuses_peer(),
        check_peer_refuses_local(),
        check_distinct_config_passes(),
    ]
    print(f"\n{sum(results)}/{len(results)} arms green")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
