import importlib.util
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "vi", Path(__file__).resolve().parents[1] / "verify_install.py")
vi = importlib.util.module_from_spec(spec)
# Register in sys.modules BEFORE exec: verify_install.py uses @dataclass,
# and dataclasses (3.11+) resolves forward-referenced annotations via
# sys.modules[cls.__module__] -- without this line that lookup returns None
# and dataclass() raises AttributeError during class creation.
sys.modules["vi"] = vi
spec.loader.exec_module(vi)


# --- floor: the brief's own Step 1 tests ------------------------------------

def test_check_is_ok_only_when_found_equals_required():
    assert vi.Check("t", 4468, 4468).ok is True
    assert vi.Check("t", 4468, 4467).ok is False


def test_check_reports_both_numbers_so_a_pass_is_evidence():
    line = vi.Check("triples", 87162, 87162).render()
    assert "87162" in line
    assert "PASS" in line
    bad = vi.Check("triples", 87162, 12).render()
    assert "87162" in bad and "12" in bad and "FAIL" in bad


def test_a_missing_value_is_a_failure_not_a_skip():
    # None means "could not read it" — that must never render as a pass.
    assert vi.Check("triples", 87162, None).ok is False


def test_exit_code_is_1_for_failure_and_0_for_all_green():
    assert vi.exit_code([vi.Check("a", 1, 1)]) == 0
    assert vi.exit_code([vi.Check("a", 1, 1), vi.Check("b", 2, 3)]) == 1


def test_connection_failure_is_exit_2_not_exit_1():
    # A store that cannot be reached is an install problem, not a data
    # problem. Reporting it as a data failure sends the reader to the
    # wrong place.
    assert vi.exit_code([vi.Check("a", 1, 1)], unreachable=["mongodb"]) == 2


# --- a missing (None) value renders as a real failure, not a soft skip -----

def test_a_missing_value_renders_as_fail_not_unreadable_pass():
    line = vi.Check("sqlite tables", 8, None).render()
    assert "FAIL" in line
    assert "unreadable" in line
    assert "PASS" not in line


def test_render_report_fails_and_exits_1_when_a_check_is_unreadable():
    checks = [vi.Check("sqlite tables", 8, None)]
    report = vi.render_report(checks, unreachable=[], skipped=[])
    assert "FAIL" in report
    assert "Estate verified" not in report
    assert vi.exit_code(checks, unreachable=[]) == 1


# --- CCF_SKIP_STORES: parsing ------------------------------------------------

def test_parse_skip_stores_handles_blank_and_none():
    assert vi.parse_skip_stores(None) == frozenset()
    assert vi.parse_skip_stores("") == frozenset()
    assert vi.parse_skip_stores("   ") == frozenset()


def test_parse_skip_stores_splits_trims_and_lowercases():
    assert vi.parse_skip_stores("neo4j, Postgres ,MONGO") == {
        "neo4j", "postgres", "mongo"}


def test_parse_skip_stores_canonicalizes_aliases():
    assert vi.parse_skip_stores("mongodb") == {"mongo"}
    assert vi.parse_skip_stores("postgresql,pg") == {"postgres"}
    assert vi.parse_skip_stores("sqlite3") == {"sqlite"}


def test_parse_skip_stores_keeps_unknown_tokens_rather_than_raising():
    # A typo should skip nothing (no store name matches it), not crash the
    # whole verifier over a spelling mistake.
    assert vi.parse_skip_stores("neoo4j") == {"neoo4j"}


# --- CCF_SKIP_STORES: run_all honors it and touches nothing for a skipped
# store (no Check is produced, no connection is attempted) --------------------

