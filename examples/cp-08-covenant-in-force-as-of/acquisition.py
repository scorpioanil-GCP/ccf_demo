"""The two source legs of cp-08, and this module imports no ``ccf`` at all.

That absence is the point and it is asserted by
``tests/examples/test_spine_separation.py``: acquisition is somebody else's
store, reached over somebody else's protocol, and the fabric's job begins at
the envelope. Swapping this file for a different estate must not touch the
fabric.

**WHAT THIS MODULE READS, AND THE ONE THING IT MUST NOT DO.** It reads
amendments carrying their two clocks, the covenants a facility holds, its
drawdowns, and the policy register. It **does not apply the two-axis cut** —
that is `Π` (`projection.py`), because the cut is a governed selection over
admitted state rather than a filter on a read. Applying it here would put the
product's whole subject outside the fabric, where nothing replays it.

**THE BOUND IS APPLIED IN THE READ, NOT AFTER IT.** `as_of` bounds the
amendment query's valid-time predicate at the source. Reading every amendment
and discarding later is the shape rung 7 exists to refuse.

**READS ONLY.** SPARQL ``SELECT`` on the graph leg, parameterised SQL
``SELECT`` on the relational leg, and nothing else. The curated estate is
evidence, not a fixture (CLAUDE.md §9).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping, Sequence

import httpx
import psycopg


@dataclass(frozen=True)
class Amendment:
    """One amendment, carrying both clocks as the source states them.

    ``asserted_at`` is ``None`` for 112 of the estate's 137 amendments. It is
    **not** defaulted to ``valid_from``: doing so would make every booking lag
    vanish and manufacture the coincidence this product exists to disprove
    (`CP08-F-03`).
    """

    uri: str
    amendment_id: str
    number: int | None
    valid_from: str | None
    valid_to: str | None
    asserted_at: str | None
    booking_lag_days: int | None


@dataclass(frozen=True)
class Covenant:
    """One covenant the facility carries, as it stands TODAY.

    Served as context and labelled unversioned. This estate carries no
    assertion time on a covenant and no supersession marker, so the terms a
    facility bore on a past date are not recoverable (`CP08-F-04`).
    """

    uri: str
    covenant_id: str
    covenant_type: str | None
    threshold: str | None
    threshold_unit: str | None
    label: str | None


@dataclass(frozen=True)
class Drawdown:
    drawdown_id: str
    drawdown_date: date
    amount: str
    currency: str | None
    in_booking_gap: bool
    amendment_number: int | None


@dataclass(frozen=True)
class PolicyVersion:
    version: str
    effective_from: date | None
    effective_to: date | None


@dataclass(frozen=True)
class FacilityWindow:
    """Everything one question needed from the two stores."""

    facility_id: str
    facility_known: bool
    amendments: tuple[Amendment, ...]
    covenants: tuple[Covenant, ...]
    drawdowns: tuple[Drawdown, ...]
    policy: PolicyVersion | None
    graph_pin: str | None


def nothing_acquired(facility_id: str) -> FacilityWindow:
    """An empty window — the shape a REFUSED question acquires.

    Returned rather than raised when the Control Plane declines the question.
    A governed refusal is a determination the fabric reached and belongs in the
    replay record as one; converting it into an exception here would replace it
    with this module's own error, and a caller would learn that a facility was
    unknown when in fact a parameter was refused.
    """
    return FacilityWindow(
        facility_id=facility_id, facility_known=False, amendments=(),
        covenants=(), drawdowns=(), policy=None, graph_pin=None,
    )


class UnknownFacility(LookupError):
    """The anchor resolves to no row.

    Raised rather than returning an empty window: an unknown facility is a
    claim about the REQUEST, and an empty covenant set is a claim about the
    world. They mean opposite things and the product answers them differently
    (`CIF-G11`).
    """


class _GraphLeg:
    """The ledger, reached over SPARQL with an optional transaction-time pin."""

    def __init__(self, *, url: str, ledger: str, client: httpx.Client,
                 at_transaction: str | None = None) -> None:
        self._url, self._ledger, self._client = url.rstrip("/"), ledger, client
        # THE READ'S UPPER BOUND ON THE STORE, and nothing more. It is not a
        # temporal cut: the product's two clocks are read from data, and this
        # says only WHICH STORE STATE answered. Measured on this build: the
        # SPARQL route honours `FROM <ledger@t:N>`, and a pin past the head is
        # refused rather than silently answered from the head.
        self._at_transaction = at_transaction

    @property
    def dataset(self) -> str:
        """The `FROM` clause — the ledger, bounded when a pin was supplied."""
        if self._at_transaction is None:
            return self._ledger
        return f"{self._ledger}@t:{self._at_transaction}"

    def select(self, body: str) -> list[Mapping[str, Any]]:
        response = self._client.post(
            f"{self._url}/v1/fluree/query",
            headers={"Content-Type": "application/sparql-query"},
            content=body,
        )
        response.raise_for_status()
        return json.loads(response.text)["results"]["bindings"]

    def head(self) -> str | None:
        """The ledger's transaction-time head, or ``None`` if unreported.

        **Execution provenance, never a temporal cut** (`D-IMPL-240` (2),
        `D-IMPL-309`). Fluree's ``t`` orders writes, not observations; the
        product's two clocks are read from data and this number says only
        *which store state answered*.
        """
        response = self._client.get(f"{self._url}/v1/fluree/ledgers")
        if response.status_code != 200:
            return None
        # THE LISTING KEYS ON `name` AND `branch` SEPARATELY, and matching the
        # two together is `CP06-F-01`'s trap: the curated estate is named
        # WITHOUT a branch segment (`fibo-v2`, not `fibo-v2:main`), so a match
        # that required one reported `unreported` for a ledger that was right
        # there. Matched on the name, with a bare name accepting any branch.
        wanted, _, branch = self._ledger.partition(":")
        for entry in response.json():
            if not isinstance(entry, Mapping) or entry.get("name") != wanted:
                continue
            if branch and entry.get("branch") != branch:
                continue
            value = entry.get("t")
            return None if value is None else str(value)
        # NOT a number invented from the listing: a head nobody could read is
        # reported absent, and the payload says so.
        return None


def _value(row: Mapping[str, Any], name: str) -> str | None:
    cell = row.get(name)
    return None if cell is None else str(cell.get("value"))


def _local(uri: str | None) -> str:
    return "" if uri is None else uri.rsplit("/", 1)[-1]


def _amendments(leg: _GraphLeg, vocab: Mapping[str, Any], *,
                facility_uri: str, as_of: str) -> tuple[Amendment, ...]:
    """Amendments effective at or before ``as_of`` — BOUNDED IN THE READ.

    The valid-time bound is a ``FILTER`` at the source. The assertion-time
    bound is deliberately NOT applied here: `Π` needs the amendments the second
    clock excludes in order to report which axis excluded them (`CIF-G06`), and
    a read that dropped them would leave the exclusion record unfillable.
    """
    g = vocab["graph_leg"]
    body = f"""
