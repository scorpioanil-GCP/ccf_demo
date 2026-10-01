"""One rule, in one place: the curated estate is READ-ONLY.

**NOT A TEST MODULE.** A helper the example test modules import; pytest
collects nothing from it.

`D-IMPL-318` and CLAUDE.md §9 settle the division this file enforces: examples
and their tests **read** the curated `.76` estate, and anything that must
**write** — a seeded fixture, a perturbed ledger — writes to a local,
disposable store instead.

**Why a guard rather than a convention.** ``CCF_TEST_FLUREE_URL`` already
defaults to ``http://localhost:8090`` and ``postgres_dsn`` already falls back to
a throwaway container, so the convention was in place the whole time. The 27
``ccf:cp04-*`` ledgers on the curated server exist because runs exported those
variables pointing at it. Fluree is append-only, so each is permanent. The
failure was a configuration accident, and only something that refuses can stop
one.

Lifted out of ``cp_04_seed`` when s1-00 needed the same rule: an estate fence
imported from a module named for one example reads as that example's business.
"""

from __future__ import annotations

import os
import re
from urllib.parse import urlsplit

from psycopg.conninfo import conninfo_to_dict
from urllib.parse import urlsplit

# ---------------------------------------------------------------------------
# The write fence — `D-IMPL-318`.
# ---------------------------------------------------------------------------

#: Hosts whose stores are CURATED and must never be written by a test. Declared
#: rather than hard-coded so a second estate is a configuration change; the
#: default is the estate CLAUDE.md §9 names.
CURATED_HOSTS_ENV = "CCF_CURATED_ESTATE_HOSTS"
DEFAULT_CURATED_HOSTS = "192.168.4.76"


def _curated_hosts() -> frozenset[str]:
    raw = os.environ.get(CURATED_HOSTS_ENV, DEFAULT_CURATED_HOSTS)
    return frozenset(part.strip() for part in raw.split(",") if part.strip())


#: The password-bearing shapes a connection target can carry. **BOTH PostgreSQL
#: serializations, because knowing one proves nothing about the other** — the same
#: lesson :func:`_destinations` records for parsing, and it had to be learned twice.
#: Until `D-IMPL-358` step 15 this function masked only the URI form, so a refusal
#: on a libpq keyword DSN (``host=... password=...``) printed the estate credential
#: verbatim. Found by RUNNING the new `make`-side gate, not by reading it: the
#: existing credential control used the URI form and so could not catch it.
_PASSWORD_SHAPES: tuple[tuple[re.Pattern[str], str], ...] = (
    # postgresql://user:secret@host -> postgresql://user:***@host
    (re.compile(r"://([^:/@]+):[^@]*@"), r"://\1:***@"),
    # password=secret | PGPASSWORD='s e c r e t' -> password=***
    (re.compile(r"((?:password|pgpassword)\s*=\s*)('[^']*'|\"[^\"]*\"|\S+)", re.I), r"\1***"),
)


def _redacted(target: str) -> str:
    """A connection target safe to put in a message.

    A DSN carries a password. This guard's whole job is to be LOUD — it raises,
    pytest prints the message once per erroring test, CI keeps that output, and
    since `D-IMPL-358` step 15 a `make`-side gate prints it to stderr too — so an
    un-redacted DSN here would publish the estate's credential every time somebody
    misconfigured a run. Found by reading this guard's own first failure output
    rather than by review; the libpq half was found by running the gate.
    """
    for pattern, replacement in _PASSWORD_SHAPES:
        target = pattern.sub(replacement, target)
    return target



def _normalize_host(host: str) -> str:
    """Lowercase, trimmed, IPv6 brackets stripped, so ``[::1]`` equals ``::1``."""
    return host.strip().strip("[]").lower()


def _hosts_from_url(target: str) -> frozenset[str] | None:
    """Every host a URL-shaped target names, or ``None`` when it cannot be read.

    Handles the MULTI-HOST form a Mongo URI may carry
    (``mongodb://h1:27017,h2:27017/db``) by splitting the authority itself rather
    than calling :attr:`~urllib.parse.SplitResult.port`, which raises on a
    malformed port and reads only the first host anyway.
    """
    try:
        authority = urlsplit(target if "://" in target else f"//{target}").netloc
    except ValueError:
        return None
    if not authority:
        return None
    authority = authority.rsplit("@", 1)[-1]          # drop any userinfo
    hosts: set[str] = set()
    for candidate in authority.split(","):
        candidate = candidate.strip()
        if not candidate:
            continue
        if candidate.startswith("["):                  # [::1]:8090
            host = candidate.partition("]")[0].lstrip("[")
        else:
            host = candidate.rsplit(":", 1)[0] if candidate.count(":") == 1 else candidate
        host = _normalize_host(host)
        if host:
            hosts.add(host)
    return frozenset(hosts) or None