def test_run_all_skips_named_stores_without_calling_their_check_fn(monkeypatch):
    # STORE_CHECKS binds the real functions in at import time, so patch the
    # tuple itself with spies -- proves a skipped store's check function is
    # never even invoked (no connection attempted), not merely that its
    # results are discarded afterward.
    called = []

    def make_spy(name):
        def _spy(checks, unreachable):
            called.append(name)
        return _spy

    monkeypatch.setattr(
        vi, "STORE_CHECKS",
        tuple((name, make_spy(name)) for name, _ in vi.STORE_CHECKS))

    checks, unreachable, skipped, unknown_skip = vi.run_all(
        skip=frozenset({"neo4j", "mongo"}))
    assert sorted(skipped) == ["mongo", "neo4j"]
    assert unknown_skip == []
    assert "neo4j" not in called
    assert "mongo" not in called
    assert "fluree" in called
    assert "postgres" in called
    assert "sqlite" in called


# --- CCF_SKIP_STORES: the summary wording must never overclaim -------------

def test_skipped_store_suppresses_estate_verified_wording():
    checks = [vi.Check("a", 1, 1), vi.Check("b", 2, 2)]
    report = vi.render_report(checks, unreachable=[], skipped=["neo4j"])
    assert "Estate verified" not in report
    assert "skipped" in report.lower()
    assert "neo4j" in report
    # Exit code must still be 0: nothing that WAS checked failed.
    assert vi.exit_code(checks, unreachable=[]) == 0


def test_no_skips_and_all_pass_says_estate_verified():
    checks = [vi.Check("a", 1, 1)]
    report = vi.render_report(checks, unreachable=[], skipped=[])
    assert "Estate verified." in report


def test_skipped_stores_are_named_even_when_something_also_fails():
    checks = [vi.Check("a", 1, 2)]
    report = vi.render_report(checks, unreachable=[], skipped=["neo4j"])
    assert "neo4j" in report
    assert "Estate verified" not in report
    assert vi.exit_code(checks, unreachable=[]) == 1


def test_unreachable_report_names_the_store_and_returns_before_estate_line():
    report = vi.render_report([], unreachable=["postgres (OperationalError)"],
                              skipped=[])
    assert "COULD NOT REACH" in report
    assert "postgres" in report
    assert "Estate verified" not in report



# --- Finding 2: exercise the REAL check_fluree / check_mongo functions with
# faked I/O, rather than hand-copied Check(...) literals that never call
# them. A wrong ledger name, wrong SPARQL query, or wrong collection/db
# logic in the implementation must fail these. -------------------------------

class _FakeResponse:
    def __init__(self, payload, ok=True):
        self._payload = payload
        self._ok = ok

    def raise_for_status(self):
        if not self._ok:
            raise RuntimeError("simulated HTTP error")

    def json(self):
        return self._payload


def _fake_requests(ledger_t: dict, triple_counts: dict):
    """Build fake get()/post() callables for the `requests` module.

    `ledger_t` backs GET .../ledgers. `triple_counts` maps a ledger name to
    the SPARQL COUNT(*) string it should answer with; the fake inspects the
    POSTed query body for the ledger name literally, so a real
    implementation change to a DIFFERENT ledger name falls through to the
    "unknown ledger" branch and mismatches the required count -- the test
    fails rather than silently agreeing.
    """
    def fake_get(url, timeout=None):
        return _FakeResponse([{"name": k, "t": v} for k, v in ledger_t.items()])

    def fake_post(url, headers=None, data=None, timeout=None):
        query = data.decode()
        for ledger, count in triple_counts.items():
            if f"<{ledger}>" in query:
                return _FakeResponse(
                    {"results": {"bindings": [{"n": {"value": str(count)}}]}})
        return _FakeResponse({"results": {"bindings": [{"n": {"value": "0"}}]}})

    return fake_get, fake_post


def test_check_fluree_peer_triples_pass_with_faked_http(monkeypatch):
    import requests
    fake_get, fake_post = _fake_requests(
        ledger_t={"fibo-v2": 5112, "fibo": 5, "bofa/syndicate": 16},
        triple_counts={"fibo-v2": 87162, "bofa/syndicate": 10})
    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr(requests, "post", fake_post)

    checks, unreachable = [], []
    vi.check_fluree(checks, unreachable)

    peer = next(c for c in checks if c.name == "fluree bofa/syndicate triples")
    assert peer.found == 10
    assert peer.ok is True


