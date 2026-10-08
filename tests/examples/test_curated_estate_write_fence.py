"""The curated estate is READ-ONLY, and the fence that makes it so runs once.

**CLAUDE.md §9 and `D-IMPL-318` state the rule absolutely** — examples and
their tests READ the curated `.76` estate; anything that must WRITE writes to a
local, disposable store named by ``CCF_TEST_FLUREE_URL`` /
``CCF_TEST_POSTGRES_DSN``. *"Nothing seeds `.76`, ever."*

**It was stated, and partly enforced.**
``tests/examples/estate_guard.py::refuse_to_write_the_curated_estate`` refuses
a seed whose target names a curated host — but only for the modules that
import it, and measured 2026-09-22 **two of the nine** modules naming
``CCF_TEST_*`` did.

**And the nine were never the whole exposure.** A test can reach the
disposable store through its example's own ``artifacts/backends.yaml`` without
naming the variable anywhere — which is exactly how
``test_s1_01_governed_resolver_adoption.py`` appended **134 transactions to
the curated `ccf:main` ledger** (``t`` 1474 → 1608) during the
release-hardening sweep, from an environment script that had mapped
``CCF_TEST_FLUREE_URL`` onto ``.76`` by pattern. Fluree is append-only, so
those transactions are permanent. No per-module call site could have caught
it: the module never mentions the variable.

So the fence moved to ``tests/conftest.py`` as a session-scoped autouse
fixture. It runs **once, before any test can write**, and refuses the run
rather than a call. This module proves it — in subprocesses, because by the
time a test in this session executes, the fence has already passed for this
session.
"""

from __future__ import annotations

import ipaddress
import json
import os
import pathlib
import socket
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

#: A node that neither reads nor writes an estate, so the ONLY thing that can
#: stop the session is the fence itself.
INERT_NODE = (
    "tests/examples/test_product_tree_import_isolation.py"
    "::test_every_shipped_binder_owns_its_process_or_proves_what_it_loaded"
)

CURATED = "192.168.4.76"


def _run(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pytest", INERT_NODE, "-q", "-p", "no:randomly"],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=300,
        env={**os.environ, **env},
    )


def test_a_disposable_fluree_on_a_curated_host_refuses_the_whole_session() -> None:
    """The exact misconfiguration that wrote to `ccf:main`, now refused.

    The fence names the variable, the host, and why it matters — that a seeded
    Fluree ledger is PERMANENT — so the operator who misconfigured a run is
    told what to change rather than left to infer it.
    """
    completed = _run({"CCF_TEST_FLUREE_URL": f"http://{CURATED}:8090"})
    assert completed.returncode != 0, (
        "a disposable-store variable pointed at the curated estate did not"
        " stop the session"
    )
    output = completed.stdout + completed.stderr
    assert "refusing to SEED a curated store" in output, output[-1500:]
    assert CURATED in output


def test_a_disposable_postgres_on_a_curated_host_refuses_too() -> None:
    """Both legs, independently — whatever the operator exported.

    `D-IMPL-318`'s wording is *"on either leg independently"*, and a fence
    that only watched Fluree would leave the schema leg open.
    """
    completed = _run(
        {"CCF_TEST_POSTGRES_DSN": f"host={CURATED} port=5432 dbname=parkavedb"}
    )
    assert completed.returncode != 0, "the Postgres leg was not fenced"
    assert "refusing to SEED a curated store" in completed.stdout + completed.stderr


def test_the_refusal_does_not_publish_the_credential() -> None:
    """A DSN carries a password, and this fence is designed to be LOUD.

    It raises, pytest prints it once per erroring test, and CI keeps the
    output — so an unredacted DSN here would publish the estate's credential
    every time somebody misconfigured a run.
    """
    secret = "hunter2-not-a-real-password"
    completed = _run(
        {"CCF_TEST_POSTGRES_DSN": f"postgresql://parkave:{secret}@{CURATED}:5432/parkavedb"}
    )
    output = completed.stdout + completed.stderr
    assert "refusing to SEED a curated store" in output
    assert secret not in output, "the fence printed the credential it was handed"
    assert ":***@" in output, "the fence did not redact; it merely omitted"


def test_a_local_disposable_store_is_not_refused() -> None:
    """THE POSITIVE CONTROL, and without it this module proves nothing.

    A fence that refused every configuration would pass all three tests above
    and be useless. ``localhost`` is the documented default and must run
    through — whether the container behind it is up is a different question,
    and this inert node does not ask it.
    """
    completed = _run({"CCF_TEST_FLUREE_URL": "http://localhost:8090"})
    output = completed.stdout + completed.stderr
    assert "refusing to SEED a curated store" not in output, output[-1000:]
    assert completed.returncode == 0, output[-1500:]


def test_the_curated_host_list_is_configuration_not_a_constant() -> None:
    """A second estate is a configuration change, not a code change.

    ``CCF_CURATED_ESTATE_HOSTS`` widens the fence. Asserted by fencing a host
    that is NOT curated by default and showing the refusal follows the
    declaration rather than a literal.
    """
    other = "10.99.99.99"
    permissive = _run({"CCF_TEST_FLUREE_URL": f"http://{other}:8090"})
    assert permissive.returncode == 0, (
        "an uncurated host was refused; the fence is matching something other"
        " than its declaration"
    )
    declared = _run(
        {
            "CCF_TEST_FLUREE_URL": f"http://{other}:8090",
            "CCF_CURATED_ESTATE_HOSTS": other,
        }
    )
    assert declared.returncode != 0, "declaring a curated host did not fence it"
    assert "refusing to SEED a curated store" in declared.stdout + declared.stderr