def _destinations(target: str) -> frozenset[str] | None:
    """Every host a connection target would actually reach, or ``None``.

    **A PostgreSQL DSN has two serializations and knowing one proves nothing
    about the other** — a URI (``postgresql://user:pw@host:5432/db``) and libpq
    keyword form (``host=... port=...``) — so both go through
    :func:`psycopg.conninfo.conninfo_to_dict`, the parser the driver itself uses.
    Wave 1 paid for that lesson directly: a credential sweep that knew only the
    URI form reported "no DSN points at the estate" while a keyword-form DSN sat
    in a census log. ``hostaddr`` is read beside ``host`` because a DSN may name
    the address and never the name, and libpq's multi-host form yields a
    comma-separated list that is split here rather than truncated to its first
    entry.

    Returning ``None`` is deliberate: a target this cannot classify is a target
    whose destination nobody has established, and the caller refuses it. *Don't
    know* must never collapse into *pass*.
    """
    if not target or not target.strip():
        return None
    looks_like_postgres = target.startswith(("postgres://", "postgresql://")) or (
        "=" in target and "://" not in target
    )
    if looks_like_postgres:
        try:
            parsed = conninfo_to_dict(target)
        except Exception:
            return None
        hosts: set[str] = set()
        for key in ("host", "hostaddr"):
            raw = parsed.get(key)
            if not isinstance(raw, str):
                continue
            hosts.update(_normalize_host(part) for part in raw.split(",") if part.strip())
        return frozenset(h for h in hosts if h) or None
    return _hosts_from_url(target)


def _names_a_curated_host(target: str) -> bool:
    """Does ``target`` reach a curated host? **Host-level, never port-scoped.**

    The estate rule is *"the curated host is read-only"* — not *"read-only on
    certain ports"* (`CLAUDE.md` section 9; `D-IMPL-358` ruling 12 as corrected).
    So **no port allow-list or deny-list is introduced here**: if any parsed
    destination is a curated host, the write is refused **regardless of port**. A
    curated declaration that happens to carry a port still fences the whole
    machine, because narrowing a host-level protection to a port list nobody
    ruled would be a weakening dressed as precision.

    Ports are still parsed — they belong in evidence and in a debugging message —
    but no port participates in this decision.

    Structural parsing throughout, never a substring test. The previous
    ``any(host in target for host in curated)`` matched a curated address
    appearing anywhere in the string, including inside a password, which refused
    legitimate throwaway targets and taught operators the fence was noise.
    """
    destinations = _destinations(target)
    if destinations is None:
        return True
    curated = {
        host
        for declaration in _curated_hosts()
        for host in (_destinations(declaration) or frozenset())
    }
    return bool(destinations & curated)


def refuse_to_write_the_curated_estate(*targets: str) -> None:
    """Refuse, by name, to seed anything that lives on a curated host.

    ``D-IMPL-318``. The modules that still seed do so because they must —
    `anchor` and `debt` perturb data to prove a guard fires, and a perturbation
    has nowhere to happen but a store the test owns. What they must NOT do is
    perform that write against the curated estate.

    **The failure this closes is a configuration accident, not a coding
    mistake.** ``CCF_TEST_FLUREE_URL`` already defaults to
    ``http://localhost:8090``; the 27 ``ccf:cp04-*`` ledgers on the curated
    server exist because runs exported it pointing there instead. Fluree is
    append-only, so each of those is permanent. Nothing in the code said no.

    **Refused rather than silently redirected.** Rewriting the target to
    localhost would run the suite against a store the operator did not choose
    and did not populate, and report the result as though they had.

    Raises:
        RuntimeError: any target names a curated host.
    """
    offending = [
        _redacted(target)
        for target in targets
        if target and _names_a_curated_host(target)
    ]
    if offending:
        raise RuntimeError(
            "refusing to SEED a curated store: "
            + ", ".join(sorted(offending))
            + f". Hosts in {CURATED_HOSTS_ENV} (default {DEFAULT_CURATED_HOSTS})"
            " hold the curated estate. A seeded Fluree ledger there is"
            " PERMANENT — the store is append-only — and a seeded PostgreSQL"
            " schema is removable but accumulates until somebody removes it."
            " Point CCF_TEST_FLUREE_URL, CCF_TEST_POSTGRES_DSN and"
            " CCF_TEST_MONGO_URI at a local"
            " container. Reading the curated estate is expected; writing to it"
            " is not (CLAUDE.md §9, `D-IMPL-318`)"
        )