def test_check_fluree_peer_triples_fails_with_faked_http_when_count_wrong(monkeypatch):
    import requests
    fake_get, fake_post = _fake_requests(
        ledger_t={"fibo-v2": 5112, "fibo": 5, "bofa/syndicate": 16},
        # peer content is actually empty -- 0 triples, not 10
        triple_counts={"fibo-v2": 87162, "bofa/syndicate": 0})
    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr(requests, "post", fake_post)

    checks, unreachable = [], []
    vi.check_fluree(checks, unreachable)

    peer = next(c for c in checks if c.name == "fluree bofa/syndicate triples")
    assert peer.found == 0
    assert peer.ok is False


def _fake_mongo_client(v2_collections: dict, v1_collections: dict):
    class FakeCollection:
        def __init__(self, n):
            self._n = n

        def count_documents(self, _filter):
            return self._n

    class FakeDB:
        def __init__(self, collections):
            self._collections = collections

        def list_collection_names(self):
            return list(self._collections.keys())

        def __getitem__(self, name):
            return FakeCollection(self._collections[name])

    class FakeAdmin:
        def command(self, _name):
            return {"ok": 1}

    class FakeClient:
        def __init__(self, uri, serverSelectionTimeoutMS=None):
            self.admin = FakeAdmin()
            self._dbs = {"fibo_v2": FakeDB(v2_collections),
                        "fibo": FakeDB(v1_collections)}

        def __getitem__(self, name):
            return self._dbs[name]

    return FakeClient


def test_check_mongo_v1_collections_pass_with_faked_client(monkeypatch):
    import pymongo
    monkeypatch.setattr(pymongo, "MongoClient", _fake_mongo_client(
        v2_collections={f"c{i}": 1 for i in range(6)},
        v1_collections={"a": 15, "b": 15}))  # 2 collections, 30 docs

    checks, unreachable = [], []
    vi.check_mongo(checks, unreachable)

    coll = next(c for c in checks if c.name == "mongo fibo (v1) collections")
    assert coll.found == 2
    assert coll.ok is True
    docs = next(c for c in checks if c.name == "mongo fibo (v1) documents")
    assert docs.found == 30
    assert docs.ok is True


def test_check_mongo_v1_collections_fails_with_faked_client_when_count_wrong(monkeypatch):
    import pymongo
    monkeypatch.setattr(pymongo, "MongoClient", _fake_mongo_client(
        v2_collections={f"c{i}": 1 for i in range(6)},
        v1_collections={"a": 30}))  # only 1 collection, not 2

    checks, unreachable = [], []
    vi.check_mongo(checks, unreachable)

    coll = next(c for c in checks if c.name == "mongo fibo (v1) collections")
    assert coll.found == 1
    assert coll.ok is False


# --- Finding 1: a query that raises MID-CHECK must render as a FAIL on
# that one check, never crash the run before the remaining checks/stores
# get a chance to report. --------------------------------------------------