def test_every_module_naming_the_disposable_store_is_now_covered() -> None:
    """The measurement that motivated moving the fence, kept executable.

    Two of nine modules called the guard. The fence is session-scoped now, so
    coverage is no longer a function of how many call sites remembered — and
    this test states the count so the claim is checkable rather than asserted.
    """
    naming = sorted(
        path.relative_to(REPO_ROOT).as_posix()
        for path in (REPO_ROOT / "tests").rglob("*.py")
        if "__pycache__" not in path.parts
        and any(
            name in path.read_text(encoding="utf-8")
            for name in ("CCF_TEST_FLUREE_URL", "CCF_TEST_POSTGRES_DSN")
        )
    )
    assert len(naming) >= 9, naming
    conftest = (REPO_ROOT / "tests" / "conftest.py").read_text(encoding="utf-8")
    assert "refuse_to_write_the_curated_estate" in conftest, (
        "the session fence is gone from tests/conftest.py; coverage would fall"
        " back to whichever modules happen to import the guard"
    )
    assert 'scope="session", autouse=True' in conftest, (
        "the fence is no longer session-scoped and autouse, so a module that"
        " does not request it writes unfenced"
    )
    assert json.dumps(naming)  # the roster is enumerated, never counted alone


# --------------------------------------------------------------------------
# D-IMPL-358 ruling 12 — the fence compares HOSTS, not substrings, and covers
# every disposable-store variable.
# --------------------------------------------------------------------------


def test_the_fence_covers_every_disposable_store_variable_including_mongo() -> None:
    """`CCF_TEST_MONGO_URI` was defined and NOT fenced (`D-IMPL-358` ruling 12).

    Eight estate-gated trees read curated Mongo `fibo_v2`, so the one store the
    session fence did not cover was a store the suite actually reaches. Asserted
    as a ROSTER rather than a count, because a right count with a wrong member
    audits clean forever.

    ``CCF_TEST_NEO4J_URI`` joined the roster under `377-FENCE` (Dave, 2026-10-07):
    the curated host runs a Neo4j, and the neo4j leg creates indexes and MERGEs
    nodes into whatever that variable names, so leaving it out left a write path
    the session fence never looked at.
    """
    from tests.conftest import DISPOSABLE_STORE_ENV, MONGO_URI_ENV, NEO4J_URI_ENV

    assert set(DISPOSABLE_STORE_ENV) == {
        "CCF_TEST_FLUREE_URL",
        "CCF_TEST_POSTGRES_DSN",
        MONGO_URI_ENV,
        NEO4J_URI_ENV,
    }


@pytest.mark.parametrize(
    "target",
    [
        "http://192.168.4.76:8090",
        "http://192.168.4.76:8091",
        "postgresql://u:pw@192.168.4.76:5432/ccf_v2",
        "host=192.168.4.76 port=5432 dbname=ccf_v2 user=u password=pw",
        "hostaddr=192.168.4.76 port=5432 dbname=ccf_v2",
        "host=h1,192.168.4.76 port=5432,5433 dbname=ccf_v2",
        "postgresql://u:pw@h1:5432,192.168.4.76:5433/db",
        "mongodb://192.168.4.76:27017",
        "mongodb://a:27017,192.168.4.76:27017/db",
        "192.168.4.76:8090",
    ],
    ids=[
        "fluree",
        "fluree-peer",
        "dsn-uri",
        "dsn-libpq",
        "dsn-hostaddr",
        "dsn-multihost-keyword",
        "dsn-multihost-uri",
        "mongo",
        "mongo-multihost",
        "bare",
    ],
)
def test_a_curated_target_is_refused_in_every_serialization(target: str) -> None:
    """Both PostgreSQL serializations, because knowing one proves nothing about
    the other.

    Wave 1 paid for this directly: a credential sweep that knew only the URI form
    reported "no DSN points at the estate" while a **libpq keyword-form** DSN was
    sitting in a census log. A fence that parses one form and not the other has a
    hole exactly the shape of the form it does not parse.
    """
    from tests.examples.estate_guard import refuse_to_write_the_curated_estate

    with pytest.raises(RuntimeError, match="refusing to SEED a curated store"):
        refuse_to_write_the_curated_estate(target)


def test_a_curated_host_inside_a_PASSWORD_is_not_a_curated_TARGET() -> None:
    """The substring test's false positive, pinned (`D-IMPL-358` ruling 12).

    `any(host in target for host in curated)` answered True for this DSN because
    the curated address appears in the password. The host is `localhost`; the
    write goes to a throwaway container; refusing it would stop a legitimate run
    and teach the operator that the fence is noise.
    """
    from tests.examples.estate_guard import refuse_to_write_the_curated_estate

    refuse_to_write_the_curated_estate(
        "postgresql://u:192.168.4.76@localhost:5432/test"
    )