SELECT ?a ?vf ?vt ?aa ?num ?lag
FROM <{leg.dataset}>
WHERE {{
  ?a <{g['amends_predicate']}> <{facility_uri}> .
  OPTIONAL {{ ?a <{g['valid_from_predicate']}> ?vf }}
  OPTIONAL {{ ?a <{g['valid_to_predicate']}> ?vt }}
  OPTIONAL {{ ?a <{g['asserted_at_predicate']}> ?aa }}
  OPTIONAL {{ ?a <{g['amendment_number_predicate']}> ?num }}
  OPTIONAL {{ ?a <{g['booking_lag_predicate']}> ?lag }}
  FILTER (!BOUND(?vf) || STR(?vf) <= "{as_of}")
}}
"""
    out: list[Amendment] = []
    for row in leg.select(body):
        uri = _value(row, "a") or ""
        number, lag = _value(row, "num"), _value(row, "lag")
        out.append(
            Amendment(
                uri=uri,
                amendment_id=_local(uri),
                number=None if number is None else int(number),
                valid_from=(_value(row, "vf") or "")[:10] or None,
                valid_to=(_value(row, "vt") or "")[:10] or None,
                asserted_at=(_value(row, "aa") or "")[:10] or None,
                booking_lag_days=None if lag is None else int(lag),
            )
        )
    return tuple(sorted(out, key=lambda a: (a.valid_from or "", a.amendment_id)))


def _covenants(leg: _GraphLeg, vocab: Mapping[str, Any], *,
               facility_uri: str) -> tuple[Covenant, ...]:
    """The covenants the facility carries, unbounded by either clock.

    Unbounded because neither clock reaches them: this estate puts no
    assertion time on a covenant. Bounding by `as_of` on `validFrom` alone
    would look like a temporal answer and would not be one.

    **A covenant TYPE is required, not optional, and that is a filter.** The
    `covenantOf` predicate also links `BreachOfCovenant` nodes — measured, one
    on the demonstration facility — and a breach is not a covenant term. Breach
    scoring is out of scope (`CP-SPEC-008` §A.3), so admitting one here would
    serve a breach dressed as a constraint.
    """
    g = vocab["graph_leg"]
    body = f"""
