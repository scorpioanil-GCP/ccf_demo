"""The co-lender's two source legs, and nothing else.

[ADAPT] everything here. [MECHANISM] nothing — **this module imports no `ccf`
at all**, which is the clearest statement of what it is: the peer's own stores,
read the way those stores want to be read.

**Two legs, neither complete on its own.** The position, the declared TTL, the
declared latency and the attestation record live in the peer's relational leg.
The counterparty's identity and the precision it discloses at live in the
peer's graph leg. No schema author has joined them, and the join is this
module's whole job — which is why the edge it mints is real evidence of a
two-store assembly rather than decoration.

**The attestation is read, never judged, here.** This module reports whether a
signed attestation record stands behind a declaration; whether that makes the
position servable is the POLICY operator's, declared in `ccf_config.yaml`. A
helpful refusal written here would put the governance decision in acquisition
code, where nothing can replay it.

**Precision is carried, never resolved.** A `band` member's `share_usd` is
NULL in the source and stays NULL here. This module does not compute a
midpoint, and neither does anything downstream — `CLD-G13`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
import psycopg
import yaml

HERE = Path(__file__).parent

#: Both legs are read once per question; neither is retried.
READ_TIMEOUT_SECONDS = 30.0


def vocabulary() -> Mapping[str, Any]:
    """The peer stores' own names — tables, columns, IRIs, literals."""
    document: Mapping[str, Any] = yaml.safe_load(
        (HERE / "artifacts" / "source-vocabulary.yaml").read_text(encoding="utf-8")
    )
    declaration: Mapping[str, Any] = document["declaration"]
    return declaration


@dataclass(frozen=True)
class Counterparty:
    """One syndicate member, as the peer's GRAPH leg describes it."""

    uri: str
    lei: str
    label: str | None
    #: ``exact`` or ``band`` — the peer's own declaration of how much it is
    #: willing to say. Not a data-quality signal: a band is a policy choice.
    precision: str
    provenance: str | None


@dataclass(frozen=True)
class Position:
    """One position, as the peer's RELATIONAL leg holds it, joined to its declaration.

    ``share_usd`` and the two band bounds are mutually exclusive in the source
    and stay that way: a band member has no point estimate anywhere, and this
    dataclass carries none for it.
    """

    position_id: str
    counterparty_lei: str
    facility_id: str
    share_usd: Decimal | None
    band_low: Decimal | None
    band_high: Decimal | None
    internal_rating: str | None
    workout_posture: str | None
    as_of: str
    provenance: str | None
    #: From `peer_product_declaration`. ``None`` where the peer published no
    #: declaration for this (counterparty, facility) at all.
    declared_ttl_seconds: int | None
    declared_latency_ms: int | None
    #: Whether a signed attestation record stands behind the declaration. Read,
    #: not judged — see the module docstring.
    attested: bool


@dataclass(frozen=True)
class PeerAnswer:
    """What the two legs found, before any fabric call has been made."""

    position: Position
    counterparty: Counterparty
    #: The peer graph leg's own transaction watermark, recorded BESIDE the
    #: fabric's snapshot instant and never inside it.
    ledger_watermark: str


class _GraphLeg:
    """A read-only SPARQL client for the peer's ledger."""

    def __init__(self, *, url: str, ledger: str, client: httpx.Client) -> None:
        self._url = url.rstrip("/")
        self._ledger = ledger
        self._client = client

    @property
    def ledger(self) -> str:
        return self._ledger

    def query(self, body: str) -> list[Mapping[str, Any]]:
        """One SPARQL SELECT, with the ledger named explicitly."""
        response = self._client.post(
            f"{self._url}/v1/fluree/query",
            headers={"Content-Type": "application/sparql-query"},
            content=body.encode("utf-8"),
        )
        response.raise_for_status()
        bindings: list[Mapping[str, Any]] = response.json()["results"]["bindings"]
        return bindings

    def watermark(self) -> str:
        """The ledger's transaction index, as the store itself reports it.

        **Reported as ``unreported`` rather than as a number this code
        invented** when the listing does not carry this ledger. A fabricated
        watermark would be worse than an absent one: a specific, checkable,
        false claim about the source's state. The reporting gap itself is
        `AIA-F-04`, a carried repository sweep this rung does not open.
        """
        response = self._client.get(f"{self._url}/v1/fluree/ledgers")
        if response.status_code != 200:
            return "unreported"
        name, separator, branch = self._ledger.partition(":")
        if not separator:
            name, branch = self._ledger, "main"
        for entry in response.json():
            if entry.get("name") == name and entry.get("branch", "main") == branch:
                return str(entry.get("t", "unreported"))
        return "unreported"


def _binding(row: Mapping[str, Any], key: str) -> str | None:
    value = row.get(key)
    return None if value is None else str(value["value"])