def test_curated_protection_is_HOST_LEVEL_and_no_port_rule_exists() -> None:
    """The estate rule is *"the curated host is read-only"*, not *"on certain
    ports"* (`D-IMPL-358` ruling 12 as corrected).

    An earlier draft of this fence treated a curated declaration carrying a port
    as fencing **only** that port. That invented a port policy nobody ruled and
    narrowed a host-level protection into a port list — a weakening dressed as
    precision. This control pins the opposite: a declaration that happens to
    carry a port still fences **every** port on that host, and a declaration
    without one behaves identically.
    """
    from tests.examples.estate_guard import (
        CURATED_HOSTS_ENV,
        refuse_to_write_the_curated_estate,
    )

    previous = os.environ.get(CURATED_HOSTS_ENV)
    os.environ[CURATED_HOSTS_ENV] = "192.168.4.76:8091"
    try:
        for port in (8090, 8091, 5432, 27017):
            with pytest.raises(RuntimeError, match="refusing to SEED a curated store"):
                refuse_to_write_the_curated_estate(f"http://192.168.4.76:{port}")
    finally:
        if previous is None:
            del os.environ[CURATED_HOSTS_ENV]
        else:
            os.environ[CURATED_HOSTS_ENV] = previous


def test_an_UNPARSEABLE_target_fails_CLOSED() -> None:
    """*Don't know* must never collapse into *pass*.

    A target whose destination cannot be established is a target nobody has
    checked, so the fence refuses it rather than admitting it.

    The carrier is a target that yields NO destination at all. A malformed port
    is deliberately NOT the carrier any more: the authority is now split
    structurally rather than through `urlsplit(...).port`, so
    `http://192.168.4.76:not-a-port` is correctly classified as the curated host
    and refused for the right reason — which is a better outcome than being
    refused for being unreadable.
    """
    from tests.examples.estate_guard import refuse_to_write_the_curated_estate

    with pytest.raises(RuntimeError, match="refusing to SEED a curated store"):
        refuse_to_write_the_curated_estate("   ")


# ---------------------------------------------------------------------------
# `D-IMPL-358` step 15 — the ONE severing for the `make example-*` gate.
# ---------------------------------------------------------------------------


def test_severing_the_make_gate_stops_refusing_a_curated_host(
    tmp_path: "object", monkeypatch: "object"
) -> None:
    """Drop the gate's refusal and the curated-host case PROCEEDS. Restored by construction.

    `tools/estate_fence.py` is what stands between an operator-exported curated
    destination and a `make example-s1-00` / `example-s1-01` run that transacts. This
    is the control that the standing between is real rather than decorative.

    **A scratch COPY, never an edit-and-revert.** The shipped source is read, mutated
    as a string, written under ``tmp_path`` and imported under a unique name, so the
    tree is never written and restoration is byte-for-byte by construction — and a
    file that did not exist a moment ago has no stale ``.pyc``. The anchor is asserted
    to occur EXACTLY ONCE before substitution: a stale anchor silently applies no
    mutation and the severing then "passes" having changed nothing.

    **No network, on either leg.** The gate only PARSES; it opens no connection. The
    curated address below is a string. Nothing here reaches the curated estate, and
    the severed leg deliberately stops at the gate's return value rather than running
    an example.
    """
    import pathlib as _p

    from tests.products.test_served_at_severings import severed

    curated = "http://192.168.4.76:8090"
    monkeypatch.setenv("CCF_TEST_FLUREE_URL", curated)  # type: ignore[attr-defined]

    # (1) SHIPPED: the gate refuses, so the make recipe stops before the run.
    from tools.estate_fence import main as shipped_main

    assert shipped_main([]) == 1, (
        "the shipped gate did not refuse a curated host — nothing below proves"
        " anything, because the control is not green"
    )

    # (2) SEVERED: the refusal call is removed and the same curated target PROCEEDS.
    module = severed(
        _p.Path(str(tmp_path)),
        "tools/estate_fence.py",
        (
            (
                "        refuse_to_write_the_curated_estate(*present.values())",
                "        pass  # severed",
            ),
        ),
        "the-make-gate-stops-refusing",
    )
    assert module.main([]) == 0, (
        "the severing cost nothing — the gate still refused with its refusal call"
        " removed, so this control is not guarding that line"
    )

    # (3) ...and the shipped gate still refuses, so the severing touched only the copy.
    assert shipped_main([]) == 1, (
        "the shipped gate stopped refusing after the severing ran — the tree was"
        " mutated, which the scratch-copy discipline exists to prevent"
    )


def test_the_refusal_masks_BOTH_postgres_password_serializations() -> None:
    """A refusal must never publish the estate credential, in EITHER DSN form.

    `D-IMPL-358` step 15. This control exists because the one beside it did not catch
    the gap: the existing credential assertion used the URI form, and `_redacted`
    masked only that form, so a refusal on a libpq keyword DSN
    (``host=... password=...``) printed the password verbatim. It was found by running
    the `make`-side gate, which writes the refusal to stderr where CI keeps it.

    **Both serializations, for the same reason `_destinations` parses both:** knowing
    one proves nothing about the other. The non-password target at the end is the
    negative control — a redactor that masked everything would pass the first four
    assertions and be useless.
    """
    from tests.examples.estate_guard import _redacted

    secret = "SUPERSECRET"
    for target in (
        f"postgresql://u:{secret}@192.168.4.76:5432/x",
        f"host=192.168.4.76 port=5432 dbname=x user=u password={secret}",
        f"host=192.168.4.76 password='{secret} with spaces' user=u",
        f"host=192.168.4.76 PGPASSWORD={secret}",
    ):
        masked = _redacted(target)
        assert secret not in masked, f"the password survived redaction: {masked}"
        assert "***" in masked, f"nothing was masked at all: {masked}"

    # NEGATIVE CONTROL: a target with no password is passed through unchanged, so
    # this test cannot be satisfied by a function that masks indiscriminately.
    assert _redacted("http://192.168.4.76:8090") == "http://192.168.4.76:8090"