def test_check_postgres_survives_a_missing_table_and_still_reports(monkeypatch):
    import psycopg

    class FakeCursor:
        def __init__(self):
            self.calls = 0

        def execute(self, sql):
            self.calls += 1
            if "legal_entity" in sql:
                raise RuntimeError("relation \"ccf_v2.legal_entity\" does not exist")
            self._sql = sql

        def fetchone(self):
            if "server_version" in self._sql:
                return ("16.4",)
            if "table_schema='ccf_v2'" in self._sql and "colender" not in self._sql:
                return (113,)
            if "table_schema='public'" in self._sql:
                return (2,)
            if "crosswalk c" in self._sql:
                return (0,)
            if "crosswalk" in self._sql:
                return (53,)
            if "colender" in self._sql:
                return (2,)
            raise AssertionError(f"unexpected query: {self._sql}")

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    class FakeConn:
        def __init__(self):
            self.rolled_back = False

        def cursor(self):
            return FakeCursor()

        def rollback(self):
            self.rolled_back = True

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    conns = []

    def fake_connect(dsn, connect_timeout=None):
        c = FakeConn()
        conns.append(c)
        return c

    monkeypatch.setattr(psycopg, "connect", fake_connect)

    checks, unreachable = [], []
    vi.check_postgres(checks, unreachable)  # must not raise

    assert unreachable == []
    by_name = {c.name: c for c in checks}
    assert by_name["postgres legal_entity rows"].found is None
    assert by_name["postgres legal_entity rows"].ok is False
    # Checks issued BEFORE and AFTER the broken query still show up and
    # still carry real values -- the crash did not take the whole
    # function down with it.
    assert by_name["postgres ccf_v2 base tables"].found == 113
    assert by_name["postgres crosswalk rows"].found == 53
    assert by_name["postgres peer colender base tables"].found is None or \
        by_name["postgres peer colender base tables"].found == 2


def test_check_sqlite_survives_a_corrupt_file(tmp_path):
    bad = tmp_path / "departmental.sqlite"
    bad.write_bytes(b"not a real sqlite file at all")
    old_path = vi.SQLITE_PATH
    vi.SQLITE_PATH = str(bad)
    try:
        checks, unreachable = [], []
        vi.check_sqlite(checks, unreachable)  # must not raise
    finally:
        vi.SQLITE_PATH = old_path

    assert unreachable == []
    assert len(checks) == 1
    assert checks[0].found is None
    assert checks[0].ok is False


def test_run_all_survives_a_check_function_that_raises_and_still_reports(monkeypatch):
    """Belt and braces: even an UNANTICIPATED crash inside one store's check
    function (not one of the already-guarded query paths) must not prevent
    the other stores from running and reporting."""
    def boom(checks, unreachable):
        raise RuntimeError("totally unexpected bug")

    def make_stub(name):
        def _stub(checks, unreachable):
            checks.append(vi.Check(f"{name} stub", 1, 1))
        return _stub

    patched = tuple(
        (name, boom if name == "postgres" else make_stub(name))
        for name, _ in vi.STORE_CHECKS)
    monkeypatch.setattr(vi, "STORE_CHECKS", patched)

    checks, unreachable, skipped, unknown_skip = vi.run_all(skip=frozenset())

    names = [c.name for c in checks]
    assert "fluree stub" in names
    assert "mongo stub" in names
    assert "sqlite stub" in names
    assert "neo4j stub" in names
    crashed = [c for c in checks if "postgres check crashed unexpectedly" in c.name]
    assert len(crashed) == 1
    assert crashed[0].ok is False
    # The report must still render, and the crash must not be reachable as a
    # PASS.
    report = vi.render_report(checks, unreachable, skipped, unknown_skip)
    assert "PASS" not in report.split("postgres check crashed")[1].split("\n")[0]


# --- Finding 3: zero checks (e.g. every store skipped) must exit non-zero,
# never read as a clean pass. ------------------------------------------------

def test_exit_code_is_1_when_zero_checks_ran():
    assert vi.exit_code([], unreachable=[]) == 1


def test_all_stores_skipped_exits_1_and_says_nothing_was_verified(monkeypatch):
    monkeypatch.setattr(
        vi, "STORE_CHECKS",
        tuple((name, lambda c, u: (_ for _ in ()).throw(
            AssertionError(f"{name} should never be called")))
              for name, _ in vi.STORE_CHECKS))

    checks, unreachable, skipped, unknown_skip = vi.run_all(
        skip=frozenset(vi.KNOWN_STORES))

    assert checks == []
    assert sorted(skipped) == sorted(vi.KNOWN_STORES)
    assert vi.exit_code(checks, unreachable) == 1
    report = vi.render_report(checks, unreachable, skipped, unknown_skip)
    assert "NOTHING WAS VERIFIED" in report
    assert "Estate verified" not in report