def _counterparty(
    *, lei: str, leg: _GraphLeg, vocab: Mapping[str, Any]
) -> Counterparty:
    """Resolve one member in the peer's graph leg, or refuse to invent one."""
    graph = vocab["graph_leg"]
    rows = leg.query(
        f"SELECT ?s ?label ?precision ?provenance FROM <{leg.ledger}> WHERE {{"
        f" ?s <{graph['lei_predicate']}> \"{lei}\" ."
        f" ?s <{graph['precision_predicate']}> ?precision ."
        f" OPTIONAL {{ ?s <{graph['label_predicate']}> ?label }}"
        f" OPTIONAL {{ ?s <{graph['provenance_predicate']}> ?provenance }} }}"
    )
    if not rows:
        raise LookupError(
            f"no member in the peer ledger {leg.ledger!r} carries LEI {lei!r};"
            " a counterparty this fabric does not hold is a refusal, never an"
            " invented node"
        )
    row = rows[0]
    subject = _binding(row, "s")
    assert subject is not None  # the SELECT binds it
    precision = _binding(row, "precision")
    assert precision is not None  # the WHERE requires it
    return Counterparty(
        uri=subject,
        lei=lei,
        label=_binding(row, "label"),
        precision=precision,
        provenance=_binding(row, "provenance"),
    )


def _position(
    *, lei: str, facility_id: str, settings: Mapping[str, str], vocab: Mapping[str, Any]
) -> Position:
    """Read one position and its published declaration from the peer's relational leg."""
    relational = vocab["relational_leg"]
    position_columns = relational["position_columns"]
    declaration_columns = relational["declaration_columns"]
    schema = settings["schema"]
    wanted = (
        "position_id", "counterparty", "facility_id", "share_usd", "band_low",
        "band_high", "internal_rating", "workout_posture", "as_of", "provenance",
    )
    selected = ", ".join(position_columns[name] for name in wanted)
    with psycopg.connect(settings["dsn"]) as connection:
        found = connection.execute(
            f"SELECT {selected}"
            f" FROM {schema}.{relational['position_table']}"
            f" WHERE {position_columns['counterparty']} = %s"
            f" AND {position_columns['facility_id']} = %s",
            (lei, facility_id),
        ).fetchall()
        if not found:
            raise LookupError(
                f"the peer holds no position for counterparty {lei!r} in"
                f" facility {facility_id!r}; an absent position is a refusal,"
                " never an empty payload"
            )
        (
            position_id, counterparty, facility, share_usd, band_low, band_high,
            internal_rating, workout_posture, as_of, provenance,
        ) = found[0]

        declared = connection.execute(
            f"SELECT {declaration_columns['declared_ttl_seconds']},"
            f" {declaration_columns['declared_latency_ms']},"
            f" ({declaration_columns['attestation']} IS NOT NULL)"
            f" FROM {schema}.{relational['declaration_table']}"
            f" WHERE {declaration_columns['counterparty']} = %s"
            f" AND {declaration_columns['product_id']} LIKE %s",
            (lei, f"%/{facility_id}/%"),
        ).fetchall()

    # NO DECLARATION AT ALL is not the same as a declaration with no
    # attestation, and neither is collapsed into the other: the first leaves
    # every declared figure `None`, the second carries the figures and says
    # the attestation is absent. Both are unattested, and the policy operator
    # treats them the same — but the RECORD can tell them apart.
    ttl_seconds, latency_ms, attested = declared[0] if declared else (None, None, False)
    return Position(
        position_id=str(position_id),
        counterparty_lei=str(counterparty),
        facility_id=str(facility),
        share_usd=share_usd,
        band_low=band_low,
        band_high=band_high,
        internal_rating=None if internal_rating is None else str(internal_rating),
        workout_posture=None if workout_posture is None else str(workout_posture),
        as_of=str(as_of),
        provenance=None if provenance is None else str(provenance),
        declared_ttl_seconds=None if ttl_seconds is None else int(ttl_seconds),
        declared_latency_ms=None if latency_ms is None else int(latency_ms),
        attested=bool(attested),
    )


def acquire(
    *,
    facility_id: str,
    counterparty_lei: str,
    positions: Mapping[str, str],
    counterparties: Mapping[str, str],
) -> PeerAnswer:
    """Open both peer stores, read one position, join the member that holds it.

    Args:
        facility_id: The syndicated facility, as the caller named it.
        counterparty_lei: The member whose position is asked for.
        positions: The relational leg's settings (``dsn``, ``schema``), as the
            paved road resolved them from the environment document.
        counterparties: The graph leg's (``url``, ``ledger``), likewise. This
            module reads no environment variable itself (`D-IMPL-343`).

    Raises:
        LookupError: the facility/counterparty pair resolves to no position, or
            the member is absent from the peer's graph leg.
    """
    vocab = vocabulary()
    position = _position(
        lei=counterparty_lei, facility_id=facility_id, settings=positions, vocab=vocab
    )
    with httpx.Client(timeout=READ_TIMEOUT_SECONDS) as client:
        leg = _GraphLeg(
            url=counterparties["url"], ledger=counterparties["ledger"], client=client
        )
        member = _counterparty(lei=counterparty_lei, leg=leg, vocab=vocab)
        watermark = leg.watermark()
    return PeerAnswer(position=position, counterparty=member, ledger_watermark=watermark)