# ---------------------------------------------------------------------------
# 377-FENCE (Dave, 2026-10-07 14:27 MST): the fence compares NETWORK ADDRESSES,
# not spellings, and `CCF_TEST_NEO4J_URI` is fenced.
# ---------------------------------------------------------------------------
#
# Measured by the D-IMPL-376 estate lane: spellings that the operating system's
# own resolver turns into the curated address were ADMITTED by the spelling
# comparison, in the URL form and the libpq keyword form alike; and the Neo4j
# disposable-store variable was in neither fence roster, although the curated
# host runs a Neo4j (`ccf_dataprep`'s `NEO4J_URI` defaults to it).
#
# Every test below is PURE CLASSIFICATION. Names are answered by a fake resolver
# that knows only the names a test hands it and otherwise parses NUMERIC forms
# with `AI_NUMERICHOST`, which makes a DNS lookup impossible; and every socket
# connect raises. Nothing here reaches the network, let alone the curated estate.

#: The curated address every spelling below designates.
CURATED_ADDRESS = CURATED

#: Spellings of `CURATED_ADDRESS` the operating system resolves to it. The first
#: five are the ones the estate lane measured admitted; the last two are the same
#: two classes (a two-part short form, a hexadecimal IPv4-mapped IPv6 form).
ALTERNATE_SPELLINGS: dict[str, str] = {
    "integer": "3232236620",
    "hex": "0xc0a8044c",
    "octal": "0300.0250.04.0114",
    "short-abc": "192.168.1100",
    "ipv4-mapped": "::ffff:192.168.4.76",
    "short-ab": "192.11011148",
    "ipv4-mapped-hex": "::ffff:c0a8:44c",
}

#: A name only the fake resolver answers — `.invalid` can never resolve (RFC 6761).
ALIAS = "curated-alias.invalid"

#: A name nothing answers.
UNRESOLVABLE = "no-such-store.invalid"

#: The serializations a write destination arrives in.
FORMS: tuple[str, ...] = ("url", "postgres-uri", "postgres-keyword", "mongo-uri", "neo4j-uri")

#: The one form each fenced variable carries in practice.
FENCED_VARIABLE_FORMS: dict[str, str] = {
    "CCF_TEST_FLUREE_URL": "url",
    "CCF_TEST_POSTGRES_DSN": "postgres-keyword",
    "CCF_TEST_MONGO_URI": "mongo-uri",
    "CCF_TEST_NEO4J_URI": "neo4j-uri",
    "CCF_S1_00_POSTGRES_DSN": "postgres-uri",
}

_REAL_GETADDRINFO = socket.getaddrinfo


def _target(form: str, host: str) -> str:
    """A write destination of shape ``form`` whose host is ``host``."""
    bracketed = f"[{host}]" if ":" in host else host
    return {
        "url": f"http://{bracketed}:8090",
        "postgres-uri": f"postgresql://u:pw@{bracketed}:5432/ccf_v2",
        "postgres-keyword": f"host={host} port=5432 dbname=ccf_v2 user=u password=pw",
        "mongo-uri": f"mongodb://{bracketed}:27017/fibo_v2",
        "neo4j-uri": f"neo4j://neo4j:pw@{bracketed}:7687",
    }[form]


def _designates(host: str) -> str:
    """The IPv4 address the operating system's NUMERIC parser makes of ``host``.

    The precondition every spelling case asserts first, so no case can pass
    against a spelling that does not actually reach the curated address.
    ``AI_NUMERICHOST`` forbids a lookup: this never touches DNS.
    """
    found = {
        ipaddress.ip_address(info[4][0])
        for info in _REAL_GETADDRINFO(host, None, flags=socket.AI_NUMERICHOST)
    }
    flattened = {
        str(address.ipv4_mapped or address)
        if isinstance(address, ipaddress.IPv6Address)
        else str(address)
        for address in found
    }
    assert len(flattened) == 1, flattened
    return flattened.pop()


class _FakeResolver:
    """`socket.getaddrinfo` without DNS: the names in ``table``, else numeric forms only."""

    def __init__(self, table: dict[str, tuple[str, ...]]) -> None:
        self.table = dict(table)
        self.asked: list[str] = []

    def __call__(
        self,
        host: "str | bytes | None",
        port: "object",
        family: int = 0,
        type: int = 0,  # noqa: A002 - the stdlib's own parameter name
        proto: int = 0,
        flags: int = 0,
    ) -> list[tuple[object, ...]]:
        name = host.decode() if isinstance(host, bytes) else (host or "")
        self.asked.append(name)
        key = name.strip().strip("[]").lower()
        if key in self.table:
            answers: list[tuple[object, ...]] = []
            for address in self.table[key]:
                if ":" in address:
                    answers.append(
                        (socket.AF_INET6, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (address, 0, 0, 0))
                    )
                else:
                    answers.append(
                        (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (address, 0))
                    )
            return answers
        return _REAL_GETADDRINFO(host, port, family, type, proto, flags | socket.AI_NUMERICHOST)