SELECT ?c ?type ?thr ?unit ?label
FROM <{leg.dataset}>
WHERE {{
  ?c <{g['covenant_of_predicate']}> <{facility_uri}> .
  ?c <{g['covenant_type_predicate']}> ?type .
  OPTIONAL {{ ?c <{g['threshold_predicate']}> ?thr }}
  OPTIONAL {{ ?c <{g['threshold_unit_predicate']}> ?unit }}
  OPTIONAL {{ ?c <{g['label_predicate']}> ?label }}
}}
"""
    out: list[Covenant] = []
    for row in leg.select(body):
        uri = _value(row, "c") or ""
        out.append(
            Covenant(
                uri=uri,
                covenant_id=_local(uri),
                covenant_type=_value(row, "type"),
                threshold=_value(row, "thr"),
                threshold_unit=_value(row, "unit"),
                label=_value(row, "label"),
            )
        )
    return tuple(sorted(out, key=lambda c: (c.covenant_type or "", c.covenant_id)))


def acquire(*, facility_id: str, as_of: str, graph_url: str, graph_ledger: str,
            postgres_dsn: str, postgres_schema: str,
            vocabulary: Mapping[str, Any],
            at_transaction: str | None = None) -> FacilityWindow:
    """Read both legs for one question, at the bound governance resolved.

    ``at_transaction`` bounds the GRAPH read at a transaction point a previous
    run recorded, which is what lets the same question answered against an
    advanced ledger return the same answer. It bounds the store; it is not one
    of the product's two clocks.
    """
    g, a = vocabulary["graph_leg"], vocabulary["attribute_leg"]
    facility_uri = f"{g['node_namespace']}{facility_id}"

    with psycopg.connect(postgres_dsn) as conn, conn.cursor() as cur:
        cur.execute(f'SET search_path TO "{postgres_schema}"')
        cur.execute(
            f'SELECT 1 FROM "{a["facility_table"]}" WHERE {a["facility_key_column"]} = %s',
            (facility_id,),
        )
        if cur.fetchone() is None:
            raise UnknownFacility(
                f"{facility_id} resolves to no row in {postgres_schema}."
                f"{a['facility_table']} — an unknown facility is a claim about"
                " the request, never an empty answer about the world"
            )
        cols = ", ".join(a["drawdown_columns"])
        cur.execute(
            f'SELECT {cols} FROM "{a["drawdown_table"]}"'
            f' WHERE {a["drawdown_key_column"]} = %s'
            f' AND {a["drawdown_date_column"]} <= %s'
            f' ORDER BY {a["drawdown_date_column"]}',
            (facility_id, as_of),
        )
        drawdowns = tuple(
            Drawdown(
                drawdown_id=str(r[0]), drawdown_date=r[2], amount=str(r[3]),
                currency=r[4], in_booking_gap=bool(r[5]),
                amendment_number=None if r[6] is None else int(r[6]),
            )
            for r in cur.fetchall()
        )
        cur.execute(
            f'SELECT {a["policy_version_column"]}, {a["policy_effective_from_column"]},'
            f' {a["policy_effective_to_column"]} FROM "{a["policy_table"]}"'
            f' WHERE {a["policy_effective_from_column"]} <= %s'
            f' AND ({a["policy_effective_to_column"]} IS NULL'
            f'      OR {a["policy_effective_to_column"]} > %s)'
            f' ORDER BY {a["policy_effective_from_column"]} DESC LIMIT 1',
            (as_of, as_of),
        )
        row = cur.fetchone()
        policy = None if row is None else PolicyVersion(str(row[0]), row[1], row[2])

    with httpx.Client(timeout=120.0) as client:
        leg = _GraphLeg(url=graph_url, ledger=graph_ledger, client=client,
                        at_transaction=at_transaction)
        return FacilityWindow(
            facility_id=facility_id,
            facility_known=True,
            amendments=_amendments(leg, vocabulary,
                                   facility_uri=facility_uri, as_of=as_of),
            covenants=_covenants(leg, vocabulary, facility_uri=facility_uri),
            drawdowns=drawdowns,
            policy=policy,
            # The point the read was bounded at when one was supplied, and the
            # head otherwise — so a served product always records the state that
            # answered it, and a replay has something to pin against.
            graph_pin=at_transaction or leg.head(),
        )