# --- Finding 4(a): a mistyped CCF_SKIP_STORES token must warn, not vanish --

def test_run_all_reports_unknown_skip_tokens(monkeypatch):
    def make_spy(name):
        def _spy(checks, unreachable):
            checks.append(vi.Check(f"{name} ran", True, True))
        return _spy

    monkeypatch.setattr(
        vi, "STORE_CHECKS",
        tuple((name, make_spy(name)) for name, _ in vi.STORE_CHECKS))

    checks, unreachable, skipped, unknown_skip = vi.run_all(
        skip=frozenset({"neo4j", "neoo4j"}))

    assert skipped == ["neo4j"]
    assert unknown_skip == ["neoo4j"]
    # everything else still ran
    ran = {c.name for c in checks}
    assert "postgres ran" in ran


def test_unknown_skip_token_appears_as_a_warning_in_the_report():
    report = vi.render_report([vi.Check("a", 1, 1)], unreachable=[],
                              skipped=[], unknown_skip=["neoo4j"])
    assert "WARNING" in report
    assert "neoo4j" in report
    assert "neo4j" in report  # the valid-names list is printed too


# --- Finding 4(b): the run command must say --no-project -------------------

def test_docstring_says_no_project():
    src = Path(__file__).resolve().parents[1].joinpath(
        "verify_install.py").read_text()
    assert "uv run --no-project verify_install.py" in src
    assert "uv run verify_install.py" not in src


# --- fix round 2: check_neo4j had the same defect Finding 1 fixed
# everywhere else -- all three queries funneled through the connect-guard,
# so a content-query failure was reported as unreachable/exit 2 instead of
# a data FAIL/exit 1. -------------------------------------------------------

def test_check_neo4j_content_query_failure_is_a_fail_not_unreachable(monkeypatch):
    import neo4j

    class FakeResult:
        def __init__(self, value=None, raise_exc=None):
            self._value = value
            self._raise_exc = raise_exc

        def single(self):
            if self._raise_exc:
                raise self._raise_exc
            return {"c": self._value}

    class FakeSession:
        def run(self, query):
            # Check `_B1` FIRST: that query's Cypher also contains the
            # substring "count(n)", so order matters here.
            if "_B1" in query:
                return FakeResult(0)
            if "count(n)" in query:
                return FakeResult(14)
            if "count(r)" in query:
                # The connection is fine; THIS query is what fails --
                # e.g. a broken label index, a transient server error.
                return FakeResult(raise_exc=RuntimeError("simulated Cypher error"))
            raise AssertionError(f"unexpected query: {query}")

        def close(self):
            pass

    class FakeDriver:
        def session(self):
            return FakeSession()

        def close(self):
            pass

    def fake_driver_factory(uri, auth=None):
        return FakeDriver()

    monkeypatch.setattr(neo4j.GraphDatabase, "driver", fake_driver_factory)

    checks, unreachable = [], []
    vi.check_neo4j(checks, unreachable)  # must not raise

    # The distinguishing assertion: connect succeeded, so this must NOT be
    # reported as unreachable (exit 2) -- it must be a data FAIL (exit 1).
    assert unreachable == []
    rels = next(c for c in checks if c.name == "neo4j v1 relationships")
    assert rels.found is None
    assert rels.ok is False
    nodes = next(c for c in checks if c.name == "neo4j v1 nodes")
    assert nodes.found == 14
    assert nodes.ok is True
    scaffold = next(c for c in checks
                    if c.name == "neo4j restore scaffolding removed")
    assert scaffold.found == 0
    assert scaffold.ok is True

    assert vi.exit_code(checks, unreachable) == 1