@pytest.fixture
def offline(monkeypatch: pytest.MonkeyPatch) -> _FakeResolver:
    """No DNS and no connection: a fake resolver, and a connect that refuses to run."""
    resolver = _FakeResolver({"localhost": ("127.0.0.1", "::1")})
    monkeypatch.setattr(socket, "getaddrinfo", resolver)

    def refuse(self: socket.socket, address: object) -> None:  # pragma: no cover - a regression
        raise AssertionError(f"a fence test opened a connection to {address!r}")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket.socket, "connect_ex", refuse)
    monkeypatch.delenv("CCF_CURATED_ESTATE_HOSTS", raising=False)
    return resolver


@pytest.mark.parametrize("form", ("url", "postgres-uri", "postgres-keyword"))
@pytest.mark.parametrize("spelling", sorted(ALTERNATE_SPELLINGS))
def test_every_spelling_of_the_curated_address_is_refused_BY_ADDRESS(
    spelling: str, form: str, offline: _FakeResolver
) -> None:
    """The measured hole (`377-FENCE`): the operating system resolves each of these
    spellings to the curated address, and the spelling comparison admitted them.

    Refused BECAUSE the host reaches the curated address — the reason is asserted by
    name, so a refusal for some other cause cannot satisfy this test — in the URL form
    and the libpq keyword form alike.
    """
    from tests.examples.estate_guard import refuse_to_write_the_curated_estate

    host = ALTERNATE_SPELLINGS[spelling]
    assert _designates(host) == CURATED_ADDRESS, (
        f"precondition: {host!r} does not designate {CURATED_ADDRESS} on this host"
    )
    with pytest.raises(RuntimeError, match="refusing to SEED a curated store") as refused:
        refuse_to_write_the_curated_estate(_target(form, host))
    assert f"reaches the curated address {CURATED_ADDRESS}" in str(refused.value)


@pytest.mark.parametrize("answer", (CURATED_ADDRESS, "::ffff:" + CURATED_ADDRESS), ids=("ipv4", "ipv4-mapped-ipv6"))
@pytest.mark.parametrize("form", FORMS)
def test_a_NAME_that_resolves_to_the_curated_address_is_refused(
    answer: str, form: str, offline: _FakeResolver
) -> None:
    """A hostname is only as safe as the address it resolves to (`377-FENCE`).

    The fake resolver answers the alias with the curated address; the refusal must
    come from asking it, which the resolver's own record shows.
    """
    from tests.examples.estate_guard import refuse_to_write_the_curated_estate

    offline.table[ALIAS] = (answer,)
    with pytest.raises(RuntimeError, match="refusing to SEED a curated store") as refused:
        refuse_to_write_the_curated_estate(_target(form, ALIAS))
    assert f"reaches the curated address {CURATED_ADDRESS}" in str(refused.value)
    assert ALIAS in offline.asked, "the refusal did not come from resolving the name"


@pytest.mark.parametrize("form", FORMS)
def test_a_host_that_cannot_be_resolved_FAILS_CLOSED_by_name(
    form: str, offline: _FakeResolver
) -> None:
    """*Don't know* never collapses into *pass* (`377-FENCE`).

    A host that cannot be resolved to an address is a destination nobody has
    checked, so it is refused — and the refusal names the host and says why.
    """
    from tests.examples.estate_guard import refuse_to_write_the_curated_estate

    with pytest.raises(RuntimeError, match="refusing to SEED a curated store") as refused:
        refuse_to_write_the_curated_estate(_target(form, UNRESOLVABLE))
    assert f"{UNRESOLVABLE!r} could not be resolved to a network address" in str(refused.value)
    assert UNRESOLVABLE in offline.asked


