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

**It compares NETWORK ADDRESSES, not spellings** (`377-FENCE`, Dave, 2026-10-07).
The estate lane measured the spelling comparison admitting ``3232236620``,
``0xc0a8044c``, ``0300.0250.04.0114``, ``192.168.1100`` and
``::ffff:192.168.4.76`` — five spellings the operating system's resolver turns
into the curated address — and any name that resolves to it would have passed
the same way. Every destination and every curated declaration is now reduced to
the addresses it reaches (:func:`_addresses`), and a destination whose host
cannot be resolved is refused by name rather than assumed safe.

**And it judges the destination libpq will actually use** (`377-FENCE2`): a
Postgres target is read with PGHOST and PGHOSTADDR filling what its connection
string leaves out, a libpq service is refused by name because it can redirect the
connection anywhere, and an EMPTY ``CCF_CURATED_ESTATE_HOSTS`` means the default
rather than switching the fence off (:func:`curated_hosts_in_force`).
"""

from __future__ import annotations

import ipaddress
import os
import re
import socket
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


def _declared(raw: str) -> frozenset[str]:
    """The hosts a comma-separated declaration names, blanks dropped."""
    return frozenset(part.strip() for part in raw.split(",") if part.strip())


def curated_hosts_in_force() -> tuple[tuple[str, ...], str]:
    """The curated declarations the fence applies, and where they came from.

    **An EMPTY declaration means the default** (`377-FENCE2`). Set but empty — or
    blank, or only separators — the variable declares nothing; it used to switch
    the fence OFF while the make gate still printed the default. It now means the
    default exactly as an unset variable does, so the fence cannot be disabled by
    accident, and a second estate is still declared by naming it. The make gate
    prints this (`tools/estate_fence.py::main`), so what it reports is what the
    guard enforces.
    """
    raw = os.environ.get(CURATED_HOSTS_ENV)
    declared = _declared(raw or "")
    if declared:
        return tuple(sorted(declared)), f"declared in {CURATED_HOSTS_ENV}"
    why = "unset" if raw is None else "set but empty"
    return tuple(sorted(_declared(DEFAULT_CURATED_HOSTS))), f"the default; {CURATED_HOSTS_ENV} is {why}"


def _curated_hosts() -> frozenset[str]:
    return frozenset(curated_hosts_in_force()[0])


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


# ---------------------------------------------------------------------------
# Addresses, not spellings — `377-FENCE` (Dave, 2026-10-07 14:27 MST).
# ---------------------------------------------------------------------------

#: Either kind of network address the comparison works in.
Address = ipaddress.IPv4Address | ipaddress.IPv6Address

#: The well-known NAT64 prefix (RFC 6052). An address under it is an IPv4 address
#: reached through a translator, and is compared as that IPv4 address.
_NAT64_WELL_KNOWN = ipaddress.ip_network("64:ff9b::/96")


def _numeric(host: str) -> Address | None:
    """``host`` as an address when it is a numeric spelling, or ``None``. No lookup.

    Two parsers, in order. :func:`ipaddress.ip_address` reads the dotted quad and
    every IPv6 form, a scope included. :func:`socket.inet_aton` then reads what the
    C library also accepts for IPv4 and :mod:`ipaddress` refuses — a bare integer
    (``3232236620``), hexadecimal (``0xc0a8044c``), octal (``0300.0250.04.0114``),
    and the short ``a.b.c`` and ``a.b`` forms. Those are not curiosities: measured,
    the operating system's resolver turns every one of them into the address it
    designates, so a connection made with any of them reaches that address.
    Neither parser performs a lookup.
    """
    try:
        return ipaddress.ip_address(host)
    except ValueError:
        pass
    try:
        return ipaddress.IPv4Address(socket.inet_aton(host))
    except (OSError, ValueError, UnicodeError, TypeError):
        return None


def _comparable(address: Address) -> frozenset[Address]:
    """``address`` and every IPv4 address it embeds, for comparison.

    An IPv4-mapped IPv6 address IS its IPv4 address: a dual-stack socket handed
    ``::ffff:192.168.4.76`` connects to ``192.168.4.76``. The other IPv6 forms that
    carry an IPv4 address — IPv4-compatible, 6to4, Teredo, the NAT64 prefix — are
    compared as that IPv4 address too. Refusing a target that might reach the
    curated host is the recoverable error; admitting one is the permanent one.
    A scope is dropped, because it selects an interface, not a host.
    """
    found: set[Address] = {address}
    if isinstance(address, ipaddress.IPv6Address):
        bare = ipaddress.IPv6Address(int(address))
        found.add(bare)
        for embedded in (bare.ipv4_mapped, bare.sixtofour, *(bare.teredo or ())):
            if embedded is not None:
                found.add(embedded)
        compatible = int(bare) >> 32 == 0 and int(bare) > 1
        if compatible or bare in _NAT64_WELL_KNOWN:
            found.add(ipaddress.IPv4Address(int(bare) & 0xFFFFFFFF))
    return frozenset(found)


def _is_local_socket(host: str) -> bool:
    """A libpq Unix-domain socket: a directory path (or Linux's abstract ``@name``).

    It has no network address at all, so no curated host can be behind it — the
    one host shape that is safe without resolving anything.
    """
    return host.startswith(("/", "@"))


def _addresses(host: str) -> frozenset[Address] | None:
    """Every address ``host`` reaches, or ``None`` when that cannot be established.

    A numeric spelling is parsed without a lookup (:func:`_numeric`). A name goes
    through :func:`socket.getaddrinfo` — the resolver every driver this suite uses
    calls to connect — so the fence classifies the destination a connection would
    actually reach rather than the string that names it. A name that does not
    resolve returns ``None`` and the caller REFUSES it: *don't know* must never
    collapse into *pass*.
    """
    if _is_local_socket(host):
        return frozenset()
    numeric = _numeric(host)
    if numeric is not None:
        return _comparable(numeric)
    try:
        answers = socket.getaddrinfo(host, None)
    except (OSError, UnicodeError, ValueError):  # `socket.gaierror` is an OSError
        return None
    found: set[Address] = set()
    for *_, sockaddr in answers:
        parsed = _numeric(str(sockaddr[0]))
        if parsed is None:
            return None  # an answer this cannot read is not an answer
        found |= _comparable(parsed)
    return frozenset(found) or None


def _curated() -> tuple[frozenset[str], frozenset[Address]]:
    """The curated declarations, as spellings AND as the addresses they reach.

    Both sides of the comparison are canonicalized: a host declared by name, or by
    another spelling of its address, fences that address however a target spells
    it. A declaration that cannot be resolved here keeps only its spelling — and a
    target naming it cannot be resolved either, so that target is refused anyway.
    """
    spellings: set[str] = set()
    addresses: set[Address] = set()
    for declaration in _curated_hosts():
        for host in _destinations(declaration) or frozenset():
            spellings.add(host)
            addresses |= _addresses(host) or frozenset()
    return frozenset(spellings), frozenset(addresses)


#: libpq reads these when the connection string leaves the parameter OUT
#: (`377-FENCE2`): ``host`` from PGHOST, and ``hostaddr`` — the address libpq
#: actually connects to, ``host`` then only naming the server — from PGHOSTADDR.
#: PGPORT is libpq's port default and, like every port, takes no part in the
#: decision: the fence is host-level (`D-IMPL-358` ruling 12).
_LIBPQ_DESTINATION_DEFAULTS: tuple[tuple[str, str], ...] = (
    ("host", "PGHOST"),
    ("hostaddr", "PGHOSTADDR"),
)

#: What makes libpq consult a service file, which fills every parameter the
#: connection string leaves out — host and hostaddr included — from a file the
#: fence does not read. The string's own ``service=`` is the third.
_LIBPQ_SERVICE_VARIABLES: tuple[str, ...] = ("PGSERVICE", "PGSERVICEFILE")

#: The source recorded for a value the connection string states itself.
_FROM_THE_STRING = "the connection string"


def _looks_like_postgres(target: str) -> bool:
    """A libpq connection string, in URI or keyword form."""
    return target.startswith(("postgres://", "postgresql://")) or (
        "=" in target and "://" not in target
    )


def _libpq_effective(
    parsed: dict[str, str],
) -> tuple[dict[str, tuple[str, str]], str | None]:
    """The destination libpq will actually connect with, and any service it consults.

    Returns ``(destination, service)``. ``destination`` maps ``host`` and
    ``hostaddr`` to ``(value, source)``: the connection string's own value when it
    states one — even an empty one, because libpq reads the environment only for a
    parameter left OUT — else the environment default, the source naming the
    variable. ``service`` names what makes libpq consult a service file — the
    string's ``service=``, PGSERVICE or PGSERVICEFILE — or is ``None``.
    """
    destination: dict[str, tuple[str, str]] = {}
    for key, variable in _LIBPQ_DESTINATION_DEFAULTS:
        if key in parsed:
            destination[key] = (str(parsed[key]), _FROM_THE_STRING)
        elif variable in os.environ:
            destination[key] = (os.environ[variable], variable)
    if "service" in parsed:
        return destination, f"service={parsed['service']} in the connection string"
    for variable in _LIBPQ_SERVICE_VARIABLES:
        if variable in os.environ:
            return destination, variable
    return destination, None


def _target_destinations(target: str) -> tuple[dict[str, str], str | None] | None:
    """Every host ``target`` will reach, each with its source, and any libpq service.

    ``None`` when no destination can be read. A Postgres target is judged as libpq
    will connect it (`377-FENCE2`): PGHOST and PGHOSTADDR fill what the string
    leaves out. Every other target is judged by its own authority, which no libpq
    variable can touch. A host's source is empty when the target states it.
    """
    if not target or not target.strip():
        return None
    if not _looks_like_postgres(target):
        hosts = _hosts_from_url(target)
        return None if hosts is None else ({host: "" for host in hosts}, None)
    try:
        parsed = conninfo_to_dict(target)
    except Exception:
        return None
    destination, service = _libpq_effective(parsed)
    found: dict[str, str] = {}
    for raw, source in destination.values():
        for part in raw.split(","):
            host = _normalize_host(part)
            if host:
                found.setdefault(host, "" if source == _FROM_THE_STRING else source)
    if service is not None:
        return found, service
    return (found, None) if found else None


def _why_refused(
    target: str, curated: tuple[frozenset[str], frozenset[Address]]
) -> str | None:
    """Why ``target`` must not be written, or ``None`` when it may be.

    **Host-level, never port-scoped.** The estate rule is *"the curated host is
    read-only"* — not *"read-only on certain ports"* (`CLAUDE.md` section 9;
    `D-IMPL-358` ruling 12 as corrected). So no port allow-list or deny-list exists
    here: if any destination reaches a curated host, the write is refused
    **regardless of port**. Ports are still parsed — they belong in evidence and in
    a debugging message — but no port participates in this decision.

    **Addresses, not spellings** (`377-FENCE`). Every destination is resolved to
    the addresses it reaches and compared with the addresses the curated
    declarations reach. A destination that cannot be resolved is refused by name.
    Numeric hosts are judged first, so a curated address in a multi-host target is
    refused before any resolver is consulted.

    Structural parsing throughout, never a substring test: a curated address
    appearing inside a password is not a destination.
    """
    view = _target_destinations(target)
    if view is None:
        return "no destination could be read from it"
    found, service = view
    if service is not None:
        return (
            f"a libpq service ({service}) fills the host and hostaddr a connection"
            " string leaves out from a file the fence does not read, so it can"
            " redirect the connection anywhere; refused rather than assumed safe"
        )
    spellings, addresses = curated
    for host in sorted(found, key=lambda name: (_numeric(name) is None, name)):
        named = f"host {host!r}" + (f" (from {found[host]})" if found[host] else "")
        reached = _addresses(host)
        hit = sorted(str(address) for address in (reached or frozenset()) & addresses)
        if hit:
            return f"{named} reaches the curated address {hit[0]}"
        if host in spellings:
            return f"{named} is declared curated in {CURATED_HOSTS_ENV}"
        if reached is None:
            return (
                f"{named} could not be resolved to a network address, so it is"
                " refused rather than assumed safe"
            )
    return None


def _names_a_curated_host(target: str) -> bool:
    """Does ``target`` reach a curated host — or fail to say where it goes?

    See :func:`_why_refused`; this is its yes/no.
    """
    return _why_refused(target, _curated()) is not None


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

    **Each refusal says why** (`377-FENCE`): the host that reaches a curated
    address and the address it reaches, or the host that could not be resolved.
    The reason names hosts and addresses only; the target itself is redacted.

    Raises:
        RuntimeError: any target reaches a curated address, names a host that
            cannot be resolved to a network address, or yields no destination.
    """
    present = [target for target in targets if target]
    if not present:
        return
    in_force, source = curated_hosts_in_force()
    curated = _curated()
    offending = []
    for target in present:
        why = _why_refused(target, curated)
        if why is not None:
            offending.append(f"{_redacted(target)} ({why})")
    if offending:
        raise RuntimeError(
            "refusing to SEED a curated store: "
            + ", ".join(sorted(offending))
            + f". Curated hosts in force: {', '.join(in_force)} ({source}),"
            " compared as the network addresses they"
            " reach: every spelling of a curated address, and every name that"
            " resolves to one, is that host. A seeded Fluree ledger there is"
            " PERMANENT — the store is append-only — and a seeded PostgreSQL"
            " schema is removable but accumulates until somebody removes it."
            " Point CCF_TEST_FLUREE_URL, CCF_TEST_POSTGRES_DSN,"
            " CCF_TEST_MONGO_URI and CCF_TEST_NEO4J_URI at a local"
            " container. Reading the curated estate is expected; writing to it"
            " is not (CLAUDE.md §9, `D-IMPL-318`)"
        )
