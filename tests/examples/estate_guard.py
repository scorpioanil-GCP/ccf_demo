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


def _redacted(target: str) -> str:
    """A connection target safe to put in a message.

    A DSN carries a password. This guard's whole job is to be LOUD — it raises,
    pytest prints the message once per erroring test, and CI keeps that output
    — so an un-redacted DSN here would publish the estate's credential every
    time somebody misconfigured a run. Found by reading this guard's own first
    failure output rather than by review.
    """
    return re.sub(r"://([^:/@]+):[^@]*@", r"://\1:***@", target)


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
    curated = _curated_hosts()
    offending = [
        _redacted(target)
        for target in targets
        if target and any(host in target for host in curated)
    ]
    if offending:
        raise RuntimeError(
            "refusing to SEED a curated store: "
            + ", ".join(sorted(offending))
            + f". Hosts in {CURATED_HOSTS_ENV} (default {DEFAULT_CURATED_HOSTS})"
            " hold the curated estate. A seeded Fluree ledger there is"
            " PERMANENT — the store is append-only — and a seeded PostgreSQL"
            " schema is removable but accumulates until somebody removes it."
            " Point CCF_TEST_FLUREE_URL and CCF_TEST_POSTGRES_DSN at a local"
            " container. Reading the curated estate is expected; writing to it"
            " is not (CLAUDE.md §9, `D-IMPL-318`)"
        )