@pytest.mark.parametrize(
    "declared", (ALIAS, ALTERNATE_SPELLINGS["integer"]), ids=("declared-by-name", "declared-by-integer")
)
def test_the_CURATED_SET_is_canonicalized_too(
    declared: str, offline: _FakeResolver, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Both sides of the comparison are addresses (`377-FENCE`): a curated host
    declared by name or by another spelling fences its address, however a target
    spells it.
    """
    from tests.examples.estate_guard import CURATED_HOSTS_ENV, refuse_to_write_the_curated_estate

    offline.table[ALIAS] = (CURATED_ADDRESS,)
    monkeypatch.setenv(CURATED_HOSTS_ENV, declared)
    for target in (f"http://{CURATED_ADDRESS}:8090", f"host={ALTERNATE_SPELLINGS['octal']} port=5432"):
        with pytest.raises(RuntimeError, match="refusing to SEED a curated store") as refused:
            refuse_to_write_the_curated_estate(target)
        assert f"reaches the curated address {CURATED_ADDRESS}" in str(refused.value)


@pytest.mark.parametrize(
    "target",
    (
        "http://127.0.0.1:8090",
        "http://localhost:8090",
        "http://[::1]:8090",
        "http://127.1:8090",
        "postgresql://u:pw@127.0.0.1:5432/x",
        "postgresql://u:pw@localhost:5432/x",
        "host=localhost port=5432 dbname=x",
        "host=::1 port=5432 dbname=x",
        "host=/var/run/postgresql dbname=x",
        "mongodb://127.0.0.1:27019/ccf_test",
        "neo4j://neo4j:pw@localhost:7687",
        "http://10.99.99.99:8090",
    ),
    ids=(
        "url-ipv4-loopback",
        "url-localhost",
        "url-ipv6-loopback",
        "url-short-loopback",
        "postgres-uri-loopback",
        "postgres-uri-localhost",
        "postgres-keyword-localhost",
        "postgres-keyword-ipv6-loopback",
        "postgres-unix-socket",
        "mongo-loopback",
        "neo4j-localhost",
        "uncurated-address",
    ),
)
def test_CONTROL_a_loopback_or_uncurated_target_still_passes(
    target: str, offline: _FakeResolver
) -> None:
    """THE POSITIVE CONTROL for the address comparison: a fence that refused every
    target would pass every refusal test above and be useless. Loopback in each form,
    a libpq Unix-socket directory (no network address at all), and an address that
    is simply not curated, all pass.
    """
    from tests.examples.estate_guard import refuse_to_write_the_curated_estate

    refuse_to_write_the_curated_estate(target)


@pytest.mark.parametrize(
    "host",
    (*sorted(ALTERNATE_SPELLINGS.values()), ALIAS),
    ids=(*(name for name, _ in sorted(ALTERNATE_SPELLINGS.items(), key=lambda item: item[1])), "alias"),
)
@pytest.mark.parametrize("variable", sorted(FENCED_VARIABLE_FORMS))
def test_every_fenced_variable_refuses_the_curated_address_however_it_is_named(
    variable: str,
    host: str,
    offline: _FakeResolver,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The `make` gate (`tools/estate_fence.py::main`), variable by variable — the
    Neo4j variable included (`377-FENCE`). Every fenced variable naming the curated
    address in any spelling, or by a name that resolves to it, stops the run.
    """
    from tools.estate_fence import main

    offline.table[ALIAS] = (CURATED_ADDRESS,)
    for name in FENCED_VARIABLE_FORMS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(variable, _target(FENCED_VARIABLE_FORMS[variable], host))
    assert main([]) == 1, f"{variable} naming the curated address as {host!r} was not refused"
    err = capsys.readouterr().err
    assert f"reaches the curated address {CURATED_ADDRESS}" in err, err
    assert variable in err, err


@pytest.mark.parametrize("variable", sorted(FENCED_VARIABLE_FORMS))
def test_CONTROL_every_fenced_variable_on_loopback_is_clear(
    variable: str, offline: _FakeResolver, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The `make` gate's positive control: loopback, on every fenced variable, runs."""
    from tools.estate_fence import main

    for name in FENCED_VARIABLE_FORMS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(variable, _target(FENCED_VARIABLE_FORMS[variable], "localhost"))
    assert main([]) == 0


def test_the_make_gate_fences_the_neo4j_disposable_variable() -> None:
    """`CCF_TEST_NEO4J_URI` was in neither roster (`377-FENCE`, the estate lane's F2)."""
    from tools.estate_fence import WRITE_TARGET_VARS

    assert "CCF_TEST_NEO4J_URI" in WRITE_TARGET_VARS, WRITE_TARGET_VARS


@pytest.mark.parametrize("variable", ("CCF_TEST_FLUREE_URL", "CCF_TEST_MONGO_URI", "CCF_TEST_NEO4J_URI", "CCF_TEST_POSTGRES_DSN"))
def test_the_SESSION_fence_refuses_an_alternate_spelling_on_every_disposable_variable(
    variable: str,
) -> None:
    """The session fence itself, in a real session (`377-FENCE`): each disposable-store
    variable naming the curated address by its integer spelling stops the whole run.
    """
    completed = _run({variable: _target(FENCED_VARIABLE_FORMS[variable], ALTERNATE_SPELLINGS["integer"])})
    output = completed.stdout + completed.stderr
    assert completed.returncode != 0, f"{variable}: the session ran:\n{output[-1500:]}"
    assert "refusing to SEED a curated store" in output, output[-1500:]
    assert f"reaches the curated address {CURATED_ADDRESS}" in output, output[-1500:]


def test_a_curated_neo4j_disposable_store_refuses_the_session_without_printing_its_password() -> None:
    """The Neo4j URI carries a credential, and this fence is designed to be LOUD."""
    secret = "neo4j-not-a-real-password"
    completed = _run({"CCF_TEST_NEO4J_URI": f"neo4j://neo4j:{secret}@{CURATED}:7687"})
    output = completed.stdout + completed.stderr
    assert completed.returncode != 0, output[-1500:]
    assert "refusing to SEED a curated store" in output, output[-1500:]
    assert "CCF_TEST_NEO4J_URI" in output, "the refusal does not name the variable to change"
    assert secret not in output, "the fence printed the credential it was handed"
    assert ":***@" in output, "the fence did not redact; it merely omitted"


# ---------------------------------------------------------------------------
# 377-FENCE2 (focused re-review, 2026-10-07): an EMPTY curated declaration
# disabled the fence, and libpq's own environment was not read.
# ---------------------------------------------------------------------------
#
# Measured by the re-review (`review/rr/probe_estate_fence_tool.out`): with
# `CCF_CURATED_ESTATE_HOSTS` set but empty the fence passed the curated address
# while the tool still printed "(default 192.168.4.76)"; with `PGHOSTADDR` naming
# the curated address, a `localhost` DSN — which libpq connects to PGHOSTADDR —
# passed. A DSN naming no host connects to `PGHOST`, which the operator's own
# shell exports as the curated address; a libpq service can redirect anywhere.
#
# Pure classification again: libpq's variables are set with `monkeypatch`, the
# `offline` fixture above makes DNS impossible and every connect raise.

#: The libpq variables the fence must read, cleared first so the operator's shell
#: (which exports PGHOST as the curated address) cannot decide a test.
LIBPQ_VARIABLES = ("PGHOST", "PGHOSTADDR", "PGPORT", "PGSERVICE", "PGSERVICEFILE")


@pytest.fixture
def libpq_clean(offline: _FakeResolver, monkeypatch: pytest.MonkeyPatch) -> _FakeResolver:
    """`offline`, with every libpq destination variable removed."""
    for name in LIBPQ_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    return offline


@pytest.mark.parametrize("declared", ("", "   ", ",", " , "), ids=("empty", "spaces", "comma", "spaced-comma"))
def test_an_EMPTY_curated_declaration_means_the_default(
    declared: str, libpq_clean: _FakeResolver, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A declaration that declares nothing is not a declaration (`377-FENCE2`).

    Set but empty, the variable used to mean "no curated host" — the fence off,
    silently. It now means the default, so the curated address is still refused.
    """
    from tests.examples.estate_guard import CURATED_HOSTS_ENV, refuse_to_write_the_curated_estate

    monkeypatch.setenv(CURATED_HOSTS_ENV, declared)
    with pytest.raises(RuntimeError, match="refusing to SEED a curated store") as refused:
        refuse_to_write_the_curated_estate(f"http://{CURATED_ADDRESS}:8090")
    assert f"reaches the curated address {CURATED_ADDRESS}" in str(refused.value)


def test_the_make_gate_with_an_EMPTY_declaration_refuses_and_reports_the_hosts_in_force(
    libpq_clean: _FakeResolver, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The tool and the guard agree (`377-FENCE2`): the gate refuses the curated
    address under an empty declaration, and when clear it prints the hosts actually
    in force rather than a default it is not applying.
    """
    from tools.estate_fence import main

    for name in FENCED_VARIABLE_FORMS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("CCF_CURATED_ESTATE_HOSTS", "")
    monkeypatch.setenv("CCF_TEST_FLUREE_URL", f"http://{CURATED_ADDRESS}:8090")
    assert main([]) == 1
    capsys.readouterr()
    monkeypatch.setenv("CCF_TEST_FLUREE_URL", "http://localhost:8090")
    assert main([]) == 0
    out = capsys.readouterr().out
    assert f"Curated hosts in force: {CURATED_ADDRESS}" in out, out


def test_the_SESSION_fence_with_an_EMPTY_declaration_still_refuses_the_curated_address() -> None:
    """The session fence, in a real session, under `CCF_CURATED_ESTATE_HOSTS=""`."""
    completed = _run({"CCF_CURATED_ESTATE_HOSTS": "", "CCF_TEST_FLUREE_URL": f"http://{CURATED}:8090"})
    output = completed.stdout + completed.stderr
    assert completed.returncode != 0, output[-1500:]
    assert f"reaches the curated address {CURATED_ADDRESS}" in output, output[-1500:]


@pytest.mark.parametrize("hostaddr", (CURATED_ADDRESS, ALTERNATE_SPELLINGS["integer"]), ids=("dotted", "integer"))
@pytest.mark.parametrize(
    "target",
    ("postgresql://u:pw@localhost:5432/x", "host=localhost port=5432 dbname=x user=u password=pw"),
    ids=("postgres-uri", "postgres-keyword"),
)
def test_PGHOSTADDR_is_where_a_localhost_dsn_actually_connects(
    target: str, hostaddr: str, libpq_clean: _FakeResolver, monkeypatch: pytest.MonkeyPatch
) -> None:
    """libpq connects to `hostaddr` — from the DSN or from PGHOSTADDR when the DSN
    leaves it out — and uses `host` only to name the server (`377-FENCE2`). The
    re-review demonstrated it against a closed loopback port; the fence must judge
    that address, and say where it came from.
    """
    from tests.examples.estate_guard import refuse_to_write_the_curated_estate

    monkeypatch.setenv("PGHOSTADDR", hostaddr)
    with pytest.raises(RuntimeError, match="refusing to SEED a curated store") as refused:
        refuse_to_write_the_curated_estate(target)
    message = str(refused.value)
    assert "(from PGHOSTADDR)" in message, message
    assert f"reaches the curated address {CURATED_ADDRESS}" in message, message


@pytest.mark.parametrize(
    "target",
    ("postgresql://u:pw@/x", "postgresql:///x", "dbname=x user=u password=pw"),
    ids=("uri-empty-authority", "uri-no-authority", "keyword-no-host"),
)
def test_PGHOST_is_where_a_dsn_that_names_no_host_connects(
    target: str, libpq_clean: _FakeResolver, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A DSN that names no host connects to PGHOST — which the operator's shell
    exports as the curated address (`377-FENCE2`). Refused for THAT reason, not as
    a destination the fence could not read.
    """
    from tests.examples.estate_guard import refuse_to_write_the_curated_estate

    monkeypatch.setenv("PGHOST", CURATED_ADDRESS)
    with pytest.raises(RuntimeError, match="refusing to SEED a curated store") as refused:
        refuse_to_write_the_curated_estate(target)
    message = str(refused.value)
    assert "(from PGHOST)" in message, message
    assert f"reaches the curated address {CURATED_ADDRESS}" in message, message


def test_PGHOST_establishes_a_LOCAL_destination_for_a_dsn_that_names_no_host(
    libpq_clean: _FakeResolver, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The other half of judging the destination libpq will use (`377-FENCE2`): a
    host-less DSN under ``PGHOST=localhost`` connects to localhost and is admitted,
    where the fence used to refuse it as a destination it could not read.
    """
    from tests.examples.estate_guard import refuse_to_write_the_curated_estate

    monkeypatch.setenv("PGHOST", "localhost")
    refuse_to_write_the_curated_estate("postgresql://u:pw@/x")


@pytest.mark.parametrize(
    ("variable", "target", "source"),
    (
        ("PGSERVICE", "postgresql://u:pw@localhost:5432/x", "PGSERVICE"),
        ("PGSERVICEFILE", "host=localhost port=5432 dbname=x", "PGSERVICEFILE"),
        (None, "host=localhost port=5432 dbname=x service=estate", "service="),
        (None, "postgresql://u@localhost/x?service=estate", "service="),
    ),
    ids=("PGSERVICE", "PGSERVICEFILE", "service-keyword", "service-uri-query"),
)
def test_a_libpq_SERVICE_refuses_by_name(
    variable: "str | None",
    target: str,
    source: str,
    libpq_clean: _FakeResolver,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A libpq service fills every parameter the DSN leaves out from a file the
    fence does not read — host and hostaddr included — so it can redirect the
    connection anywhere (`377-FENCE2`). Refused fail-closed, naming the source.
    """
    from tests.examples.estate_guard import refuse_to_write_the_curated_estate

    if variable is not None:
        monkeypatch.setenv(variable, "estate" if variable == "PGSERVICE" else "/nonexistent/pg_service.conf")
    with pytest.raises(RuntimeError, match="refusing to SEED a curated store") as refused:
        refuse_to_write_the_curated_estate(target)
    message = str(refused.value)
    assert "a libpq service" in message and source in message, message


@pytest.mark.parametrize(
    ("env", "target"),
    (
        ({"PGHOSTADDR": "127.0.0.1"}, "host=localhost port=5432 dbname=x"),
        ({"PGHOST": CURATED_ADDRESS}, "postgresql://u:pw@localhost:5432/x"),
        ({"PGHOST": CURATED_ADDRESS}, "host=localhost port=5432 dbname=x"),
        ({"PGHOSTADDR": CURATED_ADDRESS, "PGSERVICE": "estate"}, "http://localhost:8090"),
        ({"PGPORT": "5432"}, "host=localhost dbname=x"),
    ),
    ids=("loopback-hostaddr", "PGHOST-ignored-uri-names-host", "PGHOST-ignored-keyword-names-host", "not-a-postgres-target", "PGPORT-is-no-rule"),
)
def test_CONTROL_libpq_variables_that_do_not_redirect_this_target_change_nothing(
    env: dict[str, str], target: str, libpq_clean: _FakeResolver, monkeypatch: pytest.MonkeyPatch
) -> None:
    """THE POSITIVE CONTROL for reading libpq's environment: a loopback PGHOSTADDR;
    PGHOST, which libpq ignores when the DSN names a host (so the operator's shell
    exporting the curated address refuses nothing that names its own host); a
    non-Postgres target, which libpq never sees; and PGPORT, because the fence is
    host-level and no port participates.
    """
    from tests.examples.estate_guard import refuse_to_write_the_curated_estate

    for name, value in env.items():
        monkeypatch.setenv(name, value)
    refuse_to_write_the_curated_estate(target)


@pytest.mark.parametrize(
    ("env", "expected"),
    (({"PGHOSTADDR": CURATED_ADDRESS}, "(from PGHOSTADDR)"), ({"PGSERVICE": "estate"}, "a libpq service")),
    ids=("PGHOSTADDR", "PGSERVICE"),
)
def test_the_make_gate_reads_libpq_s_environment(
    env: dict[str, str],
    expected: str,
    libpq_clean: _FakeResolver,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The re-review's exact probe (`377-FENCE2`): the gate cleared a localhost DSN
    under PGHOSTADDR naming the curated address."""
    from tools.estate_fence import main

    for name in FENCED_VARIABLE_FORMS:
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("CCF_TEST_POSTGRES_DSN", "postgresql://localhost:5999/db")
    assert main([]) == 1
    assert expected in capsys.readouterr().err


def test_the_SESSION_fence_reads_PGHOSTADDR() -> None:
    """The session fence, in a real session: a localhost DSN under a curated PGHOSTADDR."""
    completed = _run(
        {"CCF_TEST_POSTGRES_DSN": "postgresql://u:pw@localhost:5432/x", "PGHOSTADDR": CURATED}
    )
    output = completed.stdout + completed.stderr
    assert completed.returncode != 0, output[-1500:]
    assert "(from PGHOSTADDR)" in output, output[-1500:]
